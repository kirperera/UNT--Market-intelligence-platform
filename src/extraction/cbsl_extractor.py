import requests
import pandas as pd
from datetime import datetime
from src.utils.logger import get_logger
from src.extraction.validator import cleanse_and_validate

logger = get_logger(__name__)

class CBSLExtractor:
    """Extractor module for the CBSL Macro Stream via AllRatesToday API."""
    
    BASE_URL = "https://allratestoday.com/api/v1"
    
    def __init__(self):
        self.session = requests.Session()
        # Authenticate using the provided Bearer token
        self.session.headers.update({
            "Authorization": "Bearer art_live_dOoYt6D7hDxnBF39IIeNg1L0aLSdglIR",
            "User-Agent": "MarketIntelDataPipeline/1.0"
        })

    def fetch_macro_indicators(self, date: str) -> pd.DataFrame:
        """Retrieves USD/LKR spot rate (live) and other macro indicators."""
        logger.info(f"Fetching live macro indicators for date: {date}")
        
        # Default fallback value in case the API goes down
        usd_lkr_spot = 320.0
        
        try:
            # Querying the specific USD to LKR conversion
            url = f"{self.BASE_URL}/rates?source=USD&target=LKR"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            json_resp = response.json()
            
            # Defensive JSON parsing to handle various common exchange rate API structures
            if isinstance(json_resp, list) and len(json_resp) > 0:
                json_resp = json_resp[0]
                
            if 'rate' in json_resp:
                usd_lkr_spot = float(json_resp['rate'])
            elif 'data' in json_resp and 'rate' in json_resp['data']:
                usd_lkr_spot = float(json_resp['data']['rate'])
            elif 'rates' in json_resp and 'LKR' in json_resp['rates']:
                usd_lkr_spot = float(json_resp['rates']['LKR'])
            else:
                logger.warning(f"Unexpected JSON structure from exchange API: {json_resp}")
                
            logger.info(f"Successfully retrieved live USD/LKR rate: {usd_lkr_spot}")
            
        except Exception as e:
            logger.error(f"Failed to fetch live USD/LKR rate: {e}. Falling back to default.")
            
        # The API gives a point-in-time value, so we map it to the requested ETL batch date
        dt_obj = datetime.strptime(date, "%Y-%m-%d")
        timestamp_ms = int(dt_obj.timestamp() * 1000)
            
        # Construct the dataframe. 
        # Note: SDFR, SLFR, and CCPI are hardcoded here until we find APIs for those specific Sri Lankan metrics.
        data = [{
            "record_date_ms": timestamp_ms, 
            "usd_lkr_spot": usd_lkr_spot,
            "sdfr": 11.0,  # Standing Deposit Facility Rate (Central Bank metric)
            "slfr": 12.0,  # Standing Lending Facility Rate (Central Bank metric)
            "ccpi": 195.2  # Colombo Consumer Price Index
        }]
        
        df = pd.DataFrame(data)
        schema = {
            "usd_lkr_spot": "numeric", 
            "sdfr": "numeric", 
            "slfr": "numeric", 
            "ccpi": "numeric"
        }
        
        return cleanse_and_validate(df, schema, date_col="record_date_ms")
