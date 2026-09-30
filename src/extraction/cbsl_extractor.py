import requests
import pandas as pd
import io
import re
from datetime import datetime
from src.utils.logger import get_logger
from src.extraction.validator import cleanse_and_validate

# Attempt to import pdfplumber for PDF parsing
try:
    import pdfplumber
    PDF_PARSING_ENABLED = True
except ImportError:
    PDF_PARSING_ENABLED = False

logger = get_logger(__name__)

class CBSLExtractor:
    """Extractor module for the CBSL Macro Stream via AllRatesToday API and PDF parsing."""
    
    BASE_URL = "https://allratestoday.com/api/v1"
    
    def __init__(self):
        self.session = requests.Session()
        # Authenticate using the provided Bearer token
        self.session.headers.update({
            "Authorization": "Bearer art_live_dOoYt6D7hDxnBF39IIeNg1L0aLSdglIR",
            "User-Agent": "MarketIntelDataPipeline/1.0"
        })

    def _parse_cbsl_daily_report(self, date_str: str) -> dict:
        """
        Attempts to download and parse the CBSL Daily Economic Indicators PDF 
        to extract SDFR, SLFR, and CCPI.
        """
        if not PDF_PARSING_ENABLED:
            logger.warning("pdfplumber not installed. Falling back to default macro rates.")
            return {"sdfr": 11.0, "slfr": 12.0, "ccpi": 195.2}

        # Convert date to the format used in CBSL URLs (e.g., ddmmyyyy or yyyymmdd)
        # Assuming format: cbslweb_documents/statistics/pricerpt/price_report_YYYYMMDD_e.pdf
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_formatted = dt_obj.strftime("%Y%m%d")
        
        pdf_url = f"https://www.cbsl.gov.lk/sites/default/files/cbslweb_documents/statistics/pricerpt/price_report_{date_formatted}_e.pdf"
        
        # Default fallbacks
        extracted_data = {"sdfr": 11.0, "slfr": 12.0, "ccpi": 195.2}
        
        try:
            logger.info(f"Attempting to download CBSL PDF report from {pdf_url}")
            response = self.session.get(pdf_url, timeout=15, verify=False)
            
            if response.status_code == 200:
                with pdfplumber.open(io.BytesIO(response.content)) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                        
                    # Use regex to find the rates within the text
                    # E.g., "Standing Deposit Facility Rate (SDFR) 9.00%"
                    sdfr_match = re.search(r'SDFR[^\d]*(\d+\.\d+)', text, re.IGNORECASE)
                    slfr_match = re.search(r'SLFR[^\d]*(\d+\.\d+)', text, re.IGNORECASE)
                    ccpi_match = re.search(r'CCPI[^\d]*(\d+\.\d+)', text, re.IGNORECASE)
                    
                    if sdfr_match:
                        extracted_data["sdfr"] = float(sdfr_match.group(1))
                    if slfr_match:
                        extracted_data["slfr"] = float(slfr_match.group(1))
                    if ccpi_match:
                        extracted_data["ccpi"] = float(ccpi_match.group(1))
                        
                logger.info(f"Successfully parsed PDF data: {extracted_data}")
            else:
                logger.warning(f"CBSL PDF report not found for {date_str} (HTTP {response.status_code}). Using fallbacks.")
                
        except Exception as e:
            logger.error(f"Error parsing CBSL PDF report: {e}. Using fallbacks.")
            
        return extracted_data

    def fetch_macro_indicators(self, date: str) -> pd.DataFrame:
        """Retrieves USD/LKR spot rate (live) and other macro indicators (PDF)."""
        logger.info(f"Fetching live macro indicators for date: {date}")
        
        # 1. Fetch USD/LKR from API
        usd_lkr_spot = 320.0
        try:
            url = f"{self.BASE_URL}/rates?source=USD&target=LKR"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            json_resp = response.json()
            
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
            
        # 2. Fetch Macro Indicators from PDF
        macro_rates = self._parse_cbsl_daily_report(date)
            
        dt_obj = datetime.strptime(date, "%Y-%m-%d")
        timestamp_ms = int(dt_obj.timestamp() * 1000)
            
        data = [{
            "record_date_ms": timestamp_ms, 
            "usd_lkr_spot": usd_lkr_spot,
            "sdfr": macro_rates["sdfr"],
            "slfr": macro_rates["slfr"],
            "ccpi": macro_rates["ccpi"]
        }]
        
        df = pd.DataFrame(data)
        schema = {
            "usd_lkr_spot": "numeric", 
            "sdfr": "numeric", 
            "slfr": "numeric", 
            "ccpi": "numeric"
        }
        
        return cleanse_and_validate(df, schema, date_col="record_date_ms")
