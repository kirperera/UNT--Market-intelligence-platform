# UNT Market Intelligence Platform

This project establishes a fully automated Extract, Transform, Load (ETL) pipeline that links corporate equity data from the Colombo Stock Exchange (CSE) with macroeconomic indicators from the Central Bank of Sri Lanka (CBSL). It features an integrated Machine Learning module (Prophet) to generate 30-day forward price forecasts.

---

## 1. System Architecture & Prerequisites
*   **Language:** Python 3.11+
*   **Database:** PostgreSQL 16+
*   **BI Tool:** Tableau Public (via CSV flat-file integration)
*   **Core Libraries:** `pandas`, `requests`, `prophet`, `pdfplumber`, `apscheduler`

---

## 2. Local / On-Premise Deployment Workflow (Option 3)

This deployment strategy keeps the database and execution environment strictly on a local/on-premise server (e.g., Mac Mini or local Linux server) for maximum data privacy and zero cloud costs.

### Step 2.1: Database Provisioning
1. Ensure PostgreSQL is running locally on port `5432`.
2. Configure your credentials in `database.ini` at the root of the project.
3. Instantiate the schema and seed initial data:
   ```bash
   psql -U postgres -d your_db_name -f sql/schema.sql
   python src/database/init_db.py
   python src/database/seed_mock_data.py
   ```

### Step 2.2: Environment Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2.3: Automating the Pipeline (Daemonizing)
The pipeline uses `APScheduler` to trigger the batch job daily at 17:30 LKT. To ensure it runs continuously in the background on your local server, use `nohup` or `pm2`:

**Using `nohup` (Mac/Linux Native):**
```bash
nohup python src/etl/orchestrator.py > pipeline_logs.out 2>&1 &
```
*To verify it is running in the background, check the logs via `tail -f pipeline_logs.out`.*

---

## 3. Operational Runbook

### 3.1. Manual Override Protocol
If the scheduled 17:30 batch fails or you need to backfill data immediately without waiting for the scheduler, you can force a manual pipeline execution:
```bash
python src/etl/orchestrator.py --run-now
```

### 3.2. Failure Recovery Procedures
*   **API Timeouts / HTTP 404s:** 
    *   *Symptom:* The CSE API goes down or the CBSL PDF isn't published.
    *   *Recovery:* The extractors are designed to fall back to default metrics or log warnings gracefully. Rerun the pipeline using the `--run-now` flag the next morning when the endpoints are back online.
*   **Database Lock/Connection Drops:**
    *   *Symptom:* `psycopg2.OperationalError`.
    *   *Recovery:* Ensure the local Postgres service is running (`brew services restart postgresql` on Mac or `sudo systemctl restart postgresql` on Linux).

### 3.3. ML Model Retraining Cadence
The `PriceForecaster` model evaluates its own drift and automatically triggers a retraining cycle every **Friday**. No manual intervention is required. It holds out the last 30 days to validate MAPE/RMSE accuracy before deploying the new JSON model to `src/ml/models/`.

### 3.4. Tableau Dashboard Refresh
The orchestrator automatically outputs flattened CSV views to `dashboard/data/`.
1. Open the `.twb` file in Tableau Desktop.
2. Navigate to **Data > Refresh All Extracts**.
3. (Optional) Publish the refreshed workbook to Tableau Public.
