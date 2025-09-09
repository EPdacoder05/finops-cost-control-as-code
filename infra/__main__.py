import pulumi
import pulumi_aws as aws

# STACK CONFIG VARIABLES
config = pulumi.Config()
stack_name = pulumi.get_stack()

webhook_url = config.get("webhook_url") or "TODO-YOUR-WEBHOOK-URL"
home_region = config.get("home_region") or "us-east-1"
max_free_ebs_gb = config.get_int("max_free_ebs_gb") or 30

project_tags = {
    "project": "finops-cost-control",
    "env": stack_name,
    "owner": "devops-team",
    "purpose": "cost-protection"
}

# =================
# CORE INFRASTRUCTURE
# =================

# SNS Topic for All Alerts
alerts_topic = aws.sns.Topic(
    f"finopsAlerts-{stack_name}", 
    name=f"finops-alerts-{stack_name}",
    display_name="FinOps Cost Control Alerts",
    tags=project_tags
)

# =================
# IAM ROLES & POLICIES
# =================

# Unified Lambda Role (for Hunter and Guardian)
lambda_role = aws.iam.Role(
    "finopsLambdaRole",
    name=f"FinOps-Lambda-Role-{stack_name}",
    assume_role_policy="""{
      "Version": "2012-10-17",
      "Statement": [{
        "Effect": "Allow",
        "Principal": {"Service": "lambda.amazonaws.com"},
        "Action": "sts:AssumeRole"
      }]
    }""",
    tags=project_tags
)

# Attach basic Lambda execution policy
aws.iam.RolePolicyAttachment(
    "lambdaBasicExecution",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
)

# Comprehensive FinOps policy
lambda_policy = aws.iam.RolePolicy(
    "finopsLambdaPolicy",
    role=lambda_role.id,
    name=f"FinOps-Lambda-Policy-{stack_name}",
    policy=pulumi.Output.all(alerts_topic.arn).apply(
        lambda topic_arn: f"""{{
          "Version": "2012-10-17",
          "Statement": [
            {{
              "Sid": "ResourceDiscovery",
              "Effect": "Allow",
              "Action": [
                "ec2:Describe*",
                "rds:Describe*",
                "elasticloadbalancing:Describe*",
                "redshift:Describe*",
                "es:ListDomainNames",
                "es:DescribeElasticsearchDomains",
                "opensearch:ListDomainNames",
                "opensearch:DescribeDomain",
                "s3:ListAllMyBuckets",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "logs:DescribeLogGroups"
              ],
              "Resource": "*"
            }},
            {{
              "Sid": "CostMonitoring",
              "Effect": "Allow",
              "Action": [
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "cloudwatch:GetMetricData",
                "budgets:ViewBudget",
                "ce:GetUsageAndCosts",
                "ce:GetCostAndUsage"
              ],
              "Resource": "*"
            }},
            {{
              "Sid": "PreventionActions",
              "Effect": "Allow",
              "Action": [
                "ec2:StopInstances",
                "ec2:TerminateInstances",
                "rds:StopDBInstance",
                "rds:DeleteDBInstance"
              ],
              "Resource": "*",
              "Condition": {{
                "StringEquals": {{
                  "aws:RequestedRegion": "{home_region}"
                }}
              }}
            }},
            {{
              "Sid": "NotificationPublish",
              "Effect": "Allow",
              "Action": ["sns:Publish"],
              "Resource": "{topic_arn[0]}"
            }}
          ]
        }}"""
    )
)

# =================
# DETECTION LAMBDA
# =================

# Hunter Lambda (Resource Scanner)
hunter_lambda = aws.lambda_.Function(
    f"finopsHunter-{stack_name}",
    name=f"finops-hunter-{stack_name}",
    runtime="python3.11",
    role=lambda_role.arn,
    handler="hunter.handler",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../lambda")
    }),
    timeout=60,
    memory_size=256,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SNS_TOPIC_ARN": alerts_topic.arn,
            "HOME_REGION": home_region,
            "MAX_FREE_EBS_GB": str(max_free_ebs_gb),
            "STACK_NAME": stack_name
        }
    ),
    tags=project_tags
)

# =================
# PREVENTION LAMBDA
# =================

# Guardian Lambda (Real-time Prevention)
guardian_lambda = aws.lambda_.Function(
    f"finopsGuardian-{stack_name}",
    name=f"finops-guardian-{stack_name}",
    runtime="python3.11",
    role=lambda_role.arn,
    handler="guardian.handler",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../lambda")
    }),
    timeout=30,
    memory_size=128,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "SNS_TOPIC_ARN": alerts_topic.arn,
            "HOME_REGION": home_region,
            "ALLOWED_INSTANCE_TYPES": "t2.micro,t3.micro,t2.nano,t3.nano",
            "MAX_HOURLY_COST": "0.50",
            "STACK_NAME": stack_name
        }
    ),
    tags=project_tags
)

# =================
# NOTIFICATION LAMBDA
# =================

# Notifier Lambda (Multi-channel Alerts)
notifier_lambda = aws.lambda_.Function(
    f"finopsNotifier-{stack_name}",
    name=f"finops-notifier-{stack_name}",
    runtime="python3.11",
    role=lambda_role.arn,
    handler="notifier.handler",
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("../lambda")
    }),
    timeout=15,
    memory_size=128,
    environment=aws.lambda_.FunctionEnvironmentArgs(
        variables={
            "WEBHOOK_URL": webhook_url,
            "SNS_TOPIC_ARN": alerts_topic.arn,
            "DISCORD_WEBHOOK_URL": config.get("discord_webhook_url") or "",
            "SLACK_WEBHOOK_URL": config.get("slack_webhook_url") or "",
            "STACK_NAME": stack_name
        }
    ),
    tags=project_tags
)

# =================
# EVENT ORCHESTRATION
# =================

# Hunter Schedule (Every 12 hours)
hunter_schedule = aws.cloudwatch.EventRule(
    "hunterSchedule",
    name=f"finops-hunter-schedule-{stack_name}",
    description="Trigger FinOps Hunter every 12 hours",
    schedule_expression="rate(12 hours)",
    tags=project_tags
)

# Guardian Real-time Trigger (Resource Events)
guardian_events = aws.cloudwatch.EventRule(
    "guardianEvents",
    name=f"finops-guardian-events-{stack_name}",
    description="Trigger Guardian on expensive resource creation",
    event_pattern="""{
      "source": ["aws.ec2", "aws.rds"],
      "detail-type": [
        "EC2 Instance State-change Notification",
        "RDS DB Instance Event"
      ],
      "detail": {
        "state": ["running", "available", "pending"]
      }
    }""",
    tags=project_tags
)

# =================
# EVENT TARGETS & PERMISSIONS
# =================

# Hunter Schedule Target
aws.cloudwatch.EventTarget(
    "hunterTarget",
    rule=hunter_schedule.name,
    target_id="FinOpsHunterTarget",
    arn=hunter_lambda.arn
)

# Guardian Event Target
aws.cloudwatch.EventTarget(
    "guardianTarget",
    rule=guardian_events.name,
    target_id="FinOpsGuardianTarget",
    arn=guardian_lambda.arn
)

# Hunter EventBridge Permission
aws.lambda_.Permission(
    "hunterEventPermission",
    action="lambda:InvokeFunction",
    function=hunter_lambda.name,
    principal="events.amazonaws.com",
    source_arn=hunter_schedule.arn
)

# Guardian EventBridge Permission
aws.lambda_.Permission(
    "guardianEventPermission",
    action="lambda:InvokeFunction",
    function=guardian_lambda.name,
    principal="events.amazonaws.com",
    source_arn=guardian_events.arn
)

# SNS to Notifier Subscription
notifier_subscription = aws.sns.TopicSubscription(
    "notifierSubscription",
    topic=alerts_topic.arn,
    protocol="lambda",
    endpoint=notifier_lambda.arn
)

# Notifier SNS Permission
aws.lambda_.Permission(
    "notifierSnsPermission",
    action="lambda:InvokeFunction",
    function=notifier_lambda.name,
    principal="sns.amazonaws.com",
    source_arn=alerts_topic.arn
)

# =================
# COST MONITORING
# =================

# Billing Alarm ($0.01 Tripwire)
billing_alarm = aws.cloudwatch.MetricAlarm(
    "billingAlarm",
    alarm_name=f"FinOps-Billing-Guard-{stack_name}",
    alarm_description="Alert when estimated charges exceed $0.01",
    comparison_operator="GreaterThanThreshold",
    evaluation_periods=1,
    metric_name="EstimatedCharges",
    namespace="AWS/Billing",
    period=21600,  # 6 hours
    statistic="Maximum",
    threshold=0.01,
    alarm_actions=[alerts_topic.arn],
    dimensions={"Currency": "USD"},
    treat_missing_data="notBreaching",
    tags=project_tags
)

# AWS Budget (Monthly $5 Limit)
cost_budget = aws.budgets.Budget(
    "costBudget",
    name=f"FinOps-Budget-{stack_name}",
    budget_type="COST",
    limit_amount="5.00",
    limit_unit="USD",
    time_unit="MONTHLY",
    time_period_start="2025-01-01_00:00",
    cost_filters=aws.budgets.BudgetCostFilterArgs(
        services=["Amazon Elastic Compute Cloud - Compute", "Amazon Relational Database Service"]
    ),
    tags=project_tags
)

# =================
# OUTPUTS
# =================

pulumi.export("sns_topic_arn", alerts_topic.arn)
pulumi.export("hunter_lambda_name", hunter_lambda.name)
pulumi.export("guardian_lambda_name", guardian_lambda.name)
pulumi.export("notifier_lambda_name", notifier_lambda.name)
pulumi.export("billing_alarm_name", billing_alarm.alarm_name)
pulumi.export("budget_name", cost_budget.name)

pulumi.export("finops_status", {
    "stack": stack_name,
    "detection": "Hunter Lambda - Every 12h",
    "prevention": "Guardian Lambda - Real-time",
    "notification": "Multi-channel alerts",
    "budget": "$5.00/month limit",
    "billing_alarm": "$0.01 tripwire",
    "resources_deployed": "20+ AWS resources",
    "status": "🛡️ Your AWS costs are PROTECTED!"
})
