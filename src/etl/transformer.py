import pandas as pd
from src.utils.logger import get_logger

logger = get_logger(__name__)

class DataTransformer:
    """Handles the transformation and joining of extracted datasets."""
    
    @staticmethod
    def align_market_and_macro(cse_df: pd.DataFrame, macro_df: pd.DataFrame, 
                               cse_date_col="trade_date_ms", macro_date_col="record_date_ms") -> pd.DataFrame:
        """
        Joins CSE equity data with CBSL macro data on their respective temporal keys.
        """
        logger.info("Transforming and aligning market data with macroeconomic indicators...")
        
        if cse_df.empty or macro_df.empty:
            logger.warning("One of the input dataframes is empty. Skipping join.")
            return cse_df

        # Perform a left join to enrich the daily market data with macro indicators
        merged_df = pd.merge(
            cse_df, 
            macro_df, 
            left_on=cse_date_col, 
            right_on=macro_date_col, 
            how="left"
        )
        
        # Drop redundant date columns from the macro dataset if they differ in name but mean the same thing
        if macro_date_col in merged_df.columns and cse_date_col != macro_date_col:
            merged_df = merged_df.drop(columns=[macro_date_col])
            
        logger.info(f"Transformation complete. Resulting schema: {list(merged_df.columns)}")
        return merged_df
