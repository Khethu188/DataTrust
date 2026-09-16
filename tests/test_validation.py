
#!/usr/bin/env python3
"""
DataTrust — Validation Engine Tests
======================================
Tests for contract-based data validation.
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "validation"))

from validation_engine import ValidationEngine


class TestValidationEngine:
    """Tests for the ValidationEngine class."""

    def test_engine_loads_contracts(self):
        """Engine should load YAML contracts from directory."""
        engine = ValidationEngine("src/contracts")
        assert len(engine.contracts) > 0, "No contracts loaded"

    def test_validate_clean_data(self, sample_customers):
        """Clean data should pass most validation checks."""
        engine = ValidationEngine("src/contracts")
        report = engine.validate(
            "customers", sample_customers, datetime.now()
        )
        assert report.trust_score > 0, "Trust score should be > 0"
        assert report.dataset_name == "customers"

    def test_trust_score_range(self, sample_customers):
        """Trust score should be between 0 and 100."""
        engine = ValidationEngine("src/contracts")
        report = engine.validate(
            "customers", sample_customers, datetime.now()
        )
        assert 0 <= report.trust_score <= 100

    def test_report_has_checks(self, sample_customers):
        """Validation report should contain check results."""
        engine = ValidationEngine("src/contracts")
        report = engine.validate(
            "customers", sample_customers, datetime.now()
        )
        assert len(report.checks) > 0, "Report should have checks"

    def test_check_verdicts_valid(self, sample_customers):
        """All check verdicts should be PASS, WARN, or FAIL."""
        engine = ValidationEngine("src/contracts")
        report = engine.validate(
            "customers", sample_customers, datetime.now()
        )
        valid_verdicts = {"PASS", "WARN", "FAIL"}
        for check in report.checks:
            assert check.verdict in valid_verdicts, (
                f"Invalid verdict: {check.verdict}"
            )

    def test_null_detection(self):
        """Engine should detect null values in non-nullable columns."""
        df = pd.DataFrame({
            "customer_id": ["C1", "C2", None, "C4"],
            "first_name": ["A", None, "C", "D"],
        })
        engine = ValidationEngine("src/contracts")
        report = engine.validate("customers", df, datetime.now())

        # Should have at least one check that catches nulls
        has_null_check = any(
            "null" in c.check_name.lower() or "null" in c.message.lower()
            for c in report.checks
        )
        assert report.trust_score < 100 or has_null_check

    def test_report_to_dict(self, sample_customers):
        """Report should serialize to dictionary."""
        engine = ValidationEngine("src/contracts")
        report = engine.validate(
            "customers", sample_customers, datetime.now()
        )
        result = report.to_dict()
        assert "dataset" in result
        assert "trust_score" in result
        assert "checks" in result
        assert "overall_verdict" in result

    def test_register_reference(self, sample_customers):
        """Engine should accept reference datasets for FK checks."""
        engine = ValidationEngine("src/contracts")
        engine.register_reference("customers", sample_customers)
        assert "customers" in engine.reference_data

    def test_empty_dataframe(self):
        """Engine should handle empty DataFrames gracefully."""
        df = pd.DataFrame()
        engine = ValidationEngine("src/contracts")
        report = engine.validate("customers", df, datetime.now())
        assert report is not None
        assert report.trust_score is not None
