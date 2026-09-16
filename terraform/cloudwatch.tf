# ═══════════════════════════════════════════════════════════
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
