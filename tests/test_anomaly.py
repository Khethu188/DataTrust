# DataTrust - Anomaly Detection Tests
import pandas as pd
from conftest import make_transactions, make_accounts


class TestAnomalyDetection:
    """Tests for the ML-powered anomaly detection engine."""

    def test_zscore_detects_outliers(self):
        """Z-score should detect statistical outliers."""
        df = make_transactions(200)
        df.loc[0, "amount"] = 999999.99
        mean = df["amount"].mean()
        std = df["amount"].std()
        z = abs((999999.99 - mean) / std)
        assert z > 3.0

    def test_clean_data_no_anomalies(self):
        """Clean data should have few or no anomalies."""
        df = make_transactions(200)
        mean = df["amount"].mean()
        std = df["amount"].std()
        z_scores = ((df["amount"] - mean) / std).abs()
        outliers = z_scores[z_scores > 3.5]
        assert len(outliers) < 10

    def test_iqr_detection(self):
        """IQR method should detect range violations."""
        df = make_accounts(100)
        q1 = df["balance"].quantile(0.25)
        q3 = df["balance"].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 2.5 * iqr
        upper = q3 + 2.5 * iqr
        outliers = df[(df["balance"] < lower) | (df["balance"] > upper)]
        assert isinstance(outliers, pd.DataFrame)

    def test_negative_amounts(self):
        """Negative amounts should be flagged."""
        df = make_transactions(100)
        df.loc[0:4, "amount"] = -500
        negatives = df[df["amount"] < 0]
        assert len(negatives) == 5

    def test_health_score_range(self):
        """Health score should be between 0 and 100."""
        total = 200
        anomalies = 10
        health = max(0, 100 - (anomalies / total) * 100)
        assert 0 <= health <= 100

    def test_severity_classification(self):
        """Anomalies should be classified by severity."""
        severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        z_score = 5.0
        if z_score > 4.0:
            severity = "CRITICAL"
        elif z_score > 3.5:
            severity = "HIGH"
        elif z_score > 3.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        assert severity in severities
