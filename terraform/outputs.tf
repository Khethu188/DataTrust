# ═══════════════════════════════════════════════════════════
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
