"""DataTrust — Anomaly Detection Lambda Handler."""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd
import numpy as np

s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ.get("DATA_LAKE_BUCKET", "")
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")


def lambda_handler(event, context):
    """Run anomaly detection on datasets in S3."""
    print(f"Event: {json.dumps(event)}")

    data_prefix = event.get("data_prefix", "raw/corrupted/")
    datasets = list_datasets(data_prefix)

    results = {}
    total_anomalies = 0
    needs_recovery = False

    for name, key in datasets.items():
        df = download_csv(key)
        anomalies = detect_anomalies(df)
        total_anomalies += len(anomalies)

        health = max(0, 100 - (len(anomalies) / max(len(df), 1)) * 100)
        results[name] = {
            "health_score": round(health, 1),
            "anomalies_found": len(anomalies),
            "rows_scanned": len(df),
        }

        if len(anomalies) > 0:
            needs_recovery = True

    if total_anomalies > 0 and SNS_TOPIC:
        sns.publish(
            _ = SNS_TOPIC,
            _ = f"DataTrust: {total_anomalies} anomalies detected",
            _ = f"Total anomalies found: {total_anomalies}",
        )

    return {
        "stage": "anomaly_detection",
        "timestamp": datetime.now().isoformat(),
        "total_anomalies": total_anomalies,
        "needs_recovery": needs_recovery,
        "results": results,
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


def detect_anomalies(df):
    anomalies = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue

        mean = series.mean()
        std = series.std()
        if std == 0:
            continue

        z_scores = np.abs((series - mean) / std)
        outliers = z_scores[z_scores > 3.5]

        for idx in outliers.index:
            anomalies.append({
                "column": col,
                "row": int(idx),
                "value": float(df.loc[idx, col]),
                "z_score": float(z_scores[idx]),
                "type": "statistical_outlier",
            })

    return anomalies
