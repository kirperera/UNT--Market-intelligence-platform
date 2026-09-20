import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import configparser
import os
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PostgresLoader:
    """Handles data loading and idempotent upserts to PostgreSQL."""
    
    def __init__(self):
        config = configparser.ConfigParser()
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../database.ini'))
        config.read(config_path)
        
        self.conn_params = {
            'host': config.get('postgresql', 'host'),
            'database': config.get('postgresql', 'database'),
            'user': config.get('postgresql', 'user'),
            'password': config.get('postgresql', 'password'),
            'port': config.get('postgresql', 'port')
        }

    def _get_connection(self):
        return psycopg2.connect(**self.conn_params)
        
    def _get_security_map(self):
        """Retrieves a dictionary mapping ticker_symbol to security_id."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ticker_symbol, security_id FROM dim_security")
                return {row[0]: row[1] for row in cursor.fetchall()}

    def upsert_security_metadata(self, df: pd.DataFrame):
        """Idempotent insert into the dim_security table."""
        if df.empty: return
        
        query = """
            INSERT INTO dim_security (ticker_symbol, company_name, sector)
            VALUES %s
            ON CONFLICT (ticker_symbol) DO UPDATE 
            SET company_name = EXCLUDED.company_name,
                sector = EXCLUDED.sector;
        """
        records = df[['ticker', 'name', 'sector']].values.tolist()
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, records)
                    logger.info(f"Successfully upserted {len(records)} records into dim_security.")
        except Exception as e:
            logger.error(f"Failed to upsert dim_security: {e}")
            raise

    def upsert_daily_price(self, df: pd.DataFrame):
        """Idempotent insert into the fact_daily_price table."""
        if df.empty: return
        
        sec_map = self._get_security_map()
        
        # Map ticker to security_id to maintain referential integrity
        valid_df = df[df['ticker'].isin(sec_map.keys())].copy()
        if valid_df.empty: 
            logger.warning("No valid security IDs found for daily price upsert.")
            return
            
        valid_df['security_id'] = valid_df['ticker'].map(sec_map)
        
        query = """
            INSERT INTO fact_daily_price (trade_date, security_id, close_price, trade_volume)
            VALUES %s
            ON CONFLICT (trade_date, security_id) DO UPDATE 
            SET close_price = EXCLUDED.close_price,
                trade_volume = EXCLUDED.trade_volume;
        """
        # Convert ISO timestamp to Date format for Postgres
        valid_df['date_only'] = pd.to_datetime(valid_df['trade_date_ms']).dt.date
        records = valid_df[['date_only', 'security_id', 'close', 'volume']].values.tolist()
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, records)
                    logger.info(f"Successfully upserted {len(records)} records into fact_daily_price.")
        except Exception as e:
            logger.error(f"Failed to upsert fact_daily_price: {e}")
            raise

    def upsert_macro_indicator(self, df: pd.DataFrame):
        """Idempotent insert into the fact_macro_indicator table."""
        if df.empty: return
        
        query = """
            INSERT INTO fact_macro_indicator (record_date, usd_lkr_spot, sdfr, slfr, ccpi)
            VALUES %s
            ON CONFLICT (record_date) DO UPDATE 
            SET usd_lkr_spot = EXCLUDED.usd_lkr_spot,
                sdfr = EXCLUDED.sdfr,
                slfr = EXCLUDED.slfr,
                ccpi = EXCLUDED.ccpi;
        """
        df = df.copy()
        df['date_only'] = pd.to_datetime(df['record_date_ms']).dt.date
        records = df[['date_only', 'usd_lkr_spot', 'sdfr', 'slfr', 'ccpi']].values.tolist()
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, records)
                    logger.info(f"Successfully upserted {len(records)} records into fact_macro_indicator.")
        except Exception as e:
            logger.error(f"Failed to upsert fact_macro_indicator: {e}")
            raise

    def upsert_price_forecast(self, df: pd.DataFrame, model_version: str = 'Prophet_v1'):
        """Idempotent insert into the fact_price_forecast table."""
        if df.empty: return
        
        sec_map = self._get_security_map()
        valid_df = df[df['ticker'].isin(sec_map.keys())].copy()
        if valid_df.empty: return
        
        valid_df['security_id'] = valid_df['ticker'].map(sec_map)
        valid_df['model_version'] = model_version
        valid_df['date_only'] = pd.to_datetime(valid_df['target_date']).dt.date
        
        query = """
            INSERT INTO fact_price_forecast (target_date, security_id, predicted_close, lower_bound, upper_bound, model_version)
            VALUES %s
            ON CONFLICT (target_date, security_id) DO UPDATE 
            SET predicted_close = EXCLUDED.predicted_close,
                lower_bound = EXCLUDED.lower_bound,
                upper_bound = EXCLUDED.upper_bound,
                model_version = EXCLUDED.model_version;
        """
        records = valid_df[['date_only', 'security_id', 'predicted_close', 'lower_bound', 'upper_bound', 'model_version']].values.tolist()
        
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    execute_values(cursor, query, records)
                    logger.info(f"Successfully upserted {len(records)} records into fact_price_forecast.")
        except Exception as e:
            logger.error(f"Failed to upsert fact_price_forecast: {e}")
            raise
