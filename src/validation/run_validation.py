
#!/usr/bin/env python3
"""
DataTrust — Validation Runner
==============================
Loads clean or corrupted data and runs the validation engine
against all data contracts.

Usage:
    python src/validation/run_validation.py              # Validate clean data
    python src/validation/run_validation.py --corrupted  # Validate corrupted data
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from validation_engine import ValidationEngine


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
    parser = argparse.ArgumentParser(description="Run DataTrust Validation")
    parser.add_argument(
        "--corrupted", action="store_true",
        help="Validate corrupted data instead of clean data",
    )
    parser.add_argument(
        "--contracts-dir", default="contracts",
        help="Path to contracts directory",
    )
    parser.add_argument(
        "--dataset", default=None,
        help="Validate a single dataset (e.g. 'transactions')",
    )
    args = parser.parse_args()

    data_dir = "data/corrupted" if args.corrupted else "data/clean"
    label = "CORRUPTED" if args.corrupted else "CLEAN"

    print("=" * 60)
    print(f"DataTrust — Validating {label} Data")
    print("=" * 60)

    # Load data
    print(f"\nLoading data from {data_dir}/")
    datasets = load_data(data_dir)

    # Initialize engine
    print(f"\nLoading contracts from {args.contracts_dir}/")
    engine = ValidationEngine(args.contracts_dir)

    # Register all datasets as reference data for FK checks
    for name, df in datasets.items():
        engine.register_reference(name, df)

    # Determine which datasets to validate
    if args.dataset:
        to_validate = [args.dataset]
    else:
        to_validate = [name for name in datasets if name in engine.contracts]

    # Run validation
    print(f"\n{'='*60}")
    print(f"  RUNNING VALIDATION ({len(to_validate)} datasets)")
    print(f"{'='*60}")

    all_reports = []
    for name in to_validate:
        if name not in datasets:
            print(f"\n  ✗ Dataset '{name}' not found — skipping")
            continue

        file_path = Path(data_dir) / f"{name}.csv"
        file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)

        report = engine.validate(name, datasets[name], file_mod_time)
        engine.print_report(report)
        engine.save_report(report)
        all_reports.append(report)

    # Summary
    print("=" * 60)
    print("  VALIDATION SUMMARY")
    print("=" * 60)
    print(f"\n  {'Dataset':<15} {'Verdict':<10} {'Score':>7} {'Pass':>6} {'Warn':>6} {'Fail':>6}")
    print(f"  {'─'*56}")

    for r in all_reports:
        print(f"  {r.dataset_name:<15} {r.overall_verdict:<10} {r.trust_score:>6.1f}% "
              f"{r.pass_count:>6} {r.warn_count:>6} {r.fail_count:>6}")

    total_checks = sum(len(r.checks) for r in all_reports)
    total_pass = sum(r.pass_count for r in all_reports)
    total_warn = sum(r.warn_count for r in all_reports)
    total_fail = sum(r.fail_count for r in all_reports)
    avg_score = sum(r.trust_score for r in all_reports) / len(all_reports) if all_reports else 0

    print(f"  {'─'*56}")
    print(f"  {'TOTAL':<15} {'':10} {avg_score:>6.1f}% {total_pass:>6} {total_warn:>6} {total_fail:>6}")
    print(f"\n  Total checks run: {total_checks}")
    print(f"  Average trust score: {avg_score:.1f}%")

    print(f"\n{'='*60}")
    print("DONE ✓")
    print("=" * 60)


if __name__ == "__main__":
    main()
