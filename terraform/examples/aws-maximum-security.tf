#
# Example: AWS Maximum Security Deployment
# Apply this to ANY AWS organization for MAXIMUM hardening
#

terraform {
  required_version = ">= 1.0"
}

provider "aws" {
  region = "us-east-1"  # Change to your region
}

#
# Maximum Security Configuration
#

module "aws_security" {
  source = "../modules/aws"
  
  # Organization settings
  org_name    = "your-organization"  # CHANGE THIS
  environment = "production"
  aws_region  = "us-east-1"
  
  # Compliance
  compliance_standard = "all"  # or "pci-dss", "hipaa", "soc2", "gdpr"
  
  # VPC - Private by default
  create_vpc = true
  vpc_cidr   = "10.0.0.0/16"
  
  # Security Services - ALL ENABLED (Maximum Hardening)
  enable_guardduty      = true  # Threat detection
  enable_security_hub   = true  # Centralized security
  enable_cloudtrail     = true  # Audit logging
  enable_config         = true  # Configuration monitoring
  enable_waf            = true  # Web Application Firewall
  enable_encryption     = true  # Encrypt everything
  enable_vpc_flow_logs  = true  # Network monitoring
}

#
# Outputs
#

output "security_status" {
  description = "Security configuration status"
  value       = module.aws_security.security_configuration
}

output "kms_key_id" {
  description = "Master encryption key"
  value       = module.aws_security.kms_key_id
  sensitive   = true
}

output "vpc_id" {
  description = "Secure VPC ID"
  value       = module.aws_security.vpc_id
}

#
# Next Steps:
# 1. Update 'org_name' to your organization name
# 2. Run: terraform init
# 3. Run: terraform plan  (review changes)
# 4. Run: terraform apply (deploy security)
# 5. Verify: Check AWS Console for enabled services
#
