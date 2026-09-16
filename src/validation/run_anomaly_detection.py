
#!/usr/bin/env python3
"""
DataTrust — Anomaly Detection Runner
======================================
Loads clean or corrupted data and runs the anomaly detection
engine across all datasets.

Usage:
    python src/validation/run_anomaly_detection.py              # Scan clean data
    python src/validation/run_anomaly_detection.py --corrupted  # Scan corrupted data
"""

import argparse
from pathlib import Path

import pandas as pd

from anomaly_engine import AnomalyDetectionEngine


def load_data(data_dir):
    """Load all CSVs from a directory into a dict of DataFrames."""
    datasets = {}
    data_path = Path(data_dir)
    for csv_file in sorted(data_path.glob("*.csv")):
        name = csv_file.stem
        datasets[name] = pd.read_csv(csv_file)
        print(f"  Loaded {name:<15} {len(datasets[name]):>8,} rows")
    return datasets


def main():
    parser = argparse.ArgumentParser(description="Run DataTrust Anomaly Detection")
    parser.add_argument(
        "--corrupted", action="store_true",
        help="Scan corrupted data instead of clean data",
    )
    parser.add_argument(
        "--dataset", default=None,
        help="Scan a single dataset (e.g. 'transactions')",
    )
    args = parser.parse_args()

    data_dir = "data/corrupted" if args.corrupted else "data/clean"
    label = "CORRUPTED" if args.corrupted else "CLEAN"

    print("=" * 60)
    print(f"DataTrust — Anomaly Detection on {label} Data")
    print("=" * 60)

    # Load data
    print(f"\nLoading data from {data_dir}/")
    datasets = load_data(data_dir)

    # Initialize engine
    engine = AnomalyDetectionEngine()

    # Determine which datasets to scan
    if args.dataset:
        to_scan = [args.dataset]
    else:
        to_scan = list(datasets.keys())

    # Run anomaly detection
    print(f"\n{'='*60}")
    print(f"  SCANNING {len(to_scan)} DATASETS")
    print(f"{'='*60}")

    all_reports = []
    for name in to_scan:
        if name not in datasets:
            print(f"\n  Dataset '{name}' not found — skipping")
            continue

        report = engine.detect_all(datasets[name], name)
        engine.print_report(report)
        engine.save_report(report)
        all_reports.append(report)

    # Summary
    print("=" * 60)
    print("  ANOMALY DETECTION SUMMARY")
    print("=" * 60)
    print(f"\n  {'Dataset':<15} {'Health':>7} {'Total':>7} {'Crit':>6} {'High':>6} {'Med':>6} {'Low':>6}")
    print(f"  {'─'*55}")

    for r in all_reports:
        print(f"  {r.dataset_name:<15} {r.health_score:>6.1f}% "
              f"{len(r.anomalies):>7} {r.critical_count:>6} {r.high_count:>6} "
              f"{r.medium_count:>6} {r.low_count:>6}")

    total_anomalies = sum(len(r.anomalies) for r in all_reports)
    avg_health = sum(r.health_score for r in all_reports) / len(all_reports) if all_reports else 0

    print(f"  {'─'*55}")
    print(f"  {'AVERAGE':<15} {avg_health:>6.1f}% {total_anomalies:>7}")
    print(f"\n  Total anomalies detected: {total_anomalies}")
    print(f"  Average health score: {avg_health:.1f}%")

    print(f"\n{'='*60}")
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()

