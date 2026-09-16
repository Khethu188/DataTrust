# ═══════════════════════════════════════════════════════════
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
