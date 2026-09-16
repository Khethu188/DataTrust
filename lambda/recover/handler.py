"""DataTrust — Recovery Lambda Handler."""

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
    """Run auto-recovery on corrupted datasets."""
    print(f"Event: {json.dumps(event)}")

    corrupted = load_datasets("raw/corrupted/")
    if not corrupted:
        return {"stage": "recovery", "message": "No corrupted data found"}

    results = {}
    total_recovered = 0
    total_quarantined = 0

    for name, df in corrupted.items():
        original_len = len(df)
        df_recovered, quarantine = recover_dataset(df)

        total_recovered += len(df_recovered)
        total_quarantined += len(quarantine)

        # Save recovered
        save_csv(df_recovered, f"processed/recovered/{name}.csv")
        if len(quarantine) > 0:
            save_csv(quarantine, f"processed/quarantine/{name}_quarantine.csv")

        rate = (len(df_recovered) / max(original_len, 1)) * 100
        results[name] = {
            "input_rows": original_len,
            "recovered_rows": len(df_recovered),
            "quarantined_rows": len(quarantine),
            "recovery_rate": round(rate, 1),
        }

    overall_rate = (total_recovered / max(total_recovered + total_quarantined, 1)) * 100

    if SNS_TOPIC:
        sns.publish(
            _ = SNS_TOPIC,
            _ = f"DataTrust Recovery: {overall_rate:.1f}%",
            _ = f"Recovered: {total_recovered:,} rows, Quarantined: {total_quarantined:,}",
        )

    return {
        "stage": "recovery",
        "timestamp": datetime.now().isoformat(),
        "total_recovered": total_recovered,
        "total_quarantined": total_quarantined,
        "overall_recovery_rate": round(overall_rate, 1),
        "results": results,
    }


def load_datasets(prefix):
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
            s3.download_file(BUCKET, key, tmp.name)
            datasets[name] = pd.read_csv(tmp.name)
    return datasets


def recover_dataset(df):
    quarantine_mask = pd.Series(False, index=df.index)

    # Fix nulls
    for col in df.columns:
        if df[col].isnull().mean() > 0.5:
            quarantine_mask |= df[col].isnull()
        elif df[col].dtype in ["float64", "int64"]:
            df[col].fillna(df[col].median(), inplace=True)
        else:
            df[col].fillna(df[col].mode().iloc[0] if len(df[col].mode()) > 0 else "UNKNOWN", inplace=True)

    # Remove duplicates
    df = df.drop_duplicates()

    # Clamp negative amounts
    for col in df.select_dtypes(include=[np.number]).columns:
        if "amount" in col.lower() or "balance" in col.lower() or "premium" in col.lower():
            neg_mask = df[col] < 0
            df.loc[neg_mask, col] = df[col].abs()

    quarantine = df[quarantine_mask].copy()
    recovered = df[~quarantine_mask].copy()

    return recovered, quarantine


def save_csv(df, key):
    tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    df.to_csv(tmp.name, index=False)
    s3.upload_file(tmp.name, BUCKET, key)
