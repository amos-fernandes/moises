import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path

def load_and_preprocess_data(filepath, window_size=30, features=None):
    # 1. Carregar os dados
    df = pd.read_csv(filepath)
    print("🔍 Dados carregados:", df.shape)

    # 2. Conversão de data
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(['Ticker', 'Date'])

    # 3. Seleção de colunas
    if features is None:
        features = ['Open', 'Close', 'Volume', 'Asset Turnover', 'Current Ratio',
                    'Debt/Equity Ratio', 'Gross Margin', 'Net Profit Margin', 'ROA - Return On Assets']

    df = df[['Ticker', 'Date'] + features].dropna()

    # 4. Normalização por Ticker
    scalers = {}
    grouped = df.groupby('Ticker')
    sequences = []
    tickers = []

    for ticker, group in grouped:
        scaler = MinMaxScaler()
        values = scaler.fit_transform(group[features])
        scalers[ticker] = scaler

        closes = group['Close'].values  # Para prever retorno futuro

        # 5. Janela deslizante para sequências temporais
        for i in range(len(values) - window_size):
            seq = values[i:i+window_size]
            label = closes[i+window_size]  # Preço após a janela
            sequences.append(seq)
            tickers.append(ticker)



    X = np.array([s for s, _ in sequences])
    y = np.array([l for _, l in sequences])

 

    X = np.array(sequences)
    print(f"✅ Total de sequências geradas: {X.shape[0]} | Formato da entrada: {X.shape}")
    return X, tickers, scalers

if __name__ == "__main__":
    filepath = Path("sp500_ratios.csv")
    X, tickers, scalers = load_and_preprocess_data(filepath)
