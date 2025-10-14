# agents/financial_data_agent.py
import yfinance as yf
import pandas as pd
from agno.agent import Agent # Commented out
from agno.models.anthropic import Claude # Commented out
from agno.tools.yfinance import YFinanceTools # Commented out

def get_stock_report(ticker="NVDA"): # Commented out
    agent = Agent(
        model=Claude(id="claude-3-7-sonnet-latest"),
        tools=[
            YFinanceTools(
                stock_price=True,
                analyst_recommendations=True,
                company_info=True,
                company_news=True,
            )
        ],
        instructions=[
            "Use tables to display data",
            "Only output the report, no other text",
        ],
        markdown=True,
    )
    return agent.get_response(f"Write a financial report on {ticker}")

def fetch_historical_ohlcv(ticker_symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetches historical OHLCV data for a given ticker symbol.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., "AAPL" for Apple on NASDAQ,
                             "PETR4.SA" for Petrobras on B3, "000001.SS" for SSE Composite Index).
        period (str): The period for which to download data (e.g., "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max").
        interval (str): The interval of data points (e.g., "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo").

    Returns:
        pd.DataFrame: A pandas DataFrame containing the OHLCV data, or an empty DataFrame if an error occurs.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        data = ticker.history(period=period, interval=interval)
        if data.empty:
            print(f"No data found for {ticker_symbol} for the given period/interval.")
            return pd.DataFrame()
        # Ensure column names are consistent (Yahoo Finance sometimes uses 'Adj Close')
        data.rename(columns={"Adj Close": "Adj_Close"}, inplace=True)
        return data
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return pd.DataFrame()

if __name__ == '__main__':
    # Example usage:
    # NASDAQ
    aapl_data = fetch_historical_ohlcv("AAPL", period="1mo", interval="1d")
    if not aapl_data.empty:
        print("\nAAPL Data (NASDAQ):")
        print(aapl_data.head())

    # B3 (Brazilian Stock Exchange) - Example: Petrobras
    petr4_data = fetch_historical_ohlcv("PETR4.SA", period="1mo", interval="1d")
    if not petr4_data.empty:
        print("\nPETR4.SA Data (B3):")
        print(petr4_data.head())

    # Asian Market - Example: Samsung Electronics (Korea Exchange)
    samsung_data = fetch_historical_ohlcv("005930.KS", period="1mo", interval="1d")
    if not samsung_data.empty:
        print("\n005930.KS Data (Samsung - KRX):")
        print(samsung_data.head())
    
    # Example for a non-existent ticker or error
    error_data = fetch_historical_ohlcv("NONEXISTENTTICKER", period="1d")
    if error_data.empty:
        print("\nSuccessfully handled non-existent ticker.")
