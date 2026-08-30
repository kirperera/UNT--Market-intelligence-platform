import pandas as pd
import numpy as np
from src.utils.logger import get_logger

logger = get_logger(__name__)

class FeatureEngineer:
    """Derives predictive technical and statistical features from raw market data."""
    
    @staticmethod
    def generate_technical_indicators(df: pd.DataFrame, price_col: str = 'close', date_col: str = 'trade_date_ms') -> pd.DataFrame:
        """
        Calculates moving averages, rolling volatility, and momentum indicators.
        Expects a DataFrame sorted chronologically.
        """
        logger.info("Engineering technical indicators (SMA, Volatility, Momentum)...")
        if df.empty:
            return df
            
        df_feat = df.copy()
        
        # Ensure data is sorted by date for accurate rolling window calculations
        if date_col in df_feat.columns:
            df_feat = df_feat.sort_values(by=date_col).reset_index(drop=True)
        
        # 1. Simple Moving Averages (30-day and 90-day)
        df_feat['sma_30'] = df_feat[price_col].rolling(window=30, min_periods=1).mean()
        df_feat['sma_90'] = df_feat[price_col].rolling(window=90, min_periods=1).mean()
        
        # 2. Rolling Volatility (30-day standard deviation of returns)
        df_feat['volatility_30d'] = df_feat[price_col].rolling(window=30, min_periods=1).std().fillna(0)
        
        # 3. Momentum (10-day Rate of Change as a percentage)
        df_feat['momentum_10d'] = df_feat[price_col].pct_change(periods=10).fillna(0) * 100
        
        logger.info("Feature engineering complete.")
        return df_feat
