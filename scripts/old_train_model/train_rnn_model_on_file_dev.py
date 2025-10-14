
import os
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import pandas_ta as ta # Para indicadores
import joblib # Para salvar scalers
import matplotlib.pyplot as plt # Para visualização
import ccxt # Para buscar dados (opcional)
from datetime import datetime, timedelta, timezone
from tensorflow.keras import regularizers

# --- Parâmetros de Configuração ---
# Dados
SYMBOL = 'BTC/USDT'  # Par de cripto para treinar
TIMEFRAME = '1h'     # Timeframe dos candles ('1m', '5m', '1h', '1d')
# Quantos dados buscar (2 anos de dados de 1h)

DAYS_OF_DATA_TO_FETCH = 365 * 2
LIMIT_PER_FETCH = 1000 # Limite de candles por chamada da API da exchange

# Features e Janela
WINDOW_SIZE = 60       # Número de passos de tempo na sequência de entrada
# Features que usaremos (OHLCV + Indicadores)
# A ordem aqui é importante para o escalonamento e para o modelo.
# O nome das colunas após o escalonamento será:'close_scaled', 'volume_scaled'...
# No nosso rnn_predictor.py, usamos EXPECTED_FEATURES_ORDER com nomes _scaled.
# Preparar as colunas base e depois escalar.
BASE_FEATURE_COLS = [
    'close_div_atr',        # Normalizado
    'volume_div_atr',       # Normalizado
    #'sma_10_div_atr',       # Normalizado
    'rsi_14',               # Índice (0-100), não precisa normalizar pelo ATR
    #'macd_div_atr',         # Normalizado
    'atr',                  # Average True Range
    'bbp' ] # Antes do scaling
    
# O NÚMERO DE FEATURES QUE O MODELO REALMENTE VERÁ APÓS O SCALING
NUM_FEATURES = len(BASE_FEATURE_COLS)

# Alvo da Predição (Target)
# Prever se o preço vai subir N passos no futuro
PREDICTION_HORIZON = 5 # Previsão de  subida em 5 horas
PRICE_CHANGE_THRESHOLD = 0.005 # Considerar "subiu" se o preço aumentar > 0.5%

# Modelo RNN
LSTM_UNITS = [32,16] # Unidades nas camadas LSTM
DENSE_UNITS = 16
DROPOUT_RATE = 0.1
LEARNING_RATE = 0.001

# Treinamento
BATCH_SIZE = 64
EPOCHS = 100 

# Patch para Salvar
MODEL_SAVE_DIR = "app/model" 
MODEL_NAME = "model.h5"
PRICE_VOL_SCALER_NAME = "price_volume_scaler.joblib"
INDICATOR_SCALER_NAME = "indicator_scaler.joblib"
# único scaler para todas as features:
# ALL_FEATURES_SCALER_NAME = "all_features_scaler.joblib"


def fetch_ohlcv_data_ccxt(symbol, timeframe, days_to_fetch, limit_per_call=1000):
    """Busca dados OHLCV de uma exchange usando ccxt."""
    exchange = ccxt.binance() # Ou outra exchange de sua preferência
    print(f"Buscando dados para {symbol} na {exchange.id} com timeframe {timeframe}...")
    

    all_ohlcv = []
    

    since_dt = datetime.now(timezone.utc) - timedelta(days=days_to_fetch)
    since = exchange.parse8601(since_dt.isoformat())
    
    while True:
        try:
            print(f"Buscando {limit_per_call} candles desde {exchange.iso8601(since)}...")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit_per_call)
            if not ohlcv: break
            all_ohlcv.extend(ohlcv)
            last_timestamp_in_batch = ohlcv[-1][0]
            since = last_timestamp_in_batch + exchange.rateLimit
            print(f"Coletados {len(ohlcv)} candles. Último: {exchange.iso8601(last_timestamp_in_batch)}. Total: {len(all_ohlcv)}")
            if len(ohlcv) < limit_per_call: break
            
            if len(all_ohlcv) >= (days_to_fetch * 24) and last_timestamp_in_batch > exchange.parse8601(datetime.now(timezone.utc).isoformat()):
                break
            
            all_ohlcv.extend(ohlcv)
            last_timestamp_in_batch = ohlcv[-1][0]
            
            # Para evitar buscar o mesmo candle, avançar 1ms do último timestamp
            since = last_timestamp_in_batch + exchange.rateLimit # Adiciona o rateLimit para a próxima busca
            
            print(f"Coletados {len(ohlcv)} candles. Último timestamp: {exchange.iso8601(last_timestamp_in_batch)}. Total: {len(all_ohlcv)}")

            # Condição de parada se já buscamos dados suficientes ou se a exchange retorna menos que o limite
            if len(ohlcv) < limit_per_call:
                break
            if len(all_ohlcv) >= (days_to_fetch * (24 if timeframe.endswith('h') else 1440 if timeframe.endswith('m') else 1)): # Estimativa
                if all_ohlcv[-1][0] > exchange.parse8601(datetime.utcnow().isoformat()): # Se passou do tempo atual
                    break
            
            # Pequena pausa para respeitar rate limits, ccxt já faz isso com enableRateLimit=True
            # Pausa extra para buscar muitos dados.
            #time.sleep(exchange.rateLimit / 1000) 

        except ccxt.NetworkError as e:
            print(f"Erro de rede CCXT: {e}. Tentando novamente em 5s...")
            # time.sleep(5)
        except ccxt.ExchangeError as e:
            print(f"Erro da Exchange CCXT: {e}. Parando busca.")
            break
        except Exception as e:
            print(f"Erro inesperado: {e}. Parando busca.")
            break
            
    if not all_ohlcv:
        raise ValueError("Nenhum dado OHLCV foi coletado. Verifique o símbolo, timeframe ou a exchange.")

    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    print(f"Total de {len(df)} candles OHLCV coletados para {symbol}.")
    return df


def calculate_targets(df, horizon=PREDICTION_HORIZON, threshold=PRICE_CHANGE_THRESHOLD):
    """
    Cria o alvo da predição.
    Retorna 1 se o preço futuro (horizonte) subir mais que o threshold, 0 caso contrário.
    """

     # Shift close para pegar o 'close' do próximo candle para comparar com o 'open' atual
    df['next_close'] = df['close'].shift(-1)
    # O alvo é 1 se o próximo candle fechou acima do seu próprio open (candle verde)
    # Ou você pode querer prever se o próximo close será maior que o close ATUAL
    # df['target'] = (df['next_close'] > df['close']).astype(int) # Prever se o próximo close é > close atual
    # Vamos tentar prever se o próximo candle em si é de alta:
    df['next_open'] = df['open'].shift(-1) # Precisamos do open do próximo candle
    df['target_raw'] = df['next_close'] - df['next_open'] # Variação do próximo candle
    df['target'] = (df['target_raw'] > 0).astype(int) # 1 se o próximo candle for de alta
    
    # Remover a última linha que terá NaN para next_close e next_open
    df.dropna(subset=['next_close', 'next_open', 'target'], inplace=True)
    return df


    """ df['future_price'] = df['close'].shift(-horizon)
    df['price_change_pct'] = (df['future_price'] - df['close']) / df['close']
    df['target'] = (df['price_change_pct'] > threshold).astype(int)
    df.dropna(inplace=True) # Remove future_price é NaN
    return df """


def create_sequences(data, target_col, window_size, feature_cols):
    """Cria sequências de dados e seus alvos correspondentes."""
    X, y = [], []
    # Assegura que estamos trabalhando com um NumPy array para slicing eficiente
    data_values = data[feature_cols].values
    target_values = data[target_col].values

    for i in range(len(data_values) - window_size):
        X.append(data_values[i:(i + window_size)])
        y.append(target_values[i + window_size -1]) # Alvo correspondente ao final da janela
        # Ou, se o alvo foi calculado com shift(-horizon), o alvo já está alinhado
        # y.append(target_values[i + window_size -1 + horizon -1]) # Se o target é para o futuro da janela
    return np.array(X), np.array(y)


def build_lstm_model(input_shape, lstm_units, dense_units, dropout_rate, initial_learning_rate):
    """Constrói o modelo LSTM com regularização L2.""" # Descrição atualizada
    
    
    model = tf.keras.Sequential() # DEFINO O MODELO 
    
    L2_REG = 0.0001 # Valor para regularização L2 

    # Camadas LSTM
    for i, units in enumerate(lstm_units):
        return_sequences = True if i < len(lstm_units) - 1 else False
        if i == 0:
            model.add(tf.keras.layers.LSTM(units, 
                                           return_sequences=return_sequences, 
                                           input_shape=input_shape,
                                           kernel_regularizer=regularizers.l2(L2_REG)
                                           ))
        else:
            model.add(tf.keras.layers.LSTM(units, 
                                           return_sequences=return_sequences,
                                           kernel_regularizer=regularizers.l2(L2_REG) 
                                           
                                           ))
        model.add(tf.keras.layers.Dropout(dropout_rate))
        
    # Camada Densa
    model.add(tf.keras.layers.Dense(dense_units, 
                                    activation='relu',
                                    kernel_regularizer=regularizers.l2(L2_REG) # ADICIONADO AQUI
                                    ))
    model.add(tf.keras.layers.Dropout(dropout_rate))
    
    # Camada de Saída (classificação binária)
    model.add(tf.keras.layers.Dense(1, activation='sigmoid'))
    
    optimizer = tf.keras.optimizers.Adam(learning_rate=initial_learning_rate ,amsgrad=True, clipvalue=1.0)
    model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy'])
    model.summary()
    return model


def main():
    print("Iniciando script de treinamento da RNN...")

    # --- 1. Carregar Dados ---
    # Opção A: Buscar com CCXT
    try:
        ohlcv_df = fetch_ohlcv_data_ccxt(SYMBOL, TIMEFRAME, DAYS_OF_DATA_TO_FETCH, LIMIT_PER_FETCH)
    except Exception as e:
        print(f"Falha ao buscar dados com CCXT: {e}")
        print("Verifique se você tem um arquivo 'data.csv' no mesmo diretório para fallback.")
        # Opção B: Carregar de CSV (se a busca falhar ou preferir)
        try:
            ohlcv_df = pd.read_csv("data.csv", index_col='timestamp', parse_dates=True)
            print("Dados carregados de data.csv")
        except FileNotFoundError:
            print("Erro: data.csv não encontrado. Forneça dados para treinamento.")
            return
    
    if ohlcv_df.empty:
        print("DataFrame de dados está vazio. Encerrando.")
        return




    # ---     
    # >>> SLIDAR COM ÍNDICES DUPLICADOS <<<
    print(f"Shape original do ohlcv_df: {ohlcv_df.shape}")
    if not ohlcv_df.index.is_unique:
        print("AVISO: Timestamps duplicados encontrados no índice. Removendo duplicatas (mantendo a primeira ocorrência)...")
        # Mantém a primeira ocorrência de cada timestamp duplicado
        ohlcv_df = ohlcv_df[~ohlcv_df.index.duplicated(keep='first')]
        # Alternativa: manter a última ocorrência:
        # ohlcv_df = ohlcv_df[~ohlcv_df.index.duplicated(keep='last')]
        # Alternativa: fazer uma média das linhas duplicadas (mais complexo se os valores OHLCV diferirem)
        print(f"Shape do ohlcv_df após remover duplicatas: {ohlcv_df.shape}")
    
    # Opcional: Reordenar o índice apenas para garantir, embora o fetch_ohlcv geralmente retorne ordenado
    ohlcv_df.sort_index(inplace=True)
    # >>> FIM DA SEÇÃO DE ÍNDICES DUPLICADOS <<<


     # >>> SEÇÃO DE LIMPEZA ROBUSTA DO ÍNDICE E TIMESTAMPS <<<
    print(f"Shape original do ohlcv_df: {ohlcv_df.shape}")
    
    # Passo 1: Mover o índice (timestamp) para uma coluna temporária
    if isinstance(ohlcv_df.index, pd.DatetimeIndex):
        ohlcv_df.reset_index(inplace=True) # Move o índice para uma coluna 'timestamp' (ou 'index')
    
    # Renomear a coluna de timestamp para 'ts' para evitar conflito se já houver 'timestamp'
    # Se o reset_index criou uma coluna 'index' contendo os timestamps:
    if 'index' in ohlcv_df.columns and pd.api.types.is_datetime64_any_dtype(ohlcv_df['index']):
         ohlcv_df.rename(columns={'index': 'ts_temp'}, inplace=True)
         timestamp_col_name = 'ts_temp'
    elif 'timestamp' in ohlcv_df.columns and pd.api.types.is_datetime64_any_dtype(ohlcv_df['timestamp']):
        # Se já existe uma coluna 'timestamp' e ela é o antigo índice
        ohlcv_df.rename(columns={'timestamp': 'ts_temp'}, inplace=True)
        timestamp_col_name = 'ts_temp'
    else:
        print("ERRO: Não foi possível identificar a coluna de timestamp após reset_index.")
        return

    # Verificar duplicatas na coluna de timestamp e remover
    initial_rows = len(ohlcv_df)
    ohlcv_df.drop_duplicates(subset=[timestamp_col_name], keep='first', inplace=True)
    rows_removed = initial_rows - len(ohlcv_df)
    if rows_removed > 0:
        print(f"AVISO: Removidas {rows_removed} linhas com timestamps duplicados (coluna '{timestamp_col_name}').")

    # Passo 3: Recriar o índice a partir da coluna de timestamp limpa
    ohlcv_df.set_index(timestamp_col_name, inplace=True)
    ohlcv_df.index.name = 'timestamp' # Renomeia o índice de volta para 'timestamp'

    # Passo 4: Garantir que o índice está ordenado
    ohlcv_df.sort_index(inplace=True)
    
    # Verificação final de unicidade do índice
    if not ohlcv_df.index.is_unique:
        print("ERRO CRÍTICO: O índice ainda não é único após a limpeza. Algo está errado.")
        # Você pode querer inspecionar ohlcv_df.index[ohlcv_df.index.duplicated(keep=False)]
        return
    else:
        print(f"Índice agora é único. Shape do ohlcv_df após limpeza: {ohlcv_df.shape}")
    # >>> FIM DA SEÇÃO DE LIMPEZA ROBUSTA DO ÍNDICE <<<

    # --- 2. Calcular Indicadores Técnicos ---
    print("Calculando indicadores técnicos...")
    if ta:
        ohlcv_df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
        ohlcv_df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
     
        ohlcv_df.ta.macd(close='close', append=True, col_names=('macd', 'macdh', 'macds')) # Adiciona 3 colunas
        ohlcv_df.ta.atr(length=14, append=True, col_names=('atr',)) # Adiciona ATR
        ohlcv_df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp')) # Adiciona 5 colunas de Bollinger

        
     

        # Após o cálculo de todos os indicadores e ohlcv_df.dropna()
        ohlcv_df['close_div_atr'] = ohlcv_df['close'] / (ohlcv_df['atr'] + 1e-7) # Adiciona epsilon para evitar divisão por zero
        ohlcv_df['volume_div_atr'] = ohlcv_df['volume'] / (ohlcv_df['atr'] + 1e-7) # Volume também pode ser normalizado se fizer sentido
        # Faça o mesmo para outras features baseadas em preço se desejar (ex: sma_10, macd, bbm)
        ohlcv_df['sma_10_div_atr'] = ohlcv_df['sma_10'] / (ohlcv_df['atr'] + 1e-7)
        ohlcv_df['macd_div_atr'] = ohlcv_df['macd'] / (ohlcv_df['atr'] + 1e-7) 


        ohlcv_df.dropna(inplace=True) # Remove NaNs dos indicadores

    # --- 3. Criar Alvo (Target) ---
    print("Criando coluna alvo para predição...")
    ohlcv_df_with_target = calculate_targets(ohlcv_df.copy(), PREDICTION_HORIZON, PRICE_CHANGE_THRESHOLD)



    #Logica dos Scalers
    api_price_vol_cols = ['close_div_atr', 'volume_div_atr'] 
    if all(col in ohlcv_df_with_target.columns for col in api_price_vol_cols):
        price_volume_scaler_to_save = MinMaxScaler()
        price_volume_scaler_to_save.fit(ohlcv_df_with_target[api_price_vol_cols]) 
        joblib.dump(price_volume_scaler_to_save, os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME))
        print(f"Scaler de Preço/Volume (API: {api_price_vol_cols}) salvo em: {os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME)}")
    else:
        print(f"ERRO: Colunas para salvar price_volume_scaler ({api_price_vol_cols}) não encontradas em ohlcv_df_with_target.")
        return # Falha crítica se não puder salvar scalers esperados

    # Colunas que representam "indicadores" para a API
    # Estas são as colunas de BASE_FEATURE_COLS que NÃO são 'close_div_atr' ou 'volume_div_atr'
    # E que o rnn_predictor.py também vai escalar com o indicator_scaler.
    # ATENÇÃO: `BASE_FEATURE_COLS` deve ser a lista FINAL de features que entram no modelo,
    # então `indicator_cols_for_api_scaler` deve pegar as colunas de INDICADORES dessa lista.

    # Supondo que BASE_FEATURE_COLS atualizada é:
    BASE_FEATURE_COLS = ['close_div_atr', 'volume_div_atr', 'sma_10_div_atr', 'rsi_14', 'macd_div_atr', 'atr', 'bbp']
    indicator_cols_for_api_scaler = ['sma_10_div_atr', 'rsi_14', 'macd_div_atr', 'atr', 'bbp']
                                   

    if indicator_cols_for_api_scaler and all(col in ohlcv_df_with_target.columns for col in indicator_cols_for_api_scaler):
        indicator_data_to_fit_api_scaler = ohlcv_df_with_target[indicator_cols_for_api_scaler].copy()
        indicator_data_to_fit_api_scaler.dropna(subset=indicator_cols_for_api_scaler, inplace=True) 
        
        if not indicator_data_to_fit_api_scaler.empty:
            indicator_scaler_to_save = MinMaxScaler()
            indicator_scaler_to_save.fit(indicator_data_to_fit_api_scaler)
            joblib.dump(indicator_scaler_to_save, os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME))
            print(f"Scaler de Indicadores (API: {indicator_cols_for_api_scaler}) salvo em: {os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME)}")
        else:
            print(f"ERRO: Não foi possível treinar/salvar o scaler de indicadores (API: {indicator_cols_for_api_scaler}) devido a dados vazios.")
            return # Falha crítica
    elif not indicator_cols_for_api_scaler:
        print("Nenhuma coluna de indicador definida para salvar o indicator_scaler para API.")
    else:
        missing_cols = [col for col in indicator_cols_for_api_scaler if col not in ohlcv_df_with_target.columns]
        print(f"ERRO: Colunas para salvar indicator_scaler ({indicator_cols_for_api_scaler}) não encontradas ou lista vazia. Ausentes: {missing_cols}")
        return # Falha crítica



    #Fimfitagem

    # --- 4. Escalonar TODAS as Features (PARA TREINAMENTO DO MODELO ATUAL) ---
    print("Escalonando features para criação de sequências (usando as colunas de BASE_FEATURE_COLS)...")

    # Garantir que ohlcv_df_with_target contenha todas as BASE_FEATURE_COLS
    if not all(col in ohlcv_df_with_target.columns for col in BASE_FEATURE_COLS):
        missing_final_base_cols = [col for col in BASE_FEATURE_COLS if col not in ohlcv_df_with_target.columns]
        print(f"ERRO: Colunas finais em BASE_FEATURE_COLS ausentes em ohlcv_df_with_target: {missing_final_base_cols}")
        print(f"Colunas disponíveis: {ohlcv_df_with_target.columns.tolist()}")
        return

    features_to_scale_df = ohlcv_df_with_target[BASE_FEATURE_COLS].copy()

    # Este scaler 'geral' é usado para preparar os dados para as sequências.
    general_training_scaler = MinMaxScaler()
    scaled_features_values = general_training_scaler.fit_transform(features_to_scale_df) # Fita e transforma TODAS as BASE_FEATURE_COLS juntas

    scaled_features_df = pd.DataFrame(scaled_features_values, 
                                    columns=[f"{col}_scaled" for col in BASE_FEATURE_COLS], 
                                    index=features_to_scale_df.index)



    # ---
    
    if ohlcv_df_with_target.empty:
        print("DataFrame vazio após cálculo do alvo. Verifique os parâmetros de horizonte/threshold. Encerrando.")
        return

    print(f"Distribuição do Alvo:\n{ohlcv_df_with_target['target'].value_counts(normalize=True)}")
    pv_cols_for_scaling = ['close_div_atr', 'volume_div_atr']
    if all(col in ohlcv_df_with_target.columns for col in pv_cols_for_scaling): # Verifica se existem
            price_volume_scaler = MinMaxScaler()
            price_volume_data_original = ohlcv_df_with_target[pv_cols_for_scaling].copy()
            price_volume_scaler.fit(price_volume_data_original)
            joblib.dump(price_volume_scaler, os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME))
            print(f"Scaler de Preço/Volume salvo em: {os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME)}")
    else:
            print(f"Aviso: Colunas para price_volume_scaler não encontradas: {pv_cols_for_scaling}")

        # Scaler para TODOS os outros indicadores definidos em BASE_FEATURE_COLS
    indicator_cols_for_scaling = [col for col in BASE_FEATURE_COLS if col not in ['close_div_atr', 'volume_div_atr']]

    if indicator_cols_for_scaling and all(col in ohlcv_df_with_target.columns for col in indicator_cols_for_scaling):
            indicator_data_original = ohlcv_df_with_target[indicator_cols_for_scaling].copy()
            indicator_data_original.dropna(inplace=True) # Importante, pois alguns indicadores podem ter mais NaNs no início
            
            if not indicator_data_original.empty:
                indicator_scaler_instance = MinMaxScaler()
                indicator_scaler_instance.fit(indicator_data_original)
                joblib.dump(indicator_scaler_instance, os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME))
                print(f"Scaler de Indicadores ({indicator_cols_for_scaling}) salvo em: {os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME)}")
            else:
                print(f"Não foi possível treinar/salvar o scaler de indicadores ({indicator_cols_for_scaling}) devido a dados vazios após dropna.")
    elif not indicator_cols_for_scaling:
            print("Nenhuma coluna de indicador definida para o indicator_scaler.")
    else:
            print(f"Aviso: Algumas colunas para indicator_scaler não encontradas: {indicator_cols_for_scaling}")

    # Verificar se as colunas base existem após os indicadores
    missing_base_cols = [col for col in BASE_FEATURE_COLS if col not in ohlcv_df.columns]
    if missing_base_cols:
        print(f"Erro: Colunas base para features ausentes após cálculo de indicadores: {missing_base_cols}")
        print(f"Colunas disponíveis: {ohlcv_df.columns.tolist()}")
        print(f"Verifique BASE_FEATURE_COLS e a saída dos indicadores.")
        return


    # --- 4. Escalonar Features ---
    print("Escalonando features...")
    # Separar features que serão escaladas
    features_to_scale_df = ohlcv_df_with_target[BASE_FEATURE_COLS].copy()
    
    # IMPORTANTE: Escalar ANTES de criar as sequências
    # E escalar APENAS as features, não o target.
    
    # Exemplo com um único scaler para todas as features (mais simples de gerenciar)
    # Se você tiver scalers separados (como no rnn_predictor.py), precisará adaptar.
    scaler = MinMaxScaler()
    scaled_features_values = scaler.fit_transform(features_to_scale_df)
    
    # Criar um DataFrame com as features escaladas para facilitar a criação de sequências
    scaled_features_df = pd.DataFrame(scaled_features_values, 
                                      columns=[f"{col}_scaled" for col in BASE_FEATURE_COLS], 
                                      index=features_to_scale_df.index)
    
    # Juntar o target de volta com as features escaladas
    # Assegurar que os índices estão alinhados para o join
    data_for_sequences = scaled_features_df.join(ohlcv_df_with_target[['target']])
    data_for_sequences.dropna(inplace=True) # Caso o join crie NaNs (improvável se os índices estiverem corretos)

    if data_for_sequences.empty:
        print("DataFrame vazio após escalonamento e join com target. Encerrando.")
        return
        
    # As colunas de features para criar sequências são as escaladas
    sequence_feature_cols = [f"{col}_scaled" for col in BASE_FEATURE_COLS]

    # --- 5. Criar Sequências ---
    print("Criando sequências de dados...")
    X, y = create_sequences(data_for_sequences, 'target', WINDOW_SIZE, sequence_feature_cols)

    if X.shape[0] == 0:
        print("Nenhuma sequência foi criada. Verifique o tamanho dos dados e WINDOW_SIZE. Encerrando.")
        return
    print(f"Shape de X (sequências de entrada): {X.shape}") # (num_samples, window_size, num_features)
    print(f"Shape de y (alvos): {y.shape}")                # (num_samples,)

    # --- 6. Dividir em Treino e Teste ---
    print("Dividindo dados em treino e teste...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Tamanho do conjunto de treino: {X_train.shape[0]}, Teste: {X_test.shape[0]}")

    # --- 7. Construir e Treinar Modelo ---
    print("Construindo modelo LSTM...")
    # O input_shape para o modelo é (WINDOW_SIZE, NUM_FEATURES)
    model = build_lstm_model((WINDOW_SIZE, NUM_FEATURES), LSTM_UNITS, DENSE_UNITS, DROPOUT_RATE, LEARNING_RATE)

    print("Iniciando treinamento do modelo...")
    # Adicionar callbacks (opcional, mas recomendado para treinamento longo)
    reduce_lr_callback = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', 
        factor=0.2,    # Reduz LR em 80% (multiplica por 0.2)
        patience=7,    # Paciência um pouco menor que o EarlyStopping
        min_lr=1e-7,   # Não reduzir abaixo disso
        verbose=1
    )
    early_stopping_callback = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', 
        patience=25, 
        restore_best_weights=True
    )
    callbacks = [early_stopping_callback, reduce_lr_callback]
    
    from sklearn.utils.class_weight import compute_class_weight
    unique_classes_in_train = np.unique(y_train)
    class_weights_values = compute_class_weight('balanced', classes=unique_classes_in_train, y=y_train)
    class_weights = {cls: weight for cls, weight in zip(unique_classes_in_train, class_weights_values)}
    print(f"Pesos de Classe para Treinamento: {class_weights}")

    history = model.fit(X_train, y_train, 
                        epochs=EPOCHS, 
                        batch_size=BATCH_SIZE, 
                        validation_data=(X_test, y_test),
                        callbacks=callbacks,
                        class_weight=class_weights,
                        verbose=1)

    # --- 8. Avaliar Modelo ---
    print("Avaliando modelo no conjunto de teste...")
    loss, accuracy = model.evaluate(X_test, y_test, verbose=0)
    print(f"Perda no Teste: {loss:.4f}")
    print(f"Acurácia no Teste: {accuracy:.4f}")

    # Após model.evaluate()
    from sklearn.metrics import classification_report, confusion_matrix
    y_pred_probs = model.predict(X_test)
    y_pred_classes = (y_pred_probs > 0.65).astype(int) # 0.5, 0.6, 0.65, 0.7, 0.75 Valores de referencia par Thresholud

    print("\nRelatório de Classificação no Conjunto de Teste:")
    print(classification_report(y_test, y_pred_classes, target_names=['No Rise (0)', 'Rise (1)']))

    print("\nMatriz de Confusão no Conjunto de Teste:")
    cm = confusion_matrix(y_test, y_pred_classes)
    print(cm)
    # import seaborn as sns # Para um plot mais bonito da matriz
    # plt.figure(figsize=(6,5))
    # sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=['No Rise', 'Rise'], yticklabels=['No Rise', 'Rise'])
    # plt.xlabel('Predito')
    # plt.ylabel('Verdadeiro')
    # plt.title('Matriz de Confusão')
    # plt.savefig(os.path.join(MODEL_SAVE_DIR, "confusion_matrix.png"))

    # --- 9. Salvar Modelo e Scalers ---
    print("Salvando modelo e scalers...")
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True) # Cria o diretório se não existir
    
    model_path = os.path.join(MODEL_SAVE_DIR, MODEL_NAME)
    model.save(model_path)
    print(f"Modelo salvo em: {model_path}")

    # Salvar o scaler usado para TODAS as features
    # Se você usou scalers separados em rnn_predictor.py (price_vol_scaler, indicator_scaler),
    # você precisará treinar e salvar esses scalers separadamente aqui.
    # Por agora, este script usa um único scaler para `BASE_FEATURE_COLS`.
    # VOCÊ PRECISA ADAPTAR ESTA PARTE PARA CORRESPONDER AO SEU `rnn_predictor.py`
    
    # Se rnn_predictor.py espera PRICE_VOL_SCALER_PATH e INDICATOR_SCALER_PATH:
    # Você precisaria criar dois DataFrames aqui: um com 'close', 'volume' e outro com 'sma_10', 'rsi_14'
    # Treinar um scaler para cada e salvá-los.
    
    # Exemplo para salvar price_volume_scaler:
    pv_cols_for_scaling = ['volume_div_atr', 'volume_div_atr'] # Colunas originais ANTES de escalar
    pv_data_to_fit_scaler = ohlcv_df_with_target[pv_cols_for_scaling].copy() # Usa o DF antes de criar sequências
    
    # É importante usar o mesmo scaler que foi usado para criar `scaled_features_df`
    # Se você fez `scaler.fit_transform(features_to_scale_df)` onde `features_to_scale_df`
    # continha todas as `BASE_FEATURE_COLS`, então esse `scaler` é o que foi treinado em todas elas.
    # Para salvar scalers separados como esperado por rnn_predictor.py, você precisa de:
    
    # Scaler para Preço e Volume
    price_volume_scaler = MinMaxScaler()
    price_volume_data_original = ohlcv_df_with_target[['close_div_atr', 'volume_div_atr']].copy() # Dados originais
    price_volume_scaler.fit(price_volume_data_original) # Fita nos dados originais
    joblib.dump(price_volume_scaler, os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME))
    print(f"Scaler de Preço/Volume salvo em: {os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME)}")

    # Scaler para Indicadores
    indicator_cols_for_scaling = ['sma_10', 'rsi_14'] # Colunas originais dos indicadores
    indicator_data_original = ohlcv_df_with_target[indicator_cols_for_scaling].copy()
    indicator_data_original.dropna(inplace=True) # Garante que não há NaNs antes de fitar
    if not indicator_data_original.empty:
        indicator_scaler_instance = MinMaxScaler()
        indicator_scaler_instance.fit(indicator_data_original)
        joblib.dump(indicator_scaler_instance, os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME))
        print(f"Scaler de Indicadores salvo em: {os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME)}")
    else:
        print("Não foi possível treinar/salvar o scaler de indicadores devido a dados vazios.")
        

    # --- 10. Plotar Histórico de Treinamento (Opcional) ---
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Acurácia Treino')
    plt.plot(history.history['val_accuracy'], label='Acurácia Validação')
    plt.title('Acurácia do Modelo')
    plt.xlabel('Época')
    plt.ylabel('Acurácia')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Perda Treino')
    plt.plot(history.history['val_loss'], label='Perda Validação')
    plt.title('Perda do Modelo')
    plt.xlabel('Época')
    plt.ylabel('Perda')
    plt.legend()
    
    # Salvar o gráfico
    plot_path = os.path.join(MODEL_SAVE_DIR, "training_history.png")
    plt.savefig(plot_path)
    print(f"Gráfico do histórico de treinamento salvo em: {plot_path}")
    # plt.show() # Descomente se quiser ver o gráfico imediatamente

    print("Script de treinamento concluído.")

    # No final do script de treino
    y_pred_probs = model.predict(X_test)
    thresholds_to_test = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    for thresh in thresholds_to_test:
        print(f"\n--- Resultados com Threshold: {thresh:.2f} ---")
        y_pred_classes = (y_pred_probs > thresh).astype(int)
        print(classification_report(y_test, y_pred_classes, target_names=['No Rise (0)', 'Rise (1)'], zero_division=0))
        print(confusion_matrix(y_test, y_pred_classes))


if __name__ == '__main__':
    # Configurar GPU (Opcional, se tiver TensorFlow com suporte a GPU)
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
        except RuntimeError as e:
            print(e)





        
    
    main()