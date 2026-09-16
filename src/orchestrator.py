
#!/usr/bin/env python3
"""
DataTrust — Pipeline Orchestrator
====================================
Ties all engines together into a single automated pipeline.

Stages:
  1. Generate synthetic data
  2. Validate clean + corrupted data
  3. Detect anomalies
  4. Auto-recover corrupted data
  5. Post-recovery validation
  6. Generate dashboard
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "validation"))
sys.path.insert(0, str(Path(__file__).parent / "data_generation"))
sys.path.insert(0, str(Path(__file__).parent / "utils"))

from logger import DataTrustLogger
from validation_engine import ValidationEngine
from anomaly_engine import AnomalyDetectionEngine
from recovery_engine import RecoveryEngine
from dashboard_generator import DashboardGenerator


class PipelineOrchestrator:
    """Orchestrates the full DataTrust pipeline."""

    def __init__(self, config_path="config.yaml"):
        with open(config_path, "r") as f:
            self.config = yaml.safe_load(f)

        self.paths = self.config["paths"]
        self.log = DataTrustLogger(log_dir=self.paths["logs"])
        self.start_time = None
        self.stage_times = {}

    def _load_csvs(self, directory):
        """Load all CSVs from a directory."""
        datasets = {}
        data_path = Path(directory)
        if not data_path.exists():
            self.log.warning(f"Directory not found: {directory}")
            return datasets
        for csv_file in sorted(data_path.glob("*.csv")):
            name = csv_file.stem
            datasets[name] = pd.read_csv(csv_file)
            self.log.info(f"  Loaded {name:<15} {len(datasets[name]):>8,} rows")
        return datasets

    def _time_stage(self, stage_name):
        """Record stage timing."""
        return _StageTimer(self, stage_name)

    # ═══════════════════════════════════════════════════════
    # FULL PIPELINE
    # ═══════════════════════════════════════════════════════

    def run_full_pipeline(self):
        """Run the complete DataTrust pipeline."""
        self.start_time = time.time()

        self.log.header("DataTrust — Full Pipeline")
        self.log.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log.info(f"  Config:  {json.dumps(self.paths, indent=2)}")

        # Stage 1: Validate clean data
        self.run_validate(data_type="clean")

        # Stage 2: Validate corrupted data
        self.run_validate(data_type="corrupted")

        # Stage 3: Anomaly detection on corrupted data
        self.run_anomaly_detection(data_type="corrupted")

        # Stage 4: Auto-recovery
        self.run_recovery()

        # Stage 5: Post-recovery validation
        self.run_validate(data_type="recovered")

        # Stage 6: Anomaly detection on recovered data
        self.run_anomaly_detection(data_type="recovered")

        # Stage 7: Generate dashboard
        self.run_dashboard()

        # Final summary
        total_time = time.time() - self.start_time
        self.log.header("PIPELINE COMPLETE")
        self.log.info(f"  Total time: {total_time:.1f} seconds")
        self.log.separator()
        self.log.info("  Stage Timings:")
        for stage, duration in self.stage_times.items():
            self.log.info(f"    {stage:<35} {duration:>6.1f}s")
        self.log.separator()
        self.log.success("All stages completed successfully!")

    # ═══════════════════════════════════════════════════════
    # INDIVIDUAL STAGES
    # ═══════════════════════════════════════════════════════

    def run_validate(self, data_type="clean"):
        """Run validation on a dataset type."""
        with self._time_stage(f"Validation ({data_type})"):
            self.log.header(f"Validation — {data_type.upper()} Data")

            data_dir = self.paths.get(f"{data_type}_data", f"data/{data_type}")
            datasets = self._load_csvs(data_dir)

            if not datasets:
                self.log.warning(f"No data found in {data_dir}")
                return

            validator = ValidationEngine(self.paths["contracts"])

            # Register all datasets as references for FK checks
            for name, df in datasets.items():
                validator.register_reference(name, df)

            for name, df in datasets.items():
                file_path = Path(data_dir) / f"{name}.csv"
                file_mod = datetime.fromtimestamp(file_path.stat().st_mtime)
                report = validator.validate(name, df, file_mod)
                validator.print_report(report)
                validator.save_report(report, self.paths["reports"])

            self.log.success(f"Validation ({data_type}) complete")

    def run_anomaly_detection(self, data_type="corrupted"):
        """Run anomaly detection on a dataset type."""
        with self._time_stage(f"Anomaly Detection ({data_type})"):
            self.log.header(f"Anomaly Detection — {data_type.upper()} Data")

            data_dir = self.paths.get(f"{data_type}_data", f"data/{data_type}")
            datasets = self._load_csvs(data_dir)

            if not datasets:
                self.log.warning(f"No data found in {data_dir}")
                return

            engine = AnomalyDetectionEngine(self.config.get("anomaly_detection"))

            for name, df in datasets.items():
                report = engine.detect_all(df, name)
                engine.print_report(report)
                engine.save_report(report, self.paths["reports"])

            self.log.success(f"Anomaly detection ({data_type}) complete")

    def run_recovery(self):
        """Run auto-recovery on corrupted data."""
        with self._time_stage("Recovery"):
            self.log.header("Auto-Recovery")

            corrupted = self._load_csvs(self.paths["corrupted_data"])
            clean = self._load_csvs(self.paths["clean_data"])

            if not corrupted:
                self.log.warning("No corrupted data found")
                return

            recovery = RecoveryEngine(contracts_dir=self.paths["contracts"])
            recovery_order = self.config.get("recovery", {}).get("recovery_order", list(corrupted.keys()))

            recovered_data = {}
            all_quarantine = {}

            for name in recovery_order:
                if name not in corrupted:
                    continue

                # Build reference data from already-recovered parents + clean fallback
                reference = {}
                for ref_name in recovered_data:
                    reference[ref_name] = recovered_data[ref_name]
                for ref_name in clean:
                    if ref_name not in reference:
                        reference[ref_name] = clean[ref_name]

                df_recovered, quarantine, report = recovery.recover(
                    name, corrupted[name], reference
                )
                recovery.print_report(report)
                recovery.save_report(report, self.paths["reports"])

                recovered_data[name] = df_recovered
                if len(quarantine) > 0:
                    all_quarantine[name] = quarantine

            # Save recovered data
            recovered_dir = Path(self.paths["recovered_data"])
            recovered_dir.mkdir(parents=True, exist_ok=True)
            for name, df in recovered_data.items():
                filepath = recovered_dir / f"{name}.csv"
                df.to_csv(filepath, index=False)
                self.log.info(f"  Saved {filepath} ({len(df):,} rows)")

            # Save quarantine
            quarantine_dir = Path(self.paths["quarantine_data"])
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            for name, df in all_quarantine.items():
                filepath = quarantine_dir / f"{name}_quarantine.csv"
                df.to_csv(filepath, index=False)
                self.log.info(f"  Quarantined {filepath} ({len(df):,} rows)")

            self.log.success("Recovery complete")

    def run_dashboard(self):
        """Generate the HTML dashboard."""
        with self._time_stage("Dashboard"):
            self.log.header("Dashboard Generation")

            generator = DashboardGenerator(reports_dir=self.paths["reports"])
            output = generator.generate(self.paths["dashboard"])

            self.log.info(f"  Validation reports: {len(generator.validation_reports)}")
            self.log.info(f"  Anomaly reports:    {len(generator.anomaly_reports)}")
            self.log.info(f"  Recovery reports:   {len(generator.recovery_reports)}")
            self.log.success(f"Dashboard saved: {output}")

    def run_status(self):
        """Show project health status."""
        self.log.header("DataTrust — Project Status")

        # Check directories
        dirs = {
            "Clean data": self.paths["clean_data"],
            "Corrupted data": self.paths["corrupted_data"],
            "Recovered data": self.paths["recovered_data"],
            "Quarantine": self.paths["quarantine_data"],
            "Reports": self.paths["reports"],
            "Contracts": self.paths["contracts"],
            "Logs": self.paths["logs"],
        }

        self.log.info("\n  Directories:")
        for label, path in dirs.items():
            p = Path(path)
            if p.exists():
                file_count = len(list(p.glob("*")))
                self.log.info(f"    [OK] {label:<20} {path:<30} ({file_count} files)")
            else:
                self.log.warning(f"    [--] {label:<20} {path:<30} (not found)")

        # Check reports
        reports_path = Path(self.paths["reports"])
        if reports_path.exists():
            val_reports = list(reports_path.glob("*_validation.json"))
            anom_reports = list(reports_path.glob("*_anomalies.json"))
            rec_reports = list(reports_path.glob("*_recovery.json"))

            self.log.info(f"\n  Reports:")
            self.log.info(f"    Validation:  {len(val_reports)}")
            self.log.info(f"    Anomaly:     {len(anom_reports)}")
            self.log.info(f"    Recovery:    {len(rec_reports)}")

            # Show latest trust scores
            if val_reports:
                self.log.info(f"\n  Latest Trust Scores:")
                for f in sorted(val_reports):
                    with open(f) as fh:
                        data = json.load(fh)
                    score = data.get("trust_score", 0)
                    verdict = data.get("overall_verdict", "N/A")
                    icon = "[OK]" if verdict == "PASS" else "[!!]" if verdict == "WARN" else "[XX]"
                    self.log.info(f"    {icon} {data['dataset']:<15} {score:>6.1f}%  ({verdict})")

        # Check dashboard
        dashboard_path = Path(self.paths["dashboard"])
        if dashboard_path.exists():
            mod_time = datetime.fromtimestamp(dashboard_path.stat().st_mtime)
            self.log.info(f"\n  Dashboard: {dashboard_path}")
            self.log.info(f"    Last updated: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.log.warning(f"\n  Dashboard not generated yet")

        self.log.separator()


class _StageTimer:
    """Context manager for timing pipeline stages."""

    def __init__(self, orchestrator, stage_name):
        self.orchestrator = orchestrator
        self.stage_name = stage_name

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        duration = time.time() - self.start
        self.orchestrator.stage_times[self.stage_name] = duration
        self.orchestrator.log.info(f"  Stage '{self.stage_name}' completed in {duration:.1f}s")

