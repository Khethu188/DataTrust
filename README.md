
# DataTrust

**Autonomous Data Integrity, Observability & Recovery Platform**

Built for the financial services sector — monitors, detects, and repairs data quality issues across 65,000+ South African financial records.

---

## What It Does

- **Validates** datasets against YAML contracts with trust scoring
- **Detects** anomalies using Isolation Forest, Z-Score, and IQR
- **Recovers** corrupted records automatically (91% recovery rate)
- **Quarantines** unfixable records to prevent downstream damage
- **Dashboards** with animated visualizations and real-time metrics

---

## Tech Stack

| Category | Technologies |
|----------|-------------|
| Language | Python 3.12 |
| Data | pandas, NumPy, SciPy |
| ML | scikit-learn (Isolation Forest) |
| Database | PostgreSQL 16 |
| Containers | Docker, Docker Compose, Nginx |
| Cloud | AWS Lambda, S3, RDS, Step Functions, API Gateway, CloudWatch, SNS |
| IaC | Terraform |
| CI/CD | GitHub Actions |
| Testing | pytest |

---

## Quick Start

### Docker (Recommended)

```bash
git clone https://github.com/Khethu188/DataTrust.git
cd DataTrust
docker compose up -d --build
docker compose exec datatrust python datatrust.py run
