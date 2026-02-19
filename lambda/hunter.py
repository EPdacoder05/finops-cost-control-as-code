import os
import datetime
import boto3
import json
import time
import sys

# Add parent directory to path for security imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from security.input_validator import InputValidator, SecureValidator

# Validate environment variables at startup
SNS_ARN = os.getenv("SNS_TOPIC_ARN")
HOME_REGION = os.getenv("HOME_REGION", "us-east-1")

# Validate region format
if HOME_REGION and not SecureValidator.validate_aws_resource_name(HOME_REGION.replace("-", "")):
    print(f"Warning: Invalid HOME_REGION format: {HOME_REGION}")
    HOME_REGION = "us-east-1"

# Validate MAX_FREE_EBS_GB is a safe integer
try:
    MAX_FREE_EBS_GB = int(os.getenv("MAX_FREE_EBS_GB", "30"))
    if not InputValidator.validate_integer(MAX_FREE_EBS_GB, min_val=1, max_val=10000):
        print(f"Warning: Invalid MAX_FREE_EBS_GB: {MAX_FREE_EBS_GB}, using default")
        MAX_FREE_EBS_GB = 30
except (ValueError, TypeError):
    MAX_FREE_EBS_GB = 30

# clients
ec2 = boto3.client("ec2", region_name=HOME_REGION)
elbv2 = boto3.client("elbv2", region_name=HOME_REGION)
classic_elb = boto3.client("elb", region_name=HOME_REGION)
rds = boto3.client("rds", region_name=HOME_REGION)
redshift = boto3.client("redshift", region_name=HOME_REGION)
logs = boto3.client("logs", region_name=HOME_REGION)
s3 = boto3.client("s3", region_name=HOME_REGION)
sns = boto3.client("sns", region_name=HOME_REGION)

def section(title, items):
    if not items:
        return f"\n### {title}: ✅ none found"
    body = f"\n### {title}: ({len(items)})\n"
    for it in items:
        body += f"- {it}\n"
    return body

def lambda_handler(event, context):
    findings = []

    # 1) NAT Gateways
    try:
        nat_resp = ec2.describe_nat_gateways()
        nat_gws = [gw["NatGatewayId"] for gw in nat_resp.get("NatGateways", []) if gw.get("State") in ("available","pending")]
    except Exception as e:
        nat_gws = [f"ERROR: {str(e)}"]
    findings.append(section("NAT Gateways (expensive)", nat_gws))

    # 2) Elastic IPs unattached
    try:
        eips = ec2.describe_addresses().get("Addresses", [])
        unattached = [a.get("PublicIp") or a.get("AllocationId") for a in eips if not a.get("AssociationId")]
    except Exception as e:
        unattached = [f"ERROR: {str(e)}"]
    findings.append(section("Unattached Elastic IPs", unattached))

    # 3) Unattached EBS volumes (status=available)
    try:
        vols = ec2.describe_volumes(Filters=[{"Name":"status","Values":["available"]}]).get("Volumes", [])
        big_orphans = [f"{v['VolumeId']} {v['Size']}GiB" for v in vols]
        oversize = [v for v in big_orphans if int(v.split()[1].replace("GiB","")) > MAX_FREE_EBS_GB]
    except Exception as e:
        big_orphans = [f"ERROR: {str(e)}"]
        oversize = []
    findings.append(section("Unattached EBS Volumes", big_orphans))
    if oversize:
        findings.append(section(f"Unattached EBS > {MAX_FREE_EBS_GB}GiB (likely billable)", oversize))

    # 4) Load Balancers (ALB/NLB/Classic)
    lbs = []
    try:
        albs = elbv2.describe_load_balancers().get("LoadBalancers", [])
        lbs += [f"{lb.get('LoadBalancerArn')} ({lb.get('Type')})" for lb in albs]
    except Exception:
        pass
    try:
        clbs = classic_elb.describe_load_balancers().get("LoadBalancerDescriptions", [])
        lbs += [lb.get("LoadBalancerName") for lb in clbs]
    except Exception:
        pass
    findings.append(section("Load Balancers (billable)", lbs))

    # 5) RDS instances
    try:
        rds_list = [db["DBInstanceIdentifier"] for db in rds.describe_db_instances().get("DBInstances", [])]
    except Exception as e:
        rds_list = [f"ERROR: {str(e)}"]
    findings.append(section("RDS Instances (billable)", rds_list))

    # 6) Redshift clusters
    try:
        rs = redshift.describe_clusters().get("Clusters", [])
        rs_list = [c["ClusterIdentifier"] for c in rs]
    except Exception as e:
        rs_list = [f"ERROR: {str(e)}"]
    findings.append(section("Redshift Clusters (billable)", rs_list))

    # 7) CloudWatch log groups with no retention
    lgs = []
    try:
        paginator = logs.get_paginator('describe_log_groups')
        for page in paginator.paginate():
            for g in page.get("logGroups", []):
                if "retentionInDays" not in g:
                    lgs.append(g["logGroupName"])
    except Exception as e:
        lgs = [f"ERROR: {str(e)}"]
    findings.append(section("CloudWatch log groups with no retention", lgs))

    # 8) Public S3 buckets (ACL check)
    pub_buckets = []
    try:
        for b in s3.list_buckets().get("Buckets", []):
            name = b["Name"]
            try:
                acl = s3.get_bucket_acl(Bucket=name)
                grants = acl.get("Grants", [])
                if any(g.get("Grantee", {}).get("URI", "").endswith("AllUsers") or g.get("Grantee", {}).get("URI","").endswith("AuthenticatedUsers") for g in grants):
                    pub_buckets.append(name)
            except Exception:
                # ignore buckets we can't inspect (permissions)
                pass
    except Exception as e:
        pub_buckets = [f"ERROR: {str(e)}"]
    findings.append(section("Public S3 buckets (check!)", pub_buckets))

    # Compose message
    title = f"FinOps Hunter — {datetime.datetime.now(datetime.timezone.utc).isoformat()}"
    body = f"**{title}**\n" + "\n".join(findings)
    
    # Limit message size to prevent DoS
    if len(body) > 100000:
        body = body[:100000] + "\n... [Message truncated due to size]"

    # Publish to SNS
    try:
        if SNS_ARN:
            # Validate SNS ARN format before publishing
            if SecureValidator.validate_aws_resource_name(SNS_ARN.split(":")[-1]):
                sns.publish(TopicArn=SNS_ARN, Message=body, Subject="FinOps Hunter Alert")
            else:
                print(f"Invalid SNS ARN format: {SNS_ARN}")
                print(body)
        else:
            print("SNS_TOPIC_ARN not set, printing message:")
            print(body)
    except Exception as e:
        print("Failed to publish SNS:", str(e))

    return {"ok": True}
