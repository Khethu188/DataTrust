
#!/usr/bin/env python3
"""
DataTrust — Recovery Runner
==============================
Loads corrupted data, runs the auto-recovery engine,
saves recovered data and quarantined records, then
runs validation on the recovered data to prove it worked.

Usage:
    python run_recovery.py
    python run_recovery.py --skip-validation
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd

from recovery_engine import RecoveryEngine
from validation_engine import ValidationEngine


def load_data(data_dir):
    """Load all CSVs from a directory."""
    datasets = {}
    data_path = Path(data_dir)
    for csv_file in sorted(data_path.glob("*.csv")):
        name = csv_file.stem
        datasets[name] = pd.read_csv(csv_file)
        print(f"  Loaded {name:<15} {len(datasets[name]):>8,} rows")
    return datasets


def main():
    parser = argparse.ArgumentParser(description="Run DataTrust Auto-Recovery")
    parser.add_argument(
        "--skip-validation", action="store_true",
        help="Skip post-recovery validation",
    )
    parser.add_argument(
        "--contracts-dir", default="src/contracts",
        help="Path to contracts directory",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("DataTrust — Auto-Recovery Engine")
    print("=" * 60)

    # ── Load corrupted data ──────────────────────────────
    print("\nLoading CORRUPTED data...")
    corrupted = load_data("data/corrupted")

    # ── Load clean data as reference for FK checks ───────
    print("\nLoading CLEAN reference data...")
    clean = load_data("data/clean")

    # ── Initialize recovery engine ───────────────────────
    recovery = RecoveryEngine(contracts_dir=args.contracts_dir)

    # ── Recovery order (parents before children) ─────────
    recovery_order = [
        "customers",    # root — no FKs
        "accounts",     # FK -> customers
        "policies",     # FK -> customers
        "transactions",  # FK -> customers, accounts
        "claims",       # FK -> policies, customers
        "payments",     # FK -> customers, accounts, policies
    ]

    # ── Run recovery ─────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RUNNING RECOVERY")
    print(f"{'='*60}")

    recovered_data = {}
    all_quarantine = {}
    all_reports = []

    for name in recovery_order:
        if name not in corrupted:
            continue

        # Use already-recovered parent tables as reference
        reference = {}
        for ref_name in recovered_data:
            reference[ref_name] = recovered_data[ref_name]
        # Also include clean data as fallback reference
        for ref_name in clean:
            if ref_name not in reference:
                reference[ref_name] = clean[ref_name]

        df_recovered, quarantine, report = recovery.recover(
            name, corrupted[name], reference
        )

        recovery.print_report(report)
        recovery.save_report(report)

        recovered_data[name] = df_recovered
        if len(quarantine) > 0:
            all_quarantine[name] = quarantine
        all_reports.append(report)

    # ── Save recovered data ──────────────────────────────
    recovered_dir = Path("data/recovered")
    recovered_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print("  SAVING RECOVERED DATA")
    print(f"{'='*60}")

    for name, df in recovered_data.items():
        filepath = recovered_dir / f"{name}.csv"
        df.to_csv(filepath, index=False)
        print(f"  Saved {filepath}  ({len(df):,} rows)")

    # ── Save quarantined records ─────────────────────────
    quarantine_dir = Path("data/quarantine")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    print("\nSaving quarantined records...")
    total_quarantined = 0
    for name, df in all_quarantine.items():
        filepath = quarantine_dir / f"{name}_quarantine.csv"
        df.to_csv(filepath, index=False)
        total_quarantined += len(df)
        print(f"  Saved {filepath}  ({len(df):,} rows)")

    if total_quarantined == 0:
        print("  No records quarantined")

    # ── Before/After Comparison ──────────────────────────
    print(f"\n{'='*60}")
    print("  BEFORE / AFTER COMPARISON")
    print(f"{'='*60}")
    print(f"\n  {'Dataset':<15} {'Corrupted':>10} {'Recovered':>10} {'Quarantine':>11} {'Recovery':>10}")
    print(f"  {'─'*56}")

    for name in recovery_order:
        if name not in corrupted:
            continue
        before = len(corrupted[name])
        after = len(recovered_data.get(name, pd.DataFrame()))
        quarantined = len(all_quarantine.get(name, pd.DataFrame()))
        rate = (after / before * 100) if before > 0 else 0
        print(f"  {name:<15} {before:>10,} {after:>10,} {quarantined:>11,} {rate:>9.1f}%")

    total_before = sum(len(corrupted[n]) for n in recovery_order if n in corrupted)
    total_after = sum(len(recovered_data.get(n, pd.DataFrame())) for n in recovery_order if n in corrupted)
    total_q = sum(len(all_quarantine.get(n, pd.DataFrame())) for n in recovery_order)
    total_rate = (total_after / total_before * 100) if total_before > 0 else 0

    print(f"  {'─'*56}")
    print(f"  {'TOTAL':<15} {total_before:>10,} {total_after:>10,} {total_q:>11,} {total_rate:>9.1f}%")

    # ── Post-Recovery Validation ─────────────────────────
    if not args.skip_validation:
        print(f"\n{'='*60}")
        print("  POST-RECOVERY VALIDATION")
        print(f"{'='*60}")

        validator = ValidationEngine(args.contracts_dir)
        for name, df in recovered_data.items():
            validator.register_reference(name, df)

        val_reports = []
        for name in recovery_order:
            if name not in recovered_data:
                continue
            file_path = recovered_dir / f"{name}.csv"
            file_mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            val_report = validator.validate(name, recovered_data[name], file_mod_time)
            validator.print_report(val_report)
            val_reports.append(val_report)

        # Validation summary
        print(f"\n{'='*60}")
        print("  VALIDATION COMPARISON: CORRUPTED vs RECOVERED")
        print(f"{'='*60}")
        print(f"\n  {'Dataset':<15} {'Recovered Trust Score':>22}")
        print(f"  {'─'*40}")
        for r in val_reports:
            print(f"  {r.dataset_name:<15} {r.trust_score:>21.1f}%")
        avg = sum(r.trust_score for r in val_reports) / len(val_reports) if val_reports else 0
        print(f"  {'─'*40}")
        print(f"  {'AVERAGE':<15} {avg:>21.1f}%")

    # ── Final Summary ────────────────────────────────────
    print(f"\n{'='*60}")
    print("  RECOVERY SUMMARY")
    print(f"{'='*60}")
    total_actions = sum(len(r.actions) for r in all_reports)
    total_fixed = sum(r.total_rows_fixed for r in all_reports)
    print(f"  Total recovery actions:  {total_actions}")
    print(f"  Total rows fixed:        {total_fixed:,}")
    print(f"  Total rows quarantined:  {total_quarantined:,}")
    print(f"  Overall recovery rate:   {total_rate:.1f}%")

    print(f"\n{'='*60}")
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()
