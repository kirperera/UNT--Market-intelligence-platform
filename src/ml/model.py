import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_percentage_error, root_mean_squared_error
from src.utils.logger import get_logger

logger = get_logger(__name__)

class PriceForecaster:
    """Time-series forecasting engine utilizing Facebook Prophet with exogenous regressors."""
    
    def __init__(self, include_macro: bool = True):
        # Initialize Prophet with yearly seasonality; daily seasonality is generally irrelevant for daily-close stock data
        self.model = Prophet(daily_seasonality=False, yearly_seasonality=True)
        
        self.include_macro = include_macro
        if self.include_macro:
            # Adding macroeconomic variables as exogenous regressors
            self.model.add_regressor('usd_lkr_spot')
            self.model.add_regressor('sdfr')

    def train(self, df: pd.DataFrame, date_col: str = 'trade_date_ms', target_col: str = 'close'):
        """Trains the Prophet model on historical data."""
        logger.info("Formatting training data for Prophet...")
        
        # Prophet strictly requires columns to be named 'ds' (datestamp) and 'y' (target)
        train_df = df.rename(columns={date_col: 'ds', target_col: 'y'}).copy()
        
        # Drop rows where target or regressors are NaN
        cols_to_check = ['ds', 'y']
        if self.include_macro:
            cols_to_check.extend(['usd_lkr_spot', 'sdfr'])
        train_df = train_df.dropna(subset=cols_to_check)

        logger.info("Training the forecasting model...")
        self.model.fit(train_df)
        logger.info("Model training complete.")

    def generate_forecast(self, future_df: pd.DataFrame) -> pd.DataFrame:
        """Generates prospective price distributions with confidence intervals."""
        logger.info("Generating prospective forecasts...")
        
        # Note: future_df must contain 'ds' and any exogenous regressors for the future dates
        forecast = self.model.predict(future_df)
        
        # Extracting target date, predicted value, and the confidence bounds
        result_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
            columns={
                'ds': 'target_date',
                'yhat': 'predicted_close',
                'yhat_lower': 'lower_bound',
                'yhat_upper': 'upper_bound'
            }
        )
        return result_df

    @staticmethod
    def evaluate(actual: pd.Series, predicted: pd.Series) -> dict:
        """Quantifies forecast accuracy using MAPE and RMSE."""
        # Align series to ensure no NaN mismatch
        valid_idx = actual.notna() & predicted.notna()
        act = actual[valid_idx]
        pred = predicted[valid_idx]

        if len(act) == 0:
            logger.warning("No valid data available for evaluation.")
            return {"mape": None, "rmse": None}

        mape = mean_absolute_percentage_error(act, pred)
        rmse = root_mean_squared_error(act, pred)
        
        logger.info(f"Model Evaluation Results - MAPE: {mape:.4f} ({mape*100:.2f}%), RMSE: {rmse:.4f}")
        return {"mape": mape, "rmse": rmse}
