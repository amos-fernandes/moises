
# agents/financial_data_agent.py
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para permitir importações relativas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import ASSET_CONFIGS, ALL_ASSET_SYMBOLS, WINDOW_SIZE, NUM_FEATURES_PER_ASSET, FINNHUB_API_KEY, TWELVE_DATA_API_KEY, ALPHA_VANTAGE_API_KEY
from scripts.data_handler_multi_asset import get_multi_asset_data_for_rl

# A chave da API da Alpha Vantage será passada para a função de coleta de dados


def get_all_portfolio_data_for_rl(timeframe: str = "1h", days_to_fetch: int = 365*2) -> pd.DataFrame:

    """
    Orchestrates fetching and processing of historical data for all assets defined in config.py
    for use in the RL environment.

    Args:
        timeframe (str): The interval of data points (e.g., "1h", "1d").
        days_to_fetch (int): Number of days of historical data to fetch.


    Returns:
        pd.DataFrame: A combined pandas DataFrame with features for all assets, or an empty DataFrame.
    """
    print(f"Fetching and processing data for {len(ALL_ASSET_SYMBOLS)} assets using Twelve Data/Finnhub/Alpha Vantage...")
    
    combined_df = get_multi_asset_data_for_rl(
        asset_configs=ASSET_CONFIGS,
        timeframe_av=timeframe, # Usar timeframe_av para Alpha Vantage
        days_to_fetch=days_to_fetch,
        api_key=ALPHA_VANTAGE_API_KEY,
        finnhub_api_key=FINNHUB_API_KEY,
        twelve_data_api_key=TWELVE_DATA_API_KEY
    )

    if combined_df is None or combined_df.empty:
        print("Failed to get combined multi-asset data.")
        return pd.DataFrame()
    
    print(f"Successfully fetched and processed combined data with shape: {combined_df.shape}")
    return combined_df


if __name__ == '__main__':
    print("\nTestando a função get_all_portfolio_data_for_rl com Twelve Data/Finnhub/Alpha Vantage...")
    all_data = get_all_portfolio_data_for_rl(timeframe="1d", days_to_fetch=365)
    if not all_data.empty:
        print("\n--- Exemplo do DataFrame Multi-Ativo Gerado (Twelve Data/Finnhub/Alpha Vantage) ---")
        print(all_data.head())
        print(f"Shape of combined data: {all_data.shape}")
    else:
        print("Failed to retrieve combined portfolio data from Twelve Data/Finnhub/Alpha Vantage.")

