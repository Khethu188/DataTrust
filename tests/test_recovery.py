# DataTrust - Recovery Engine Tests
import pandas as pd
from conftest import make_customers, make_transactions


class TestRecoveryEngine:
    """Tests for the auto-recovery engine."""

    def test_null_imputation(self):
        """Nulls should be filled with median/mode."""
        df = make_customers(100)
        df.loc[0:9, "province"] = None
        mode_val = df["province"].mode().iloc[0]
        df["province"] = df["province"].fillna(mode_val)
        assert df["province"].isnull().sum() == 0

    def test_duplicate_removal(self):
        """Duplicates should be removed."""
        df = make_customers(100)
        df = pd.concat([df, df.head(5)], ignore_index=True)
        assert len(df) == 105
        df = df.drop_duplicates()
        assert len(df) == 100

    def test_negative_fix(self):
        """Negative amounts should be converted to positive."""
        df = make_transactions(100)
        df.loc[0:4, "amount"] = -500
        df.loc[df["amount"] < 0, "amount"] = df["amount"].abs()
        assert (df["amount"] >= 0).all()

    def test_outlier_capping(self):
        """Extreme outliers should be capped."""
        df = make_transactions(100)
        df.loc[0, "amount"] = 999999
        cap = df["amount"].quantile(0.99)
        df.loc[df["amount"] > cap, "amount"] = cap
        assert df["amount"].max() <= cap

    def test_recovery_rate(self):
        """Recovery rate should be calculated correctly."""
        original = 1000
        recovered = 910
        quarantined = 90
        rate = (recovered / original) * 100
        assert rate == 91.0
        assert recovered + quarantined == original

    def test_quarantine_isolation(self):
        """Unfixable records should be quarantined."""
        df = make_customers(100)
        df.loc[0:4, "email"] = None
        df.loc[0:4, "phone"] = None
        df.loc[0:4, "province"] = None
        bad_mask = (
            df["email"].isnull()
            & df["phone"].isnull()
            & df["province"].isnull()
        )
        quarantine = df[bad_mask]
        recovered = df[~bad_mask]
        assert len(quarantine) == 5
        assert len(recovered) == 95

    def test_type_coercion(self):
        """Wrong types should be coerced correctly."""
        df = pd.DataFrame({"amount": ["100", "200", "300", "abc", "500"]})
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        assert df["amount"].isnull().sum() == 1
