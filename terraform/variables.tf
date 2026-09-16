# ═══════════════════════════════════════════════════════════
# DataTrust — Variables
# ═══════════════════════════════════════════════════════════

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "af-south-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "datatrust"
}

variable "db_username" {
  description = "Database master username"
  type        = string
  default     = "datatrust_admin"
  sensitive   = true
}

variable "db_password" {
  description = "Database master password"
  type        = string
  sensitive   = true
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "alert_email" {
  description = "Email for SNS alerts"
  type        = string
  default     = "khethukuthula.sabela@outlook.com"
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}
