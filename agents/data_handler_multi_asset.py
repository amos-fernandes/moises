import pandas as pd
import numpy as np
import yfinance as yf # / ccxt,
import pandas_ta as ta
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from config import *

#(Todos do Config)
INDIVIDUAL_ASSET_BASE_FEATURES = BASE_FEATURES_PER_ASSET_INPUT

# Features que serão normalizadas pelo ATR
COLS_TO_NORM_BY_ATR = ['open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd', 'body_size']
#----------------------------------
# -- New get multi asset data for rl
# ... (imports e outras funções como antes) ...
def get_multi_asset_data_for_rl(
    asset_symbols_map: Dict[str, str], 
    timeframe_yf: str, 
    days_to_fetch: int,
    logger_instance # Adicionar logger como parâmetro
) -> Optional[pd.DataFrame]: # Adicionar logger como parâmetro

    all_asset_features_list: List[pd.DataFrame] = [] # Tipagem para clareza
    min_data_length = float('inf')
    print(all_asset_features_list)
    
    #logger_instance.info(f"Iniciando get_multi_asset_data_for_rl para: {list(asset_symbols_map.keys())}")

    for asset_key, yf_ticker in asset_symbols_map.items():
       
        single_asset_ohlcv = fetch_single_asset_ohlcv_yf(yf_ticker, period=f"{days_to_fetch}d", interval=timeframe_yf) # Passar logger se a função aceitar

    
        single_asset_features = calculate_all_features_for_single_asset(single_asset_ohlcv)#, logger_instance) 
        
        if single_asset_features is None or single_asset_features.empty:
            logger_instance.warning(f"Sem features calculadas para {yf_ticker}, pulando.")
            continue
        
        #logger_instance.info(f"Features para {asset_key} shape: {single_asset_features.shape}, Index Min: {single_asset_features.index.min()}, Index Max: {single_asset_features.index.max()}")
        
        # Garantir que o índice é DatetimeIndex e UTC para todos antes de adicionar prefixo e à lista
        if not isinstance(single_asset_features.index, pd.DatetimeIndex):
            single_asset_features.index = pd.to_datetime(single_asset_features.index)
        if single_asset_features.index.tz is None:
            single_asset_features.index = single_asset_features.index.tz_localize('UTC')
        else:
            single_asset_features.index = single_asset_features.index.tz_convert('UTC')

        single_asset_features = single_asset_features.add_prefix(f"{asset_key}_")
        all_asset_features_list.append(single_asset_features)
        min_data_length = min(min_data_length, len(single_asset_features))

    if not all_asset_features_list:
        logger_instance.error("Nenhum DataFrame de feature de ativo foi adicionado à lista.")
        return None

    if min_data_length == float('inf') or min_data_length < WINDOW_SIZE: # Adicionada checagem de WINDOW_SIZE
        logger_instance.error(f"min_data_length inválido ({min_data_length}) ou menor que WINDOW_SIZE ({WINDOW_SIZE}). Não é possível truncar/usar.")
        return None

    #logger_instance.info(f"Menor número de linhas de dados encontrado (min_data_length): {min_data_length}")
    
    # Truncar para garantir que todos os DFs tenham o mesmo comprimento ANTES do concat
    # E que tenham pelo menos min_data_length.
    # É importante que os ÍNDICES de data/hora se sobreponham para o join='inner' funcionar.
    # Apenas pegar o .tail() pode não alinhar os timestamps se os DFs tiverem começos diferentes.
    
    # Melhor abordagem: encontrar o índice comum mais recente e o mais antigo.
    if not all_asset_features_list: # Checagem se a lista não ficou vazia por algum motivo
        logger_instance.error("all_asset_features_list está vazia antes do alinhamento de índice.")
        return None
    print(all_asset_features_list)
    # Alinhar DataFrames por um índice comum antes de concatenar
    # 1. Encontrar o primeiro timestamp comum a todos
    # 2. Encontrar o último timestamp comum a todos
    # Confiar no join='inner' do concat, mas garantir que os DFs são válidos.

    # Vamos simplificar e manter o truncamento pelo tail, mas com mais logs
    # e garantir que são DataFrames.
    
    truncated_asset_features_list = []
    for i, df_asset in enumerate(all_asset_features_list):
        if isinstance(df_asset, pd.DataFrame) and len(df_asset) >= min_data_length:
            truncated_df = df_asset.tail(min_data_length)
            #logger_instance.info(f"  DF truncado {i} ({df_asset.columns[0].split('_')[0]}): shape {truncated_df.shape}, ")
                                 #f"Index Min: {truncated_df.index.min()}, Max: {truncated_df.index.max()}")
            truncated_asset_features_list.append(truncated_df)
        else:
            asset_name_debug = df_asset.columns[0].split('_')[0] if isinstance(df_asset, pd.DataFrame) and not df_asset.empty else f"DF_{i}"
            logger_instance.warning(f"  DF {asset_name_debug} inválido ou muito curto (len: {len(df_asset) if isinstance(df_asset, pd.DataFrame) else 'N/A'}) para truncamento. Pulando.")

    if not truncated_asset_features_list:
        #ogger_instance.error("Nenhum DataFrame válido restou após truncamento para concatenar.")
        return None
    
    # Se houver apenas UM DataFrame na lista, não precisa concatenar, apenas retorna ele.
    if len(truncated_asset_features_list) == 1:
        #logger_instance.info("Apenas um DataFrame de ativo processado, retornando-o diretamente.")
        combined_df = truncated_asset_features_list[0]
    else:
        #logger_instance.info(f"Concatenando {len(truncated_asset_features_list)} DataFrames de ativos com join='inner'...")
        try:
            combined_df = pd.concat(truncated_asset_features_list, axis=1, join='outer')
            print(combined_df)
        except Exception as e_concat:
            logger_instance.error(f"ERRO CRÍTICO durante pd.concat: {e_concat}", exc_info=True)
            return None
        

    combined_df.fillna(method='ffill', inplace=True)
    # Depois do ffill, ainda pode haver NaNs no início se algum ativo começar depois dos outros.
    if not combined_df.empty:
        #logger_instance.info(f"Shape após ffill: {combined_df.shape}. Buscando primeiro/último índice válido...")
        first_valid_index = combined_df.first_valid_index()
        last_valid_index = combined_df.last_valid_index()

    if pd.isna(first_valid_index) or pd.isna(last_valid_index):
        print("Não foi possível determinar first/last_valid_index após ffill.")
        return None
    
    print(f"Primeiro índice válido: {first_valid_index}, Último índice válido: {last_valid_index}")
    combined_df = combined_df.loc[first_valid_index:last_valid_index]
    print(f"Shape após fatiar por first/last valid index: {combined_df.shape}")
    
    # Um dropna final pode ser necessário se o ffill não pegou tudo (improvável, mas seguro)
    combined_df.dropna(inplace=True) 
    print(f"Shape após dropna final (pós-fatiamento): {combined_df.shape}")
    print("Imprimindo DF_COMBINED com index ")
    print(combined_df)

    #logger_instance.info(f"Tipo de combined_df após concat: {type(combined_df)}")
    if not isinstance(combined_df, pd.DataFrame):
        logger_instance.error(f"combined_df NÃO é um DataFrame após concat. Tipo: {type(combined_df)}")
        return None
    

    return combined_df
   




def fetch_single_asset_ohlcv_yf(ticker_symbol: str, period: str = "2y", interval: str = "1h") -> pd.DataFrame:
    """ Adaptação da sua função fetch_historical_ohlcv de financial_data_agent.py """
    print(f"Buscando dados para {ticker_symbol} com yfinance (period: {period}, interval: {interval})...")
    try:
        ticker = yf.Ticker(ticker_symbol)
        # Para dados horários, o período máximo é geralmente 730 dias com yfinance
        # Considerar '1d' e depois reamostrar, ou usar ccxt para cripto. (Módulo de Cripto)
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

    # GARANTIR que a coluna 'close' original será preservada no DataFrame final
    if 'close' in df.columns:
        df['close'] = df['close']  # redundante, mas deixa explícito que não será sobrescrita

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
        df['volume'] = df['volume'].astype(float) 
        df.ta.mfi(length=37, close='close', high='high', low='low', volume='volume', append=True, col_names=('mfi_37',))
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
        
        
        # final_feature_columns = [
        #    'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr', 
        #    'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 
        #    'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr', 
        #    'adx_14', 'volume_zscore', 'buy_condition_v1'
        # ] # Esta é a BASE_FEATURE_COLS do config.py

        # Verificar se todas as colunas em INDIVIDUAL_ASSET_BASE_FEATURES existem
        # (INDIVIDUAL_ASSET_BASE_FEATURES deve ser igual a config.BASE_FEATURE_COLS)
        current_feature_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col in df.columns]
        missing_cols = [col for col in INDIVIDUAL_ASSET_BASE_FEATURES if col not in df.columns]
        if missing_cols:
            print(f"AVISO: Colunas de features ausentes após cálculo: {missing_cols}. Usando apenas as disponíveis: {current_feature_cols}")
        # GARANTIR que 'close' (preço original) está presente nas features finais
        if 'close' not in current_feature_cols and 'close' in df.columns:
            current_feature_cols.append('close')
        
        df_final_features = df[current_feature_cols].copy()
        df_final_features.dropna(inplace=True)
        print(f"Features calculadas. Shape após dropna: {df_final_features.shape}. Colunas: {df_final_features.columns.tolist()}")
        return df_final_features
    else:
        print("pandas_ta não está disponível.")
        return None


if __name__ == '__main__':
    print("Testando data_handler_multi_asset.py...")
    
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