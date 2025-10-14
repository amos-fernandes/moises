# rnn/data_handler_multi_asset.py (NOVO ARQUIVO)

import pandas as pd
import numpy as np
import yfinance as yf # Ou ccxt, dependendo da sua preferência de fonte de dados
import pandas_ta as ta
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

# Importar do seu config.py
# Assumindo que config.py está em ../config.py ou rnn/config.py
# Ajuste o import conforme sua estrutura.
# Se train_rnn_model.py e este data_handler estiverem na mesma pasta 'scripts',
# e config.py estiver um nível acima:
# from ..app/config.py import (
#     MULTI_ASSET_LIST, TIMEFRAME, DAYS_OF_DATA_TO_FETCH, 
#     # etc. para features a serem calculadas
# )
# Por agora, vamos definir aqui para exemplo:

# EXEMPLO DE CONFIGURAÇÃO (Mova para config.py depois)
MULTI_ASSET_SYMBOLS = {
    'crypto_eth': 'ETH-USD',  # yfinance ticker para ETH/USD
    'crypto_ada': 'ADA-USD',  # yfinance ticker para ADA/USD
    'stock_aapl': 'AAPL',     # NASDAQ
    'stock_petr': 'PETR4.SA'  # B3
} # Use os tickers corretos para yfinance ou ccxt
TIMEFRAME_YFINANCE = '1h' # yfinance suporta '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
# Para '1h', yfinance só retorna os últimos 730 dias. Para mais dados, use '1d'.
# Se usar ccxt, TIMEFRAME = '1h' como antes.
DAYS_TO_FETCH = 365 * 2 # 2 anos

# Lista das features base que você quer calcular para CADA ativo
# (as 19 que definimos antes)
INDIVIDUAL_ASSET_BASE_FEATURES = [
    'open', 'high', 'low', 'close', 'volume', # OHLCV originais são necessários para os cálculos
    'sma_10', 'rsi_14', 'macd', 'macds', 'atr', 'bbp', 'cci_37', 'mfi_37', 'adx_14',
    'volume_zscore', 'body_size', 'body_size_norm_atr', 'body_vs_avg_body',
    'log_return', 'buy_condition_v1', # 'sma_50' é calculada dentro de buy_condition_v1
    # As colunas _div_atr serão criadas a partir destas
]

# Features que serão normalizadas pelo ATR
COLS_TO_NORM_BY_ATR = ['open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd', 'body_size']


def fetch_single_asset_ohlcv_yf(ticker_symbol: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    """ Adaptação da sua função fetch_historical_ohlcv de financial_data_agent.py """
    print(f"Buscando dados para {ticker_symbol} com yfinance (period: {period}, interval: {interval})...")
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Para dados horários, o período máximo é geralmente 730 dias com yfinance
        # Se precisar de mais, considere '1d' e depois reamostre, ou use ccxt para cripto.
        if interval == '1h' and period.endswith('y') and int(period[:-1]) * 365 > 730:
             print(f"AVISO: yfinance pode limitar dados horários a 730 dias. Buscando 'max' para {interval} e depois fatiando.")
             data = ticker.history(interval=interval, period="730d") # Pega o máximo possível
        elif interval == '1d' and period.endswith('y'):
             data = ticker.history(period=period, interval=interval)
        else: # Para períodos menores ou outros intervalos
            data = ticker.history(period=period, interval=interval)

        if data.empty:
            print(f"Nenhum dado encontrado para {ticker_symbol}.")
            return pd.DataFrame()
        
        data.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume", "Adj Close": "adj_close"
        }, inplace=True)
        
        # Selecionar apenas as colunas OHLCV e garantir que o índice é DatetimeIndex UTC
        data = data[['open', 'high', 'low', 'close', 'volume']]
        if data.index.tz is None:
            data.index = data.index.tz_localize('UTC')
        else:
            data.index = data.index.tz_convert('UTC')

        # Para dados horários, yfinance pode retornar dados do fim de semana (sem volume)
        # e o último candle pode estar incompleto.
        # if interval == '1h':
        #     data = data[data['volume'] > 0] # Remover candles sem volume
            # data = data[:-1] # Remover o último candle que pode estar incompleto

        print(f"Dados coletados para {ticker_symbol}: {len(data)} linhas.")
        return data
    except Exception as e:
        print(f"Erro ao buscar dados para {ticker_symbol} com yfinance: {e}")
        return pd.DataFrame()


def calculate_all_features_for_single_asset(ohlcv_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Calcula todas as features base para um único ativo."""
    if ohlcv_df.empty: return None
    df = ohlcv_df.copy()
    print(f"Calculando features para ativo (shape inicial: {df.shape})...")

    if ta:
        df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
        df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
        macd_out = df.ta.macd(close='close', append=False)
        if macd_out is not None and not macd_out.empty:
            df['macd'] = macd_out.iloc[:,0]
            df['macds'] = macd_out.iloc[:,2] # Linha de sinal para buy_condition
        df.ta.atr(length=14, append=True, col_names=('atr',))
        df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp'))
        df.ta.cci(length=37, append=True, col_names=('cci_37',))
        df.ta.mfi(length=37, append=True, col_names=('mfi_37',))
        adx_out = df.ta.adx(length=14, append=False)
        if adx_out is not None and not adx_out.empty:
             df['adx_14'] = adx_out.iloc[:,0]
        
        rolling_vol_mean = df['volume'].rolling(window=20).mean()
        rolling_vol_std = df['volume'].rolling(window=20).std()
        df['volume_zscore'] = (df['volume'] - rolling_vol_mean) / (rolling_vol_std + 1e-9)

        df['body_size'] = abs(df['close'] - df['open'])
        
        # ATR precisa existir para as próximas. Drop NaNs do ATR primeiro.
        df.dropna(subset=['atr'], inplace=True)
        df_atr_valid = df[df['atr'] > 1e-9].copy()
        if df_atr_valid.empty:
            print("AVISO: ATR inválido para todas as linhas restantes, features _div_atr e body_size_norm_atr podem ser todas NaN ou vazias.")
            # Criar colunas com NaN para manter a estrutura
            df['body_size_norm_atr'] = np.nan
            for col in COLS_TO_NORM_BY_ATR:
                df[f'{col}_div_atr'] = np.nan
        else:
            df['body_size_norm_atr'] = df['body_size'] / df['atr'] # ATR já filtrado para > 1e-9
            for col in COLS_TO_NORM_BY_ATR:
                if col in df.columns:
                    df[f'{col}_div_atr'] = df[col] / (df['atr'] + 1e-9) # Adicionar 1e-9 aqui também por segurança
                else:
                    df[f'{col}_div_atr'] = np.nan


        df['body_vs_avg_body'] = df['body_size'] / (df['body_size'].rolling(window=20).mean() + 1e-9)
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))
        
        sma_50_series = df.ta.sma(length=50, close='close', append=False)
        if sma_50_series is not None: df['sma_50'] = sma_50_series
        else: df['sma_50'] = np.nan
        
        if all(col in df.columns for col in ['macd', 'macds', 'rsi_14', 'close', 'sma_50']):
            df['buy_condition_v1'] = ((df['macd'] > df['macds']) & (df['rsi_14'] > 50) & (df['close'] > df['sma_50'])).astype(int)
        else:
            df['buy_condition_v1'] = 0
        
        # Selecionar apenas as colunas que realmente usaremos como features base para o modelo
        # (incluindo as _div_atr e as originais que não foram normalizadas por ATR)
        # Esta lista de features é a que será passada para os scalers no script de treino.
        # E também as colunas que o rnn_predictor.py precisará ter antes de aplicar seus scalers.
        # Esta lista deve vir do config.py (BASE_FEATURE_COLS)
        
        # Exemplo:
        # final_feature_columns = [
        #    'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 
        #    'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 
        #    'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr', 
        #    'adx_14', 'volume_zscore', 'buy_condition_v1'
        # ] # Esta é a BASE_FEATURE_COLS do seu config.py

        # Verificar se todas as colunas em INDIVIDUAL_ASSET_BASE_FEATURES existem
        # (INDIVIDUAL_ASSET_BASE_FEATURES deve ser igual a config.BASE_FEATURE_COLS)
        current_feature_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col in df.columns]
        missing_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col not in df.columns]
        if missing_cols:
            print(f"AVISO: Colunas de features ausentes após cálculo: {missing_cols}. Usando apenas as disponíveis: {current_feature_cols}")
        
        df_final_features = df[current_feature_cols].copy()
        df_final_features.dropna(inplace=True)
        print(f"Features calculadas. Shape após dropna: {df_final_features.shape}. Colunas: {df_final_features.columns.tolist()}")
        return df_final_features
    else:
        print("pandas_ta não está disponível.")
        return None


def get_multi_asset_data_for_rl(
    asset_symbols_map: Dict[str, str], # Ex: {'crypto_eth': 'ETH-USD', ...}
    timeframe_yf: str, 
    days_to_fetch: int
) -> Optional[pd.DataFrame]:
    """
    Busca, processa e combina dados de múltiplos ativos em um DataFrame achatado.
    """
    all_asset_features_list = []
    min_data_length = float('inf') # Para truncar todos os DFs para o mesmo comprimento
    
    # Usar os tickers yfinance do asset_symbols_map
    for asset_key, yf_ticker in asset_symbols_map.items():
        print(f"\n--- Processando {asset_key} ({yf_ticker}) ---")
        # Para yfinance, '1h' retorna max 730d. '1d' retorna mais.
        # Se days_to_fetch for > 730 e timeframe_yf for '1h', ajuste o período.
        period_yf = f"{days_to_fetch}d" # yfinance aceita "Xd" para dias
        if timeframe_yf == '1h' and days_to_fetch > 730:
            print(f"AVISO: Para {timeframe_yf}, buscando no máximo 730 dias com yfinance para {yf_ticker}.")
            period_yf = "730d" 
        
        single_asset_ohlcv = fetch_single_asset_ohlcv_yf(yf_ticker, period=period_yf, interval=timeframe_yf)
        if single_asset_ohlcv.empty:
            print(f"AVISO: Sem dados OHLCV para {yf_ticker}, pulando este ativo.")
            continue
            
        single_asset_features = calculate_all_features_for_single_asset(single_asset_ohlcv)
        if single_asset_features is None or single_asset_features.empty:
            print(f"AVISO: Sem features calculadas para {yf_ticker}, pulando este ativo.")
            continue
        
        # Adicionar prefixo para achatar
        single_asset_features = single_asset_features.add_prefix(f"{asset_key}_")
        all_asset_features_list.append(single_asset_features)
        min_data_length = min(min_data_length, len(single_asset_features))

    if not all_asset_features_list:
        print("ERRO: Nenhum dado de feature de ativo foi processado com sucesso.")
        return None

    # Truncar todos os DataFrames para o mesmo comprimento (o do menor) ANTES de concatenar
    # para garantir alinhamento temporal mais robusto se os históricos tiverem começos diferentes.
    # Isso é feito alinhando pelo final dos DataFrames.
    if min_data_length == float('inf') or min_data_length == 0 :
        print("ERRO: min_data_length inválido, não é possível truncar DataFrames.")
        return None

    truncated_asset_features_list = [df.tail(min_data_length) for df in all_asset_features_list]

    # Concatenar todos os DataFrames de features (alinhados por timestamp/índice)
    # join='inner' garante que só teremos timestamps onde TODOS os ativos (que retornaram dados) têm dados.
    combined_df = pd.concat(truncated_asset_features_list, axis=1, join='inner')
    
    # Verificar se o resultado não está vazio
    if combined_df.empty:
        print("ERRO: DataFrame combinado está vazio após concatenação e join. Verifique os dados dos ativos.")
        return None
        
    # Drop quaisquer linhas que ainda possam ter NaNs após o join (improvável se cada df individual já foi tratado)
    combined_df.dropna(inplace=True)
    
    if combined_df.empty:
        print("ERRO: DataFrame combinado está vazio após dropna final.")
        return None

    print(f"\nDataFrame multi-ativo final gerado com shape: {combined_df.shape}")
    print(f"Exemplo de colunas: {combined_df.columns.tolist()[:10]}...") # Mostra as primeiras 10
    return combined_df


if __name__ == '__main__':
    print("Testando data_handler_multi_asset.py...")
    # Substitua pelos tickers yfinance reais que você quer usar
    test_assets = {
        'eth': 'ETH-USD', 
        'btc': 'BTC-USD',
        # 'aapl': 'AAPL' # Exemplo de ação
    }
    multi_asset_data = get_multi_asset_data_for_rl(
        test_assets, 
        timeframe_yf='1h', # Para teste rápido, período menor
        days_to_fetch=90   # Para teste rápido, período menor
    )

    if multi_asset_data is not None and not multi_asset_data.empty:
        print("\n--- Exemplo do DataFrame Multi-Ativo Gerado ---")
        print(multi_asset_data.head())
        print(f"\nShape: {multi_asset_data.shape}")
        print(f"\nInfo:")
        multi_asset_data.info()
    else:
        print("\nFalha ao gerar DataFrame multi-ativo.")