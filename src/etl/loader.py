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

    def upsert_security_metadata(self, df: pd.DataFrame):
        """Idempotent insert into the dim_security table."""
        if df.empty: 
            return
        
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
