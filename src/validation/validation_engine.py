
#!/usr/bin/env python3
"""
DataTrust — Validation Engine
==============================
Reads YAML data contracts and validates DataFrames against them.
Produces PASS / WARN / FAIL verdicts per check and calculates
an overall Trust Score.

Usage:
    from validation_engine import ValidationEngine
    engine = ValidationEngine("contracts/")
    results = engine.validate("transactions", df_transactions)
    engine.print_report(results)
"""

import re  # noqa: F401
import json
from datetime import datetime
from pathlib import Path

import numpy as np  # noqa: F401
import pandas as pd
import yaml


# ═══════════════════════════════════════════════════════════════
# VALIDATION RESULT CLASSES
# ═══════════════════════════════════════════════════════════════

class CheckResult:
    """Result of a single validation check."""

    def __init__(self, check_name, category, verdict, message, details=None):
        self.check_name = check_name
        self.category = category
        self.verdict = verdict  # "PASS", "WARN", "FAIL"
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "check_name": self.check_name,
            "category": self.category,
            "verdict": self.verdict,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class ValidationReport:
    """Collection of check results for a dataset."""

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.checks = []
        self.start_time = datetime.now()
        self.end_time = None

    def add(self, result):
        self.checks.append(result)

    def finalize(self):
        self.end_time = datetime.now()

    @property
    def pass_count(self):
        return sum(1 for c in self.checks if c.verdict == "PASS")

    @property
    def warn_count(self):
        return sum(1 for c in self.checks if c.verdict == "WARN")

    @property
    def fail_count(self):
        return sum(1 for c in self.checks if c.verdict == "FAIL")

    @property
    def trust_score(self):
        if not self.checks:
            return 0.0
        weights = {"PASS": 1.0, "WARN": 0.5, "FAIL": 0.0}
        total = sum(weights[c.verdict] for c in self.checks)
        return round((total / len(self.checks)) * 100, 1)

    @property
    def overall_verdict(self):
        if self.fail_count > 0:
            return "FAIL"
        if self.warn_count > 0:
            return "WARN"
        return "PASS"

    def to_dict(self):
        return {
            "dataset": self.dataset_name,
            "overall_verdict": self.overall_verdict,
            "trust_score": self.trust_score,
            "summary": {
                "total_checks": len(self.checks),
                "passed": self.pass_count,
                "warnings": self.warn_count,
                "failed": self.fail_count,
            },
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
            "checks": [c.to_dict() for c in self.checks],
        }


# ═══════════════════════════════════════════════════════════════
# VALIDATION ENGINE
# ═══════════════════════════════════════════════════════════════

class ValidationEngine:
    """Core validation engine that checks data against YAML contracts."""

    def __init__(self, contracts_dir="contracts"):
        self.contracts_dir = Path(contracts_dir)
        self.contracts = {}
        self.reference_data = {}
        self._load_contracts()

    def _load_contracts(self):
        """Load all YAML contracts from the contracts directory."""
        for filepath in self.contracts_dir.glob("*.yaml"):
            with open(filepath, "r") as f:
                contract = yaml.safe_load(f)
            name = contract.get("dataset", filepath.stem)
            self.contracts[name] = contract
            print(f"  Loaded contract: {name}")

    def register_reference(self, name, df):
        """Register a DataFrame for foreign key validation."""
        self.reference_data[name] = df

    def validate(self, dataset_name, df, file_modified_time=None):
        """Run all validations for a dataset against its contract."""
        if dataset_name not in self.contracts:
            raise ValueError(f"No contract found for '{dataset_name}'")

        contract = self.contracts[dataset_name]
        report = ValidationReport(dataset_name)

        # Run all check categories
        self._check_schema(df, contract, report)
        self._check_completeness(df, contract, report)
        self._check_uniqueness(df, contract, report)
        self._check_volume(df, contract, report)
        self._check_validity(df, contract, report)
        self._check_foreign_keys(df, contract, report)
        self._check_statistical(df, contract, report)

        if file_modified_time:
            self._check_freshness(file_modified_time, contract, report)

        report.finalize()
        return report

    # ── Schema Checks ────────────────────────────────────────

    def _check_schema(self, df, contract, report):
        """Validate column presence and types."""
        schema = contract.get("schema", {})
        expected_cols = set(schema.get("columns", {}).keys())
        actual_cols = set(df.columns)

        # Check for missing columns
        missing = expected_cols - actual_cols
        if missing:
            report.add(CheckResult(
                "schema_missing_columns", "SCHEMA", "FAIL",
                f"Missing columns: {sorted(missing)}",
                {"missing_columns": sorted(missing)},
            ))
        else:
            report.add(CheckResult(
                "schema_missing_columns", "SCHEMA", "PASS",
                "All expected columns present",
            ))

        # Check for unexpected columns
        unexpected = actual_cols - expected_cols
        if unexpected:
            report.add(CheckResult(
                "schema_unexpected_columns", "SCHEMA", "WARN",
                f"Unexpected columns found: {sorted(unexpected)}",
                {"unexpected_columns": sorted(unexpected)},
            ))
        else:
            report.add(CheckResult(
                "schema_unexpected_columns", "SCHEMA", "PASS",
                "No unexpected columns",
            ))

    # ── Completeness Checks ──────────────────────────────────

    def _check_completeness(self, df, contract, report):
        """Check for null/missing values."""
        quality = contract.get("quality_rules", {})
        completeness = quality.get("completeness", {})
        min_comp = completeness.get("min_completeness", 0.95)
        critical_cols = completeness.get("critical_columns", [])

        # Overall completeness
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        comp_ratio = 1 - (null_cells / total_cells) if total_cells > 0 else 1.0

        if comp_ratio >= min_comp:
            verdict = "PASS"
        elif comp_ratio >= min_comp - 0.05:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        report.add(CheckResult(
            "completeness_overall", "COMPLETENESS", verdict,
            f"Overall completeness: {comp_ratio:.1%} (threshold: {min_comp:.0%})",
            {"completeness": round(comp_ratio, 4), "threshold": min_comp,
             "null_cells": int(null_cells), "total_cells": total_cells},
        ))

        # Critical column completeness
        for col in critical_cols:
            if col not in df.columns:
                continue
            null_count = df[col].isnull().sum()
            col_comp = 1 - (null_count / len(df)) if len(df) > 0 else 1.0

            if null_count == 0:
                verdict = "PASS"
            elif col_comp >= 0.99:
                verdict = "WARN"
            else:
                verdict = "FAIL"

            report.add(CheckResult(
                f"completeness_{col}", "COMPLETENESS", verdict,
                f"Column '{col}': {null_count:,} nulls ({col_comp:.1%} complete)",
                {"column": col, "null_count": int(null_count),
                 "completeness": round(col_comp, 4)},
            ))

    # ── Uniqueness Checks ────────────────────────────────────

    def _check_uniqueness(self, df, contract, report):
        """Check for duplicate values in unique columns."""
        quality = contract.get("quality_rules", {})
        uniqueness = quality.get("uniqueness", {})
        unique_cols = uniqueness.get("unique_columns", [])

        for col in unique_cols:
            if col not in df.columns:
                continue
            non_null = df[col].dropna()
            dup_count = non_null.duplicated().sum()

            if dup_count == 0:
                verdict = "PASS"
                msg = f"Column '{col}': all values unique"
            else:
                verdict = "FAIL"
                msg = f"Column '{col}': {dup_count:,} duplicate values found"

            report.add(CheckResult(
                f"uniqueness_{col}", "UNIQUENESS", verdict, msg,
                {"column": col, "duplicate_count": int(dup_count)},
            ))

        # Check for exact duplicate rows
        max_dup_rate = quality.get("volume", {}).get("max_duplicate_rate", 0.01)
        dup_rows = df.duplicated().sum()
        dup_rate = dup_rows / len(df) if len(df) > 0 else 0

        if dup_rows == 0:
            verdict = "PASS"
        elif dup_rate <= max_dup_rate:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        report.add(CheckResult(
            "uniqueness_duplicate_rows", "UNIQUENESS", verdict,
            f"Duplicate rows: {dup_rows:,} ({dup_rate:.2%})",
            {"duplicate_rows": int(dup_rows), "duplicate_rate": round(dup_rate, 4),
             "threshold": max_dup_rate},
        ))

    # ── Volume Checks ────────────────────────────────────────

    def _check_volume(self, df, contract, report):
        """Check row count is within expected range."""
        quality = contract.get("quality_rules", {})
        volume = quality.get("volume", {})
        min_rows = volume.get("min_rows", 0)
        max_rows = volume.get("max_rows", float("in"))

        row_count = len(df)
        if min_rows <= row_count <= max_rows:
            verdict = "PASS"
            msg = f"Row count {row_count:,} within range [{min_rows:,}, {max_rows:,}]"
        else:
            verdict = "FAIL"
            msg = f"Row count {row_count:,} outside range [{min_rows:,}, {max_rows:,}]"

        report.add(CheckResult(
            "volume_row_count", "VOLUME", verdict, msg,
            {"row_count": row_count, "min_rows": min_rows, "max_rows": max_rows},
        ))

    # ── Validity Checks ──────────────────────────────────────

    def _check_validity(self, df, contract, report):
        """Check values against allowed values, patterns, and ranges."""
        schema = contract.get("schema", {})
        columns = schema.get("columns", {})

        for col_name, rules in columns.items():
            if col_name not in df.columns:
                continue

            series = df[col_name].dropna()
            if len(series) == 0:
                continue

            # Allowed values check
            if "allowed_values" in rules:
                allowed = set(rules["allowed_values"])
                invalid = series[~series.isin(allowed)]
                if len(invalid) == 0:
                    report.add(CheckResult(
                        f"validity_{col_name}_allowed", "VALIDITY", "PASS",
                        f"Column '{col_name}': all values in allowed set",
                    ))
                else:
                    bad_vals = invalid.unique()[:5].tolist()
                    report.add(CheckResult(
                        f"validity_{col_name}_allowed", "VALIDITY", "FAIL",
                        f"Column '{col_name}': {len(invalid):,} invalid values",
                        {"invalid_count": int(len(invalid)),
                         "sample_invalid": [str(v) for v in bad_vals]},
                    ))

            # Pattern check
            if "pattern" in rules and rules.get("type") == "string":
                pattern = rules["pattern"]
                str_series = series.astype(str)
                matches = str_series.str.match(pattern, na=False)
                invalid_count = (~matches).sum()
                if invalid_count == 0:
                    report.add(CheckResult(
                        f"validity_{col_name}_pattern", "VALIDITY", "PASS",
                        f"Column '{col_name}': all values match pattern",
                    ))
                else:
                    bad_vals = str_series[~matches].head(5).tolist()
                    report.add(CheckResult(
                        f"validity_{col_name}_pattern", "VALIDITY", "FAIL",
                        f"Column '{col_name}': {invalid_count:,} values don't match pattern",
                        {"invalid_count": int(invalid_count),
                         "pattern": pattern,
                         "sample_invalid": bad_vals},
                    ))

            # Numeric range check
            if rules.get("type") in ("numeric", "integer"):
                min_val = rules.get("min_value")
                max_val = rules.get("max_value")
                numeric_series = pd.to_numeric(series, errors="coerce").dropna()

                violations = 0
                if min_val is not None:
                    violations += (numeric_series < min_val).sum()
                if max_val is not None:
                    violations += (numeric_series > max_val).sum()

                if violations == 0:
                    report.add(CheckResult(
                        f"validity_{col_name}_range", "VALIDITY", "PASS",
                        f"Column '{col_name}': all values within range",
                    ))
                else:
                    report.add(CheckResult(
                        f"validity_{col_name}_range", "VALIDITY", "FAIL",
                        f"Column '{col_name}': {int(violations):,} values outside range [{min_val}, {max_val}]",
                        {"violations": int(violations),
                         "min_value": min_val, "max_value": max_val},
                    ))

            # Date range check
            if rules.get("type") == "date":
                min_date = rules.get("min_value")
                max_date = rules.get("max_value")
                if min_date or max_date:
                    date_series = pd.to_datetime(series, errors="coerce")
                    invalid_dates = date_series.isna().sum()
                    valid_dates = date_series.dropna()

                    violations = 0
                    if min_date and len(valid_dates) > 0:
                        violations += (valid_dates < pd.Timestamp(min_date)).sum()
                    if max_date and len(valid_dates) > 0:
                        violations += (valid_dates > pd.Timestamp(max_date)).sum()

                    total_issues = int(invalid_dates) + int(violations)
                    if total_issues == 0:
                        report.add(CheckResult(
                            f"validity_{col_name}_date_range", "VALIDITY", "PASS",
                            f"Column '{col_name}': all dates valid and in range",
                        ))
                    else:
                        verdict = "FAIL" if total_issues > 10 else "WARN"
                        report.add(CheckResult(
                            f"validity_{col_name}_date_range", "VALIDITY", verdict,
                            f"Column '{col_name}': {total_issues:,} date issues "
                            f"({int(invalid_dates)} unparseable, {int(violations)} out of range)",
                            {"unparseable": int(invalid_dates),
                             "out_of_range": int(violations)},
                        ))

    # ── Foreign Key Checks ───────────────────────────────────

    def _check_foreign_keys(self, df, contract, report):
        """Validate foreign key references exist in parent tables."""
        schema = contract.get("schema", {})
        foreign_keys = schema.get("foreign_keys", [])

        for fk in foreign_keys:
            fk_col = fk["column"]
            ref_dataset = fk["references"]["dataset"]
            ref_col = fk["references"]["column"]

            if fk_col not in df.columns:
                continue

            if ref_dataset not in self.reference_data:
                report.add(CheckResult(
                    f"fk_{fk_col}_to_{ref_dataset}", "CONSISTENCY", "WARN",
                    f"Cannot validate FK '{fk_col}' → '{ref_dataset}.{ref_col}': "
                    "reference data not registered",
                ))
                continue

            ref_df = self.reference_data[ref_dataset]
            if ref_col not in ref_df.columns:
                continue

            valid_ids = set(ref_df[ref_col].dropna().unique())
            fk_values = df[fk_col].dropna()
            orphans = fk_values[~fk_values.isin(valid_ids)]

            if len(orphans) == 0:
                report.add(CheckResult(
                    f"fk_{fk_col}_to_{ref_dataset}", "CONSISTENCY", "PASS",
                    f"FK '{fk_col}' → '{ref_dataset}.{ref_col}': all references valid",
                ))
            else:
                orphan_rate = len(orphans) / len(fk_values) if len(fk_values) > 0 else 0
                verdict = "FAIL" if orphan_rate > 0.01 else "WARN"
                sample = orphans.unique()[:5].tolist()
                report.add(CheckResult(
                    f"fk_{fk_col}_to_{ref_dataset}", "CONSISTENCY", verdict,
                    f"FK '{fk_col}' → '{ref_dataset}.{ref_col}': "
                    f"{len(orphans):,} orphan records ({orphan_rate:.2%})",
                    {"orphan_count": int(len(orphans)),
                     "orphan_rate": round(orphan_rate, 4),
                     "sample_orphans": [str(v) for v in sample]},
                ))

    # ── Statistical Checks ───────────────────────────────────

    def _check_statistical(self, df, contract, report):
        """Detect statistical anomalies (outliers) in numeric columns."""
        quality = contract.get("quality_rules", {})
        statistical = quality.get("statistical", {})

        for col_name, rules in statistical.items():
            if col_name not in df.columns:
                continue

            series = pd.to_numeric(df[col_name], errors="coerce").dropna()
            if len(series) < 10:
                continue

            # Z-score method
            z_threshold = rules.get("z_score_threshold", 4.0)
            mean = series.mean()
            std = series.std()
            if std > 0:
                z_scores = ((series - mean) / std).abs()
                z_outliers = (z_scores > z_threshold).sum()
            else:
                z_outliers = 0

            # IQR method
            iqr_mult = rules.get("iqr_multiplier", 3.0)
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - iqr_mult * iqr
            upper = q3 + iqr_mult * iqr
            iqr_outliers = ((series < lower) | (series > upper)).sum()

            total_outliers = max(int(z_outliers), int(iqr_outliers))
            outlier_rate = total_outliers / len(series)

            if outlier_rate == 0:
                verdict = "PASS"
            elif outlier_rate < 0.01:
                verdict = "WARN"
            else:
                verdict = "FAIL"

            report.add(CheckResult(
                f"statistical_{col_name}_outliers", "STATISTICAL", verdict,
                f"Column '{col_name}': {total_outliers:,} outliers detected ({outlier_rate:.2%})",
                {"z_score_outliers": int(z_outliers),
                 "iqr_outliers": int(iqr_outliers),
                 "outlier_rate": round(outlier_rate, 4),
                 "mean": round(float(mean), 2),
                 "std": round(float(std), 2)},
            ))

    # ── Freshness Check ──────────────────────────────────────

    def _check_freshness(self, file_modified_time, contract, report):
        """Check if data is stale based on file modification time."""
        quality = contract.get("quality_rules", {})
        freshness = quality.get("freshness", {})
        max_age = freshness.get("max_age_hours", 48)

        age_hours = (datetime.now() - file_modified_time).total_seconds() / 3600

        if age_hours <= max_age:
            verdict = "PASS"
        elif age_hours <= max_age * 2:
            verdict = "WARN"
        else:
            verdict = "FAIL"

        report.add(CheckResult(
            "freshness_age", "FRESHNESS", verdict,
            f"Data age: {age_hours:.1f} hours (max: {max_age} hours)",
            {"age_hours": round(age_hours, 1), "max_age_hours": max_age},
        ))

    # ── Report Printing ──────────────────────────────────────

    @staticmethod
    def print_report(report):
        """Print a formatted validation report to console."""
        verdict_icons = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗"}
        _ = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}

        print(f"\n{'='*60}")
        print(f"  VALIDATION REPORT: {report.dataset_name.upper()}")
        print(f"{'='*60}")
        print(f"  Overall Verdict:  {report.overall_verdict}")
        print(f"  Trust Score:      {report.trust_score}%")
        print(f"  Checks:           {len(report.checks)} total "
              f"({report.pass_count} pass, {report.warn_count} warn, {report.fail_count} fail)")
        print(f"{'─'*60}")

        current_category = None
        for check in report.checks:
            if check.category != current_category:
                current_category = check.category
                print(f"\n  ── {current_category} ──")

            icon = verdict_icons[check.verdict]
            print(f"    {icon} [{check.verdict}] {check.message}")

            # Print details for failures
            if check.verdict == "FAIL" and check.details:
                for key, val in check.details.items():
                    if key.startswith("sample"):
                        print(f"             └─ {key}: {val}")

        print(f"\n{'='*60}\n")

    @staticmethod
    def save_report(report, output_dir="data/reports"):
        """Save validation report as JSON."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{report.dataset_name}_validation.json"
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        print(f"  Saved report: {filepath}")
        return filepath
