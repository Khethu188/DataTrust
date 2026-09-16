
#!/usr/bin/env python3
"""
Create all missing files — Terraform, GitHub Actions, Lambda handlers.
Run from the DataTrust project root.
"""

import os

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  Created: {path}")


print("=" * 60)
print("  Creating missing files...")
print("=" * 60)

# ═══════════════════════════════════════════════════════════
# TERRAFORM FILES
# ═══════════════════════════════════════════════════════════

write_file("terraform/main.tf", '''# ═══════════════════════════════════════════════════════════
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
''')

write_file("terraform/variables.tf", '''# ═══════════════════════════════════════════════════════════
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
''')

write_file("terraform/outputs.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — Outputs
# ═══════════════════════════════════════════════════════════

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = aws_api_gateway_deployment.main.invoke_url
}

output "dashboard_url" {
  description = "S3 static website URL for dashboard"
  value       = "http://${aws_s3_bucket.dashboard.bucket}.s3-website.${var.aws_region}.amazonaws.com"
}

output "data_lake_bucket" {
  description = "S3 data lake bucket name"
  value       = aws_s3_bucket.data_lake.id
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.main.endpoint
}

output "step_function_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.pipeline.arn
}

output "sns_topic_arn" {
  description = "SNS alert topic ARN"
  value       = aws_sns_topic.alerts.arn
}
''')

write_file("terraform/vpc.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — VPC & Networking
# ═══════════════════════════════════════════════════════════

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${var.project_name}-vpc" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"

  tags = { Name = "${var.project_name}-private-a" }
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}b"

  tags = { Name = "${var.project_name}-private-b" }
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.10.0/24"
  availability_zone       = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-public-a" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-igw" }
}

resource "aws_eip" "nat" {
  domain = "vpc"

  tags = { Name = "${var.project_name}-nat-eip" }
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public_a.id

  tags = { Name = "${var.project_name}-nat" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public-rt" }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = { Name = "${var.project_name}-private-rt" }
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_security_group" "lambda" {
  name_prefix = "${var.project_name}-lambda-"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-lambda-sg" }
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}
''')

write_file("terraform/s3.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — S3 Buckets
# ═══════════════════════════════════════════════════════════

resource "aws_s3_bucket" "data_lake" {
  bucket = "${var.project_name}-data-lake-${var.environment}"

  tags = { Name = "${var.project_name}-data-lake" }
}

resource "aws_s3_bucket_versioning" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "data_lake" {
  bucket = aws_s3_bucket.data_lake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket" "dashboard" {
  bucket = "${var.project_name}-dashboard-${var.environment}"

  tags = { Name = "${var.project_name}-dashboard" }
}

resource "aws_s3_bucket_website_configuration" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "aws_s3_bucket_policy" "dashboard" {
  bucket = aws_s3_bucket.dashboard.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.dashboard.arn}/*"
      }
    ]
  })
}
''')

write_file("terraform/rds.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — RDS PostgreSQL
# ═══════════════════════════════════════════════════════════

resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = { Name = "${var.project_name}-db-subnet" }
}

resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-db"
  engine         = "postgres"
  engine_version = "16.3"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_encrypted     = true

  db_name  = "datatrust"
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  backup_retention_period = 7
  skip_final_snapshot     = true
  deletion_protection     = false

  performance_insights_enabled = true

  tags = { Name = "${var.project_name}-db" }
}
''')

write_file("terraform/lambda.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — Lambda Functions
# ═══════════════════════════════════════════════════════════

# IAM Role for Lambda
resource "aws_iam_role" "lambda" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*",
          aws_s3_bucket.dashboard.arn,
          "${aws_s3_bucket.dashboard.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = [aws_sns_topic.alerts.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [aws_secretsmanager_secret.db_credentials.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = ["arn:aws:logs:*:*:*"]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = ["*"]
      }
    ]
  })
}

# Lambda Functions
resource "aws_lambda_function" "validate" {
  filename         = "lambda/validate.zip"
  function_name    = "${var.project_name}-validate"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory
  timeout          = var.lambda_timeout
  source_code_hash = filebase64sha256("lambda/validate.zip")

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATA_LAKE_BUCKET  = aws_s3_bucket.data_lake.id
      CONTRACTS_PREFIX  = "contracts/"
      SNS_TOPIC_ARN     = aws_sns_topic.alerts.arn
      TRUST_THRESHOLD   = "70"
    }
  }

  tags = { Name = "${var.project_name}-validate" }
}

resource "aws_lambda_function" "detect" {
  filename         = "lambda/detect.zip"
  function_name    = "${var.project_name}-detect"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory
  timeout          = var.lambda_timeout
  source_code_hash = filebase64sha256("lambda/detect.zip")

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATA_LAKE_BUCKET = aws_s3_bucket.data_lake.id
      SNS_TOPIC_ARN    = aws_sns_topic.alerts.arn
    }
  }

  tags = { Name = "${var.project_name}-detect" }
}

resource "aws_lambda_function" "recover" {
  filename         = "lambda/recover.zip"
  function_name    = "${var.project_name}-recover"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory
  timeout          = var.lambda_timeout
  source_code_hash = filebase64sha256("lambda/recover.zip")

  vpc_config {
    subnet_ids         = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_group_ids = [aws_security_group.lambda.id]
  }

  environment {
    variables = {
      DATA_LAKE_BUCKET  = aws_s3_bucket.data_lake.id
      CONTRACTS_PREFIX  = "contracts/"
      SNS_TOPIC_ARN     = aws_sns_topic.alerts.arn
    }
  }

  tags = { Name = "${var.project_name}-recover" }
}

resource "aws_lambda_function" "dashboard" {
  filename         = "lambda/dashboard.zip"
  function_name    = "${var.project_name}-dashboard"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  memory_size      = var.lambda_memory
  timeout          = var.lambda_timeout
  source_code_hash = filebase64sha256("lambda/dashboard.zip")

  environment {
    variables = {
      DATA_LAKE_BUCKET  = aws_s3_bucket.data_lake.id
      DASHBOARD_BUCKET  = aws_s3_bucket.dashboard.id
    }
  }

  tags = { Name = "${var.project_name}-dashboard" }
}
''')

write_file("terraform/step_functions.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — Step Functions Pipeline
# ═══════════════════════════════════════════════════════════

resource "aws_iam_role" "step_functions" {
  name = "${var.project_name}-sfn-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "step_functions" {
  name = "${var.project_name}-sfn-policy"
  role = aws_iam_role.step_functions.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["lambda:InvokeFunction"]
        Resource = [
          aws_lambda_function.validate.arn,
          aws_lambda_function.detect.arn,
          aws_lambda_function.recover.arn,
          aws_lambda_function.dashboard.arn
        ]
      }
    ]
  })
}

resource "aws_sfn_state_machine" "pipeline" {
  name     = "${var.project_name}-pipeline"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "DataTrust — Autonomous Data Quality Pipeline"
    StartAt = "Validate"
    States = {
      Validate = {
        Type     = "Task"
        Resource = aws_lambda_function.validate.arn
        Parameters = {
          "stage"       = "validation"
          "data_prefix" = "raw/clean/"
        }
        ResultPath = "$.validation"
        Next       = "DetectAnomalies"
        Retry = [
          {
            ErrorEquals     = ["States.TaskFailed"]
            IntervalSeconds = 30
            MaxAttempts     = 2
            BackoffRate     = 2
          }
        ]
      }
      DetectAnomalies = {
        Type     = "Task"
        Resource = aws_lambda_function.detect.arn
        Parameters = {
          "stage"       = "anomaly_detection"
          "data_prefix" = "raw/corrupted/"
        }
        ResultPath = "$.anomaly_detection"
        Next       = "NeedsRecovery"
      }
      NeedsRecovery = {
        Type = "Choice"
        Choices = [
          {
            Variable     = "$.anomaly_detection.needs_recovery"
            BooleanEquals = true
            Next         = "Recover"
          }
        ]
        Default = "GenerateDashboard"
      }
      Recover = {
        Type     = "Task"
        Resource = aws_lambda_function.recover.arn
        Parameters = {
          "stage" = "recovery"
        }
        ResultPath = "$.recovery"
        Next       = "GenerateDashboard"
      }
      GenerateDashboard = {
        Type     = "Task"
        Resource = aws_lambda_function.dashboard.arn
        Parameters = {
          "stage" = "dashboard"
        }
        ResultPath = "$.dashboard"
        End        = true
      }
    }
  })

  tags = { Name = "${var.project_name}-pipeline" }
}
''')

write_file("terraform/api_gateway.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — API Gateway
# ═══════════════════════════════════════════════════════════

resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-api"
  description = "DataTrust Pipeline API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

resource "aws_api_gateway_resource" "pipeline" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "pipeline"
}

resource "aws_api_gateway_resource" "run" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.pipeline.id
  path_part   = "run"
}

resource "aws_api_gateway_method" "run_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.run.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "step_functions" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.run.id
  http_method             = aws_api_gateway_method.run_post.http_method
  integration_http_method = "POST"
  type                    = "AWS"
  uri                     = "arn:aws:apigateway:${var.aws_region}:states:action/StartExecution"
  credentials             = aws_iam_role.api_gateway.arn

  request_templates = {
    "application/json" = jsonencode({
      input           = "$util.escapeJavaScript($input.json('$'))"
      stateMachineArn = aws_sfn_state_machine.pipeline.arn
    })
  }
}

resource "aws_api_gateway_method_response" "run_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.run.id
  http_method = aws_api_gateway_method.run_post.http_method
  status_code = "200"
}

resource "aws_api_gateway_integration_response" "run_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.run.id
  http_method = aws_api_gateway_method.run_post.http_method
  status_code = aws_api_gateway_method_response.run_200.status_code

  depends_on = [aws_api_gateway_integration.step_functions]
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  depends_on = [aws_api_gateway_integration.step_functions]

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment
}

resource "aws_iam_role" "api_gateway" {
  name = "${var.project_name}-apigw-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "api_gateway" {
  name = "${var.project_name}-apigw-policy"
  role = aws_iam_role.api_gateway.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["states:StartExecution"]
        Resource = [aws_sfn_state_machine.pipeline.arn]
      }
    ]
  })
}
''')

write_file("terraform/cloudwatch.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — CloudWatch Monitoring
# ═══════════════════════════════════════════════════════════

# Log Groups
resource "aws_cloudwatch_log_group" "validate" {
  name              = "/aws/lambda/${var.project_name}-validate"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "detect" {
  name              = "/aws/lambda/${var.project_name}-detect"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "recover" {
  name              = "/aws/lambda/${var.project_name}-recover"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "dashboard" {
  name              = "/aws/lambda/${var.project_name}-dashboard"
  retention_in_days = 30
}

# Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Lambda function errors detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.validate.function_name
  }
}

resource "aws_cloudwatch_metric_alarm" "pipeline_failed" {
  alarm_name          = "${var.project_name}-pipeline-failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Step Functions pipeline execution failed"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.pipeline.arn
  }
}

# Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-monitoring"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-validate"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-detect"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-recover"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.project_name}-dashboard"]
          ]
          period = 300
          title  = "Lambda Invocations"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-validate"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-detect"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.project_name}-recover"]
          ]
          period = 300
          title  = "Lambda Duration (ms)"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.pipeline.arn],
            ["AWS/States", "ExecutionsSucceeded", "StateMachineArn", aws_sfn_state_machine.pipeline.arn],
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.pipeline.arn]
          ]
          period = 300
          title  = "Pipeline Executions"
        }
      }
    ]
  })
}
''')

write_file("terraform/sns.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — SNS Alerts
# ═══════════════════════════════════════════════════════════

resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"

  tags = { Name = "${var.project_name}-alerts" }
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
''')

write_file("terraform/secrets.tf", '''# ═══════════════════════════════════════════════════════════
# DataTrust — Secrets Manager
# ═══════════════════════════════════════════════════════════

resource "aws_secretsmanager_secret" "db_credentials" {
  name        = "${var.project_name}/db-credentials"
  description = "DataTrust database credentials"

  tags = { Name = "${var.project_name}-db-credentials" }
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id

  secret_string = jsonencode({
    username = var.db_username
    password = var.db_password
    host     = aws_db_instance.main.address
    port     = 5432
    dbname   = "datatrust"
  })
}
''')


# ═══════════════════════════════════════════════════════════
# GITHUB ACTIONS CI/CD
# ═══════════════════════════════════════════════════════════

write_file(".github/workflows/ci.yml", '''name: DataTrust CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install flake8
      - run: flake8 src/ tests/ datatrust.py --max-line-length=120 --ignore=E501,W503 --statistics

  test:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: datatrust_test
          POSTGRES_USER: datatrust_admin
          POSTGRES_PASSWORD: datatrust_pass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: pytest tests/ -v --cov=src --cov-report=term-missing
        env:
          DB_HOST: localhost
          DB_PORT: 5432
          DB_NAME: datatrust_test
          DB_USER: datatrust_admin
          DB_PASSWORD: datatrust_pass
          PYTHONPATH: src/validation:src/data_generation:src/utils:src

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install bandit
      - run: bandit -r src/ datatrust.py --severity-level medium -ll || true

  docker:
    name: Docker Build
    runs-on: ubuntu-latest
    needs: [test, security]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v5
        with:
          context: .
          push: false
          tags: datatrust:latest

  smoke-test:
    name: Pipeline Smoke Test
    runs-on: ubuntu-latest
    needs: docker
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      - run: pip install -r requirements.txt
      - run: python src/data_generation/generate_data.py
        env:
          PYTHONPATH: src/validation:src/data_generation:src/utils:src
      - run: python datatrust.py validate
        env:
          PYTHONPATH: src/validation:src/data_generation:src/utils:src
''')


# ═══════════════════════════════════════════════════════════
# LAMBDA HANDLERS
# ═══════════════════════════════════════════════════════════

write_file("lambda/validate/handler.py", '''"""DataTrust — Validation Lambda Handler."""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ.get("DATA_LAKE_BUCKET", "")
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")
TRUST_THRESHOLD = float(os.environ.get("TRUST_THRESHOLD", "70"))


def lambda_handler(event, context):
    """Run contract-based validation on datasets in S3."""
    print(f"Event: {json.dumps(event)}")

    data_prefix = event.get("data_prefix", "raw/clean/")
    datasets = list_datasets(data_prefix)
    print(f"Found {len(datasets)} datasets")

    results = {}
    for name, key in datasets.items():
        df = download_csv(key)
        trust_score = validate_dataset(name, df)
        results[name] = {"trust_score": trust_score, "rows": len(df)}

        if trust_score < TRUST_THRESHOLD and SNS_TOPIC:
            sns.publish(
                TopicArn=SNS_TOPIC,
                Subject=f"DataTrust Alert: {name} ({trust_score:.1f}%)",
                Message=f"Trust score {trust_score:.1f}% below threshold {TRUST_THRESHOLD}%",
            )

    return {
        "stage": "validation",
        "timestamp": datetime.now().isoformat(),
        "datasets_validated": len(results),
        "results": results,
        "needs_recovery": any(r["trust_score"] < TRUST_THRESHOLD for r in results.values()),
    }


def list_datasets(prefix):
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            datasets[name] = key
    return datasets


def download_csv(s3_key):
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    s3.download_file(BUCKET, s3_key, tmp.name)
    return pd.read_csv(tmp.name)


def validate_dataset(name, df):
    total_checks = 0
    passed = 0

    # Null check
    for col in df.columns:
        total_checks += 1
        null_rate = df[col].isnull().mean()
        if null_rate < 0.05:
            passed += 1

    # Duplicate check
    total_checks += 1
    dup_rate = df.duplicated().mean()
    if dup_rate < 0.01:
        passed += 1

    return round((passed / max(total_checks, 1)) * 100, 1)
''')

write_file("lambda/detect/handler.py", '''"""DataTrust — Anomaly Detection Lambda Handler."""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd
import numpy as np

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ.get("DATA_LAKE_BUCKET", "")
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    """Run anomaly detection on datasets in S3."""
    print(f"Event: {json.dumps(event)}")

    data_prefix = event.get("data_prefix", "raw/corrupted/")
    datasets = list_datasets(data_prefix)

    results = {}
    total_anomalies = 0
    needs_recovery = False

    for name, key in datasets.items():
        df = download_csv(key)
        anomalies = detect_anomalies(df)
        total_anomalies += len(anomalies)

        health = max(0, 100 - (len(anomalies) / max(len(df), 1)) * 100)
        results[name] = {
            "health_score": round(health, 1),
            "anomalies_found": len(anomalies),
            "rows_scanned": len(df),
        }

        if len(anomalies) > 0:
            needs_recovery = True

    if total_anomalies > 0 and SNS_TOPIC:
        sns.publish(
            TopicArn=SNS_TOPIC,
            Subject=f"DataTrust: {total_anomalies} anomalies detected",
            Message=f"Total anomalies found: {total_anomalies}",
        )

    return {
        "stage": "anomaly_detection",
        "timestamp": datetime.now().isoformat(),
        "total_anomalies": total_anomalies,
        "needs_recovery": needs_recovery,
        "results": results,
    }


def list_datasets(prefix):
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            datasets[name] = key
    return datasets


def download_csv(s3_key):
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    s3.download_file(BUCKET, s3_key, tmp.name)
    return pd.read_csv(tmp.name)


def detect_anomalies(df):
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue

        mean = series.mean()
        std = series.std()
        if std == 0:
            continue

        z_scores = np.abs((series - mean) / std)
        outliers = z_scores[z_scores > 3.5]

        for idx in outliers.index:
            anomalies.append({
                "column": col,
                "row": int(idx),
                "value": float(df.loc[idx, col]),
                "z_score": float(z_scores[idx]),
                "type": "statistical_outlier",
            })

    return anomalies
''')

write_file("lambda/recover/handler.py", '''"""DataTrust — Recovery Lambda Handler."""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd
import numpy as np

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ.get("DATA_LAKE_BUCKET", "")
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    """Run auto-recovery on corrupted datasets."""
    print(f"Event: {json.dumps(event)}")

    corrupted = load_datasets("raw/corrupted/")
    if not corrupted:
        return {"stage": "recovery", "message": "No corrupted data found"}

    results = {}
    total_recovered = 0
    total_quarantined = 0

    for name, df in corrupted.items():
        original_len = len(df)
        df_recovered, quarantine = recover_dataset(df)

        total_recovered += len(df_recovered)
        total_quarantined += len(quarantine)

        # Save recovered
        save_csv(df_recovered, f"processed/recovered/{name}.csv")
        if len(quarantine) > 0:
            save_csv(quarantine, f"processed/quarantine/{name}_quarantine.csv")

        rate = (len(df_recovered) / max(original_len, 1)) * 100
        results[name] = {
            "input_rows": original_len,
            "recovered_rows": len(df_recovered),
            "quarantined_rows": len(quarantine),
            "recovery_rate": round(rate, 1),
        }

    overall_rate = (total_recovered / max(total_recovered + total_quarantined, 1)) * 100

    if SNS_TOPIC:
        sns.publish(
            TopicArn=SNS_TOPIC,
            Subject=f"DataTrust Recovery: {overall_rate:.1f}%",
            Message=f"Recovered: {total_recovered:,} rows, Quarantined: {total_quarantined:,}",
        )

    return {
        "stage": "recovery",
        "timestamp": datetime.now().isoformat(),
        "total_recovered": total_recovered,
        "total_quarantined": total_quarantined,
        "overall_recovery_rate": round(overall_rate, 1),
        "results": results,
    }


def load_datasets(prefix):
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
            s3.download_file(BUCKET, key, tmp.name)
            datasets[name] = pd.read_csv(tmp.name)
    return datasets


def recover_dataset(df):
    quarantine_mask = pd.Series(False, index=df.index)

    # Fix nulls
    for col in df.columns:
        if df[col].isnull().mean() > 0.5:
            quarantine_mask |= df[col].isnull()
        elif df[col].dtype in ["float64", "int64"]:
            df[col].fillna(df[col].median(), inplace=True)
        else:
            df[col].fillna(df[col].mode().iloc[0] if len(df[col].mode()) > 0 else "UNKNOWN", inplace=True)

    # Remove duplicates
    df = df.drop_duplicates()

    # Clamp negative amounts
    for col in df.select_dtypes(include=[np.number]).columns:
        if "amount" in col.lower() or "balance" in col.lower() or "premium" in col.lower():
            neg_mask = df[col] < 0
            df.loc[neg_mask, col] = df[col].abs()

    quarantine = df[quarantine_mask].copy()
    recovered = df[~quarantine_mask].copy()

    return recovered, quarantine


def save_csv(df, key):
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    df.to_csv(tmp.name, index=False)
    s3.upload_file(tmp.name, BUCKET, key)
''')

write_file("lambda/dashboard/handler.py", '''"""DataTrust — Dashboard Generator Lambda Handler."""

import json
import os
import tempfile
from datetime import datetime

import boto3

s3 = boto3.client("s3")

DATA_BUCKET = os.environ.get("DATA_LAKE_BUCKET", "")
DASHBOARD_BUCKET = os.environ.get("DASHBOARD_BUCKET", "")


def lambda_handler(event, context):
    """Generate HTML dashboard and upload to S3."""
    print(f"Event: {json.dumps(event)}")

    reports = download_reports()

    html = generate_dashboard(reports)

    # Upload to S3
    s3.put_object(
        Bucket=DASHBOARD_BUCKET,
        Key="index.html",
        Body=html,
        ContentType="text/html",
        CacheControl="no-cache, no-store, must-revalidate",
    )

    region = os.environ.get("AWS_REGION", "af-south-1")
    dashboard_url = f"http://{DASHBOARD_BUCKET}.s3-website.{region}.amazonaws.com"

    return {
        "stage": "dashboard",
        "timestamp": datetime.now().isoformat(),
        "dashboard_url": dashboard_url,
        "reports_processed": len(reports),
    }


def download_reports():
    reports = []
    for prefix in ["reports/validation/", "reports/anomaly/", "reports/recovery/"]:
        response = s3.list_objects_v2(Bucket=DATA_BUCKET, Prefix=prefix)
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                body = s3.get_object(Bucket=DATA_BUCKET, Key=key)["Body"].read()
                reports.append(json.loads(body))
    return reports


def generate_dashboard(reports):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>DataTrust Dashboard</title>
    <style>
        body {{ font-family: sans-serif; background: #0a0e1a; color: #f0f4ff; padding: 40px; }}
        h1 {{ text-align: center; font-size: 2.5rem; }}
        .stats {{ display: flex; gap: 20px; justify-content: center; margin: 40px 0; }}
        .card {{ background: rgba(17,24,39,0.7); border: 1px solid rgba(255,255,255,0.06);
                 border-radius: 16px; padding: 24px; text-align: center; min-width: 200px; }}
        .value {{ font-size: 2rem; font-weight: 800; color: #00ff88; }}
        .label {{ color: #8892a4; font-size: 0.85rem; margin-top: 8px; }}
        .footer {{ text-align: center; color: #8892a4; margin-top: 60px; font-size: 0.8rem; }}
    </style>
</head>
<body>
    <h1>DataTrust Dashboard</h1>
    <div class="stats">
        <div class="card">
            <div class="value">{len(reports)}</div>
            <div class="label">Reports Processed</div>
        </div>
    </div>
    <div class="footer">Generated: {timestamp}</div>
</body>
</html>"""
''')


# ═══════════════════════════════════════════════════════════
# DONE
# ═══════════════════════════════════════════════════════════

print()
print("=" * 60)
print("  ALL FILES CREATED SUCCESSFULLY!")
print("=" * 60)
print()
print("  Terraform:      11 files in terraform/")
print("  GitHub Actions:  1 file in .github/workflows/")
print("  Lambda:          4 files in lambda/")
print()
print("  Now run:")
print("    git add .")
print('    git commit -m "Add Terraform, CI/CD, Lambda handlers"')
print("    git push")
print()

