
#!/usr/bin/env python3
"""
DataTrust — Premium Animated Dashboard Generator
====================================================
Generates a stunning, modern HTML dashboard with:
  - Animated counters
  - Smooth fade-in/slide-up animations
  - Glassmorphism cards
  - Animated progress rings
  - Particle background
  - Responsive grid layout
  - Dark theme with gradient accents

Author: Khethukuthula Sabela
"""

import json
import os
from datetime import datetime
from pathlib import Path


class DashboardGenerator:
    """Generates a premium animated HTML dashboard from pipeline reports."""

    def __init__(self, reports_dir="data/reports"):
        self.reports_dir = Path(reports_dir)
        self.validation_reports = {}
        self.anomaly_reports = {}
        self.recovery_reports = {}
        self._load_reports()

    def _load_reports(self):
        """Load all JSON reports from the reports directory."""
        if not self.reports_dir.exists():
            return

        for f in self.reports_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                name = f.stem

                if "trust_score" in data:
                    dataset = data.get("dataset", name.replace("_validation", ""))
                    self.validation_reports[dataset] = data
                elif "health_score" in data:
                    dataset = data.get("dataset", name.replace("_anomalies", ""))
                    self.anomaly_reports[dataset] = data
                elif "recovery_rate" in data:
                    dataset = data.get("dataset", name.replace("_recovery", ""))
                    self.recovery_reports[dataset] = data
            except (json.JSONDecodeError, KeyError):
                continue

    def generate(self, output_path="data/dashboard/index.html"):
        """Generate the full HTML dashboard."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Calculate summary stats
        trust_scores = {k: v.get("trust_score", 0) for k, v in self.validation_reports.items()}
        health_scores = {k: v.get("health_score", 0) for k, v in self.anomaly_reports.items()}
        recovery_rates = {k: v.get("recovery_rate", 0) for k, v in self.recovery_reports.items()}

        avg_trust = sum(trust_scores.values()) / max(len(trust_scores), 1)
        avg_health = sum(health_scores.values()) / max(len(health_scores), 1)
        total_anomalies = sum(
            len(v.get("anomalies", [])) for v in self.anomaly_reports.values()
        )
        avg_recovery = sum(recovery_rates.values()) / max(len(recovery_rates), 1)

        total_rows_recovered = sum(
            v.get("rows_after_recovery", 0) for v in self.recovery_reports.values()
        )
        total_quarantined = sum(
            v.get("quarantined_rows", 0) for v in self.recovery_reports.values()
        )
        total_actions = sum(
            len(v.get("actions", [])) for v in self.recovery_reports.values()
        )

        # Build dataset cards
        dataset_cards = ""
        datasets = sorted(set(
            list(self.validation_reports.keys()) +
            list(self.anomaly_reports.keys()) +
            list(self.recovery_reports.keys())
        ))

        for i, ds in enumerate(datasets):
            ts = trust_scores.get(ds, 0)
            hs = health_scores.get(ds, 0)
            rr = recovery_rates.get(ds, 0)

            val = self.validation_reports.get(ds, {})
            anom = self.anomaly_reports.get(ds, {})
            rec = self.recovery_reports.get(ds, {})

            checks_pass = sum(1 for c in val.get("checks", []) if c.get("verdict") == "PASS")
            checks_fail = sum(1 for c in val.get("checks", []) if c.get("verdict") == "FAIL")
            checks_warn = sum(1 for c in val.get("checks", []) if c.get("verdict") == "WARN")
            total_checks = checks_pass + checks_fail + checks_warn

            anom_count = len(anom.get("anomalies", []))
            anom_summary = anom.get("summary", {})
            critical = anom_summary.get("critical", 0) if isinstance(anom_summary, dict) else 0
            high = anom_summary.get("high", 0) if isinstance(anom_summary, dict) else 0

            rec_actions = len(rec.get("actions", []))
            rec_quarantined = rec.get("quarantined_rows", 0)

            ts_color = "#00ff88" if ts >= 80 else "#ffaa00" if ts >= 60 else "#ff4466"
            hs_color = "#00ff88" if hs >= 80 else "#ffaa00" if hs >= 60 else "#ff4466"

            dataset_cards += f"""
            <div class="dataset-card" style="animation-delay: {i * 0.1}s">
                <div class="dataset-header">
                    <h3>{ds.upper()}</h3>
                    <span class="badge" style="background: {ts_color}20; color: {ts_color}">
                        {"HEALTHY" if ts >= 80 else "WARNING" if ts >= 60 else "CRITICAL"}
                    </span>
                </div>
                <div class="rings-row">
                    <div class="ring-container">
                        <svg class="progress-ring" viewBox="0 0 120 120">
                            <circle class="ring-bg" cx="60" cy="60" r="52"/>
                            <circle class="ring-fill" cx="60" cy="60" r="52"
                                stroke="{ts_color}"
                                stroke-dasharray="{ts * 3.267} {326.7 - ts * 3.267}"
                                stroke-dashoffset="81.675"/>
                        </svg>
                        <div class="ring-label">
                            <span class="ring-value" data-target="{ts:.1f}" style="color:{ts_color}">{ts:.1f}%</span>
                            <span class="ring-text">Trust</span>
                        </div>
                    </div>
                    <div class="ring-container">
                        <svg class="progress-ring" viewBox="0 0 120 120">
                            <circle class="ring-bg" cx="60" cy="60" r="52"/>
                            <circle class="ring-fill" cx="60" cy="60" r="52"
                                stroke="{hs_color}"
                                stroke-dasharray="{hs * 3.267} {326.7 - hs * 3.267}"
                                stroke-dashoffset="81.675"/>
                        </svg>
                        <div class="ring-label">
                            <span class="ring-value" data-target="{hs:.1f}" style="color:{hs_color}">{hs:.1f}%</span>
                            <span class="ring-text">Health</span>
                        </div>
                    </div>
                </div>
                <div class="dataset-stats">
                    <div class="stat-row">
                        <span class="stat-icon">✓</span>
                        <span>Checks Passed</span>
                        <span class="stat-val pass">{checks_pass}/{total_checks}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-icon">⚠</span>
                        <span>Anomalies</span>
                        <span class="stat-val warn">{anom_count}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-icon">🔧</span>
                        <span>Recovery Actions</span>
                        <span class="stat-val info">{rec_actions}</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-icon">🚫</span>
                        <span>Quarantined</span>
                        <span class="stat-val fail">{rec_quarantined:,}</span>
                    </div>
                </div>
                <div class="recovery-bar-container">
                    <div class="recovery-bar-label">
                        <span>Recovery Rate</span>
                        <span style="color: #00ff88">{rr:.1f}%</span>
                    </div>
                    <div class="recovery-bar-bg">
                        <div class="recovery-bar-fill" style="width: {rr}%"></div>
                    </div>
                </div>
            </div>
            """

        # Build trust score chart data
        trust_chart_labels = json.dumps(list(trust_scores.keys()))
        trust_chart_data = json.dumps([round(v, 1) for v in trust_scores.values()])
        health_chart_data = json.dumps([round(v, 1) for v in health_scores.values()])
        recovery_chart_data = json.dumps([round(v, 1) for v in recovery_rates.values()])

        # Validation details table
        validation_rows = ""
        for ds in datasets:
            val = self.validation_reports.get(ds, {})
            for check in val.get("checks", []):
                verdict = check.get("verdict", "N/A")
                v_class = "pass" if verdict == "PASS" else "fail" if verdict == "FAIL" else "warn"
                validation_rows += f"""
                <tr>
                    <td>{ds}</td>
                    <td>{check.get("check_name", "N/A")}</td>
                    <td><span class="verdict-badge {v_class}">{verdict}</span></td>
                    <td>{check.get("message", "")}</td>
                </tr>"""

        # Anomaly details table
        anomaly_rows = ""
        for ds in datasets:
            anom = self.anomaly_reports.get(ds, {})
            for a in anom.get("anomalies", []):
                sev = a.get("severity", "LOW")
                s_class = sev.lower()
                anomaly_rows += f"""
                <tr>
                    <td>{ds}</td>
                    <td>{a.get("anomaly_type", "N/A")}</td>
                    <td><span class="severity-badge {s_class}">{sev}</span></td>
                    <td>{a.get("column", "N/A")}</td>
                    <td>{a.get("affected_rows", 0):,}</td>
                    <td>{a.get("description", "")}</td>
                </tr>"""

        # Recovery details table
        recovery_rows = ""
        for ds in datasets:
            rec = self.recovery_reports.get(ds, {})
            for action in rec.get("actions", []):
                recovery_rows += f"""
                <tr>
                    <td>{ds}</td>
                    <td>{action.get("action_type", "N/A")}</td>
                    <td>{action.get("column", "N/A")}</td>
                    <td>{action.get("rows_affected", 0):,}</td>
                    <td>{action.get("strategy", "N/A")}</td>
                    <td>{action.get("description", "")}</td>
                </tr>"""

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataTrust — Dashboard</title>
    <style>
        /* ═══ RESET & BASE ═══ */
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        :root {{
            --bg-primary: #0a0e1a;
            --bg-secondary: #111827;
            --bg-card: rgba(17, 24, 39, 0.7);
            --border: rgba(255, 255, 255, 0.06);
            --text-primary: #f0f4ff;
            --text-secondary: #8892a4;
            --accent-green: #00ff88;
            --accent-blue: #3b82f6;
            --accent-purple: #8b5cf6;
            --accent-orange: #f59e0b;
            --accent-red: #ef4444;
            --accent-cyan: #06b6d4;
            --glow-green: rgba(0, 255, 136, 0.15);
            --glow-blue: rgba(59, 130, 246, 0.15);
            --glow-purple: rgba(139, 92, 246, 0.15);
        }}

        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            min-height: 100vh;
            overflow-x: hidden;
        }}

        /* ═══ PARTICLE BACKGROUND ═══ */
        #particles {{
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            z-index: 0;
            pointer-events: none;
        }}

        .particle {{
            position: absolute;
            border-radius: 50%;
            opacity: 0.3;
            animation: float linear infinite;
        }}

        @keyframes float {{
            0% {{ transform: translateY(100vh) rotate(0deg); opacity: 0; }}
            10% {{ opacity: 0.3; }}
            90% {{ opacity: 0.3; }}
            100% {{ transform: translateY(-10vh) rotate(720deg); opacity: 0; }}
        }}

        /* ═══ ANIMATIONS ═══ */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}

        @keyframes slideInLeft {{
            from {{ opacity: 0; transform: translateX(-30px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}

        @keyframes shimmer {{
            0% {{ background-position: -200% 0; }}
            100% {{ background-position: 200% 0; }}
        }}

        @keyframes ringGrow {{
            from {{ stroke-dasharray: 0 326.7; }}
        }}

        @keyframes countUp {{
            from {{ opacity: 0; transform: scale(0.5); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}

        @keyframes gradientShift {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}

        @keyframes borderGlow {{
            0%, 100% {{ border-color: rgba(0, 255, 136, 0.1); }}
            50% {{ border-color: rgba(0, 255, 136, 0.3); }}
        }}

        .animate-in {{
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
        }}

        /* ═══ LAYOUT ═══ */
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
            z-index: 1;
        }}

        /* ═══ HEADER ═══ */
        .header {{
            text-align: center;
            padding: 40px 0 30px;
            animation: fadeIn 1s ease-out;
        }}

        .header h1 {{
            font-size: 3rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-green), var(--accent-blue), var(--accent-purple));
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: gradientShift 4s ease infinite;
            letter-spacing: -1px;
        }}

        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin-top: 8px;
            font-weight: 300;
        }}

        .header .timestamp {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 12px;
            opacity: 0.6;
        }}

        .header .live-dot {{
            display: inline-block;
            width: 8px; height: 8px;
            background: var(--accent-green);
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s ease-in-out infinite;
            vertical-align: middle;
        }}

        /* ═══ HERO CARDS ═══ */
        .hero-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .hero-card {{
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            position: relative;
            overflow: hidden;
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .hero-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }}

        .hero-card::before {{
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            border-radius: 16px 16px 0 0;
        }}

        .hero-card:nth-child(1)::before {{ background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan)); }}
        .hero-card:nth-child(2)::before {{ background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)); }}
        .hero-card:nth-child(3)::before {{ background: linear-gradient(90deg, var(--accent-orange), var(--accent-red)); }}
        .hero-card:nth-child(4)::before {{ background: linear-gradient(90deg, var(--accent-purple), var(--accent-green)); }}
        .hero-card:nth-child(5)::before {{ background: linear-gradient(90deg, var(--accent-cyan), var(--accent-blue)); }}
        .hero-card:nth-child(6)::before {{ background: linear-gradient(90deg, var(--accent-green), var(--accent-orange)); }}

        .hero-card .hero-icon {{
            font-size: 2rem;
            margin-bottom: 12px;
        }}

        .hero-card .hero-value {{
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -1px;
            animation: countUp 1s ease-out;
        }}

        .hero-card .hero-label {{
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 4px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .hero-card .hero-sub {{
            color: var(--text-secondary);
            font-size: 0.8rem;
            margin-top: 8px;
        }}

        /* ═══ SECTION HEADERS ═══ */
        .section-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 40px 0 20px;
            animation: slideInLeft 0.6s ease-out;
        }}

        .section-header h2 {{
            font-size: 1.5rem;
            font-weight: 700;
        }}

        .section-header .section-line {{
            flex: 1;
            height: 1px;
            background: linear-gradient(90deg, var(--border), transparent);
        }}

        /* ═══ CHART CONTAINER ═══ */
        .chart-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .chart-card {{
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
        }}

        .chart-card h3 {{
            font-size: 1rem;
            margin-bottom: 20px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }}

        .bar-chart {{
            display: flex;
            align-items: flex-end;
            gap: 12px;
            height: 200px;
            padding-top: 20px;
        }}

        .bar-group {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            height: 100%;
            justify-content: flex-end;
        }}

        .bar {{
            width: 100%;
            max-width: 60px;
            border-radius: 8px 8px 4px 4px;
            position: relative;
            animation: barGrow 1s ease-out forwards;
            transform-origin: bottom;
            min-height: 4px;
            transition: filter 0.3s ease;
        }}

        .bar:hover {{
            filter: brightness(1.3);
        }}

        @keyframes barGrow {{
            from {{ transform: scaleY(0); }}
            to {{ transform: scaleY(1); }}
        }}

        .bar-label {{
            font-size: 0.7rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .bar-value {{
            font-size: 0.75rem;
            font-weight: 700;
            color: var(--text-primary);
        }}

        /* ═══ DATASET CARDS ═══ */
        .dataset-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .dataset-card {{
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
            transition: transform 0.3s ease, border-color 0.3s ease;
        }}

        .dataset-card:hover {{
            transform: translateY(-2px);
            border-color: rgba(255, 255, 255, 0.12);
        }}

        .dataset-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}

        .dataset-header h3 {{
            font-size: 1.1rem;
            font-weight: 700;
            letter-spacing: 1px;
        }}

        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 1px;
        }}

        /* ═══ PROGRESS RINGS ═══ */
        .rings-row {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 20px;
        }}

        .ring-container {{
            position: relative;
            width: 100px;
            height: 100px;
        }}

        .progress-ring {{
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }}

        .ring-bg {{
            fill: none;
            stroke: rgba(255, 255, 255, 0.05);
            stroke-width: 8;
        }}

        .ring-fill {{
            fill: none;
            stroke-width: 8;
            stroke-linecap: round;
            animation: ringGrow 1.5s ease-out forwards;
        }}

        .ring-label {{
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
        }}

        .ring-value {{
            font-size: 1rem;
            font-weight: 800;
            display: block;
        }}

        .ring-text {{
            font-size: 0.65rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* ═══ DATASET STATS ═══ */
        .dataset-stats {{
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 16px;
        }}

        .stat-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 0;
            border-bottom: 1px solid var(--border);
            font-size: 0.85rem;
        }}

        .stat-row:last-child {{ border-bottom: none; }}

        .stat-icon {{ font-size: 0.9rem; width: 24px; text-align: center; }}

        .stat-row span:nth-child(2) {{ flex: 1; color: var(--text-secondary); }}

        .stat-val {{ font-weight: 700; }}
        .stat-val.pass {{ color: var(--accent-green); }}
        .stat-val.warn {{ color: var(--accent-orange); }}
        .stat-val.fail {{ color: var(--accent-red); }}
        .stat-val.info {{ color: var(--accent-blue); }}

        /* ═══ RECOVERY BAR ═══ */
        .recovery-bar-container {{ margin-top: 8px; }}

        .recovery-bar-label {{
            display: flex;
            justify-content: space-between;
            font-size: 0.8rem;
            margin-bottom: 6px;
            color: var(--text-secondary);
        }}

        .recovery-bar-bg {{
            height: 6px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 3px;
            overflow: hidden;
        }}

        .recovery-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, var(--accent-green), var(--accent-cyan));
            border-radius: 3px;
            animation: barGrow 1.5s ease-out;
            transform-origin: left;
        }}

        /* ═══ TABS ═══ */
        .tabs {{
            display: flex;
            gap: 4px;
            margin-bottom: 20px;
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 4px;
            overflow-x: auto;
        }}

        .tab {{
            padding: 10px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            transition: all 0.3s ease;
            white-space: nowrap;
            border: none;
            background: none;
        }}

        .tab:hover {{ color: var(--text-primary); background: rgba(255,255,255,0.05); }}
        .tab.active {{
            color: var(--text-primary);
            background: var(--accent-blue);
        }}

        .tab-content {{ display: none; animation: fadeIn 0.4s ease-out; }}
        .tab-content.active {{ display: block; }}

        /* ═══ TABLES ═══ */
        .table-container {{
            background: var(--bg-card);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 20px;
            animation: fadeInUp 0.6s ease-out;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            background: rgba(255, 255, 255, 0.03);
            padding: 14px 16px;
            text-align: left;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--text-secondary);
            font-weight: 600;
            border-bottom: 1px solid var(--border);
        }}

        td {{
            padding: 12px 16px;
            font-size: 0.85rem;
            border-bottom: 1px solid var(--border);
            color: var(--text-secondary);
        }}

        tr:hover td {{ background: rgba(255, 255, 255, 0.02); }}
        tr:last-child td {{ border-bottom: none; }}

        .verdict-badge, .severity-badge {{
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}

        .verdict-badge.pass {{ background: rgba(0,255,136,0.15); color: var(--accent-green); }}
        .verdict-badge.fail {{ background: rgba(239,68,68,0.15); color: var(--accent-red); }}
        .verdict-badge.warn {{ background: rgba(245,158,11,0.15); color: var(--accent-orange); }}

        .severity-badge.critical {{ background: rgba(239,68,68,0.2); color: #ff6b6b; }}
        .severity-badge.high {{ background: rgba(245,158,11,0.2); color: var(--accent-orange); }}
        .severity-badge.medium {{ background: rgba(59,130,246,0.15); color: var(--accent-blue); }}
        .severity-badge.low {{ background: rgba(255,255,255,0.05); color: var(--text-secondary); }}

        /* ═══ FOOTER ═══ */
        .footer {{
            text-align: center;
            padding: 40px 0;
            color: var(--text-secondary);
            font-size: 0.8rem;
            opacity: 0.5;
        }}

        /* ═══ RESPONSIVE ═══ */
        @media (max-width: 768px) {{
            .header h1 {{ font-size: 2rem; }}
            .hero-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .dataset-grid {{ grid-template-columns: 1fr; }}
            .chart-grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>

<!-- Particle Background -->
<div id="particles"></div>

<div class="container">

    <!-- Header -->
    <div class="header">
        <h1>DataTrust</h1>
        <div class="subtitle">Autonomous Data Integrity, Observability & Recovery</div>
        <div class="timestamp">
            <span class="live-dot"></span>
            Last updated: {timestamp}
        </div>
    </div>

    <!-- Hero Cards -->
    <div class="hero-grid">
        <div class="hero-card" style="animation-delay: 0.1s">
            <div class="hero-icon">🛡️</div>
            <div class="hero-value" style="color: {"var(--accent-green)" if avg_trust >= 80 else "var(--accent-orange)" if avg_trust >= 60 else "var(--accent-red)"}">{avg_trust:.1f}%</div>
            <div class="hero-label">Avg Trust Score</div>
            <div class="hero-sub">{len(trust_scores)} datasets validated</div>
        </div>
        <div class="hero-card" style="animation-delay: 0.2s">
            <div class="hero-icon">💓</div>
            <div class="hero-value" style="color: {"var(--accent-green)" if avg_health >= 80 else "var(--accent-orange)" if avg_health >= 60 else "var(--accent-red)"}">{avg_health:.1f}%</div>
            <div class="hero-label">Avg Health Score</div>
            <div class="hero-sub">{len(health_scores)} datasets scanned</div>
        </div>
        <div class="hero-card" style="animation-delay: 0.3s">
            <div class="hero-icon">🔍</div>
            <div class="hero-value" style="color: var(--accent-orange)">{total_anomalies}</div>
            <div class="hero-label">Anomalies Found</div>
            <div class="hero-sub">Across all datasets</div>
        </div>
        <div class="hero-card" style="animation-delay: 0.4s">
            <div class="hero-icon">🔧</div>
            <div class="hero-value" style="color: var(--accent-green)">{avg_recovery:.1f}%</div>
            <div class="hero-label">Recovery Rate</div>
            <div class="hero-sub">{total_actions} actions taken</div>
        </div>
        <div class="hero-card" style="animation-delay: 0.5s">
            <div class="hero-icon">✅</div>
            <div class="hero-value" style="color: var(--accent-cyan)">{total_rows_recovered:,}</div>
            <div class="hero-label">Rows Recovered</div>
            <div class="hero-sub">Automatically repaired</div>
        </div>
        <div class="hero-card" style="animation-delay: 0.6s">
            <div class="hero-icon">🚫</div>
            <div class="hero-value" style="color: var(--accent-red)">{total_quarantined:,}</div>
            <div class="hero-label">Quarantined</div>
            <div class="hero-sub">Unfixable records isolated</div>
        </div>
    </div>

    <!-- Charts -->
    <div class="section-header">
        <h2>📊 Score Overview</h2>
        <div class="section-line"></div>
    </div>

    <div class="chart-grid">
        <div class="chart-card" style="animation-delay: 0.2s">
            <h3>Trust Scores by Dataset</h3>
            <div class="bar-chart" id="trustChart"></div>
        </div>
        <div class="chart-card" style="animation-delay: 0.3s">
            <h3>Health Scores by Dataset</h3>
            <div class="bar-chart" id="healthChart"></div>
        </div>
    </div>

    <!-- Dataset Cards -->
    <div class="section-header">
        <h2>📋 Dataset Details</h2>
        <div class="section-line"></div>
    </div>

    <div class="dataset-grid">
        {dataset_cards}
    </div>

    <!-- Detail Tables -->
    <div class="section-header">
        <h2>🔎 Detailed Reports</h2>
        <div class="section-line"></div>
    </div>

    <div class="tabs">
        <button class="tab active" onclick="switchTab('validation')">Validation Checks</button>
        <button class="tab" onclick="switchTab('anomalies')">Anomalies</button>
        <button class="tab" onclick="switchTab('recovery')">Recovery Actions</button>
    </div>

    <div id="tab-validation" class="tab-content active">
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Dataset</th>
                        <th>Check</th>
                        <th>Verdict</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>{validation_rows}</tbody>
            </table>
        </div>
    </div>

    <div id="tab-anomalies" class="tab-content">
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Dataset</th>
                        <th>Type</th>
                        <th>Severity</th>
                        <th>Column</th>
                        <th>Affected</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>{anomaly_rows}</tbody>
            </table>
        </div>
    </div>

    <div id="tab-recovery" class="tab-content">
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Dataset</th>
                        <th>Action</th>
                        <th>Column</th>
                        <th>Rows Fixed</th>
                        <th>Strategy</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>{recovery_rows}</tbody>
            </table>
        </div>
    </div>

    <div class="footer">
        DataTrust v1.0 — Built by Khethukuthula Sabela — {timestamp}
    </div>
</div>

<script>
    // ═══ PARTICLE SYSTEM ═══
    (function() {{
        const container = document.getElementById('particles');
        const colors = ['#00ff88', '#3b82f6', '#8b5cf6', '#06b6d4'];
        for (let i = 0; i < 50; i++) {{
            const p = document.createElement('div');
            p.className = 'particle';
            const size = Math.random() * 4 + 1;
            p.style.width = size + 'px';
            p.style.height = size + 'px';
            p.style.left = Math.random() * 100 + '%';
            p.style.background = colors[Math.floor(Math.random() * colors.length)];
            p.style.animationDuration = (Math.random() * 20 + 15) + 's';
            p.style.animationDelay = (Math.random() * 20) + 's';
            container.appendChild(p);
        }}
    }})();

    // ═══ BAR CHARTS ═══
    function createBarChart(containerId, labels, data, colorFn) {{
        const container = document.getElementById(containerId);
        const max = Math.max(...data, 100);
        labels.forEach((label, i) => {{
            const group = document.createElement('div');
            group.className = 'bar-group';
            const height = (data[i] / max) * 100;
            const color = colorFn(data[i]);
            group.innerHTML =
                '<div class="bar-value">' + data[i] + '%</div>' +
                '<div class="bar" style="height:' + height + '%;background:linear-gradient(180deg,' + color + ',' + color + '88);animation-delay:' + (i*0.1) + 's"></div>' +
                '<div class="bar-label">' + label + '</div>';
            container.appendChild(group);
        }});
    }}

    function scoreColor(v) {{
        return v >= 80 ? '#00ff88' : v >= 60 ? '#f59e0b' : '#ef4444';
    }}

    const labels = {trust_chart_labels};
    createBarChart('trustChart', labels, {trust_chart_data}, scoreColor);
    createBarChart('healthChart', labels, {health_chart_data}, scoreColor);

    // ═══ TAB SWITCHING ═══
    function switchTab(name) {{
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById('tab-' + name).classList.add('active');
        event.target.classList.add('active');
    }}

    // ═══ INTERSECTION OBSERVER (animate on scroll) ═══
    const observer = new IntersectionObserver((entries) => {{
        entries.forEach(entry => {{
            if (entry.isIntersecting) {{
                entry.target.style.animationPlayState = 'running';
            }}
        }});
    }}, {{ threshold: 0.1 }});

    document.querySelectorAll('.hero-card, .chart-card, .dataset-card').forEach(el => {{
        observer.observe(el);
    }});
</script>

</body>
</html>"""

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"Dashboard generated: {output_path}")
        return output_path


if __name__ == "__main__":
    gen = DashboardGenerator()
    gen.generate()
    print("Open data/dashboard/index.html in your browser")

