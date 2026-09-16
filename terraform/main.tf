# ═══════════════════════════════════════════════════════════
# DataTrust — Terraform Main Configuration
# ═══════════════════════════════════════════════════════════

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "datatrust-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "af-south-1"
    encrypt        = true
    dynamodb_table = "datatrust-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "DataTrust"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "Khethukuthula Sabela"
    }
  }
}
