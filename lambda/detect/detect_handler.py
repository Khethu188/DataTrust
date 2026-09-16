
#!/usr/bin/env python3
"""
DataTrust — Anomaly Detection Lambda Handler
================================================
Runs ML-powered anomaly detection on datasets in S3.

Triggered by: Step Functions pipeline
Input: { "stage": "anomaly_detection", "data_prefix": "raw/" }
Output: { "total_anomalies": N, "health_scores": {...}, "needs_recovery": bool }
"""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd

from anomaly_engine import AnomalyDetectionEngine


s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ["DATA_LAKE_BUCKET"]
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    """Main Lambda entry point."""
    print(f"Event: {json.dumps(event)}")

    stage = event.get("stage", "anomaly_detection")
    data_prefix = event.get("data_prefix", "raw/corrupted/")

    # List datasets
    datasets = list_datasets(data_prefix)
    print(f"Found {len(datasets)} datasets in {data_prefix}")

    # Initialize engine with config
    config = {
        "z_score_threshold": 3.5,
        "iqr_multiplier": 2.5,
        "isolation_forest": {
            "contamination": 0.05,
            "n_estimators": 100,
            "random_state": 42,
        },
        "severity_thresholds": {
            "critical_rate": 0.05,
            "high_rate": 0.02,
            "medium_rate": 0.01,
        },
    }
    engine = AnomalyDetectionEngine(config)

    # Detect anomalies in each dataset
    results = {}
    health_scores = {}
    total_anomalies = 0
    needs_recovery = False

    for dataset_name, s3_key in datasets.items():
        print(f"Scanning: {dataset_name}")

        df = download_csv(s3_key)
        report = engine.detect_all(df, dataset_name)

        health_scores[dataset_name] = report.health_score
        total_anomalies += len(report.anomalies)

        results[dataset_name] = {
            "health_score": report.health_score,
            "anomalies_found": len(report.anomalies),
            "critical": report.critical_count,
            "high": report.high_count,
            "medium": report.medium_count,
            "low": report.low_count,
            "rows_scanned": report.rows_scanned,
        }

        # Save report to S3
        report_key = f"reports/anomaly/{dataset_name}_anomalies.json"
        save_json_to_s3(report.to_dict(), report_key)

        # Flag for recovery if critical anomalies found
        if report.critical_count > 0 or report.high_count > 0:
            needs_recovery = True

    # Alert if anomalies detected
    if total_anomalies > 0 and SNS_TOPIC:
        send_anomaly_alert(total_anomalies, health_scores)

    response = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "datasets_scanned": len(results),
        "total_anomalies": total_anomalies,
        "health_scores": health_scores,
        "needs_recovery": needs_recovery,
        "results": results,
    }

    print(f"Anomaly detection complete: {json.dumps(response, default=str)}")
    return response


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
    """Download CSV from S3."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    s3.download_file(BUCKET, s3_key, tmpfile.name)
    return pd.read_csv(tmpfile.name)


def save_json_to_s3(data, key):
    """Save JSON to S3."""
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        _ = json.dumps(data, indent=2, default=str),
        _ = "application/json",
    )


def send_anomaly_alert(total, health_scores):
    """Send SNS alert for detected anomalies."""
    scores_text = "\n".join(
        f"  {name}: {score:.1f}%" for name, score in health_scores.items()
    )
    message = (
        "🔍 DataTrust — Anomalies Detected\n\n"
        f"Total anomalies: {total}\n\n"
        f"Health Scores:\n{scores_text}\n\n"
        f"Timestamp: {datetime.now().isoformat()}\n"
        "Action: Auto-recovery will be triggered."
    )
    sns.publish(
        _ = SNS_TOPIC,
        _ = f"DataTrust: {total} anomalies detected",
        _ = message,
    )
