
#!/usr/bin/env python3
"""
DataTrust — Validation Lambda Handler
========================================
Runs contract-based validation on datasets stored in S3.

Triggered by: Step Functions pipeline
Input: { "stage": "validation", "data_prefix": "raw/" }
Output: { "trust_scores": {...}, "overall_verdict": "..." }
"""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd

# Import engines (packaged in Lambda layer)
from validation_engine import ValidationEngine


# AWS clients
s3 = boto3.client("s3")
sns = boto3.client("sns")
secretsmanager = boto3.client("secretsmanager")

# Environment
BUCKET = os.environ["DATA_LAKE_BUCKET"]
CONTRACTS_PREFIX = os.environ.get("CONTRACTS_PREFIX", "contracts/")
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")
TRUST_THRESHOLD = float(os.environ.get("TRUST_THRESHOLD", "70"))


def lambda_handler(event, context):
    """Main Lambda entry point."""
    print(f"Event: {json.dumps(event)}")

    stage = event.get("stage", "validation")
    data_prefix = event.get("data_prefix", "raw/clean/")

    # Download contracts from S3
    contracts_dir = download_contracts()

    # List datasets in S3 prefix
    datasets = list_datasets(data_prefix)
    print(f"Found {len(datasets)} datasets in {data_prefix}")

    # Initialize validation engine
    engine = ValidationEngine(contracts_dir)

    # Validate each dataset
    results = {}
    all_trust_scores = {}
    overall_pass = True

    for dataset_name, s3_key in datasets.items():
        print(f"Validating: {dataset_name}")

        # Download CSV from S3
        df = download_csv(s3_key)

        # Register as reference for FK checks
        engine.register_reference(dataset_name, df)

        # Run validation
        report = engine.validate(dataset_name, df, datetime.now())

        # Store results
        trust_score = report.trust_score
        verdict = report.overall_verdict
        all_trust_scores[dataset_name] = trust_score

        results[dataset_name] = {
            "trust_score": trust_score,
            "verdict": verdict,
            "checks_passed": sum(1 for c in report.checks if c.verdict == "PASS"),
            "checks_failed": sum(1 for c in report.checks if c.verdict == "FAIL"),
            "total_checks": len(report.checks),
        }

        # Save report to S3
        report_key = f"reports/validation/{dataset_name}_validation.json"
        save_json_to_s3(report.to_dict(), report_key)

        if verdict == "FAIL":
            overall_pass = False

        # Alert if trust score below threshold
        if trust_score < TRUST_THRESHOLD and SNS_TOPIC:
            send_alert(dataset_name, trust_score, verdict)

    # Build response
    response = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "datasets_validated": len(results),
        "trust_scores": all_trust_scores,
        "overall_pass": overall_pass,
        "needs_recovery": not overall_pass,
        "results": results,
    }

    print(f"Validation complete: {json.dumps(response, default=str)}")
    return response


def download_contracts():
    """Download YAML contracts from S3 to temp directory."""
    tmpdir = tempfile.mkdtemp()
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=CONTRACTS_PREFIX)

    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".yaml") or key.endswith(".yml"):
            filename = key.split("/")[-1]
            local_path = os.path.join(tmpdir, filename)
            s3.download_file(BUCKET, key, local_path)
            print(f"Downloaded contract: {filename}")

    return tmpdir


def list_datasets(prefix):
    """List CSV datasets in an S3 prefix."""
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)

    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            datasets[name] = key

    return datasets


def download_csv(s3_key):
    """Download a CSV from S3 and return as DataFrame."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    s3.download_file(BUCKET, s3_key, tmpfile.name)
    return pd.read_csv(tmpfile.name)


def save_json_to_s3(data, key):
    """Save a JSON object to S3."""
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(data, indent=2, default=str),
        ContentType="application/json",
    )
    print(f"Saved report: s3://{BUCKET}/{key}")


def send_alert(dataset_name, trust_score, verdict):
    """Send SNS alert for low trust score."""
    message = (
        f"⚠️ DataTrust Alert — Low Trust Score\n\n"
        f"Dataset:     {dataset_name}\n"
        f"Trust Score: {trust_score:.1f}%\n"
        f"Verdict:     {verdict}\n"
        f"Threshold:   {TRUST_THRESHOLD}%\n"
        f"Timestamp:   {datetime.now().isoformat()}\n\n"
        f"Action: Auto-recovery will be triggered."
    )
    sns.publish(
        TopicArn=SNS_TOPIC,
        Subject=f"DataTrust Alert: {dataset_name} ({trust_score:.1f}%)",
        Message=message,
    )
    print(f"Alert sent for {dataset_name}")

