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
        loader.upsert_macro_indicator(cbsl_macro_df)
        loader.upsert_daily_price(enriched_market_df)
        
        # Phase 5: Machine Learning Forecasting Engine
        logger.info("Initializing Machine Learning Forecasting Engine...")
        from src.ml.model import PriceForecaster
        
        all_forecasts = []
        tickers = enriched_market_df['ticker'].unique()
        
        for ticker in tickers:
            ticker_df = enriched_market_df[enriched_market_df['ticker'] == ticker].copy()
            if len(ticker_df) < 5: 
                continue # Skip if not enough history
                
            # Train the Prophet model
            forecaster = PriceForecaster(include_macro=True)
            forecaster.train(ticker_df, date_col='trade_date_ms', target_col='close')
            
            # Generate 30 days of future dates
            last_date = pd.to_datetime(ticker_df['trade_date_ms'], unit='ms', origin='unix').max()
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30)
            future_df = pd.DataFrame({'ds': future_dates})
            
            # Carry forward last known macro values for prediction
            future_df['usd_lkr_spot'] = ticker_df['usd_lkr_spot'].iloc[-1]
            future_df['sdfr'] = ticker_df['sdfr'].iloc[-1]
            
            # Predict and append
            forecast_res = forecaster.generate_forecast(future_df)
            forecast_res['ticker'] = ticker
            all_forecasts.append(forecast_res)

        if all_forecasts:
            master_forecast_df = pd.concat(all_forecasts, ignore_index=True)
            loader.upsert_price_forecast(master_forecast_df, model_version='Prophet_v1')
        
        # 4. Export to CSV (for Tableau Public compatibility)
        from src.etl.csv_exporter import CSVExporter
        exporter = CSVExporter()
        exporter.export_views()
        
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
