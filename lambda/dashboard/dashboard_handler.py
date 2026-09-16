
#!/usr/bin/env python3
"""
DataTrust — Dashboard Generator Lambda Handler
==================================================
Generates HTML dashboard and uploads to S3 static website.

Triggered by: Step Functions pipeline
Input: { "stage": "dashboard" }
Output: { "dashboard_url": "..." }
"""

import json
import os
import tempfile
from datetime import datetime

import boto3

from dashboard_generator import DashboardGenerator


s3 = boto3.client("s3")

DATA_BUCKET = os.environ["DATA_LAKE_BUCKET"]
DASHBOARD_BUCKET = os.environ["DASHBOARD_BUCKET"]


def lambda_handler(event, context):
    """Main Lambda entry point."""
    print(f"Event: {json.dumps(event)}")

    # Download reports from S3
    reports_dir = download_reports()

    # Generate dashboard
    generator = DashboardGenerator(reports_dir=reports_dir)
    output_path = os.path.join(tempfile.mkdtemp(), "index.html")
    generator.generate(output_path)

    print(f"Validation reports: {len(generator.validation_reports)}")
    print(f"Anomaly reports:    {len(generator.anomaly_reports)}")
    print(f"Recovery reports:   {len(generator.recovery_reports)}")

    # Upload to S3 dashboard bucket
    s3.upload_file(
        output_path,
        DASHBOARD_BUCKET,
        "index.html",
        ExtraArgs={
            "ContentType": "text/html",
            "CacheControl": "no-cache, no-store, must-revalidate",
        },
    )

    # Build dashboard URL
    region = os.environ.get("AWS_REGION", "af-south-1")
    dashboard_url = (
        f"http://{DASHBOARD_BUCKET}.s3-website.{region}.amazonaws.com"
    )

    response = {
        "stage": "dashboard",
        "timestamp": datetime.now().isoformat(),
        "dashboard_url": dashboard_url,
        "reports_processed": {
            "validation": len(generator.validation_reports),
            "anomaly": len(generator.anomaly_reports),
            "recovery": len(generator.recovery_reports),
        },
    }

    print(f"Dashboard uploaded: {dashboard_url}")
    return response


def download_reports():
    """Download all JSON reports from S3."""
    tmpdir = tempfile.mkdtemp()

    for prefix in ["reports/validation/", "reports/anomaly/", "reports/recovery/"]:
        response = s3.list_objects_v2(Bucket=DATA_BUCKET, Prefix=prefix)
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if key.endswith(".json"):
                filename = key.split("/")[-1]
                local_path = os.path.join(tmpdir, filename)
                s3.download_file(DATA_BUCKET, key, local_path)
                print(f"Downloaded: {filename}")

    return tmpdir

