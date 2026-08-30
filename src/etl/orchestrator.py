import sys
import os
import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

# Ensure Python finds the src module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.extraction.cse_extractor import CSEExtractor
from src.extraction.cbsl_extractor import CBSLExtractor
from src.etl.transformer import DataTransformer
from src.etl.loader import PostgresLoader
from src.utils.logger import get_logger

logger = get_logger(__name__)

def run_daily_batch():
    """Executes the end-to-end ETL sequence (Extract -> Validate -> Transform -> Load)."""
    logger.info("Starting daily ETL batch run...")
    
    try:
        # 1. Extract & Validate (Validation is handled within extractors)
        cse = CSEExtractor()
        cbsl = CBSLExtractor()
        
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        
        sec_meta_df = cse.fetch_security_metadata()
        cse_daily_df = cse.fetch_daily_summary(today_str)
        cbsl_macro_df = cbsl.fetch_macro_indicators(today_str)
        
        # 2. Transform
        enriched_market_df = DataTransformer.align_market_and_macro(
            cse_daily_df, cbsl_macro_df
        )
        
        # 3. Load
        loader = PostgresLoader()
        loader.upsert_security_metadata(sec_meta_df)
        # Note: Further upsert methods (e.g., upsert_daily_price) would be called here.
        
        logger.info("ETL batch completed successfully.")
        
    except Exception as e:
        logger.error(f"ETL pipeline failed during execution: {e}")
        # Placeholder for alerting logic (e.g., sending an email or Slack message)

if __name__ == "__main__":
    # Check if a flag was passed to run once immediately
    if len(sys.argv) > 1 and sys.argv[1] == '--run-now':
        run_daily_batch()
    else:
        # 4. Schedule via APScheduler
        logger.info("Initializing ETL Scheduler...")
        scheduler = BlockingScheduler(timezone="Asia/Colombo")
        
        # Schedule to run daily at 17:30 LKT (post-market close)
        scheduler.add_job(run_daily_batch, 'cron', day_of_week='mon-fri', hour=17, minute=30)
        
        logger.info("Scheduler started. Waiting for the next batch window at 17:30 LKT...")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler shutting down...")
