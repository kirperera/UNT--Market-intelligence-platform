import pandas as pd
from typing import Optional

def cleanse_and_validate(df: pd.DataFrame, schema: dict, date_col: Optional[str] = None) -> pd.DataFrame:
    """
    Validates the dataframe against a schema, normalizes dates to ISO 8601 (Asia/Colombo),
    and handles missing/null values.
    """
    if df.empty:
        return df

    # Create a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # 1. Normalize dates to ISO 8601 in Asia/Colombo timezone
    if date_col and date_col in df.columns:
        df[date_col] = pd.to_datetime(df[date_col], unit='ms', origin='unix').dt.tz_localize('UTC').dt.tz_convert('Asia/Colombo')
        df[date_col] = df[date_col].dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    # 2. Type casting, schema enforcement, and missing value handling
    for col, dtype in schema.items():
        if col in df.columns:
            if dtype == 'numeric':
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Forward fill then fill with 0 to handle market holidays or non-trading days
                df[col] = df[col].ffill().fillna(0)
            elif dtype == 'string':
                df[col] = df[col].astype(str).fillna('')
                
    return df
