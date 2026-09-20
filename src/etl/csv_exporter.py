import psycopg2
import pandas as pd
import configparser
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.utils.logger import get_logger

logger = get_logger(__name__)

class CSVExporter:
    """Exports analytical views from PostgreSQL to CSV files for Tableau Public."""
    
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
        
        self.export_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../dashboard/data'))
        os.makedirs(self.export_dir, exist_ok=True)

    def export_views(self):
        logger.info("Exporting analytical views to CSV for Tableau Public...")
        try:
            with psycopg2.connect(**self.conn_params) as conn:
                # Export daily market summary
                query_market = "SELECT * FROM vw_daily_market_summary"
                # Using pandas to easily dump SQL to CSV
                df_market = pd.read_sql_query(query_market, conn)
                market_csv_path = os.path.join(self.export_dir, 'daily_market_summary.csv')
                df_market.to_csv(market_csv_path, index=False)
                
                # Export forecast vs actual
                query_forecast = "SELECT * FROM vw_forecast_vs_actual"
                df_forecast = pd.read_sql_query(query_forecast, conn)
                forecast_csv_path = os.path.join(self.export_dir, 'forecast_vs_actual.csv')
                df_forecast.to_csv(forecast_csv_path, index=False)
                
                logger.info(f"Successfully exported {len(df_market)} market records and {len(df_forecast)} forecast records to {self.export_dir}")
                
        except Exception as e:
            logger.error(f"Failed to export CSVs: {e}")
            raise

if __name__ == "__main__":
    exporter = CSVExporter()
    exporter.export_views()
