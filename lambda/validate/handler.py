"""DataTrust — Validation Lambda Handler."""

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
                _ = SNS_TOPIC,
                _ = f"DataTrust Alert: {name} ({trust_score:.1f}%)",
                _ = f"Trust score {trust_score:.1f}% below threshold {TRUST_THRESHOLD}%",
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
