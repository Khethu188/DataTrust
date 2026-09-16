
#!/usr/bin/env python3
"""
DataTrust — Auto-Recovery Engine
==================================
Automatically repairs data quality issues detected by the
validation and anomaly detection engines.

Recovery strategies:
  - Deduplication (exact + key-based)
  - Null imputation (mode, median, forward-fill)
  - Outlier capping (winsorization)
  - Foreign key repair (remap or quarantine)
  - Invalid value correction
  - Quarantine system for unfixable records

Usage:
    from recovery_engine import RecoveryEngine
    engine = RecoveryEngine(contracts_dir="src/contracts")
    _ = engine.recover("transactions", df, reference_data)
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd
import yaml


# ═══════════════════════════════════════════════════════════════
# RECOVERY ACTION CLASSES
# ═══════════════════════════════════════════════════════════════

class RecoveryAction:
    """Records a single recovery action taken on the data."""

    def __init__(self, action_type, column, description,
                 rows_affected=0, strategy="", details=None):
        self.action_type = action_type
        self.column = column
        self.description = description
        self.rows_affected = rows_affected
        self.strategy = strategy
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "action_type": self.action_type,
            "column": self.column,
            "description": self.description,
            "rows_affected": self.rows_affected,
            "strategy": self.strategy,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class RecoveryReport:
    """Full report of all recovery actions for a dataset."""

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.actions = []
        self.quarantined_rows = 0
        self.rows_before = 0
        self.rows_after = 0
        self.start_time = datetime.now()
        self.end_time = None

    def add(self, action):
        self.actions.append(action)

    def finalize(self, rows_before, rows_after, quarantined):
        self.rows_before = rows_before
        self.rows_after = rows_after
        self.quarantined_rows = quarantined
        self.end_time = datetime.now()

    @property
    def total_rows_fixed(self):
        return sum(a.rows_affected for a in self.actions)

    @property
    def recovery_rate(self):
        if self.rows_before == 0:
            return 0.0
        return round((self.rows_after / self.rows_before) * 100, 1)

    def to_dict(self):
        return {
            "dataset": self.dataset_name,
            "rows_before": self.rows_before,
            "rows_after": self.rows_after,
            "quarantined_rows": self.quarantined_rows,
            "recovery_rate": self.recovery_rate,
            "total_actions": len(self.actions),
            "total_rows_fixed": self.total_rows_fixed,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
            "actions": [a.to_dict() for a in self.actions],
        }


# ═══════════════════════════════════════════════════════════════
# RECOVERY ENGINE
# ═══════════════════════════════════════════════════════════════

class RecoveryEngine:
    """Autonomous data recovery engine."""

    def __init__(self, contracts_dir="src/contracts"):
        self.contracts_dir = Path(contracts_dir)
        self.contracts = {}
        self._load_contracts()

    def _load_contracts(self):
        """Load YAML contracts for recovery rules."""
        for filepath in self.contracts_dir.glob("*.yaml"):
            with open(filepath, "r") as f:
                contract = yaml.safe_load(f)
            name = contract.get("dataset", filepath.stem)
            self.contracts[name] = contract

    def recover(self, dataset_name, df, reference_data=None):
        """Run full recovery pipeline on a dataset."""
        if dataset_name not in self.contracts:
            print(f"  WARNING: No contract for '{dataset_name}', using defaults")
            contract = {}
        else:
            contract = self.contracts[dataset_name]

        reference_data = reference_data or {}
        report = RecoveryReport(dataset_name)
        rows_before = len(df)

        print(f"\n  Recovering {dataset_name} ({rows_before:,} rows)...")

        # Work on a copy
        df_recovered = df.copy()
        quarantine = pd.DataFrame()

        # ── Recovery Pipeline (order matters) ────────────────
        # 1. Remove exact duplicates first
        df_recovered, quarantine = self._deduplicate_exact(
            df_recovered, quarantine, report
        )

        # 2. Remove key-based duplicates
        df_recovered, quarantine = self._deduplicate_keys(
            df_recovered, quarantine, contract, report
        )

        # 3. Fix null values
        df_recovered = self._impute_nulls(
            df_recovered, contract, report
        )

        # 4. Fix invalid categorical values
        df_recovered = self._fix_invalid_categories(
            df_recovered, contract, report
        )

        # 5. Fix negative amounts
        df_recovered = self._fix_negative_amounts(
            df_recovered, contract, report
        )

        # 6. Cap outliers (winsorization)
        df_recovered = self._cap_outliers(
            df_recovered, contract, report
        )

        # 7. Fix invalid dates
        df_recovered = self._fix_invalid_dates(
            df_recovered, contract, report
        )

        # 8. Fix foreign key violations
        df_recovered, quarantine = self._fix_foreign_keys(
            df_recovered, quarantine, contract, reference_data, report
        )

        # 9. Fix invalid currencies
        df_recovered = self._fix_invalid_currencies(
            df_recovered, contract, report
        )

        # Finalize
        report.finalize(rows_before, len(df_recovered), len(quarantine))

        return df_recovered, quarantine, report

    # ── 1. Exact Deduplication ───────────────────────────────

    def _deduplicate_exact(self, df, quarantine, report):
        """Remove exact duplicate rows."""
        dupes = df.duplicated(keep="first")
        dupe_count = dupes.sum()

        if dupe_count > 0:
            quarantine = pd.concat([quarantine, df[dupes].assign(
                _quarantine_reason="EXACT_DUPLICATE"
            )])
            df = df[~dupes].reset_index(drop=True)

            report.add(RecoveryAction(
                action_type="DEDUPLICATION",
                column="[all]",
                description=f"Removed {dupe_count:,} exact duplicate rows",
                rows_affected=int(dupe_count),
                strategy="keep_first",
            ))
            print(f"    [DEDUP] Removed {dupe_count:,} exact duplicates")

        return df, quarantine

    # ── 2. Key-Based Deduplication ───────────────────────────

    def _deduplicate_keys(self, df, quarantine, contract, report):
        """Remove duplicates based on primary key column."""
        schema = contract.get("schema", {})
        pk = schema.get("primary_key")

        if not pk or pk not in df.columns:
            return df, quarantine

        dupes = df.duplicated(subset=[pk], keep="first")
        dupe_count = dupes.sum()

        if dupe_count > 0:
            quarantine = pd.concat([quarantine, df[dupes].assign(
                _quarantine_reason=f"DUPLICATE_KEY_{pk}"
            )])
            df = df[~dupes].reset_index(drop=True)

            report.add(RecoveryAction(
                action_type="DEDUPLICATION",
                column=pk,
                description=f"Removed {dupe_count:,} duplicate '{pk}' values",
                rows_affected=int(dupe_count),
                strategy="keep_first_by_key",
            ))
            print(f"    [DEDUP] Removed {dupe_count:,} duplicate keys in '{pk}'")

        return df, quarantine

    # ── 3. Null Imputation ───────────────────────────────────

    def _impute_nulls(self, df, contract, report):
        """Fill null values using appropriate strategies."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        for col_name, rules in columns.items():
            if col_name not in df.columns:
                continue

            null_count = df[col_name].isnull().sum()
            if null_count == 0:
                continue

            col_type = rules.get("type", "string")
            nullable = rules.get("nullable", True)

            # Skip if column is allowed to be null
            if nullable:
                continue

            original_nulls = null_count

            # Choose strategy based on type
            if col_type in ("numeric", "integer"):
                # Use median for numeric columns
                median_val = df[col_name].median()
                if pd.notna(median_val):
                    df[col_name] = df[col_name].fillna(median_val)
                    strategy = f"median ({median_val:.2f})"
                else:
                    df[col_name] = df[col_name].fillna(0)
                    strategy = "zero"

            elif col_type == "string":
                # Use mode for categorical, "UNKNOWN" as fallback
                allowed = rules.get("allowed_values", [])
                if allowed:
                    mode_val = df[col_name].mode()
                    if len(mode_val) > 0:
                        df[col_name] = df[col_name].fillna(mode_val.iloc[0])
                        strategy = f"mode ({mode_val.iloc[0]})"
                    else:
                        df[col_name] = df[col_name].fillna(allowed[0])
                        strategy = f"first_allowed ({allowed[0]})"
                else:
                    df[col_name] = df[col_name].fillna("UNKNOWN")
                    strategy = "UNKNOWN"

            elif col_type == "boolean":
                df[col_name] = df[col_name].fillna(False)
                strategy = "False"

            elif col_type == "date":
                # Forward fill for dates, then backfill
                df[col_name] = df[col_name].ffill().bfill()
                remaining = df[col_name].isnull().sum()
                if remaining > 0:
                    df[col_name] = df[col_name].fillna("1900-01-01")
                strategy = "forward_fill"

            else:
                continue

            fixed = original_nulls - df[col_name].isnull().sum()
            if fixed > 0:
                report.add(RecoveryAction(
                    action_type="NULL_IMPUTATION",
                    column=col_name,
                    description=f"Filled {fixed:,} nulls in '{col_name}'",
                    rows_affected=int(fixed),
                    strategy=strategy,
                ))
                print(f"    [NULL] Filled {fixed:,} nulls in '{col_name}' using {strategy}")

        return df

    # ── 4. Fix Invalid Categories ────────────────────────────

    def _fix_invalid_categories(self, df, contract, report):
        """Replace invalid categorical values with the mode."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        for col_name, rules in columns.items():
            if col_name not in df.columns:
                continue

            allowed = rules.get("allowed_values")
            if not allowed:
                continue

            allowed_set = set(allowed)
            series = df[col_name].dropna()
            invalid_mask = ~series.isin(allowed_set)
            invalid_count = invalid_mask.sum()

            if invalid_count > 0:
                # Get the most common valid value
                valid_values = series[series.isin(allowed_set)]
                if len(valid_values) > 0:
                    replacement = valid_values.mode().iloc[0]
                else:
                    replacement = allowed[0]

                # Store invalid values for audit
                invalid_vals = series[invalid_mask].unique()[:5].tolist()

                # Fix: replace invalid values
                df.loc[df[col_name].notna() & ~df[col_name].isin(allowed_set), col_name] = replacement

                report.add(RecoveryAction(
                    action_type="INVALID_CATEGORY_FIX",
                    column=col_name,
                    description=f"Fixed {invalid_count:,} invalid values in '{col_name}'",
                    rows_affected=int(invalid_count),
                    strategy=f"replace_with_mode ({replacement})",
                    details={"sample_invalid": [str(v) for v in invalid_vals]},
                ))
                print(f"    [CAT] Fixed {invalid_count:,} invalid values in '{col_name}' -> '{replacement}'")

        return df

    # ── 5. Fix Negative Amounts ──────────────────────────────

    def _fix_negative_amounts(self, df, contract, report):
        """Convert negative amounts to absolute values."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        amount_cols = [
            col for col, rules in columns.items()
            if rules.get("type") in ("numeric", "integer")
            and rules.get("min_value", -1) >= 0
            and col in df.columns
        ]

        for col in amount_cols:
            series = pd.to_numeric(df[col], errors="coerce")
            negative_mask = series < 0
            neg_count = negative_mask.sum()

            if neg_count > 0:
                df.loc[negative_mask, col] = series[negative_mask].abs()

                report.add(RecoveryAction(
                    action_type="NEGATIVE_AMOUNT_FIX",
                    column=col,
                    description=f"Converted {neg_count:,} negative values to absolute in '{col}'",
                    rows_affected=int(neg_count),
                    strategy="absolute_value",
                ))
                print(f"    [NEG] Fixed {neg_count:,} negative amounts in '{col}'")

        return df

    # ── 6. Outlier Capping (Winsorization) ───────────────────

    def _cap_outliers(self, df, contract, report):
        """Cap extreme outliers using IQR-based winsorization."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        numeric_cols = [
            col for col, rules in columns.items()
            if rules.get("type") in ("numeric", "integer")
            and col in df.columns
        ]

        for col in numeric_cols:
            series = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(series) < 20:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower = q1 - 3.0 * iqr
            upper = q3 + 3.0 * iqr

            # Get contract bounds if available
            rules = columns[col]
            min_val = rules.get("min_value")
            max_val = rules.get("max_value")

            if min_val is not None:
                lower = max(lower, min_val)
            if max_val is not None:
                upper = min(upper, max_val)

            numeric_series = pd.to_numeric(df[col], errors="coerce")
            below = (numeric_series < lower).sum()
            above = (numeric_series > upper).sum()
            total_capped = int(below) + int(above)

            if total_capped > 0:
                df[col] = numeric_series.clip(lower=lower, upper=upper)

                report.add(RecoveryAction(
                    action_type="OUTLIER_CAPPING",
                    column=col,
                    description=(
                        f"Capped {total_capped:,} outliers in '{col}' "
                        f"to [{lower:,.2f}, {upper:,.2f}]"
                    ),
                    rows_affected=total_capped,
                    strategy="iqr_winsorization",
                    details={
                        "lower_bound": round(float(lower), 2),
                        "upper_bound": round(float(upper), 2),
                        "capped_below": int(below),
                        "capped_above": int(above),
                    },
                ))
                print(f"    [CAP] Capped {total_capped:,} outliers in '{col}'")

        return df

    # ── 7. Fix Invalid Dates ─────────────────────────────────

    def _fix_invalid_dates(self, df, contract, report):
        """Fix unparseable and out-of-range dates."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        date_cols = [
            col for col, rules in columns.items()
            if rules.get("type") == "date" and col in df.columns
        ]

        for col in date_cols:
            original = df[col].copy()
            parsed = pd.to_datetime(df[col], errors="coerce")
            unparseable = parsed.isna() & original.notna()
            unparseable_count = unparseable.sum()

            rules = columns[col]
            min_date = rules.get("min_value")
            max_date = rules.get("max_value")

            out_of_range = 0
            if min_date:
                too_early = parsed < pd.Timestamp(min_date)
                out_of_range += too_early.sum()
                parsed = parsed.where(~too_early, pd.Timestamp(min_date))
            if max_date:
                too_late = parsed > pd.Timestamp(max_date)
                out_of_range += too_late.sum()
                parsed = parsed.where(~too_late, pd.Timestamp(max_date))

            # Replace unparseable with median date
            if unparseable_count > 0:
                valid_dates = parsed.dropna()
                if len(valid_dates) > 0:
                    median_date = valid_dates.sort_values().iloc[len(valid_dates) // 2]
                    parsed = parsed.fillna(median_date)

            total_fixed = int(unparseable_count) + int(out_of_range)
            if total_fixed > 0:
                df[col] = parsed.dt.strftime("%Y-%m-%d")

                report.add(RecoveryAction(
                    action_type="DATE_FIX",
                    column=col,
                    description=(
                        f"Fixed {total_fixed:,} date issues in '{col}' "
                        f"({int(unparseable_count)} unparseable, {int(out_of_range)} out of range)"
                    ),
                    rows_affected=total_fixed,
                    strategy="median_replace_and_clamp",
                ))
                print(f"    [DATE] Fixed {total_fixed:,} date issues in '{col}'")

        return df

    # ── 8. Foreign Key Repair ────────────────────────────────

    def _fix_foreign_keys(self, df, quarantine, contract, reference_data, report):
        """Fix or quarantine records with broken foreign keys."""
        schema = contract.get("schema", {})
        foreign_keys = schema.get("foreign_keys", [])

        for fk in foreign_keys:
            fk_col = fk["column"]
            ref_dataset = fk["references"]["dataset"]
            ref_col = fk["references"]["column"]

            if fk_col not in df.columns:
                continue
            if ref_dataset not in reference_data:
                continue

            ref_df = reference_data[ref_dataset]
            if ref_col not in ref_df.columns:
                continue

            valid_ids = set(ref_df[ref_col].dropna().unique())
            orphan_mask = df[fk_col].notna() & ~df[fk_col].isin(valid_ids)
            orphan_count = orphan_mask.sum()

            if orphan_count > 0:
                # Quarantine orphan records
                quarantine = pd.concat([quarantine, df[orphan_mask].assign(
                    _quarantine_reason=f"BROKEN_FK_{fk_col}_to_{ref_dataset}"
                )])
                df = df[~orphan_mask].reset_index(drop=True)

                report.add(RecoveryAction(
                    action_type="FOREIGN_KEY_QUARANTINE",
                    column=fk_col,
                    description=(
                        f"Quarantined {orphan_count:,} records with broken FK "
                        f"'{fk_col}' -> '{ref_dataset}.{ref_col}'"
                    ),
                    rows_affected=int(orphan_count),
                    strategy="quarantine_orphans",
                ))
                print(f"    [FK] Quarantined {orphan_count:,} orphan records ({fk_col} -> {ref_dataset})")

        return df, quarantine

    # ── 9. Fix Invalid Currencies ────────────────────────────

    def _fix_invalid_currencies(self, df, contract, report):
        """Replace invalid currency codes with the default (ZAR)."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        for col_name, rules in columns.items():
            if col_name not in df.columns:
                continue
            if col_name != "currency":
                continue

            allowed = rules.get("allowed_values", ["ZAR"])
            allowed_set = set(allowed)
            invalid_mask = df[col_name].notna() & ~df[col_name].isin(allowed_set)
            invalid_count = invalid_mask.sum()

            if invalid_count > 0:
                invalid_vals = df.loc[invalid_mask, col_name].unique()[:5].tolist()
                df.loc[invalid_mask, col_name] = "ZAR"

                report.add(RecoveryAction(
                    action_type="CURRENCY_FIX",
                    column=col_name,
                    description=f"Fixed {invalid_count:,} invalid currencies to 'ZAR'",
                    rows_affected=int(invalid_count),
                    strategy="replace_with_default",
                    details={"invalid_values": [str(v) for v in invalid_vals]},
                ))
                print(f"    [CUR] Fixed {invalid_count:,} invalid currencies -> 'ZAR'")

        return df

    # ── Report Printing ──────────────────────────────────────

    @staticmethod
    def print_report(report):
        """Print a formatted recovery report."""
        print(f"\n{'='*60}")
        print(f"  RECOVERY REPORT: {report.dataset_name.upper()}")
        print(f"{'='*60}")
        print(f"  Rows Before:      {report.rows_before:,}")
        print(f"  Rows After:       {report.rows_after:,}")
        print(f"  Quarantined:      {report.quarantined_rows:,}")
        print(f"  Recovery Rate:    {report.recovery_rate}%")
        print(f"  Actions Taken:    {len(report.actions)}")
        print(f"  Total Rows Fixed: {report.total_rows_fixed:,}")
        print(f"{'─'*60}")

        if not report.actions:
            print("\n  No recovery actions needed — data is clean!")
        else:
            for action in report.actions:
                print(f"    [{action.action_type}] {action.description}")
                print(f"      Strategy: {action.strategy}")

        print(f"\n{'='*60}\n")

    @staticmethod
    def save_report(report, output_dir="data/reports"):
        """Save recovery report as JSON."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{report.dataset_name}_recovery.json"
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        print(f"  Saved report: {filepath}")
        return filepath
