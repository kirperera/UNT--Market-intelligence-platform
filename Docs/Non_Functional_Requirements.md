# Non-Functional Requirements (NFRs)

## 1. Data Latency & Freshness
*   **Batch Processing Window:** The automated ETL batch process must execute daily post-market close (e.g., 17:00 LKT).
*   **Data Freshness:** Data surfaced on the BI dashboard must reflect the prior trading day's closing figures by 08:00 LKT the following morning.
*   **Pipeline Execution Time:** The end-to-end ETL process (Extraction, Validation, Transformation, Load) should complete within 60 minutes to allow ample time for retries in case of transient failures.

## 2. Database Performance Benchmarks
*   **Query Response Time:** Analytical queries powering the Power BI dashboard (aggregating daily market summaries and forecasting views) must return results within 3-5 seconds.
*   **Concurrency:** The database should comfortably support up to 10 concurrent read connections from the BI layer without noticeable performance degradation.
*   **Index Utilization:** Time-series retrieval operations must hit composite B-Tree indexes on `(trade_date, security_id)` to optimize range-scan performance.

## 3. System Availability & Reliability
*   **Uptime:** The ETL orchestrator and database services should maintain a 99% uptime during operational hours (08:00 - 18:00 LKT).
*   **Fault Tolerance:** In the event of a source endpoint outage (e.g., CSE API downtime), the pipeline must fail gracefully, alert administrators, and retry extraction automatically on the next scheduled interval without duplicating records.
*   **Data Retention:** Raw historical data and model forecasts must be retained for a minimum of 5 years to support long-term trend analysis and model retraining.

## 4. Security & Compliance
*   **Access Control:** Read/write access to PostgreSQL must be strictly segregated by role. The ETL pipeline will use a dedicated service account, while the BI tool will use a read-only account.
*   **Data Sensitivity:** Since the data (market indices, prices) is public, encryption at rest is recommended but not strictly mandatory. Environment variables must be used to manage database credentials (e.g., `database.ini` excluded from source control).
