
#!/usr/bin/env python3
"""
DataTrust — Anomaly Detection Tests
======================================
Tests for ML-powered anomaly detection.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "validation"))

from anomaly_engine import AnomalyDetectionEngine, Anomaly, AnomalyReport


class TestAnomaly:
    """Tests for the Anomaly data class."""

    def test_anomaly_creation(self):
        """Anomaly should store all fields correctly."""
        a = Anomaly(
            anomaly_type="ZSCORE_OUTLIER",
            severity="HIGH",
            column="amount",
            description="Test anomaly",
            affected_rows=10,
        )
        assert a.anomaly_type == "ZSCORE_OUTLIER"
        assert a.severity == "HIGH"
        assert a.affected_rows == 10

    def test_anomaly_to_dict(self):
        """Anomaly should serialize to dictionary."""
        a = Anomaly("TEST", "LOW", "col", "desc", 5)
        d = a.to_dict()
        assert d["anomaly_type"] == "TEST"
        assert d["severity"] == "LOW"
        assert "timestamp" in d


class TestAnomalyReport:
    """Tests for the AnomalyReport class."""

    def test_empty_report_health_score(self):
        """Empty report should have 100% health score."""
        report = AnomalyReport("test")
        report.finalize(1000)
        assert report.health_score == 100.0

    def test_health_score_decreases_with_anomalies(self):
        """Health score should decrease when anomalies are added."""
        report = AnomalyReport("test")
        report.add(Anomaly("TEST", "CRITICAL", "col", "desc", 100))
        report.finalize(1000)
        assert report.health_score < 100.0

    def test_severity_counts(self):
        """Report should correctly count anomalies by severity."""
        report = AnomalyReport("test")
        report.add(Anomaly("A", "CRITICAL", "c", "d", 1))
        report.add(Anomaly("B", "HIGH", "c", "d", 1))
        report.add(Anomaly("C", "MEDIUM", "c", "d", 1))
        report.add(Anomaly("D", "LOW", "c", "d", 1))
        report.add(Anomaly("E", "LOW", "c", "d", 1))
        assert report.critical_count == 1
        assert report.high_count == 1
        assert report.medium_count == 1
        assert report.low_count == 2


class TestAnomalyDetectionEngine:
    """Tests for the AnomalyDetectionEngine."""

    def test_engine_initialization(self):
        """Engine should initialize with default config."""
        engine = AnomalyDetectionEngine()
        assert engine.config is not None
        assert "z_score_threshold" in engine.config

    def test_detect_all_returns_report(self, sample_transactions):
        """detect_all should return an AnomalyReport."""
        engine = AnomalyDetectionEngine()
        report = engine.detect_all(sample_transactions, "transactions")
        assert isinstance(report, AnomalyReport)
        assert report.dataset_name == "transactions"
        assert report.rows_scanned == len(sample_transactions)

    def test_detects_negative_amounts(self):
        """Engine should detect negative amounts."""
        df = pd.DataFrame({
            "amount": [100, 200, -500, 300, -100, 400, 500, 600, 700, 800],
        })
        engine = AnomalyDetectionEngine()
        report = engine.detect_all(df, "test")
        neg_anomalies = [
            a for a in report.anomalies
            if a.anomaly_type == "NEGATIVE_AMOUNT"
        ]
        assert len(neg_anomalies) > 0, "Should detect negative amounts"

    def test_detects_duplicates(self):
        """Engine should detect exact duplicate rows."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 3, 4, 5, 5, 5, 6, 7],
            "value": [10, 20, 30, 30, 40, 50, 50, 50, 60, 70],
        })
        engine = AnomalyDetectionEngine()
        report = engine.detect_all(df, "test")
        dupe_anomalies = [
            a for a in report.anomalies
            if "DUPLICATE" in a.anomaly_type
        ]
        assert len(dupe_anomalies) > 0, "Should detect duplicates"

    def test_detects_null_spikes(self):
        """Engine should detect columns with high null rates."""
        df = pd.DataFrame({
            "col_a": [1, 2, None, None, None, None, None, None, None, None],
            "col_b": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        engine = AnomalyDetectionEngine()
        report = engine.detect_all(df, "test")
        null_anomalies = [
            a for a in report.anomalies
            if a.anomaly_type == "NULL_SPIKE"
        ]
        assert len(null_anomalies) > 0, "Should detect null spikes"

    def test_detects_zscore_outliers(self):
        """Engine should detect statistical outliers."""
        np.random.seed(42)
        normal_data = np.random.normal(100, 10, 1000)
        # Inject extreme outliers
        normal_data[0] = 500
        normal_data[1] = -300
        df = pd.DataFrame({"value": normal_data})

        engine = AnomalyDetectionEngine()
        report = engine.detect_all(df, "test")
        zscore_anomalies = [
            a for a in report.anomalies
            if a.anomaly_type == "ZSCORE_OUTLIER"
        ]
        assert len(zscore_anomalies) > 0, "Should detect Z-score outliers"

    def test_corrupted_data_lower_health(self, sample_transactions, corrupted_transactions):
        """Corrupted data should have lower health score than clean."""
        engine = AnomalyDetectionEngine()
        clean_report = engine.detect_all(sample_transactions, "clean")
        corrupt_report = engine.detect_all(corrupted_transactions, "corrupt")
        assert corrupt_report.health_score <= clean_report.health_score

    def test_report_to_dict(self, sample_transactions):
        """Report should serialize correctly."""
        engine = AnomalyDetectionEngine()
        report = engine.detect_all(sample_transactions, "test")
        d = report.to_dict()
        assert "dataset" in d
        assert "health_score" in d
        assert "summary" in d
        assert "anomalies" in d
