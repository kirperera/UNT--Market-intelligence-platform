import requests
import pandas as pd
import time
from datetime import datetime
from src.utils.logger import get_logger
from src.extraction.validator import cleanse_and_validate

logger = get_logger(__name__)

class CSEExtractor:
    """Extractor module for the CSE Data Stream via live JSON endpoints."""
    
    BASE_URL = "https://www.cse.lk/api"

    
    def __init__(self):
        self.session = requests.Session()
        # Ensure we look like a standard browser to avoid getting blocked by their WAF
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        })
        
        # Since this specific endpoint requires querying one symbol at a time, 
        # we maintain a target portfolio of symbols to track.
        self.target_symbols = ["JKH.N0000", "COMB.N0000", "LOLC.N0000"]

    def fetch_security_metadata(self) -> pd.DataFrame:
        """Retrieves ticker metadata iteratively from companyInfoSummery."""
        url = f"{self.BASE_URL}/companyInfoSummery"
        data = []
        
        logger.info(f"Fetching live security metadata for {len(self.target_symbols)} symbols...")
        
        for symbol in self.target_symbols:
            try:
                payload = {"symbol": symbol}
                response = self.session.post(url, data=payload, timeout=10)
                response.raise_for_status()
                json_resp = response.json()
                
                if "reqSymbolInfo" in json_resp:
                    info = json_resp["reqSymbolInfo"]
                    data.append({
                        "ticker": info.get("symbol"),
                        "name": info.get("name"),
                        "sector": "Unknown" # Endpoint does not provide Sector
                    })
                
                # Sleep briefly to be polite and avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Failed to fetch metadata for {symbol}: {e}")
        
        df = pd.DataFrame(data)
        schema = {"ticker": "string", "name": "string", "sector": "string"}
        return cleanse_and_validate(df, schema)

    def fetch_daily_summary(self, trade_date: str) -> pd.DataFrame:
        """Retrieves live closing prices from companyInfoSummery."""
        url = f"{self.BASE_URL}/companyInfoSummery"
        data = []
        
        logger.info(f"Fetching live daily prices for trade date: {trade_date}")
        
        # The API doesn't return a timestamp, so we enforce the trade_date passed by the orchestrator
        dt_obj = datetime.strptime(trade_date, "%Y-%m-%d")
        timestamp_ms = int(dt_obj.timestamp() * 1000)
        
        for symbol in self.target_symbols:
            try:
                payload = {"symbol": symbol}
                response = self.session.post(url, data=payload, timeout=10)
                response.raise_for_status()
                json_resp = response.json()
                
                if "reqSymbolInfo" in json_resp:
                    info = json_resp["reqSymbolInfo"]
                    data.append({
                        "ticker": info.get("symbol"),
                        "trade_date_ms": timestamp_ms,
                        "close": info.get("lastTradedPrice"),
                        "volume": 0 # Endpoint does not provide VolumeTraded
                    })
                    
                time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Failed to fetch daily summary for {symbol}: {e}")
                
        df = pd.DataFrame(data)
        schema = {"close": "numeric", "volume": "numeric"}
        return cleanse_and_validate(df, schema, date_col="trade_date_ms")
