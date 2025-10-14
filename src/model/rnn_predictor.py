# rnn/app/models/rnn_predictor.py (ou o nome que você deu, ex: data_preprocessing_api.py)

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, List, Tuple

try:
    import pandas_ta as ta
except ImportError:
    print("AVISO URGENTE (RNN PREDICTOR): pandas_ta não instalado! Cálculo de features falhará.")
    ta = None

try:
    import joblib
except ImportError:
    print("AVISO URGENTE (RNN PREDICTOR): joblib não instalado! Carregamento de scalers falhará.")
    joblib = None

# Importar DO CONFIG.PY para consistência
from src.config.config import  * 

# Defina as colunas EXATAS que cada scaler da API espera, baseado no config e no script de treino
# Estas devem corresponder às colunas usadas para FITAR os scalers no train_rnn_model.py
# ANTES de serem escaladas pelo general_training_scaler.
API_PRICE_VOL_COLS_TO_SCALE = ['close_div_atr', 'volume_div_atr', 'open_div_atr', 'high_div_atr', 'low_div_atr', 'body_size_norm_atr']
API_INDICATOR_COLS_TO_SCALE = ['log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 'body_vs_avg_body', 'macd', 'sma_10_div_atr', 'adx_14', 'volume_zscore', 'buy_condition_v1']


API_PRICE_VOL_COLS = ['close_div_atr', 'volume_div_atr'] # Como no seu log de treino

API_INDICATOR_COLS = [col for col in BASE_FEATURES_PER_ASSET_INPUT if col not in API_PRICE_VOL_COLS]

def calculate_features_for_prediction(ohlcv_df: pd.DataFrame, logger_instance) -> Optional[pd.DataFrame]:
    """
    Calcula TODAS as features base necessárias para a predição,
    EXATAMENTE como no script de treinamento ANTES do escalonamento final.
    """
    if logger_instance is None: import logging; logger_instance = logging.getLogger(__name__)
    if ta is None: logger_instance.error("pandas_ta não está disponível para calcular features."); return None
    
    df = ohlcv_df.copy()
    required_ohlc_cols = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_ohlc_cols):
        logger_instance.error(f"DataFrame OHLCV não contém todas as colunas necessárias: {required_ohlc_cols}")
        return None
    try:
        # Indicadores base
        df.ta.sma(length=10, close='close', append=True, col_names=('sma_10',))
        df.ta.rsi(length=14, close='close', append=True, col_names=('rsi_14',))
        macd_out = df.ta.macd(close='close', append=False)
        if macd_out is not None:
            df['macd'] = macd_out.iloc[:,0] # MACD line
            df['macds'] = macd_out.iloc[:,2] # Signal line
        df.ta.atr(length=14, append=True, col_names=('atr',))
        df.ta.bbands(length=20, close='close', append=True, col_names=('bbl', 'bbm', 'bbu', 'bbb', 'bbp'))
        df.ta.cci(length=37, append=True, col_names=('cci_37',)) # Usando o período do seu log
        df.ta.mfi(length=37, append=True, col_names=('mfi_37',)) # Usando o período do seu log
        df.ta.adx(length=14, append=True) # Adiciona ADX_14, DMP_14, DMN_14
        if 'ADX_14' not in df.columns and 'ADX_14_ADX' in df.columns: # Handle naming variation
             df.rename(columns={'ADX_14_ADX': 'ADX_14'}, inplace=True)

        # Features de Volume Z-score
        rolling_vol_mean = df['volume'].rolling(window=20).mean()
        rolling_vol_std = df['volume'].rolling(window=20).std()
        df['volume_zscore'] = (df['volume'] - rolling_vol_mean) / (rolling_vol_std + 1e-9)

        # Features de Candle
        df['body_size'] = abs(df['close'] - df['open'])
        df['body_size_norm_atr'] = df['body_size'] / (df['atr'] + 1e-9)
        df['body_vs_avg_body'] = df['body_size'] / (df['body_size'].rolling(window=20).mean() + 1e-9)

        # Log Return
        df['log_return'] = np.log(df['close'] / df['close'].shift(1))

        # Normalização pelo ATR (DEPOIS de calcular ATR e outras features que o usam)
        # Garanta que o ATR não é zero para evitar divisão por zero
        df_atr_valid = df[df['atr'] > 1e-7].copy() # Trabalhar em cópia para evitar SettingWithCopyWarning
        if df_atr_valid.empty: # Se todos os ATRs forem zero ou NaN
            logger_instance.warning("ATR é zero ou NaN para todos os dados, não é possível normalizar pelo ATR.")
            # Preencher colunas _div_atr com um valor (ex: 0 ou o valor original) ou retornar None
            # Para simplificar, vamos preencher com o valor original se ATR for problemático
            cols_to_norm_by_atr = ['open', 'high', 'low', 'close', 'volume', 'sma_10', 'macd']
            for col in cols_to_norm_by_atr:
                df[f'{col}_div_atr'] = df[col] # Fallback
        else:
            df['open_div_atr'] = df['open'] / (df['atr'] + 1e-9)
            df['high_div_atr'] = df['high'] / (df['atr'] + 1e-9)
            df['low_div_atr'] = df['low'] / (df['atr'] + 1e-9)
            df['close_div_atr'] = df['close'] / (df['atr'] + 1e-9)
            df['volume_div_atr'] = df['volume'] / (df['atr'] + 1e-9)
            if 'sma_10' in df.columns: df['sma_10_div_atr'] = df['sma_10'] / (df['atr'] + 1e-9)
            if 'macd' in df.columns: df['macd_div_atr'] = df['macd'] / (df['atr'] + 1e-9)
        
        # Feature de Condição de Compra
        sma_50_series = df.ta.sma(length=50, close='close', append=False)
        if sma_50_series is not None: df['sma_50'] = sma_50_series
        else: df['sma_50'] = np.nan
        
        if all(col in df.columns for col in ['macd', 'macds', 'rsi_14', 'close', 'sma_50']):
            df['buy_condition_v1'] = ((df['macd'] > df['macds']) & (df['rsi_14'] > 50) & (df['close'] > df['sma_50'])).astype(int)
        else:
            df['buy_condition_v1'] = 0 # Fallback

        df.dropna(inplace=True) # Remove todos os NaNs gerados
        logger_instance.info("Features para predição calculadas.")
        return df

    except Exception as e:
        logger_instance.error(f"Erro ao calcular features para predição: {e}", exc_info=True)
        return None


def preprocess_for_model_prediction(
    features_df: pd.DataFrame, 
    price_vol_scaler, 
    indicator_scaler,
    expected_scaled_feature_order: List[str], # Vem do config.EXPECTED_SCALED_FEATURES_FOR_MODEL
    window_size: int,
    logger_instance
) -> np.ndarray:
    """
    Aplica scalers carregados e formata os dados para a entrada do modelo.
    `features_df` deve conter TODAS as colunas de `API_PRICE_VOL_COLS_TO_SCALE` e `API_INDICATOR_COLS_TO_SCALE`.
    """
    if features_df.empty or len(features_df) < window_size:
        logger_instance.warning(f"Preprocessing API: Dados insuficientes para janela. Necessário: {window_size}, Disponível: {len(features_df)}")
        return np.array([])

    # Pegar a última janela de dados
    window_data_df = features_df.tail(window_size).copy()

    if len(window_data_df) < window_size: # Checagem extra
        logger_instance.warning(f"Preprocessing API: Janela de dados incompleta após tail. Necessário: {window_size}, Disponível: {len(window_data_df)}")
        return np.array([])

    scaled_features_dict = {}

    # Aplicar scaler de Preço/Volume
    if price_vol_scaler and all(col in window_data_df.columns for col in API_PRICE_VOL_COLS_TO_SCALE):
        scaled_pv = price_vol_scaler.transform(window_data_df[API_PRICE_VOL_COLS_TO_SCALE])
        for i, col_name in enumerate(API_PRICE_VOL_COLS_TO_SCALE):
            scaled_features_dict[f"{col_name}_scaled"] = scaled_pv[:, i]
    elif not price_vol_scaler:
        logger_instance.error("Preprocessing API: price_volume_scaler não carregado!")
        return np.array([])
    else:
        missing = [col for col in API_PRICE_VOL_COLS_TO_SCALE if col not in window_data_df.columns]
        logger_instance.error(f"Preprocessing API: Colunas ausentes para price_volume_scaler: {missing}")
        return np.array([])

    # Aplicar scaler de Indicadores
    if indicator_scaler and all(col in window_data_df.columns for col in API_INDICATOR_COLS_TO_SCALE):
        scaled_ind = indicator_scaler.transform(window_data_df[API_INDICATOR_COLS_TO_SCALE])
        for i, col_name in enumerate(API_INDICATOR_COLS_TO_SCALE):
            scaled_features_dict[f"{col_name}_scaled"] = scaled_ind[:, i]


       


    elif not indicator_scaler:
        logger_instance.error("Preprocessing API: indicator_scaler não carregado!")
        return np.array([])
    else:
        missing = [col for col in API_INDICATOR_COLS_TO_SCALE if col not in window_data_df.columns]
        logger_instance.error(f"Preprocessing API: Colunas ausentes para indicator_scaler: {missing}")
        return np.array([])
    

    # News --

    if features_df.empty or len(features_df) < window_size:
        logger_instance.warning(f"API Preprocessing: Dados insuficientes. Necessário: {window_size}, Disp: {len(features_df)}")
        return np.array([])

    window_data_df = features_df.tail(window_size).copy()
    if len(window_data_df) < window_size: return np.array([]) # Checagem extra

    scaled_data_dict = {} 

    if price_vol_scaler and all(col in window_data_df.columns for col in API_PRICE_VOL_COLS):
        scaled_pv = price_vol_scaler.transform(window_data_df[API_PRICE_VOL_COLS])
        for i, col_name in enumerate(API_PRICE_VOL_COLS):
            scaled_data_dict[f"{col_name}_scaled"] = scaled_pv[:, i]
    else:
        missing = [col for col in API_INDICATOR_COLS_TO_SCALE if col not in window_data_df.columns]
        logger_instance.error(f"Preprocessing API: Colunas ausentes para indicator_scaler: {missing}")
        return np.array([])
    

    if indicator_scaler and all(col in window_data_df.columns for col in API_INDICATOR_COLS):
        scaled_ind = indicator_scaler.transform(window_data_df[API_INDICATOR_COLS])
        for i, col_name in enumerate(API_INDICATOR_COLS):
            # A feature 'buy_condition_v1' é binária. Escalar pode não ser ideal,
            # mas se foi escalada no treino, precisa ser aqui também.
            # Se não foi escalada no treino e está em EXPECTED_SCALED_FEATURES_FOR_MODEL sem _scaled,
            # a lógica abaixo precisaria de ajuste.
            scaled_data_dict[f"{col_name}_scaled"] = scaled_ind[:, i]
    else: 
        missing = [col for col in API_INDICATOR_COLS_TO_SCALE if col not in window_data_df.columns]
        logger_instance.error(f"Preprocessing API: Colunas ausentes para indicator_scaler: {missing}")
        return np.array([])

    # Montar o array final na ordem de EXPECTED_SCALED_FEATURES_FOR_MODEL
    final_feature_list_for_model = []
    for scaled_feature_name in EXPECTED_SCALED_FEATURES_FOR_MODEL: # Esta é config.EXPECTED_SCALED_FEATURES_FOR_MODEL
        if scaled_feature_name in scaled_data_dict:
            final_feature_list_for_model.append(scaled_data_dict[scaled_feature_name])
        else:
            # Isso aconteceria se uma feature em EXPECTED_SCALED_FEATURES_FOR_MODEL
            # não foi corretamente gerada e adicionada ao scaled_data_dict.
            # Ex: se 'buy_condition_v1' não fosse escalada mas seu nome '_scaled' estivesse em EXPECTED_SCALED_FEATURES_FOR_MODEL
            logger_instance.error(f"API Preprocessing: Feature escalada '{scaled_feature_name}' não encontrada no dict. Verifique config e lógica de scaling.")
            return np.array([])
            
    final_features_array = np.stack(final_feature_list_for_model, axis=-1) # (window_size, num_model_features)
    
    if final_features_array.shape[1] != len(EXPECTED_SCALED_FEATURES_FOR_MODEL):
        logger_instance.error(f"API Preprocessing: Discrepância no número de features! "
                              f"Esperado: {len(EXPECTED_SCALED_FEATURES_FOR_MODEL)}, Obtido: {final_features_array.shape[1]}")
        return np.array([])
    

    #Criar DataFrame com todas as features escaladas e na ordem correta
    try:
        # Construir o array de features na ordem de EXPECTED_SCALED_FEATURES_FOR_MODEL
        final_feature_list_for_model = []
        final_ordered_features_list = []
        for scaled_col_name in expected_scaled_feature_order: # Esta é config.EXPECTED_SCALED_FEATURES_FOR_MODEL
            if scaled_col_name in scaled_features_dict:
                final_ordered_features_list.append(scaled_features_dict[scaled_col_name])
            else:
                # Se uma feature em EXPECTED_SCALED_FEATURES_FOR_MODEL não foi gerada/escalada
                # Isso indica um desalinhamento entre config.py e a lógica aqui.
                # Exemplo: se 'buy_condition_v1' não for escalada e seu nome escalado não existir.
                # Tentativa: pegar a coluna original se o _scaled não existir E a original estiver em expected_scaled_feature_order
                original_col_name = scaled_col_name.replace("_scaled", "")
                if original_col_name in window_data_df.columns and original_col_name == scaled_col_name : # Se a feature esperada é a original não escalada
                    logger_instance.warning(f"Preprocessing API: Usando feature original não escalada '{original_col_name}' conforme esperado.")
                    final_ordered_features_list.append(window_data_df[original_col_name].values)
                else:
                    logger_instance.error(f"Preprocessing API: Feature escalada '{scaled_col_name}' esperada pelo modelo não foi encontrada no dicionário de features escaladas.")
                    return np.array([])
        
        # Transpor para ter (timesteps, features) e depois adicionar dimensão de batch
        final_features_array = np.stack(final_ordered_features_list, axis=-1) # (window_size, num_features)
        final_features_array = np.stack(final_feature_list_for_model, axis=-1)
    except KeyError as e_key:
        logger_instance.error(f"Preprocessing API: Erro de chave ao montar features finais. Provavelmente uma feature em "
                              f"EXPECTED_SCALED_FEATURES_FOR_MODEL não foi corretamente gerada/escalada. Erro: {e_key}", exc_info=True)
        return np.array([])
    except Exception as e_stack:
        logger_instance.error(f"Preprocessing API: Erro ao empilhar features finais: {e_stack}", exc_info=True)
        return np.array([])


    if final_features_array.shape != (window_size, len(expected_scaled_feature_order)):
        logger_instance.error(f"Preprocessing API: Shape incorreto após escalonamento e ordenação. "
                              f"Esperado: ({window_size}, {len(expected_scaled_feature_order)}), "
                              f"Obtido: {final_features_array.shape}")
        return np.array([])

    reshaped_data = np.reshape(final_features_array, (1, window_size, len(expected_scaled_feature_order)))
    logger_instance.info(f"Preprocessing API: Dados pré-processados com shape: {reshaped_data.shape}")
    return reshaped_data

    


    #


class RNNModelPredictor:
    def __init__(self, model_dir="src/model", model_filename="ppo_custom_deep_portfolio_agent.zip", 
                 pv_scaler_filename="price_volume_atr_norm_scaler_sup.joblib", ind_scaler_filename="other_indicators_scaler_sup.joblib", 
                 logger_instance=None): 
        self.model_path = os.path.join(model_dir, model_filename)
        self.pv_scaler_path = os.path.join(model_dir, pv_scaler_filename)
        self.ind_scaler_path = os.path.join(model_dir, ind_scaler_filename)
        
        self.model: Optional[tf.keras.Model] = None
        self.price_volume_scaler = None
        self.indicator_scaler = None
        self.logger = logger_instance
        self.num_model_features = len(EXPECTED_SCALED_FEATURES_FOR_MODEL)
        self._load_model_and_scalers()

       

        self._load_model_and_scalers()

    def _load_scaler(self, scaler_path: str, scaler_name: str): # ... (como antes)
        if not joblib: self.logger.error(f"Joblib não importado, não é possível carregar scaler {scaler_name}."); return None
        try:
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
                self.logger.info(f"Scaler {scaler_name} carregado de {scaler_path}.")
                return scaler
            else:
                self.logger.error(f"Arquivo do scaler {scaler_name} NÃO ENCONTRADO em {scaler_path}.")
                return None
        except Exception as e:
            self.logger.error(f"Erro ao carregar scaler {scaler_name} de {scaler_path}: {e}", exc_info=True)
            return None



    def _load_scaler(self, scaler_path: str, scaler_name: str): # ... (como antes)
        if not joblib: self.logger.error(f"Joblib não importado, não é possível carregar scaler {scaler_name}."); return None
        try:
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
                self.logger.info(f"Scaler {scaler_name} carregado de {scaler_path}.")
                return scaler
            else:
                self.logger.error(f"Arquivo do scaler {scaler_name} NÃO ENCONTRADO em {scaler_path}.")
                return None
        except Exception as e:
            self.logger.error(f"Erro ao carregar scaler {scaler_name} de {scaler_path}: {e}", exc_info=True)
            return None



    def _load_model_and_scalers(self):
        try:
            self.logger.info(f"RNNPredictor: Carregando modelo de {self.model_path}...")
            if not os.path.exists(self.model_path):
                self.logger.error(f"Arquivo do modelo NÃO ENCONTRADO em {self.model_path}")
                return
            self.model = tf.keras.models.load_model(self.model_path)
            self.logger.info(f"RNNPredictor: Modelo carregado. Input shape esperado: {self.model.input_shape}")
            
            model_features_count = self.model.input_shape[-1]
            if model_features_count != self.num_model_features_expected:
                 self.logger.error(f"DISCREPÂNCIA DE FEATURES! Modelo espera {model_features_count} features, "
                                   f"mas config.EXPECTED_SCALED_FEATURES_FOR_MODEL tem {self.num_model_features_expected} features.")
                 self.model = None 
                 return

            self.price_volume_scaler = self._load_scaler(self.pv_scaler_path, "Price/Volume (API)")
            self.indicator_scaler = self._load_scaler(self.ind_scaler_path, "Indicator (API)")

            if self.price_volume_scaler is None or self.indicator_scaler is None:
                self.logger.error("Um ou ambos os scalers não puderam ser carregados. O preditor pode não funcionar.")
        except Exception as e:
            self.logger.error(f"RNNPredictor: Falha crítica ao carregar modelo ou scalers: {e}", exc_info=True)
            self.model = None # Invalida tudo se houver erro
            self.price_volume_scaler = None
            self.indicator_scaler = None

    async def predict_for_asset_ohlcv(
        self, 
        ohlcv_df_raw: pd.DataFrame, 
        api_operation_threshold: float = 0.65 # Seu threshold escolhido
    ) -> Tuple[Optional[int], Optional[float]]:
        
        current_loop = asyncio.get_event_loop()

        if self.model is None or self.price_volume_scaler is None or self.indicator_scaler is None:
            self.logger.warning("API Predict: Modelo ou scalers não carregados. Predição pulada.")
            return None, None

        # 1. Calcular todas as features base
        features_df_base = await current_loop.run_in_executor(
            None, calculate_all_base_features_api, ohlcv_df_raw, self.logger
        )
        if features_df_base is None or features_df_base.empty:
            self.logger.warning("API Predict: Falha ao calcular features base.")
            return None, None
        
        # 2. Aplicar scalers e formatar
        processed_input = await current_loop.run_in_executor(
            None, preprocess_for_model_prediction,
            features_df_base, # Passa o DF com as features base calculadas
            self.price_volume_scaler,
            self.indicator_scaler,
            EXPECTED_SCALED_FEATURES_FOR_MODEL, # Do config
            DEFAULT_WINDOW_SIZE, # Do config
            self.logger
        )

        if processed_input.size == 0:
            self.logger.warning(f"API Predict: Pré-processamento falhou.")
            return None, None
        
           
        # 3. Fazer a predição
        try:
            raw_predictions = await current_loop.run_in_executor(None, self.model.predict, processed_input_sequence)
            
            if raw_predictions.ndim == 2 and raw_predictions.shape[0] == 1 and raw_predictions.shape[1] == 1:
                prediction_prob = float(raw_predictions[0, 0])
                signal = int(prediction_prob > api_operation_threshold) 
                self.logger.info(f"API Predict: Prob: {prediction_prob:.4f}, Thr: {api_operation_threshold}, Sinal: {signal}")
                return signal, prediction_prob
            else:
                self.logger.warning(f"RNNPredictor: Formato de predição inesperado: {raw_predictions.shape}")
                return None, None
        except Exception as e:
            self.logger.error(f"RNNPredictor: Erro durante a predição com o modelo: {e}", exc_info=True)
            return None, None

# --- Para teste local do rnn_predictor.py (exemplo) ---
async def test_predictor():
    # Este é apenas um exemplo de como você poderia testar o predictor isoladamente.
    # Você precisaria fornecer um DataFrame ohlcv_df_raw de teste.
    
    # Configuração de Log para Teste
    import logging
    test_logger = logging.getLogger("TestRNNPredictor")
    test_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    if not test_logger.handlers: # Evitar adicionar handlers múltiplos se rodar várias vezes
        test_logger.addHandler(handler)

    # Caminhos (ajuste se config.py não estiver acessível diretamente assim)
    # Supondo que este script está em rnn/app/models/ e config.py em rnn/app/
    # e os modelos/scalers estão em rnn/app/model/
    model_dir_path = os.path.join(os.path.dirname(__file__), "..", "model") # rnn/app/model/

    predictor = RNNModelPredictor(
        model_dir=model_dir_path,
        model_filename=DEFAULT_MODEL_NAME, # Do config
        pv_scaler_filename=DEFAULT_PRICE_VOL_SCALER_NAME, # Do config
        ind_scaler_filename=DEFAULT_INDICATOR_SCALER_NAME, # Do config
        logger_instance=test_logger
    )

    if predictor.model is None:
        test_logger.error("Teste Falhou: Modelo não carregado no preditor.")
        return

    # Criar um DataFrame OHLCV de exemplo (substitua por dados reais ou carregados de CSV)
    # Precisa ter pelo menos WINDOW_SIZE + (maior lookback de indicador) linhas
    num_test_rows = DEFAULT_WINDOW_SIZE + 50 
    example_data = {
        'open': np.random.rand(num_test_rows) * 1000 + 30000,
        'high': np.random.rand(num_test_rows) * 1200 + 30000,
        'low': np.random.rand(num_test_rows) * 800 + 29800,
        'close': np.random.rand(num_test_rows) * 1000 + 30000,
        'volume': np.random.rand(num_test_rows) * 100 + 10
    }
    # Gerar timestamps de 1h para trás a partir de agora
    end_time = pd.Timestamp.now(tz='UTC')
    start_time = end_time - pd.Timedelta(hours=num_test_rows - 1)
    timestamps = pd.date_range(start=start_time, end=end_time, freq='h')
    
    # Ajustar se o número de timestamps não bater exatamente com num_test_rows
    if len(timestamps) > num_test_rows:
        timestamps = timestamps[:num_test_rows]
    elif len(timestamps) < num_test_rows:
        # Ajustar dados de exemplo para o número de timestamps disponíveis
        for key in example_data:
            example_data[key] = example_data[key][:len(timestamps)]
            
    test_ohlcv_df = pd.DataFrame(example_data, index=timestamps)
    test_ohlcv_df['high'] = np.maximum(test_ohlcv_df['high'], test_ohlcv_df['close'], test_ohlcv_df['open'])
    test_ohlcv_df['low'] = np.minimum(test_ohlcv_df['low'], test_ohlcv_df['close'], test_ohlcv_df['open'])
    
    test_logger.info(f"DataFrame de teste criado com {len(test_ohlcv_df)} linhas.")

    signal, probability = await predictor.predict_for_asset_ohlcv(test_ohlcv_df, api_operation_threshold=0.65)

    if signal is not None:
        test_logger.info(f"Resultado do Teste - Sinal: {signal}, Probabilidade: {probability:.4f}")
    else:
        test_logger.error("Resultado do Teste - Predição falhou.")

if __name__ == '__main__':
    # Para rodar o teste: python rnn/app/models/rnn_predictor.py (ou o nome que você deu)
    # Certifique-se que o config.py está acessível (ex: no mesmo diretório ou PYTHONPATH)
    # E que os arquivos de modelo e scalers existem em app/model/
    import asyncio
    # Definir um caminho base para que os imports relativos de config funcionem se rodar daqui
    # Isso é um pouco hacky para teste direto do script. Idealmente, teste via pytest com estrutura de projeto.
    import sys
    # Adiciona o diretório 'app' ao sys.path para encontrar config.py
    # Supondo que este script rnn_predictor.py está em rnn/app/models/
    # e config.py está em rnn/app/
    # Sobe dois níveis para 'rnn', depois desce para 'app'
    # app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    # if app_dir not in sys.path:
    #    sys.path.insert(0, app_dir)
    # Para o import `from ..config import ...` funcionar, você geralmente roda o módulo
    # como parte de um pacote, não diretamente.
    # Para teste direto, você pode precisar de um import absoluto ou ajuste de PYTHONPATH.

    # Simplesmente para teste rápido, vamos assumir que o diretório de trabalho é 'rnn'
    # e o import de config seria 'from app.config import ...'
    # Se você rodar `python rnn/app/models/rnn_predictor.py` da raiz 'rnn', o import ..config deve funcionar.
    
    print("Rodando teste do RNNModelPredictor...")
    asyncio.run(test_predictor())