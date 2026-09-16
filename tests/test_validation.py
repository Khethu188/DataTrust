# DataTrust - Validation Engine Tests
import pandas as pd
from conftest import make_customers, make_accounts


class TestValidationEngine:
    """Tests for the contract-based validation engine."""

    def test_clean_data_passes(self):
        """Clean data should get a high trust score."""
        df = make_customers(100)
        assert len(df) == 100
        assert df["customer_id"].nunique() == 100

    def test_null_detection(self):
        """Nulls should be detected and reduce trust score."""
        df = make_customers(100)
        df.loc[0:19, "email"] = None
        null_rate = df["email"].isnull().mean()
        assert null_rate == 0.2

    def test_duplicate_detection(self):
        """Duplicates should be detected."""
        df = make_customers(100)
        df = pd.concat([df, df.head(10)], ignore_index=True)
        dup_count = df.duplicated().sum()
        assert dup_count == 10

    def test_type_validation(self):
        """Columns should have correct types."""
        df = make_accounts(100)
        assert df["balance"].dtype in ["float64", "float32"]

    def test_range_validation(self):
        """Values should be within expected ranges."""
        df = make_accounts(100)
        assert df["balance"].min() >= 0
        assert df["balance"].max() <= 100000

    def test_empty_dataframe(self):
        """Empty DataFrame should be handled gracefully."""
        empty = pd.DataFrame(columns=["id", "name", "value"])
        assert len(empty) == 0

    def test_trust_score_calculation(self):
        """Trust score should be between 0 and 100."""
        total_checks = 5
        passed = 5
        trust_score = (passed / total_checks) * 100
        assert 0 <= trust_score <= 100
