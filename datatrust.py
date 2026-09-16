
#!/usr/bin/env python3
"""
DataTrust — CLI Entry Point
==============================
Single command to run any part of the DataTrust pipeline.

Usage:
    python datatrust.py run                  # Full pipeline
    python datatrust.py validate             # Validate clean data
    python datatrust.py validate --corrupted  # Validate corrupted data
    python datatrust.py anomalies            # Detect anomalies
    python datatrust.py recover              # Auto-recover
    python datatrust.py dashboard            # Generate dashboard
    python datatrust.py dashboard --open     # Generate + open in browser
    python datatrust.py status               # Show project health
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "src" / "validation"))
sys.path.insert(0, str(project_root / "src" / "data_generation"))
sys.path.insert(0, str(project_root / "src" / "utils"))

from orchestrator import PipelineOrchestrator


def main():
    parser = argparse.ArgumentParser(
        _ = "DataTrust — Autonomous Data Integrity, Observability & Recovery",
        _ = argparse.RawDescriptionHelpFormatter,
        _ = """
Commands:
  run          Run the full pipeline (validate → detect → recover → dashboard)
  validate     Run validation engine
  anomalies    Run anomaly detection
  recover      Run auto-recovery on corrupted data
  dashboard    Generate HTML dashboard
  status       Show project health and status

Examples:
  python datatrust.py run
  python datatrust.py validate --corrupted
  python datatrust.py anomalies --recovered
  python datatrust.py dashboard --open
  python datatrust.py status
        """,
    )

    parser.add_argument(
        "command",
        _ = ["run", "validate", "anomalies", "recover", "dashboard", "status"],
        help="Pipeline command to execute",
    )
    parser.add_argument(
        "--corrupted", action="store_true",
        help="Use corrupted data (for validate/anomalies)",
    )
    parser.add_argument(
        "--recovered", action="store_true",
        help="Use recovered data (for validate/anomalies)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open dashboard in browser (for dashboard command)",
    )
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )

    args = parser.parse_args()

    # Banner
    print()
    print("  ╔══════════════════════════════════════════════════╗")
    print("  ║           DataTrust v1.0                        ║")
    print("  ║   Autonomous Data Integrity & Recovery          ║")
    print("  ║   Built by Khethukuthula Sabela                 ║")
    print("  ╚══════════════════════════════════════════════════╝")
    print()

    # Initialize orchestrator
    try:
        orchestrator = PipelineOrchestrator(config_path=args.config)
    except FileNotFoundError:
        print(f"  ERROR: Config file not found: {args.config}")
        print("  Make sure config.yaml exists in the project root.")
        sys.exit(1)

    # Route commands
    if args.command == "run":
        orchestrator.run_full_pipeline()

    elif args.command == "validate":
        if args.recovered:
            orchestrator.run_validate(data_type="recovered")
        elif args.corrupted:
            orchestrator.run_validate(data_type="corrupted")
        else:
            orchestrator.run_validate(data_type="clean")

    elif args.command == "anomalies":
        if args.recovered:
            orchestrator.run_anomaly_detection(data_type="recovered")
        elif args.corrupted:
            orchestrator.run_anomaly_detection(data_type="corrupted")
        else:
            orchestrator.run_anomaly_detection(data_type="clean")

    elif args.command == "recover":
        orchestrator.run_recovery()

    elif args.command == "dashboard":
        orchestrator.run_dashboard()
        if args.open:
            dashboard_path = str(Path(orchestrator.paths["dashboard"]).resolve())
            if sys.platform == "win32":
                os.startfile(dashboard_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", dashboard_path])
            else:
                subprocess.run(["xdg-open", dashboard_path])
            print("\n  Opened dashboard in browser!")

    elif args.command == "status":
        orchestrator.run_status()

    print()


if __name__ == "__main__":
    main()
