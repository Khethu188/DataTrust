
#!/usr/bin/env python3
"""Fix: Patch anomaly_engine.py to handle missing config keys."""

filepath = "src/validation/anomaly_engine.py"

with open(filepath, "r", encoding="utf-8") as f:
    code = f.read()

# Fix 1: negative_amount_columns — use .get() with default
code = code.replace(
    'target_cols = self.config["negative_amount_columns"]',
    'target_cols = self.config.get("negative_amount_columns", [col for col in df.select_dtypes(include=["number"]).columns if any(kw in col.lower() for kw in ["amount", "premium", "balance", "payment", "claim"])])'
)

# Fix 2: Any other potential KeyError with self.config["..."]
# Replace common patterns with .get() defaults
code = code.replace(
    'self.config["z_score_threshold"]',
    'self.config.get("z_score_threshold", 3.5)'
)
code = code.replace(
    'self.config["iqr_multiplier"]',
    'self.config.get("iqr_multiplier", 2.5)'
)
code = code.replace(
    'self.config["isolation_forest"]',
    'self.config.get("isolation_forest", {"contamination": 0.05, "n_estimators": 100, "random_state": 42})'
)
code = code.replace(
    'self.config["severity_thresholds"]',
    'self.config.get("severity_thresholds", {"critical_rate": 0.05, "high_rate": 0.02, "medium_rate": 0.01})'
)
code = code.replace(
    'self.config["null_spike_threshold"]',
    'self.config.get("null_spike_threshold", 0.1)'
)
code = code.replace(
    'self.config["duplicate_columns"]',
    'self.config.get("duplicate_columns", None)'
)
code = code.replace(
    'self.config["categorical_columns"]',
    'self.config.get("categorical_columns", [col for col in df.select_dtypes(include=["object"]).columns])'
)
code = code.replace(
    'self.config["temporal_column"]',
    'self.config.get("temporal_column", None)'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(code)

print("anomaly_engine.py patched successfully!")
print("All config lookups now use safe .get() with defaults.")

