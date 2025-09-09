import pulumi
import pulumi_aws as aws

# STACK CONFIG VARIABLES
config = pulumi.Config()
stack_name = pulumi.get_stack()

webhook_url = config.get("webhook_url") or "TODO-YOUR-WEBHOOK-URL"
home_region = config.get("home_region") or "us-east-1"
max_free_ebs_gb = config.get_int("max_free_ebs_gb") or 30
enable_anomaly_detection = config.get_bool("enable_anomaly_detection") or False
enable_cur = config.get_bool("enable_cur") or False

project_tags = {
    "project": "platform",
    "env": stack_name,
}

# SNS Topic
alerts_topic = aws.sns.Topic(
    f"alertsTopic-{stack_name}", 
    name=f"finops-alerts-{stack_name}",
    tags=project_tags
)

# Hunter Lambda IAM Role & Policy
hunter_role = aws.iam.Role(
    "hunterRole",
    assume_role_policy="""{
      "Version":"2012-10-17",
      "Statement":[{
        "Effect":"Allow",
        "Principal":{"Service":"lambda.amazonaws.com"},
        "Action":"sts:AssumeRole"
      }]
    }"""
)

aws.iam.RolePolicyAttachment(
    "hunterLogsPolicy",
    role=hunter_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

hunter_policy = aws.iam.RolePolicy(
    "hunterInlinePolicy",
    role=hunter_role.id,
    policy=pulumi.Output.all(alerts_topic.arn).apply(
        lambda topic_arn: f"""{{
          "Version": "2012-10-17",
          "Statement": [
            {{
              "Effect": "Allow",
              "Action": [
                "ec2:Describe*","elasticloadbalancing:Describe*","rds:Describe*","redshift:Describe*",
                "es:ListDomainNames","es:DescribeElasticsearchDomains",
                "opensearch:ListDomainNames","opensearch:DescribeDomain",
                "s3:ListAllMyBuckets","s3:ListBucket","s3:GetBucketLocation",
                "logs:DescribeLogGroups","cloudwatch:GetMetricStatistics","cloudwatch:ListMetrics",
                "sns:Publish"
              ],
              "Resource": "*"
            }}
          ]
        }}"""
    )
)

# Hunter Lambda Function
hunter_lambda = aws.lambda_.Function(
    f"hunterLambda-{stack_name}",
    runtime="python3.11",
    role=hunter_role.arn,
    handler="hunter.handler",  # In ./lambda/hunter.py define handler
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../lambda")
    }),
    timeout=30,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SNS_TOPIC_ARN": alerts_topic.arn,
            "HOME_REGION": home_region,
            "MAX_FREE_EBS_GB": str(max_free_ebs_gb),
        }
    ),
    tags=project_tags
)

# Notifier Lambda IAM Role & Policy Attach
notifier_role = aws.iam.Role(
    "notifierRole",
    assume_role_policy="""{
      "Version":"2012-10-17",
      "Statement":[{
        "Effect":"Allow",
        "Principal":{"Service":"lambda.amazonaws.com"},
        "Action":"sts:AssumeRole"
      }]
    }"""
)

aws.iam.RolePolicyAttachment(
    "notifierLogsPolicy",
    role=notifier_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# Notifier Lambda Function
notifier_lambda = aws.lambda_.Function(
    f"notifierLambda-{stack_name}",
    runtime="python3.11",
    role=notifier_role.arn,
    handler="notifier.handler",  # handler defined in lambda
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../lambda")
    }),
    timeout=10,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "WEBHOOK_URL": webhook_url,
            "SNS_TOPIC_ARN": alerts_topic.arn,
            "DISCORD_WEBHOOK_URL": config.get("discord_webhook_url") or "",
            "SLACK_WEBHOOK_URL": config.get("slack_webhook_url") or ""
        }
    ),
    tags=project_tags
)

# SNS → Lambda Subscription
notifier_sub = aws.sns.TopicSubscription(
    "notifierSub",
    topic=alerts_topic.arn,
    protocol="lambda",
    endpoint=notifier_lambda.arn
)

aws.lambda_.Permission(
    "notifierSnsInvoke",
    action="lambda:InvokeFunction",
    function=notifier_lambda.name,
    principal="sns.amazonaws.com",
    source_arn=alerts_topic.arn
)

# EventBridge (Scheduler) for Hunter Lambda (every 12h)
# Note: provider version naming may differ; this is standard Pulumi resource
hunter_rule = aws.cloudwatch.EventRule(
    "hunterScheduleRule",
    schedule_expression="rate(12 hours)",
    tags=project_tags
)

# Hook the rule to lambda via target and permission
aws.cloudwatch.EventTarget(
    "hunterTarget",
    rule=hunter_rule.name,
    target_id="HunterLambdaTarget",
    arn=hunter_lambda.arn
)

aws.lambda_.Permission(
    "hunterEventBridgeInvoke",
    action="lambda:InvokeFunction",
    function=hunter_lambda.name,
    principal="events.amazonaws.com",
    source_arn=hunter_rule.arn
)

# CloudWatch Billing Alarm ($0.01 tripwire)
billing_alarm = aws.cloudwatch.MetricAlarm(
    "billingAlarm",
    name="Billing-Alarm-Free-Guard",           
    alarm_description="Alert when estimated charges exceed $0.01",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=1,
    metric_name="EstimatedCharges",
    namespace="AWS/Billing",
    period=21600,  # 6h
    statistic="Maximum",
    threshold=0.01,
    alarm_actions=[alerts_topic.arn],
    dimensions={"Currency": "USD"},
    tags=project_tags
)


prevention_policy = aws.organizations.Policy(
    "preventionSCP",
    name="FinOps-Cost-Prevention-SCP",
    description="Prevent expensive AWS services from being created",
    type="SERVICE_CONTROL_POLICY",
    content="""{
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "DenyExpensiveServices",
          "Effect": "Deny",
          "Action": [
            "redshift:*",
            "elasticsearch:*",
            "sagemaker:*",
            "databrew:*",
            "mwaa:*",
            "emr:*",
            "ec2:RunInstances"
          ],
          "Resource": "*",
          "Condition": {
            "ForAllValues:StringNotEquals": {
              "ec2:InstanceType": ["t2.micro", "t3.micro"]
            }
          }
        }
      ]
    }"""
)

# Optional resources (feature flags)
if enable_anomaly_detection:
    pulumi.log.info("Anomaly Detection ENABLED (define schema/resources below)")

if enable_cur:
    pulumi.log.info("CUR/Athena ENABLED (define schema/resources below)")

# Export key resource ARNs
pulumi.export("sns_topic_arn", alerts_topic.arn)
pulumi.export("hunter_lambda_name", hunter_lambda.name)
pulumi.export("notifier_lambda_name", notifier_lambda.name)
pulumi.export("billing_alarm_name", billing_alarm.name)
