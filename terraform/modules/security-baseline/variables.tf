#
# Universal Security Baseline Variables
#

variable "environment" {
  description = "Environment name (production, staging, development)"
  type        = string
  default     = "production"
  
  validation {
    condition     = contains(["production", "staging", "development"], var.environment)
    error_message = "Environment must be production, staging, or development."
  }
}

variable "org_name" {
  description = "Organization name"
  type        = string
}

variable "security_level" {
  description = "Security level (maximum, high, medium)"
  type        = string
  default     = "maximum"
  
  validation {
    condition     = contains(["maximum", "high", "medium"], var.security_level)
    error_message = "Security level must be maximum, high, or medium."
  }
}

variable "compliance_standard" {
  description = "Compliance standard (pci-dss, hipaa, soc2, gdpr, all)"
  type        = string
  default     = "all"
}

# Network Security
variable "private_networks_only" {
  description = "Use private networks only (no public access)"
  type        = bool
  default     = true
}

variable "disable_public_access" {
  description = "Disable all public access"
  type        = bool
  default     = true
}

# IAM Security
variable "require_mfa" {
  description = "Require MFA for all users"
  type        = bool
  default     = true
}

variable "credential_rotation_days" {
  description = "Days before credential rotation required"
  type        = number
  default     = 90
}

# Encryption
variable "customer_managed_keys" {
  description = "Use customer-managed encryption keys"
  type        = bool
  default     = true
}

variable "key_rotation_enabled" {
  description = "Enable automatic key rotation"
  type        = bool
  default     = true
}

# Monitoring & Detection
variable "enable_threat_detection" {
  description = "Enable threat detection"
  type        = bool
  default     = true
}

variable "enable_anomaly_detection" {
  description = "Enable anomaly detection"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention period in days"
  type        = number
  default     = 365
}

# Zero-Day Protection
variable "enable_waf" {
  description = "Enable Web Application Firewall"
  type        = bool
  default     = true
}

variable "enable_ids_ips" {
  description = "Enable Intrusion Detection/Prevention System"
  type        = bool
  default     = true
}

variable "enable_vulnerability_scanning" {
  description = "Enable continuous vulnerability scanning"
  type        = bool
  default     = true
}
