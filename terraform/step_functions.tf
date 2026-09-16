# ═══════════════════════════════════════════════════════════
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
