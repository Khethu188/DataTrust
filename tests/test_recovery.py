
#!/usr/bin/env python3
"""
DataTrust — Recovery Engine Tests
====================================
Tests for auto-recovery and quarantine system.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "validation"))

from recovery_engine import RecoveryEngine, RecoveryAction, RecoveryReport


class TestRecoveryAction:
    """Tests for the RecoveryAction class."""

    def test_action_creation(self):
        """RecoveryAction should store all fields."""
        action = RecoveryAction(
            action_type="DEDUPLICATION",
            column="id",
            description="Removed 5 duplicates",
            rows_affected=5,
            strategy="keep_first",
        )
        assert action.action_type == "DEDUPLICATION"
        assert action.rows_affected == 5

    def test_action_to_dict(self):
        """RecoveryAction should serialize to dictionary."""
        action = RecoveryAction("TEST", "col", "desc", 10, "strat")
        d = action.to_dict()
        assert d["action_type"] == "TEST"
        assert d["rows_affected"] == 10
        assert "timestamp" in d


class TestRecoveryReport:
    """Tests for the RecoveryReport class."""

    def test_empty_report(self):
        """Empty report should have no actions."""
        report = RecoveryReport("test")
        report.finalize(100, 100, 0)
        assert len(report.actions) == 0
        assert report.recovery_rate == 100.0

    def test_recovery_rate_calculation(self):
        """Recovery rate should reflect rows preserved."""
        report = RecoveryReport("test")
        report.finalize(100, 90, 10)
        assert report.recovery_rate == 90.0

    def test_total_rows_fixed(self):
        """Should sum rows_affected across all actions."""
        report = RecoveryReport("test")
        report.add(RecoveryAction("A", "c", "d", 10, "s"))
        report.add(RecoveryAction("B", "c", "d", 20, "s"))
        assert report.total_rows_fixed == 30


class TestRecoveryEngine:
    """Tests for the RecoveryEngine."""

    def test_engine_loads_contracts(self):
        """Engine should load contracts from directory."""
        engine = RecoveryEngine("src/contracts")
        assert len(engine.contracts) > 0

    def test_removes_exact_duplicates(self):
        """Engine should remove exact duplicate rows."""
        df = pd.DataFrame({
            "id": [1, 2, 3, 3, 4],
            "value": [10, 20, 30, 30, 40],
        })
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover("test_dataset", df)

        assert len(recovered) < len(df), "Should have fewer rows after dedup"
        assert len(quarantine) > 0, "Duplicates should be quarantined"

    def test_fixes_negative_amounts(self, corrupted_transactions):
        """Engine should convert negative amounts to absolute values."""
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover(
            "transactions", corrupted_transactions
        )

        # Check if any negative fix actions were taken
        neg_actions = [
            a for a in report.actions
            if a.action_type == "NEGATIVE_AMOUNT_FIX"
        ]
        if neg_actions:
            amount_col = pd.to_numeric(recovered["amount"], errors="coerce")
            assert (amount_col.dropna() >= 0).all(), "No negatives should remain"

    def test_recovery_preserves_data(self, corrupted_transactions):
        """Recovery should preserve most of the data."""
        engine = RecoveryEngine("src/contracts")
        original_len = len(corrupted_transactions)
        recovered, quarantine, report = engine.recover(
            "transactions", corrupted_transactions
        )

        total_output = len(recovered) + len(quarantine)
        assert total_output <= original_len, "Output should not exceed input"
        assert report.recovery_rate > 0, "Recovery rate should be > 0"

    def test_quarantine_has_reasons(self, corrupted_transactions):
        """Quarantined records should have a reason column."""
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover(
            "transactions", corrupted_transactions
        )

        if len(quarantine) > 0:
            assert "_quarantine_reason" in quarantine.columns

    def test_report_has_actions(self, corrupted_transactions):
        """Recovery report should contain actions taken."""
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover(
            "transactions", corrupted_transactions
        )
        assert len(report.actions) > 0, "Should have recovery actions"

    def test_report_to_dict(self, corrupted_transactions):
        """Report should serialize correctly."""
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover(
            "transactions", corrupted_transactions
        )
        d = report.to_dict()
        assert "dataset" in d
        assert "recovery_rate" in d
        assert "actions" in d
        assert "quarantined_rows" in d

    def test_recovered_data_is_cleaner(self, sample_transactions, corrupted_transactions):
        """Recovered data should have fewer issues than corrupted."""
        engine = RecoveryEngine("src/contracts")
        recovered, _, _ = engine.recover(
            "transactions", corrupted_transactions
        )

        # Recovered should have no exact duplicates
        original_dupes = corrupted_transactions.duplicated().sum()
        recovered_dupes = recovered.duplicated().sum()
        assert recovered_dupes <= original_dupes

    def test_empty_dataframe(self):
        """Engine should handle empty DataFrames gracefully."""
        df = pd.DataFrame()
        engine = RecoveryEngine("src/contracts")
        recovered, quarantine, report = engine.recover("test", df)
        assert report is not None
        assert len(recovered) == 0

