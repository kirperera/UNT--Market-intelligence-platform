import requests
import pandas as pd
from src.utils.logger import get_logger
from src.extraction.validator import cleanse_and_validate

logger = get_logger(__name__)

class CBSLExtractor:
    """Extractor module for the CBSL Macro Stream."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MarketIntelDataPipeline/1.0"})

    def fetch_macro_indicators(self, date: str) -> pd.DataFrame:
        """Retrieves USD/LKR spot rate, policy rates, and CCPI."""
        logger.info(f"Fetching CBSL macro indicators for date: {date}")
        try:
            # Placeholder for HTML/CSV/PDF parsing logic.
            # Mock data for initial pipeline staging
            data = [{
                "record_date_ms": 1693526400000, 
                "usd_lkr_spot": 320.50,
                "sdfr": 11.0,
                "slfr": 12.0,
                "ccpi": 195.2
            }]
            df = pd.DataFrame(data)
            schema = {
                "usd_lkr_spot": "numeric", 
                "sdfr": "numeric", 
                "slfr": "numeric", 
                "ccpi": "numeric"
            }
            
            return cleanse_and_validate(df, schema, date_col="record_date_ms")
            
        except Exception as e:
            logger.error(f"Failed to fetch CBSL macro data: {e}")
            raise
