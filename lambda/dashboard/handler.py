"""DataTrust — Dashboard Generator Lambda Handler."""

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
