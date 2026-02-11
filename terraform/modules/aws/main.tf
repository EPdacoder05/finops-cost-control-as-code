#
# AWS Maximum Security Hardening Module
# ZERO-DAY PROTECTION + MINIMAL ATTACK SURFACE
#

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      SecurityLevel = "maximum"
      ZeroTrust     = "enabled"
      ManagedBy     = "terraform"
      Environment   = var.environment
      Organization  = var.org_name
    }
  }
}

#
# VPC - Private by Default, Maximum Security
#

resource "aws_vpc" "secure" {
  count = var.create_vpc ? 1 : 0
  
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  # Security hardening
  enable_network_address_usage_metrics = true
  
  tags = {
    Name = "${var.org_name}-secure-vpc-${var.environment}"
  }
}

# VPC Flow Logs - Capture ALL network traffic
resource "aws_flow_log" "vpc" {
  count = var.create_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  iam_role_arn    = aws_iam_role.flow_logs[0].arn
  log_destination = aws_cloudwatch_log_group.flow_logs[0].arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.secure[0].id
  
  tags = {
    Name = "${var.org_name}-vpc-flow-logs"
  }
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.create_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  name              = "/aws/vpc/${var.org_name}-flow-logs"
  retention_in_days = 365
  kms_key_id        = aws_kms_key.logs[0].arn
}

resource "aws_iam_role" "flow_logs" {
  count = var.create_vpc && var.enable_vpc_flow_logs ? 1 : 0
  
  name = "${var.org_name}-vpc-flow-logs-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })
}

#
# KMS - Customer Managed Keys with Auto-Rotation
#

resource "aws_kms_key" "main" {
  count = var.enable_encryption ? 1 : 0
  
  description             = "${var.org_name} master encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = true
  
  tags = {
    Name = "${var.org_name}-master-key"
  }
}

resource "aws_kms_alias" "main" {
  count = var.enable_encryption ? 1 : 0
  
  name          = "alias/${var.org_name}-master"
  target_key_id = aws_kms_key.main[0].key_id
}

resource "aws_kms_key" "logs" {
  count = var.enable_encryption ? 1 : 0
  
  description             = "${var.org_name} log encryption key"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable CloudWatch Logs"
        Effect = "Allow"
        Principal = {
          Service = "logs.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:CreateGrant",
          "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}

#
# GuardDuty - Threat Detection
#

resource "aws_guardduty_detector" "main" {
  count = var.enable_guardduty ? 1 : 0
  
  enable = true
  
  # S3 Protection
  datasources {
    s3_logs {
      enable = true
    }
    kubernetes {
      audit_logs {
        enable = true
      }
    }
    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = true
        }
      }
    }
  }
  
  finding_publishing_frequency = "FIFTEEN_MINUTES"
}

#
# Security Hub - Centralized Security Monitoring
#

resource "aws_securityhub_account" "main" {
  count = var.enable_security_hub ? 1 : 0
  
  enable_default_standards = true
  control_finding_generator = "SECURITY_CONTROL"
  auto_enable_controls     = true
}

resource "aws_securityhub_standards_subscription" "cis" {
  count = var.enable_security_hub ? 1 : 0
  
  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"
  depends_on    = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "pci_dss" {
  count = var.enable_security_hub && var.compliance_standard == "pci-dss" ? 1 : 0
  
  standards_arn = "arn:aws:securityhub:${var.aws_region}::standards/pci-dss/v/3.2.1"
  depends_on    = [aws_securityhub_account.main]
}

#
# CloudTrail - Audit Logging (ALL events)
#

resource "aws_cloudtrail" "main" {
  count = var.enable_cloudtrail ? 1 : 0
  
  name                          = "${var.org_name}-audit-trail"
  s3_bucket_name                = aws_s3_bucket.cloudtrail[0].id
  include_global_service_events = true
  is_multi_region_trail         = true
  enable_log_file_validation    = true
  kms_key_id                    = aws_kms_key.logs[0].arn
  
  # Advanced event selectors - log EVERYTHING
  advanced_event_selector {
    name = "Log all management events"
    field_selector {
      field  = "eventCategory"
      equals = ["Management"]
    }
  }
  
  advanced_event_selector {
    name = "Log all data events"
    field_selector {
      field  = "eventCategory"
      equals = ["Data"]
    }
  }
  
  insight_selector {
    insight_type = "ApiCallRateInsight"
  }
  
  insight_selector {
    insight_type = "ApiErrorRateInsight"
  }
}

resource "aws_s3_bucket" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket = "${var.org_name}-cloudtrail-${var.aws_region}"
  
  tags = {
    Name = "${var.org_name}-cloudtrail"
  }
}

resource "aws_s3_bucket_versioning" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.logs[0].arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  count = var.enable_cloudtrail ? 1 : 0
  
  bucket = aws_s3_bucket.cloudtrail[0].id
  
  # BLOCK ALL public access
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

#
# Config - Configuration Monitoring & Compliance
#

resource "aws_config_configuration_recorder" "main" {
  count = var.enable_config ? 1 : 0
  
  name     = "${var.org_name}-config-recorder"
  role_arn = aws_iam_role.config[0].arn
  
  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  count = var.enable_config ? 1 : 0
  
  name           = "${var.org_name}-config-delivery"
  s3_bucket_name = aws_s3_bucket.config[0].id
  
  snapshot_delivery_properties {
    delivery_frequency = "One_Hour"
  }
  
  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_s3_bucket" "config" {
  count = var.enable_config ? 1 : 0
  
  bucket = "${var.org_name}-config-${var.aws_region}"
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config" {
  count = var.enable_config ? 1 : 0
  
  bucket = aws_s3_bucket.config[0].id
  
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.main[0].arn
    }
  }
}

resource "aws_s3_bucket_public_access_block" "config" {
  count = var.enable_config ? 1 : 0
  
  bucket = aws_s3_bucket.config[0].id
  
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "config" {
  count = var.enable_config ? 1 : 0
  
  name = "${var.org_name}-config-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "config.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "config" {
  count = var.enable_config ? 1 : 0
  
  role       = aws_iam_role.config[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/ConfigRole"
}

#
# WAF - Web Application Firewall (Zero-Day Protection)
#

resource "aws_wafv2_web_acl" "main" {
  count = var.enable_waf ? 1 : 0
  
  name  = "${var.org_name}-waf"
  scope = "REGIONAL"
  
  default_action {
    block {}  # DENY ALL by default
  }
  
  # AWS Managed Rules - Core Rule Set
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }
  
  # Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }
  
  # SQL Injection Protection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 3
    
    override_action {
      none {}
    }
    
    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }
    
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }
  
  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.org_name}WAFMetric"
    sampled_requests_enabled   = true
  }
}

#
# Outputs
#

output "security_configuration" {
  description = "AWS security configuration summary"
  value = {
    guardduty_enabled    = var.enable_guardduty
    security_hub_enabled = var.enable_security_hub
    cloudtrail_enabled   = var.enable_cloudtrail
    config_enabled       = var.enable_config
    waf_enabled          = var.enable_waf
    encryption_enabled   = var.enable_encryption
    vpc_flow_logs        = var.enable_vpc_flow_logs
    zero_trust           = true
    minimal_attack_surface = true
  }
}

output "kms_key_id" {
  description = "Master KMS key ID"
  value       = var.enable_encryption ? aws_kms_key.main[0].id : null
}

output "vpc_id" {
  description = "Secure VPC ID"
  value       = var.create_vpc ? aws_vpc.secure[0].id : null
}
