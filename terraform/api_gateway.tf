# ═══════════════════════════════════════════════════════════
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
