
#!/usr/bin/env python3
"""
DataTrust — Dashboard Runner
==============================
Generates the HTML dashboard from existing JSON reports.

Usage:
    python run_dashboard.py
    python run_dashboard.py --open
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from dashboard_generator import DashboardGenerator


def main():
    parser = argparse.ArgumentParser(description="Generate DataTrust Dashboard")
    parser.add_argument(
        "--reports-dir", default="data/reports",
        help="Path to reports directory",
    )
    parser.add_argument(
        "--output", default="data/dashboard/index.html",
        help="Output HTML file path",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open dashboard in browser after generating",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("DataTrust — Dashboard Generator")
    print("=" * 60)

    # Check reports exist
    reports_path = Path(args.reports_dir)
    if not reports_path.exists():
        print(f"\n  ERROR: Reports directory not found: {args.reports_dir}")
        print("  Run validation, anomaly detection, and recovery first!")
        sys.exit(1)

    report_files = list(reports_path.glob("*.json"))
    print(f"\n  Found {len(report_files)} report files in {args.reports_dir}/")
    for f in sorted(report_files):
        print(f"    - {f.name}")

    # Generate dashboard
    print(f"\n  Generating dashboard...")
    generator = DashboardGenerator(reports_dir=args.reports_dir)

    print(f"  Validation reports: {len(generator.validation_reports)}")
    print(f"  Anomaly reports:    {len(generator.anomaly_reports)}")
    print(f"  Recovery reports:   {len(generator.recovery_reports)}")

    output_path = generator.generate(args.output)

    print(f"\n  Dashboard ready!")
    print(f"  Open in browser: {output_path.resolve()}")

    # Auto-open in browser
    if args.open:
        abs_path = str(output_path.resolve())
        if sys.platform == "win32":
            os.startfile(abs_path)
        elif sys.platform == "darwin":
            subprocess.run(["open", abs_path])
        else:
            subprocess.run(["xdg-open", abs_path])
        print("  Opened in browser!")

    print(f"\n{'='*60}")
    print("DONE")
    print("=" * 60)


if __name__ == "__main__":
    main()

