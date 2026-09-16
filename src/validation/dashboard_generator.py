
#!/usr/bin/env python3
"""
DataTrust — Dashboard & Report Generator
==========================================
Reads JSON reports from validation, anomaly detection, and
recovery engines, then generates a full interactive HTML
dashboard with charts, tables, and health indicators.

Usage:
    from dashboard_generator import DashboardGenerator
    gen = DashboardGenerator(reports_dir="data/reports")
    gen.generate("data/dashboard/index.html")
"""

import json
from datetime import datetime
from pathlib import Path


class DashboardGenerator:
    """Generates an interactive HTML dashboard from DataTrust reports."""

    def __init__(self, reports_dir="data/reports"):
        self.reports_dir = Path(reports_dir)
        self.validation_reports = {}
        self.anomaly_reports = {}
        self.recovery_reports = {}
        self._load_reports()

    def _load_reports(self):
        """Load all JSON reports."""
        for filepath in self.reports_dir.glob("*_validation.json"):
            with open(filepath) as f:
                data = json.load(f)
            self.validation_reports[data["dataset"]] = data

        for filepath in self.reports_dir.glob("*_anomalies.json"):
            with open(filepath) as f:
                data = json.load(f)
            self.anomaly_reports[data["dataset"]] = data

        for filepath in self.reports_dir.glob("*_recovery.json"):
            with open(filepath) as f:
                data = json.load(f)
            self.recovery_reports[data["dataset"]] = data

    def generate(self, output_path="data/dashboard/index.html"):
        """Generate the full HTML dashboard."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        html = self._build_html()

        with open(output, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"  Dashboard saved: {output}")
        return output

    def _build_html(self):
        """Build the complete HTML document."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calculate summary metrics
        datasets = sorted(set(
            list(self.validation_reports.keys()) +
            list(self.anomaly_reports.keys()) +
            list(self.recovery_reports.keys())
        ))

        trust_scores = {}
        health_scores = {}
        recovery_rates = {}

        for ds in datasets:
            if ds in self.validation_reports:
                trust_scores[ds] = self.validation_reports[ds].get("trust_score", 0)
            if ds in self.anomaly_reports:
                health_scores[ds] = self.anomaly_reports[ds].get("health_score", 0)
            if ds in self.recovery_reports:
                recovery_rates[ds] = self.recovery_reports[ds].get("recovery_rate", 0)

        avg_trust = sum(trust_scores.values()) / len(trust_scores) if trust_scores else 0
        avg_health = sum(health_scores.values()) / len(health_scores) if health_scores else 0
        avg_recovery = sum(recovery_rates.values()) / len(recovery_rates) if recovery_rates else 0

        total_anomalies = sum(
            r.get("summary", {}).get("total_anomalies", 0)
            for r in self.anomaly_reports.values()
        )
        total_fixed = sum(
            r.get("total_rows_fixed", 0)
            for r in self.recovery_reports.values()
        )
        total_quarantined = sum(
            r.get("quarantined_rows", 0)
            for r in self.recovery_reports.values()
        )

        # Build HTML sections
        hero_cards = self._build_hero_cards(
            avg_trust, avg_health, total_anomalies,
            total_fixed, total_quarantined, avg_recovery
        )
        trust_table = self._build_trust_score_table(datasets, trust_scores)
        anomaly_table = self._build_anomaly_table(datasets)
        recovery_table = self._build_recovery_table(datasets)
        validation_details = self._build_validation_details(datasets)
        anomaly_details = self._build_anomaly_details(datasets)
        recovery_details = self._build_recovery_details(datasets)
        trust_chart_data = self._build_chart_data(datasets, trust_scores, health_scores)
        recovery_chart_data = self._build_recovery_chart_data(datasets)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataTrust Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1117;
            color: #e1e4e8;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, #1a1f36 0%, #0d1117 100%);
            border: 1px solid #30363d;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 24px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.2em;
            background: linear-gradient(90deg, #58a6ff, #3fb950, #58a6ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 8px;
        }}
        .header .subtitle {{ color: #8b949e; font-size: 1.1em; }}
        .header .timestamp {{ color: #6e7681; font-size: 0.85em; margin-top: 8px; }}

        /* Hero Cards */
        .hero-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .hero-card {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        .hero-card .label {{ color: #8b949e; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; }}
        .hero-card .value {{ font-size: 2.2em; font-weight: 700; margin: 8px 0; }}
        .hero-card .sub {{ color: #6e7681; font-size: 0.8em; }}
        .green {{ color: #3fb950; }}
        .yellow {{ color: #d29922; }}
        .red {{ color: #f85149; }}
        .blue {{ color: #58a6ff; }}
        .purple {{ color: #bc8cff; }}
        .orange {{ color: #db6d28; }}

        /* Section */
        .section {{
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 24px;
            margin-bottom: 24px;
        }}
        .section h2 {{
            font-size: 1.4em;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #30363d;
        }}
        .section h3 {{
            font-size: 1.1em;
            margin: 16px 0 8px 0;
            color: #58a6ff;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
        }}
        th {{
            background: #0d1117;
            color: #58a6ff;
            padding: 10px 14px;
            text-align: left;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #30363d;
        }}
        td {{
            padding: 10px 14px;
            border-bottom: 1px solid #21262d;
        }}
        tr:hover {{ background: #1c2128; }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        .badge-pass {{ background: #0d2818; color: #3fb950; }}
        .badge-warn {{ background: #2d1b00; color: #d29922; }}
        .badge-fail {{ background: #2d0000; color: #f85149; }}
        .badge-critical {{ background: #3d0000; color: #ff6b6b; }}
        .badge-high {{ background: #2d1500; color: #db6d28; }}
        .badge-medium {{ background: #2d2200; color: #d29922; }}
        .badge-low {{ background: #0d2818; color: #3fb950; }}

        /* Progress Bar */
        .progress-bar {{
            background: #21262d;
            border-radius: 6px;
            height: 24px;
            overflow: hidden;
            position: relative;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75em;
            font-weight: 600;
            color: #fff;
            min-width: 40px;
        }}

        /* Chart Container */
        .chart-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin: 16px 0;
        }}
        .chart-box {{
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
        }}
        .chart-box h4 {{
            color: #8b949e;
            font-size: 0.9em;
            margin-bottom: 12px;
            text-align: center;
        }}
        .bar-chart {{ display: flex; flex-direction: column; gap: 8px; }}
        .bar-row {{ display: flex; align-items: center; gap: 10px; }}
        .bar-label {{ width: 100px; font-size: 0.85em; text-align: right; color: #8b949e; }}
        .bar-track {{ flex: 1; background: #21262d; border-radius: 4px; height: 20px; overflow: hidden; }}
        .bar-fill {{ height: 100%; border-radius: 4px; display: flex; align-items: center; padding-left: 8px; font-size: 0.75em; font-weight: 600; }}
        .bar-value {{ width: 50px; font-size: 0.85em; text-align: right; }}

        /* Detail blocks */
        .detail-item {{
            background: #0d1117;
            border: 1px solid #21262d;
            border-radius: 6px;
            padding: 10px 14px;
            margin: 6px 0;
            font-size: 0.9em;
        }}
        .detail-pass {{ border-left: 3px solid #3fb950; }}
        .detail-warn {{ border-left: 3px solid #d29922; }}
        .detail-fail {{ border-left: 3px solid #f85149; }}

        /* Tabs */
        .tab-container {{ margin: 16px 0; }}
        .tab-buttons {{ display: flex; gap: 4px; margin-bottom: 12px; flex-wrap: wrap; }}
        .tab-btn {{
            background: #0d1117;
            border: 1px solid #30363d;
            color: #8b949e;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85em;
        }}
        .tab-btn:hover {{ background: #1c2128; color: #e1e4e8; }}
        .tab-btn.active {{ background: #1f6feb; color: #fff; border-color: #1f6feb; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        /* Footer */
        .footer {{
            text-align: center;
            color: #6e7681;
            font-size: 0.8em;
            padding: 20px;
            border-top: 1px solid #21262d;
            margin-top: 24px;
        }}

        @media (max-width: 768px) {{
            .hero-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .chart-container {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>DataTrust Dashboard</h1>
            <div class="subtitle">Autonomous Data Integrity, Observability &amp; Recovery</div>
            <div class="timestamp">Generated: {timestamp}</div>
        </div>

        <!-- Hero Cards -->
        {hero_cards}

        <!-- Charts -->
        <div class="section">
            <h2>Data Health Overview</h2>
            <div class="chart-container">
                <div class="chart-box">
                    <h4>Trust Score by Dataset</h4>
                    {trust_chart_data}
                </div>
                <div class="chart-box">
                    <h4>Recovery: Before vs After</h4>
                    {recovery_chart_data}
                </div>
            </div>
        </div>

        <!-- Trust Score Table -->
        <div class="section">
            <h2>Validation Results</h2>
            {trust_table}
        </div>

        <!-- Anomaly Table -->
        <div class="section">
            <h2>Anomaly Detection Results</h2>
            {anomaly_table}
        </div>

        <!-- Recovery Table -->
        <div class="section">
            <h2>Recovery Results</h2>
            {recovery_table}
        </div>

        <!-- Validation Details -->
        <div class="section">
            <h2>Validation Details</h2>
            {validation_details}
        </div>

        <!-- Anomaly Details -->
        <div class="section">
            <h2>Anomaly Details</h2>
            {anomaly_details}
        </div>

        <!-- Recovery Details -->
        <div class="section">
            <h2>Recovery Action Details</h2>
            {recovery_details}
        </div>

        <!-- Footer -->
        <div class="footer">
            DataTrust v1.0 | Built by Khethukuthula | {timestamp}
        </div>
    </div>

    <script>
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                const group = btn.dataset.group;
                const target = btn.dataset.target;

                document.querySelectorAll(`.tab-btn[data-group="${{group}}"]`).forEach(b => b.classList.remove('active'));
                document.querySelectorAll(`.tab-content[data-group="${{group}}"]`).forEach(c => c.classList.remove('active'));

                btn.classList.add('active');
                document.getElementById(target).classList.add('active');
            }});
        }});
    </script>
</body>
</html>"""
        return html

    # ── Hero Cards ───────────────────────────────────────

    def _build_hero_cards(self, avg_trust, avg_health, total_anomalies,
                          total_fixed, total_quarantined, avg_recovery):
        trust_color = "green" if avg_trust >= 80 else "yellow" if avg_trust >= 60 else "red"
        health_color = "green" if avg_health >= 80 else "yellow" if avg_health >= 60 else "red"

        return f"""
        <div class="hero-grid">
            <div class="hero-card">
                <div class="label">Avg Trust Score</div>
                <div class="value {trust_color}">{avg_trust:.1f}%</div>
                <div class="sub">Validation Engine</div>
            </div>
            <div class="hero-card">
                <div class="label">Avg Health Score</div>
                <div class="value {health_color}">{avg_health:.1f}%</div>
                <div class="sub">Anomaly Detection</div>
            </div>
            <div class="hero-card">
                <div class="label">Anomalies Found</div>
                <div class="value orange">{total_anomalies}</div>
                <div class="sub">Across all datasets</div>
            </div>
            <div class="hero-card">
                <div class="label">Rows Fixed</div>
                <div class="value blue">{total_fixed:,}</div>
                <div class="sub">Auto-recovered</div>
            </div>
            <div class="hero-card">
                <div class="label">Quarantined</div>
                <div class="value purple">{total_quarantined:,}</div>
                <div class="sub">Unfixable records</div>
            </div>
            <div class="hero-card">
                <div class="label">Recovery Rate</div>
                <div class="value green">{avg_recovery:.1f}%</div>
                <div class="sub">Data preserved</div>
            </div>
        </div>"""

    # ── Trust Score Table ────────────────────────────────

    def _build_trust_score_table(self, datasets, trust_scores):
        rows = ""
        for ds in datasets:
            if ds not in self.validation_reports:
                continue
            report = self.validation_reports[ds]
            score = trust_scores.get(ds, 0)
            verdict = report.get("overall_verdict", "N/A")
            summary = report.get("summary", {})

            badge_class = "badge-pass" if verdict == "PASS" else "badge-warn" if verdict == "WARN" else "badge-fail"
            bar_color = "#3fb950" if score >= 80 else "#d29922" if score >= 60 else "#f85149"

            rows += f"""
            <tr>
                <td><strong>{ds}</strong></td>
                <td><span class="badge {badge_class}">{verdict}</span></td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{score}%;background:{bar_color}">{score}%</div>
                    </div>
                </td>
                <td class="green">{summary.get('passed', 0)}</td>
                <td class="yellow">{summary.get('warnings', 0)}</td>
                <td class="red">{summary.get('failed', 0)}</td>
                <td>{summary.get('total_checks', 0)}</td>
            </tr>"""

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Dataset</th>
                    <th>Verdict</th>
                    <th>Trust Score</th>
                    <th>Pass</th>
                    <th>Warn</th>
                    <th>Fail</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    # ── Anomaly Table ────────────────────────────────────

    def _build_anomaly_table(self, datasets):
        rows = ""
        for ds in datasets:
            if ds not in self.anomaly_reports:
                continue
            report = self.anomaly_reports[ds]
            health = report.get("health_score", 0)
            summary = report.get("summary", {})

            bar_color = "#3fb950" if health >= 80 else "#d29922" if health >= 60 else "#f85149"

            rows += f"""
            <tr>
                <td><strong>{ds}</strong></td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{max(health, 5)}%;background:{bar_color}">{health}%</div>
                    </div>
                </td>
                <td>{summary.get('total_anomalies', 0)}</td>
                <td class="red">{summary.get('critical', 0)}</td>
                <td class="orange">{summary.get('high', 0)}</td>
                <td class="yellow">{summary.get('medium', 0)}</td>
                <td class="green">{summary.get('low', 0)}</td>
                <td>{report.get('rows_scanned', 0):,}</td>
            </tr>"""

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Dataset</th>
                    <th>Health Score</th>
                    <th>Total</th>
                    <th>Critical</th>
                    <th>High</th>
                    <th>Medium</th>
                    <th>Low</th>
                    <th>Rows Scanned</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    # ── Recovery Table ───────────────────────────────────

    def _build_recovery_table(self, datasets):
        rows = ""
        for ds in datasets:
            if ds not in self.recovery_reports:
                continue
            report = self.recovery_reports[ds]
            rate = report.get("recovery_rate", 0)
            bar_color = "#3fb950" if rate >= 90 else "#d29922" if rate >= 70 else "#f85149"

            rows += f"""
            <tr>
                <td><strong>{ds}</strong></td>
                <td>{report.get('rows_before', 0):,}</td>
                <td>{report.get('rows_after', 0):,}</td>
                <td class="purple">{report.get('quarantined_rows', 0):,}</td>
                <td class="blue">{report.get('total_rows_fixed', 0):,}</td>
                <td>{report.get('total_actions', 0)}</td>
                <td>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width:{rate}%;background:{bar_color}">{rate}%</div>
                    </div>
                </td>
            </tr>"""

        return f"""
        <table>
            <thead>
                <tr>
                    <th>Dataset</th>
                    <th>Before</th>
                    <th>After</th>
                    <th>Quarantined</th>
                    <th>Rows Fixed</th>
                    <th>Actions</th>
                    <th>Recovery Rate</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    # ── Validation Details ───────────────────────────────

    def _build_validation_details(self, datasets):
        tabs_buttons = ""
        tabs_content = ""

        valid_datasets = [ds for ds in datasets if ds in self.validation_reports]
        for i, ds in enumerate(valid_datasets):
            active = "active" if i == 0 else ""
            tabs_buttons += f'<button class="tab-btn {active}" data-group="val" data-target="val-{ds}">{ds}</button>'

            report = self.validation_reports[ds]
            checks_html = ""
            for check in report.get("checks", []):
                verdict = check.get("verdict", "N/A")
                css_class = f"detail-{verdict.lower()}"
                badge_class = f"badge-{verdict.lower()}"
                checks_html += f"""
                <div class="detail-item {css_class}">
                    <span class="badge {badge_class}">{verdict}</span>
                    <strong>{check.get('check_name', '')}</strong> — {check.get('message', '')}
                </div>"""

            tabs_content += f'<div id="val-{ds}" class="tab-content {active}" data-group="val">{checks_html}</div>'

        return f"""
        <div class="tab-container">
            <div class="tab-buttons">{tabs_buttons}</div>
            {tabs_content}
        </div>"""

    # ── Anomaly Details ──────────────────────────────────

    def _build_anomaly_details(self, datasets):
        tabs_buttons = ""
        tabs_content = ""

        valid_datasets = [ds for ds in datasets if ds in self.anomaly_reports]
        for i, ds in enumerate(valid_datasets):
            active = "active" if i == 0 else ""
            tabs_buttons += f'<button class="tab-btn {active}" data-group="anom" data-target="anom-{ds}">{ds}</button>'

            report = self.anomaly_reports[ds]
            anomalies_html = ""

            if not report.get("anomalies"):
                anomalies_html = '<div class="detail-item detail-pass">No anomalies detected</div>'
            else:
                severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
                sorted_anomalies = sorted(
                    report["anomalies"],
                    key=lambda a: severity_order.get(a.get("severity", "LOW"), 4)
                )
                for anomaly in sorted_anomalies:
                    severity = anomaly.get("severity", "LOW")
                    badge_class = f"badge-{severity.lower()}"
                    css_class = "detail-fail" if severity in ("CRITICAL", "HIGH") else "detail-warn" if severity == "MEDIUM" else "detail-pass"
                    anomalies_html += f"""
                    <div class="detail-item {css_class}">
                        <span class="badge {badge_class}">{severity}</span>
                        <strong>[{anomaly.get('anomaly_type', '')}]</strong>
                        {anomaly.get('description', '')}
                    </div>"""

            tabs_content += f'<div id="anom-{ds}" class="tab-content {active}" data-group="anom">{anomalies_html}</div>'

        return f"""
        <div class="tab-container">
            <div class="tab-buttons">{tabs_buttons}</div>
            {tabs_content}
        </div>"""

    # ── Recovery Details ─────────────────────────────────

    def _build_recovery_details(self, datasets):
        tabs_buttons = ""
        tabs_content = ""

        valid_datasets = [ds for ds in datasets if ds in self.recovery_reports]
        for i, ds in enumerate(valid_datasets):
            active = "active" if i == 0 else ""
            tabs_buttons += f'<button class="tab-btn {active}" data-group="rec" data-target="rec-{ds}">{ds}</button>'

            report = self.recovery_reports[ds]
            actions_html = ""

            if not report.get("actions"):
                actions_html = '<div class="detail-item detail-pass">No recovery actions needed</div>'
            else:
                for action in report["actions"]:
                    actions_html += f"""
                    <div class="detail-item detail-warn">
                        <strong>[{action.get('action_type', '')}]</strong>
                        {action.get('description', '')}
                        <br><small style="color:#6e7681">Strategy: {action.get('strategy', 'N/A')} | Rows affected: {action.get('rows_affected', 0):,}</small>
                    </div>"""

            tabs_content += f'<div id="rec-{ds}" class="tab-content {active}" data-group="rec">{actions_html}</div>'

        return f"""
        <div class="tab-container">
            <div class="tab-buttons">{tabs_buttons}</div>
            {tabs_content}
        </div>"""

    # ── Chart Data (Bar Charts via HTML/CSS) ─────────────

    def _build_chart_data(self, datasets, trust_scores, health_scores):
        bars = ""
        for ds in datasets:
            trust = trust_scores.get(ds, 0)
            health = health_scores.get(ds, 0)
            trust_color = "#3fb950" if trust >= 80 else "#d29922" if trust >= 60 else "#f85149"
            health_color = "#58a6ff" if health >= 80 else "#d29922" if health >= 60 else "#f85149"

            bars += f"""
            <div class="bar-row">
                <div class="bar-label">{ds}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{max(trust, 3)}%;background:{trust_color}">{trust:.0f}%</div>
                </div>
            </div>"""

        return f'<div class="bar-chart">{bars}</div>'

    def _build_recovery_chart_data(self, datasets):
        bars = ""
        for ds in datasets:
            if ds not in self.recovery_reports:
                continue
            report = self.recovery_reports[ds]
            before = report.get("rows_before", 0)
            after = report.get("rows_after", 0)
            quarantined = report.get("quarantined_rows", 0)

            if before == 0:
                continue

            after_pct = (after / before) * 100
            quarantine_pct = (quarantined / before) * 100

            bars += f"""
            <div class="bar-row">
                <div class="bar-label">{ds}</div>
                <div class="bar-track">
                    <div class="bar-fill" style="width:{after_pct}%;background:#3fb950">{after:,}</div>
                </div>
                <div class="bar-value" style="color:#bc8cff">-{quarantined:,}</div>
            </div>"""

        return f'<div class="bar-chart">{bars}</div>'

