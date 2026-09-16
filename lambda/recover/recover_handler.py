
#!/usr/bin/env python3
"""
DataTrust — Recovery Lambda Handler
======================================
Runs auto-recovery on corrupted datasets in S3.

Triggered by: Step Functions pipeline
Input: { "stage": "recovery", "data_prefix": "raw/" }
Output: { "recovery_rate": N, "rows_recovered": N, "rows_quarantined": N }
"""

import json
import os
import tempfile
from datetime import datetime

import boto3
import pandas as pd

from recovery_engine import RecoveryEngine


s3 = boto3.client("s3")
sns = boto3.client("sns")

BUCKET = os.environ["DATA_LAKE_BUCKET"]
SNS_TOPIC = os.environ.get("SNS_TOPIC_ARN", "")

RECOVERY_ORDER = [
    "customers", "accounts", "policies",
    "transactions", "claims", "payments",
]


def lambda_handler(event, context):
    """Main Lambda entry point."""
    print(f"Event: {json.dumps(event)}")

    stage = event.get("stage", "recovery")

    # Download contracts
    contracts_dir = download_contracts()

    # Load corrupted datasets
    corrupted = load_datasets("raw/corrupted/")
    clean = load_datasets("raw/clean/")

    if not corrupted:
        return {
            "stage": stage,
            "message": "No corrupted data found",
            "needs_recovery": False,
        }

    # Initialize recovery engine
    engine = RecoveryEngine(contracts_dir)

    # Recover in dependency order
    recovered_data = {}
    all_quarantine = {}
    results = {}
    total_recovered = 0
    total_quarantined = 0

    for name in RECOVERY_ORDER:
        if name not in corrupted:
            continue

        print(f"Recovering: {name}")

        # Build reference from already-recovered + clean
        reference = {}
        for ref_name in recovered_data:
            reference[ref_name] = recovered_data[ref_name]
        for ref_name in clean:
            if ref_name not in reference:
                reference[ref_name] = clean[ref_name]

        df_recovered, quarantine, report = engine.recover(
            name, corrupted[name], reference
        )

        recovered_data[name] = df_recovered
        if len(quarantine) > 0:
            all_quarantine[name] = quarantine

        total_recovered += len(df_recovered)
        total_quarantined += len(quarantine)

        results[name] = {
            "input_rows": len(corrupted[name]),
            "recovered_rows": len(df_recovered),
            "quarantined_rows": len(quarantine),
            "recovery_rate": report.recovery_rate,
            "actions_taken": len(report.actions),
        }

        # Save report
        report_key = f"reports/recovery/{name}_recovery.json"
        save_json_to_s3(report.to_dict(), report_key)

    # Save recovered data to S3
    for name, df in recovered_data.items():
        save_csv_to_s3(df, f"processed/recovered/{name}.csv")

    # Save quarantine
    for name, df in all_quarantine.items():
        save_csv_to_s3(df, f"processed/quarantine/{name}_quarantine.csv")

    # Calculate overall recovery rate
    total_input = sum(len(corrupted[n]) for n in corrupted if n in results)
    overall_rate = (total_recovered / total_input * 100) if total_input > 0 else 0

    # Send alert
    if SNS_TOPIC:
        send_recovery_alert(results, overall_rate, total_recovered, total_quarantined)

    response = {
        "stage": stage,
        "timestamp": datetime.now().isoformat(),
        "datasets_recovered": len(results),
        "total_recovered": total_recovered,
        "total_quarantined": total_quarantined,
        "overall_recovery_rate": round(overall_rate, 1),
        "results": results,
    }

    print(f"Recovery complete: {json.dumps(response, default=str)}")
    return response


def download_contracts():
    """Download YAML contracts from S3."""
    tmpdir = tempfile.mkdtemp()
    prefix = os.environ.get("CONTRACTS_PREFIX", "contracts/")
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".yaml") or key.endswith(".yml"):
            filename = key.split("/")[-1]
            s3.download_file(BUCKET, key, os.path.join(tmpdir, filename))
    return tmpdir


def load_datasets(prefix):
    """Load all CSVs from an S3 prefix."""
    datasets = {}
    response = s3.list_objects_v2(Bucket=BUCKET, Prefix=prefix)
    for obj in response.get("Contents", []):
        key = obj["Key"]
        if key.endswith(".csv"):
            name = key.split("/")[-1].replace(".csv", "")
            datasets[name] = download_csv(key)
    return datasets


def download_csv(s3_key):
    """Download CSV from S3."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    s3.download_file(BUCKET, s3_key, tmpfile.name)
    return pd.read_csv(tmpfile.name)


def save_csv_to_s3(df, key):
    """Save DataFrame as CSV to S3."""
    tmpfile = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    df.to_csv(tmpfile.name, index=False)
    s3.upload_file(tmpfile.name, BUCKET, key)
    print(f"Saved: s3://{BUCKET}/{key} ({len(df):,} rows)")


def save_json_to_s3(data, key):
    """Save JSON to S3."""
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=json.dumps(data, indent=2, default=str),
        ContentType="application/json",
    )


def send_recovery_alert(results, rate, recovered, quarantined):
    """Send SNS recovery summary."""
    details = "\n".join(
        f"  {n}: {r['recovery_rate']:.1f}% ({r['actions_taken']} actions)"
        for n, r in results.items()
    )
    message = (
        f"🔧 DataTrust — Recovery Complete\n\n"
        f"Overall rate:  {rate:.1f}%\n"
        f"Rows recovered:    {recovered:,}\n"
        f"Rows quarantined:  {quarantined:,}\n\n"
        f"Details:\n{details}\n\n"
        f"Timestamp: {datetime.now().isoformat()}"
    )
    sns.publish(
        TopicArn=SNS_TOPIC,
        Subject=f"DataTrust Recovery: {rate:.1f}% rate",
        Message=message,
    )

