
#!/usr/bin/env python3
"""
DataTrust — Anomaly Detection Engine
======================================
ML-powered anomaly detection for financial data.
Uses statistical methods (Z-score, IQR) and machine learning
(Isolation Forest) to detect outliers, drift, and suspicious patterns.

Usage:
    from anomaly_engine import AnomalyDetectionEngine
    engine = AnomalyDetectionEngine()
    _ = engine.detect_all(df_transactions, "transactions")
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ═══════════════════════════════════════════════════════════════
# ANOMALY RESULT CLASSES
# ═══════════════════════════════════════════════════════════════

class Anomaly:
    """Represents a single detected anomaly."""

    def __init__(self, anomaly_type, severity, column, description,
                 affected_rows=0, details=None):
        self.anomaly_type = anomaly_type
        self.severity = severity  # LOW, MEDIUM, HIGH, CRITICAL
        self.column = column
        self.description = description
        self.affected_rows = affected_rows
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "anomaly_type": self.anomaly_type,
            "severity": self.severity,
            "column": self.column,
            "description": self.description,
            "affected_rows": self.affected_rows,
            "details": self.details,
            "timestamp": self.timestamp,
        }


class AnomalyReport:
    """Collection of anomalies detected in a dataset."""

    def __init__(self, dataset_name):
        self.dataset_name = dataset_name
        self.anomalies = []
        self.start_time = datetime.now()
        self.end_time = None
        self.rows_scanned = 0

    def add(self, anomaly):
        self.anomalies.append(anomaly)

    def finalize(self, rows_scanned):
        self.end_time = datetime.now()
        self.rows_scanned = rows_scanned

    @property
    def critical_count(self):
        return sum(1 for a in self.anomalies if a.severity == "CRITICAL")

    @property
    def high_count(self):
        return sum(1 for a in self.anomalies if a.severity == "HIGH")

    @property
    def medium_count(self):
        return sum(1 for a in self.anomalies if a.severity == "MEDIUM")

    @property
    def low_count(self):
        return sum(1 for a in self.anomalies if a.severity == "LOW")

    @property
    def health_score(self):
        """Calculate data health score (0-100). Higher = healthier."""
        if not self.anomalies or self.rows_scanned == 0:
            return 100.0
        severity_weights = {"CRITICAL": 10, "HIGH": 5, "MEDIUM": 2, "LOW": 1}
        total_penalty = sum(
            severity_weights[a.severity] * a.affected_rows
            for a in self.anomalies
        )
        max_penalty = self.rows_scanned * 10
        score = max(0, 100 - (total_penalty / max_penalty * 100))
        return round(score, 1)

    def to_dict(self):
        return {
            "dataset": self.dataset_name,
            "health_score": self.health_score,
            "rows_scanned": self.rows_scanned,
            "summary": {
                "total_anomalies": len(self.anomalies),
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count,
            },
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.end_time else None
            ),
            "anomalies": [a.to_dict() for a in self.anomalies],
        }


# ═══════════════════════════════════════════════════════════════
# ANOMALY DETECTION ENGINE
# ═══════════════════════════════════════════════════════════════

class AnomalyDetectionEngine:
    """ML-powered anomaly detection for financial datasets."""

    def __init__(self, config=None):
        self.config = config or self._default_config()

    @staticmethod
    def _default_config():
        return {
            "z_score_threshold": 3.5,
            "iqr_multiplier": 2.5,
            "isolation_forest": {
                "contamination": 0.05,
                "n_estimators": 100,
                "random_state": 42,
            },
            "drift_window_days": 30,
            "negative_amount_columns": ["amount", "claim_amount", "premium_amount"],
            "severity_thresholds": {
                "critical_rate": 0.05,
                "high_rate": 0.02,
                "medium_rate": 0.01,
            },
        }

    def _classify_severity(self, anomaly_rate):
        """Classify severity based on the rate of anomalous records."""
        thresholds = self.config.get("severity_thresholds", {"critical_rate": 0.05, "high_rate": 0.02, "medium_rate": 0.01})
        if anomaly_rate >= thresholds["critical_rate"]:
            return "CRITICAL"
        elif anomaly_rate >= thresholds["high_rate"]:
            return "HIGH"
        elif anomaly_rate >= thresholds["medium_rate"]:
            return "MEDIUM"
        return "LOW"

    # ── Main Detection Pipeline ──────────────────────────────

    def detect_all(self, df, dataset_name):
        """Run all anomaly detection methods on a dataset."""
        report = AnomalyReport(dataset_name)

        print(f"\n  Scanning {dataset_name} ({len(df):,} rows)...")

        # 1. Statistical outlier detection
        self._detect_zscore_outliers(df, report)
        self._detect_iqr_outliers(df, report)

        # 2. Negative amount detection
        self._detect_negative_amounts(df, report)

        # 3. Isolation Forest (multivariate)
        self._detect_isolation_forest(df, report)

        # 4. Duplicate detection
        self._detect_suspicious_duplicates(df, report)

        # 5. Time-series drift detection
        self._detect_temporal_drift(df, report)

        # 6. Categorical anomalies
        self._detect_categorical_anomalies(df, report)

        # 7. Null spike detection
        self._detect_null_spikes(df, report)

        report.finalize(len(df))
        return report

    # ── Z-Score Outlier Detection ────────────────────────────

    def _detect_zscore_outliers(self, df, report):
        """Detect outliers using Z-score method on numeric columns."""
        threshold = self.config.get("z_score_threshold", 3.5)
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            z_scores = np.abs(stats.zscore(series))
            outlier_mask = z_scores > threshold
            outlier_count = outlier_mask.sum()

            if outlier_count > 0:
                outlier_values = series[outlier_mask]
                anomaly_rate = outlier_count / len(series)
                severity = self._classify_severity(anomaly_rate)

                report.add(Anomaly(
                    anomaly_type="ZSCORE_OUTLIER",
                    severity=severity,
                    column=col,
                    description=(
                        f"Z-score outliers in '{col}': {outlier_count:,} values "
                        f"exceed {threshold} std devs ({anomaly_rate:.2%})"
                    ),
                    affected_rows=int(outlier_count),
                    details={
                        "threshold": threshold,
                        "outlier_count": int(outlier_count),
                        "anomaly_rate": round(anomaly_rate, 4),
                        "mean": round(float(series.mean()), 2),
                        "std": round(float(series.std()), 2),
                        "min_outlier": round(float(outlier_values.min()), 2),
                        "max_outlier": round(float(outlier_values.max()), 2),
                        "sample_values": [round(float(v), 2) for v in outlier_values.head(5)],
                    },
                ))

    # ── IQR Outlier Detection ────────────────────────────────

    def _detect_iqr_outliers(self, df, report):
        """Detect outliers using Interquartile Range method."""
        multiplier = self.config.get("iqr_multiplier", 2.5)
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - multiplier * iqr
            upper_bound = q3 + multiplier * iqr

            outliers = series[(series < lower_bound) | (series > upper_bound)]
            outlier_count = len(outliers)

            if outlier_count > 0:
                anomaly_rate = outlier_count / len(series)
                severity = self._classify_severity(anomaly_rate)

                report.add(Anomaly(
                    anomaly_type="IQR_OUTLIER",
                    severity=severity,
                    column=col,
                    description=(
                        f"IQR outliers in '{col}': {outlier_count:,} values "
                        f"outside [{lower_bound:,.2f}, {upper_bound:,.2f}]"
                    ),
                    affected_rows=int(outlier_count),
                    details={
                        "q1": round(float(q1), 2),
                        "q3": round(float(q3), 2),
                        "iqr": round(float(iqr), 2),
                        "lower_bound": round(float(lower_bound), 2),
                        "upper_bound": round(float(upper_bound), 2),
                        "outlier_count": int(outlier_count),
                        "below_lower": int((series < lower_bound).sum()),
                        "above_upper": int((series > upper_bound).sum()),
                    },
                ))

    # ── Negative Amount Detection ────────────────────────────

    def _detect_negative_amounts(self, df, report):
        """Detect negative values in financial amount columns."""
        target_cols = self.config.get("negative_amount_columns", [col for col in df.select_dtypes(include=["number"]).columns if any(kw in col.lower() for kw in ["amount", "premium", "balance", "payment", "claim"])])

        for col in target_cols:
            if col not in df.columns:
                continue

            series = pd.to_numeric(df[col], errors="coerce").dropna()
            negative_count = (series < 0).sum()

            if negative_count > 0:
                anomaly_rate = negative_count / len(series)
                severity = self._classify_severity(anomaly_rate)
                negative_values = series[series < 0]

                report.add(Anomaly(
                    anomaly_type="NEGATIVE_AMOUNT",
                    severity=severity,
                    column=col,
                    description=(
                        f"Negative amounts in '{col}': {negative_count:,} records "
                        f"({anomaly_rate:.2%})"
                    ),
                    affected_rows=int(negative_count),
                    details={
                        "negative_count": int(negative_count),
                        "anomaly_rate": round(anomaly_rate, 4),
                        "min_value": round(float(negative_values.min()), 2),
                        "max_negative": round(float(negative_values.max()), 2),
                        "total_negative_sum": round(float(negative_values.sum()), 2),
                    },
                ))

    # ── Isolation Forest Detection ───────────────────────────

    def _detect_isolation_forest(self, df, report):
        """Use Isolation Forest for multivariate anomaly detection."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()

        if len(numeric_cols) < 2:
            return

        # Prepare data
        numeric_df = df[numeric_cols].dropna()
        if len(numeric_df) < 50:
            return

        # Scale features
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_df)

        # Fit Isolation Forest
        iso_config = self.config.get("isolation_forest", {"contamination": 0.05, "n_estimators": 100, "random_state": 42})
        model = IsolationForest(
            contamination=iso_config["contamination"],
            n_estimators=iso_config["n_estimators"],
            random_state=iso_config["random_state"],
        )
        predictions = model.fit_predict(scaled_data)
        scores = model.decision_function(scaled_data)

        # Count anomalies (-1 = anomaly)
        anomaly_count = (predictions == -1).sum()
        anomaly_rate = anomaly_count / len(numeric_df)

        if anomaly_count > 0:
            severity = self._classify_severity(anomaly_rate)

            report.add(Anomaly(
                anomaly_type="ISOLATION_FOREST",
                severity=severity,
                column="[multivariate]",
                description=(
                    f"Isolation Forest detected {anomaly_count:,} multivariate "
                    f"anomalies ({anomaly_rate:.2%}) across {len(numeric_cols)} features"
                ),
                affected_rows=int(anomaly_count),
                details={
                    "anomaly_count": int(anomaly_count),
                    "anomaly_rate": round(anomaly_rate, 4),
                    "features_used": numeric_cols,
                    "mean_anomaly_score": round(float(scores[predictions == -1].mean()), 4),
                    "worst_score": round(float(scores.min()), 4),
                },
            ))

    # ── Suspicious Duplicate Detection ───────────────────────

    def _detect_suspicious_duplicates(self, df, report):
        """Detect exact and near-duplicate rows."""
        # Exact duplicates
        exact_dupes = df.duplicated().sum()
        if exact_dupes > 0:
            dupe_rate = exact_dupes / len(df)
            severity = self._classify_severity(dupe_rate)

            report.add(Anomaly(
                anomaly_type="EXACT_DUPLICATE",
                severity=severity,
                column="[all columns]",
                description=(
                    f"Exact duplicate rows: {exact_dupes:,} ({dupe_rate:.2%})"
                ),
                affected_rows=int(exact_dupes),
                details={
                    "duplicate_count": int(exact_dupes),
                    "duplicate_rate": round(dupe_rate, 4),
                },
            ))

        # Near-duplicates: same key fields but different amounts
        key_candidates = ["transaction_id", "claim_id", "payment_id", "policy_id"]
        for key_col in key_candidates:
            if key_col not in df.columns:
                continue
            id_dupes = df[key_col].dropna().duplicated().sum()
            if id_dupes > 0:
                dupe_rate = id_dupes / len(df)
                severity = self._classify_severity(dupe_rate)

                report.add(Anomaly(
                    anomaly_type="DUPLICATE_KEY",
                    severity=severity,
                    column=key_col,
                    description=(
                        f"Duplicate values in '{key_col}': {id_dupes:,} ({dupe_rate:.2%})"
                    ),
                    affected_rows=int(id_dupes),
                    details={
                        "column": key_col,
                        "duplicate_count": int(id_dupes),
                        "duplicate_rate": round(dupe_rate, 4),
                    },
                ))

    # ── Temporal Drift Detection ─────────────────────────────

    def _detect_temporal_drift(self, df, report):
        """Detect distribution shifts over time windows."""
        date_cols = ["transaction_date", "claim_date", "payment_date"]
        amount_cols = ["amount", "claim_amount"]

        for date_col in date_cols:
            if date_col not in df.columns:
                continue

            for amount_col in amount_cols:
                if amount_col not in df.columns:
                    continue

                # Parse dates
                temp_df = df[[date_col, amount_col]].copy()
                temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df[amount_col] = pd.to_numeric(temp_df[amount_col], errors="coerce")
                temp_df = temp_df.dropna()

                if len(temp_df) < 100:
                    continue

                # Split into monthly windows
                temp_df["month"] = temp_df[date_col].dt.to_period("M")
                monthly = temp_df.groupby("month")[amount_col]
                monthly_stats = monthly.agg(["mean", "std", "count"])

                if len(monthly_stats) < 3:
                    continue

                # Detect drift: compare each month to overall distribution
                overall_mean = temp_df[amount_col].mean()
                overall_std = temp_df[amount_col].std()

                if overall_std == 0:
                    continue

                drift_months = []
                for period, row in monthly_stats.iterrows():
                    if row["count"] < 10:
                        continue
                    z = abs(row["mean"] - overall_mean) / (overall_std / np.sqrt(row["count"]))
                    if z > 3.0:
                        drift_months.append({
                            "month": str(period),
                            "mean": round(float(row["mean"]), 2),
                            "z_score": round(float(z), 2),
                            "count": int(row["count"]),
                        })

                if drift_months:
                    severity = "HIGH" if len(drift_months) > 2 else "MEDIUM"
                    report.add(Anomaly(
                        anomaly_type="TEMPORAL_DRIFT",
                        severity=severity,
                        column=f"{date_col}/{amount_col}",
                        description=(
                            f"Distribution drift detected in '{amount_col}' over time: "
                            f"{len(drift_months)} months with significant deviation"
                        ),
                        affected_rows=sum(m["count"] for m in drift_months),
                        details={
                            "overall_mean": round(float(overall_mean), 2),
                            "overall_std": round(float(overall_std), 2),
                            "drift_months": drift_months,
                        },
                    ))

    # ── Categorical Anomaly Detection ────────────────────────

    def _detect_categorical_anomalies(self, df, report):
        """Detect unexpected or rare categorical values."""
        categorical_cols = df.select_dtypes(include=["object"]).columns

        for col in categorical_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            value_counts = series.value_counts()
            total = len(series)

            # Detect extremely rare values (< 0.1% of data)
            rare_threshold = max(1, total * 0.001)
            rare_values = value_counts[value_counts <= rare_threshold]

            if len(rare_values) > 0 and len(value_counts) > 3:
                rare_count = rare_values.sum()
                anomaly_rate = rare_count / total

                if anomaly_rate > 0.001:
                    severity = self._classify_severity(anomaly_rate)
                    report.add(Anomaly(
                        anomaly_type="RARE_CATEGORY",
                        severity=severity,
                        column=col,
                        description=(
                            f"Rare categorical values in '{col}': "
                            f"{len(rare_values)} rare categories ({rare_count:,} records)"
                        ),
                        affected_rows=int(rare_count),
                        details={
                            "rare_values": {
                                str(k): int(v) for k, v in rare_values.head(10).items()
                            },
                            "total_categories": len(value_counts),
                            "rare_categories": len(rare_values),
                        },
                    ))

    # ── Null Spike Detection ─────────────────────────────────

    def _detect_null_spikes(self, df, report):
        """Detect columns with unusually high null rates."""
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_rate = null_count / len(df) if len(df) > 0 else 0

            if null_rate > 0.01:
                severity = self._classify_severity(null_rate)
                report.add(Anomaly(
                    anomaly_type="NULL_SPIKE",
                    severity=severity,
                    column=col,
                    description=(
                        f"High null rate in '{col}': {null_count:,} nulls ({null_rate:.2%})"
                    ),
                    affected_rows=int(null_count),
                    details={
                        "null_count": int(null_count),
                        "null_rate": round(null_rate, 4),
                    },
                ))

    # ── Report Printing ──────────────────────────────────────

    @staticmethod
    def print_report(report):
        """Print a formatted anomaly report to console."""
        severity_icons = {
            "CRITICAL": "!!",
            "HIGH": "!",
            "MEDIUM": "*",
            "LOW": "-",
        }

        print(f"\n{'='*60}")
        print(f"  ANOMALY REPORT: {report.dataset_name.upper()}")
        print(f"{'='*60}")
        print(f"  Health Score:     {report.health_score}%")
        print(f"  Rows Scanned:     {report.rows_scanned:,}")
        print(f"  Anomalies Found:  {len(report.anomalies)}")
        print(f"    Critical: {report.critical_count}  |  High: {report.high_count}  "
              f"|  Medium: {report.medium_count}  |  Low: {report.low_count}")
        print(f"{'─'*60}")

        if not report.anomalies:
            print("\n  No anomalies detected — data looks clean!")
        else:
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_anomalies = sorted(
                report.anomalies,
                key=lambda a: severity_order.get(a.severity, 4),
            )

            current_severity = None
            for anomaly in sorted_anomalies:
                if anomaly.severity != current_severity:
                    current_severity = anomaly.severity
                    icon = severity_icons[current_severity]
                    print(f"\n  {icon} -- {current_severity} --")

                print(f"    [{anomaly.anomaly_type}] {anomaly.description}")

        print(f"\n{'='*60}\n")

    @staticmethod
    def save_report(report, output_dir="data/reports"):
        """Save anomaly report as JSON."""
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{report.dataset_name}_anomalies.json"
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2, default=str)
        print(f"  Saved report: {filepath}")
        return filepath
