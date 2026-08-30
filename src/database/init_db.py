import psycopg2
import configparser
import os
import sys

# Add the project root to sys.path to ensure absolute imports work
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.logger import get_logger

logger = get_logger(__name__)

def init_db():
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), '../../database.ini')
    config.read(config_path)
    
    try:
        logger.info("Attempting to connect to PostgreSQL...")
        conn = psycopg2.connect(
            host=config.get('postgresql', 'host'),
            database=config.get('postgresql', 'database'),
            user=config.get('postgresql', 'user'),
            password=config.get('postgresql', 'password'),
            port=config.get('postgresql', 'port')
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        schema_path = os.path.join(os.path.dirname(__file__), '../../sql/schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        logger.info("Executing schema.sql...")
        cursor.execute(schema_sql)
        logger.info("Database schema initialized successfully.")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    init_db()
