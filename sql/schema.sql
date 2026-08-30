-- 1. dim_security
CREATE TABLE IF NOT EXISTS dim_security (
    security_id SERIAL PRIMARY KEY,
    ticker_symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. fact_daily_price
CREATE TABLE IF NOT EXISTS fact_daily_price (
    price_id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    security_id INT NOT NULL REFERENCES dim_security(security_id) ON DELETE CASCADE,
    close_price NUMERIC(10, 4) CHECK (close_price >= 0),
    trade_volume BIGINT CHECK (trade_volume >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (trade_date, security_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_daily_price_date_sec ON fact_daily_price (trade_date, security_id);

-- 3. fact_market_index
CREATE TABLE IF NOT EXISTS fact_market_index (
    index_id SERIAL PRIMARY KEY,
    trade_date DATE NOT NULL UNIQUE,
    aspi NUMERIC(10, 4) CHECK (aspi >= 0),
    sp_sl20 NUMERIC(10, 4) CHECK (sp_sl20 >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. fact_macro_indicator
CREATE TABLE IF NOT EXISTS fact_macro_indicator (
    macro_id SERIAL PRIMARY KEY,
    record_date DATE NOT NULL UNIQUE,
    usd_lkr_spot NUMERIC(10, 4) CHECK (usd_lkr_spot > 0),
    sdfr NUMERIC(5, 2),
    slfr NUMERIC(5, 2),
    ccpi NUMERIC(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. fact_price_forecast
CREATE TABLE IF NOT EXISTS fact_price_forecast (
    forecast_id SERIAL PRIMARY KEY,
    target_date DATE NOT NULL,
    security_id INT NOT NULL REFERENCES dim_security(security_id) ON DELETE CASCADE,
    predicted_close NUMERIC(10, 4),
    lower_bound NUMERIC(10, 4),
    upper_bound NUMERIC(10, 4),
    model_version VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (target_date, security_id)
);
CREATE INDEX IF NOT EXISTS idx_fact_price_forecast_date_sec ON fact_price_forecast (target_date, security_id);

-- Views
-- vw_daily_market_summary
CREATE OR REPLACE VIEW vw_daily_market_summary AS
SELECT 
    f.trade_date,
    d.ticker_symbol,
    d.company_name,
    d.sector,
    f.close_price,
    f.trade_volume,
    m.aspi,
    m.sp_sl20,
    mac.usd_lkr_spot
FROM fact_daily_price f
JOIN dim_security d ON f.security_id = d.security_id
LEFT JOIN fact_market_index m ON f.trade_date = m.trade_date
LEFT JOIN fact_macro_indicator mac ON f.trade_date = mac.record_date;

-- vw_forecast_vs_actual
CREATE OR REPLACE VIEW vw_forecast_vs_actual AS
SELECT 
    fc.target_date,
    d.ticker_symbol,
    fc.predicted_close,
    fc.lower_bound,
    fc.upper_bound,
    ac.close_price AS actual_close,
    (ac.close_price - fc.predicted_close) AS variance,
    CASE WHEN ac.close_price IS NOT NULL AND fc.predicted_close != 0 
         THEN ABS(ac.close_price - fc.predicted_close) / fc.predicted_close * 100 
         ELSE NULL END AS absolute_percentage_error
FROM fact_price_forecast fc
JOIN dim_security d ON fc.security_id = d.security_id
LEFT JOIN fact_daily_price ac ON fc.target_date = ac.trade_date AND fc.security_id = ac.security_id;
