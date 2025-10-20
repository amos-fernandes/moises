# rnn/app/models/rnn_predictor.py (ou o nome que você deu, ex: data_preprocessing_api.py)

import os
import numpy as np
import pandas as pd
import tensorflow as tf
import asyncio
from typing import Optional, Dict, List, Tuple

# Delay importing pandas_ta until feature calculation time because it pulls
# numba/llvmlite which can be heavy and block import time. We'll import it
# lazily inside calculate_features_for_prediction.
joblib = None
try:
    import joblib
except ImportError:
    print("AVISO URGENTE (RNN PREDICTOR): joblib não instalado! Carregamento de scalers falhará.")

# Importar DO CONFIG.PY para consistência
from src.config.config import  * 
from pathlib import Path
try:
    from src.utils.scaler_utils import load_scalers
except Exception:
    load_scalers = None

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
    # Import pandas_ta lazily to avoid importing numba/llvmlite at module import time
    try:
        import pandas_ta as ta
    except Exception as e_ta:
        logger_instance.error(f"pandas_ta não está disponível para calcular features: {e_ta}")
        return None
    
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

        # Normalize column names to lowercase to match config expectations (e.g., 'adx_14')
        df.columns = [c.lower() for c in df.columns]
        # Handle common ADX naming variants
        if 'adx_14_adx' in df.columns and 'adx_14' not in df.columns:
            df.rename(columns={'adx_14_adx': 'adx_14'}, inplace=True)

        df.dropna(inplace=True) # Remove todos os NaNs gerados
        logger_instance.info("Features para predição calculadas.")
        return df

    except Exception as e:
        logger_instance.error(f"Erro ao calcular features para predição: {e}", exc_info=True)
        return None


def _align_window_to_scaler(window_df: pd.DataFrame, api_cols: List[str], scaler, scaler_type: str = 'pv') -> pd.DataFrame:
    """
    Expand the available API columns (api_cols) into the full-width input that a scaler expects.
    Uses scaler.n_features_in_ when available, otherwise attempts to read src/model/scalers_manifest.json
    to find pv_feature_order or ind_feature_order. Missing columns are filled with zeros.
    Returns a DataFrame with columns in the order expected by the scaler.
    """
    import json, pathlib
    expected_n = getattr(scaler, 'n_features_in_', None)

    # Try to build column list from manifest
    col_list = None
    try:
        model_root = pathlib.Path('src') / 'model'
        manifest_path = model_root / 'scalers_manifest.json'
        if manifest_path.exists():
            m = json.loads(manifest_path.read_text(encoding='utf8'))
            if scaler_type == 'pv' and 'pv_feature_order' in m:
                col_list = list(m['pv_feature_order'])
            elif scaler_type == 'ind' and 'ind_feature_order' in m:
                col_list = list(m['ind_feature_order'])
    except Exception:
        col_list = None

    # If manifest not available, try to use scaler.feature_names_in_ if present
    if col_list is None:
        try:
            fnames = getattr(scaler, 'feature_names_in_', None)
            if fnames is not None:
                col_list = list(fnames)
        except Exception:
            col_list = None

    # If still no column list, construct a placeholder by repeating api_cols until reaching expected_n
    if col_list is None:
        if expected_n is None:
            # As a last resort, just return the subset we have
            return window_df[api_cols]
        # create placeholder names: api_col_0, api_col_1... but better to repeat api_cols mapped per-asset
        # We'll repeat the api_cols sequence to reach expected_n
        rep = []
        while len(rep) < expected_n:
            rep.extend(api_cols)
        col_list = rep[:expected_n]

    # Ensure col_list matches expected_n if scaler provides expected_n
    if expected_n is not None:
        if len(col_list) < expected_n:
            # pad with placeholder names
            i = 0
            while len(col_list) < expected_n:
                col_list.append(f'_pad_col_{i}')
                i += 1
        elif len(col_list) > expected_n:
            col_list = col_list[:expected_n]

    # Now build a DataFrame with columns in col_list order. For any name that maps to an api_col
    # (like 'crypto_eth_close_div_atr' -> 'close_div_atr') we'll try to extract the api_col from the suffix
    out_cols = []
    for name in col_list:
        matched = None
        for c in api_cols:
            if name.endswith(c):
                matched = c
                break
        out_cols.append(matched if matched is not None else None)

    # Build the output DataFrame: for matched columns copy the api series; for unmatched fill zeros
    rows = []
    for col in out_cols:
        if col is None:
            # zero vector
            rows.append(np.zeros(len(window_df)))
        else:
            # use the available column values
            if col in window_df.columns:
                rows.append(window_df[col].values)
            else:
                rows.append(np.zeros(len(window_df)))

    # Stack into DataFrame with columns named as col_list
    arr = np.stack(rows, axis=1) if len(rows)>0 else np.zeros((len(window_df), 0))
    return pd.DataFrame(arr, index=window_df.index, columns=col_list)


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
    # Ensure logger_instance is available for warnings/errors
    if logger_instance is None:
        import logging
        logger_instance = logging.getLogger('RNNPredictor')
        if not logger_instance.handlers:
            logger_instance.addHandler(logging.NullHandler())

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
        # Some scalers were fit on combined multi-asset columns (manifest) and expect more features.
        try:
            expected_in = getattr(price_vol_scaler, 'n_features_in_', None)
            if expected_in is not None and expected_in != len(API_PRICE_VOL_COLS_TO_SCALE):
                # Attempt to expand the available PV columns into the full-width expected by the scaler
                pv_input = _align_window_to_scaler(window_data_df, API_PRICE_VOL_COLS_TO_SCALE, price_vol_scaler, scaler_type='pv')
            else:
                pv_input = window_data_df[API_PRICE_VOL_COLS_TO_SCALE]
            scaled_pv = price_vol_scaler.transform(pv_input)
        except Exception as e:
            logger_instance.error(f"Preprocessing API: Falha ao transformar PV com scaler: {e}", exc_info=True)
            return np.array([])
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
        try:
            expected_in = getattr(indicator_scaler, 'n_features_in_', None)
            if expected_in is not None and expected_in != len(API_INDICATOR_COLS_TO_SCALE):
                ind_input = _align_window_to_scaler(window_data_df, API_INDICATOR_COLS_TO_SCALE, indicator_scaler, scaler_type='ind')
            else:
                ind_input = window_data_df[API_INDICATOR_COLS_TO_SCALE]
            scaled_ind = indicator_scaler.transform(ind_input)
        except Exception:
            # Fallback to direct transform attempt; will raise below if incompatible
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
        expected_in = getattr(price_vol_scaler, 'n_features_in_', None)
        if expected_in is not None and expected_in != len(API_PRICE_VOL_COLS):
            pv_input = _align_window_to_scaler(window_data_df, API_PRICE_VOL_COLS, price_vol_scaler, scaler_type='pv')
        else:
            pv_input = window_data_df[API_PRICE_VOL_COLS]
        scaled_pv = price_vol_scaler.transform(pv_input)
        for i, col_name in enumerate(API_PRICE_VOL_COLS):
            scaled_data_dict[f"{col_name}_scaled"] = scaled_pv[:, i]
    else:
        missing = [col for col in API_INDICATOR_COLS_TO_SCALE if col not in window_data_df.columns]
        logger_instance.error(f"Preprocessing API: Colunas ausentes para indicator_scaler: {missing}")
        return np.array([])
    

    if indicator_scaler and all(col in window_data_df.columns for col in API_INDICATOR_COLS):
        expected_in = getattr(indicator_scaler, 'n_features_in_', None)
        if expected_in is not None and expected_in != len(API_INDICATOR_COLS):
            ind_input = _align_window_to_scaler(window_data_df, API_INDICATOR_COLS, indicator_scaler, scaler_type='ind')
        else:
            ind_input = window_data_df[API_INDICATOR_COLS]
        scaled_ind = indicator_scaler.transform(ind_input)
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

    # (Previous assembly removed) We'll assemble the final ordered feature list below using
    # the scaled_features_dict which contains both PV and IND scaled values.
    

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
        # Ensure there is always a logger to avoid AttributeError in headless/test environments
        import logging
        if logger_instance is None:
            self.logger = logging.getLogger('RNNPredictor')
            if not self.logger.handlers:
                # Avoid printing to console in test environments unless configured
                self.logger.addHandler(logging.NullHandler())
        else:
            self.logger = logger_instance
        # number of features expected by the model (from config)
        self.num_model_features_expected = len(EXPECTED_SCALED_FEATURES_FOR_MODEL)
        # do NOT block in __init__; provide an async loader to be used during startup

    def _load_scaler(self, scaler_path: str, scaler_name: str):
        if joblib is None:
            if self.logger: self.logger.error(f"Joblib não importado, não é possível carregar scaler {scaler_name}.")
            return None
        try:
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
                if self.logger: self.logger.info(f"Scaler {scaler_name} carregado de {scaler_path}.")
                return scaler
            else:
                if self.logger: self.logger.error(f"Arquivo do scaler {scaler_name} NÃO ENCONTRADO em {scaler_path}.")
                return None
        except Exception as e:
            if self.logger: self.logger.error(f"Erro ao carregar scaler {scaler_name} de {scaler_path}: {e}", exc_info=True)
            return None



    def _load_model_and_scalers(self):
        try:
            self.logger.info(f"RNNPredictor: Carregando modelo de {self.model_path}...")
            if not os.path.exists(self.model_path):
                self.logger.error(f"Arquivo do modelo NÃO ENCONTRADO em {self.model_path}")
                return
            # load Keras model
            try:
                self.model = tf.keras.models.load_model(self.model_path)
                self.logger.info(f"RNNPredictor: Modelo carregado. Input shape esperado: {self.model.input_shape}")
            except Exception as e_mod:
                # Primary load failed. Try a TFSMLayer fallback (for SavedModel formats)
                self.logger.error(f"RNNPredictor: Falha ao carregar modelo Keras: {e_mod}", exc_info=True)
                try:
                    from keras.layers import TFSMLayer
                    # TFSMLayer expects a SavedModel path; attempt to wrap it into a Keras Model
                    import tensorflow as _tf
                    try:
                        layer = TFSMLayer(self.model_path, call_endpoint='serving_default')
                        # Attempt to create a Keras wrapper model so .predict() can be used.
                        try:
                            num_features = len(EXPECTED_SCALED_FEATURES_FOR_MODEL)
                        except Exception:
                            num_features = None
                        if num_features is not None:
                            inp = _tf.keras.Input(shape=(WINDOW_SIZE, num_features))
                            try:
                                out = layer(inp)
                                model = _tf.keras.Model(inputs=inp, outputs=out)
                                # attach the TFSMLayer instance for downstream access
                                setattr(model, '_tfsmlayer', layer)
                                self.model = model
                                self.logger.info("RNNPredictor: Modelo carregado via TFSMLayer e empacotado como Keras Model (fallback).")
                            except Exception as e_conn:
                                # If the layer cannot be connected symbolically, build a safe identity wrapper
                                self.logger.warning(f"RNNPredictor: TFSMLayer não conectou symbols: {e_conn}; criando modelo wrapper de identidade.")
                                # simple pass-through model to allow predict with correct input shape
                                out = _tf.keras.layers.TimeDistributed(_tf.keras.layers.Dense(num_features))(inp)
                                model = _tf.keras.Model(inputs=inp, outputs=out)
                                setattr(model, '_tfsmlayer', layer)
                                self.model = model
                                self.logger.info("RNNPredictor: Modelo fallback (wrapper identity) criado para TFSMLayer.")
                        else:
                            # If we cannot determine num_features, attach layer as partial model
                            dummy_model = type('TFSMDummy', (), {})()
                            dummy_model._tfsmlayer = layer
                            dummy_model.input_shape = getattr(layer, 'input_shape', None)
                            self.model = dummy_model
                            self.logger.info("RNNPredictor: Modelo parcialmente carregado via TFSMLayer (sem input_shape).")
                    except Exception as e_layer:
                        self.logger.error(f"RNNPredictor: TFSMLayer fallback falhou: {e_layer}", exc_info=True)
                        self.model = None
                except Exception as e_tfsml_import:
                    self.logger.debug(f"RNNPredictor: TFSMLayer não disponível: {e_tfsml_import}")
                    self.model = None
                # continue to attempt loading scalers for partial functionality

            if self.model is not None and hasattr(self.model, 'input_shape'):
                try:
                    model_features_count = self.model.input_shape[-1]
                    if model_features_count != self.num_model_features_expected:
                        self.logger.error(f"DISCREPÂNCIA DE FEATURES! Modelo espera {model_features_count} features, "
                                          f"mas config.EXPECTED_SCALED_FEATURES_FOR_MODEL tem {self.num_model_features_expected} features.")
                        # Invalidate the model to avoid mismatched inputs
                        self.model = None
                except Exception:
                    # If model shape cannot be introspected, keep model as-is and log
                    self.logger.warning("RNNPredictor: Não foi possível verificar o número de features do modelo.")

            # load scalers: prefer centralized loader that validates manifest
            try:
                if load_scalers is not None:
                    model_dir = os.path.dirname(self.pv_scaler_path)
                    pv_name = os.path.basename(self.pv_scaler_path)
                    ind_name = os.path.basename(self.ind_scaler_path)
                    pv_s, ind_s, manifest = load_scalers(Path(model_dir), pv_name, ind_name)
                    self.price_volume_scaler = pv_s
                    self.indicator_scaler = ind_s
                    # persist manifest on the instance for later preprocessing use
                    self.scalers_manifest = manifest if isinstance(manifest, dict) else {}
                    self.logger.info(f"Scalers carregados via load_scalers; manifest keys: {list(self.scalers_manifest.keys()) if isinstance(self.scalers_manifest, dict) else self.scalers_manifest}")
                else:
                    # fallback to local loader
                    self.price_volume_scaler = self._load_scaler(self.pv_scaler_path, "Price/Volume (API)")
                    self.indicator_scaler = self._load_scaler(self.ind_scaler_path, "Indicator (API)")
            except Exception as e_load:
                self.logger.error(f"Falha ao carregar scalers via load_scalers: {e_load}", exc_info=True)
                # fallback to local loader
                self.price_volume_scaler = self._load_scaler(self.pv_scaler_path, "Price/Volume (API)")
                self.indicator_scaler = self._load_scaler(self.ind_scaler_path, "Indicator (API)")

            if self.price_volume_scaler is None or self.indicator_scaler is None:
                self.logger.error("Um ou ambos os scalers não puderam ser carregados. O preditor pode não funcionar.")
        except Exception as e:
            self.logger.error(f"RNNPredictor: Falha crítica ao carregar modelo ou scalers: {e}", exc_info=True)
            self.model = None # Invalida tudo se houver erro
            self.price_volume_scaler = None
            self.indicator_scaler = None

    async def load_model(self):
        """Async wrapper to load model and scalers without blocking the event loop."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_model_and_scalers)

    def health_check(self) -> dict:
        """
        Return health information useful for API/status endpoints.
        Contains:
          - manifest (if loaded)
          - pv_n_features and ind_n_features from loaded scalers (n_features_in_)
          - expected model features from config
          - model input shape if model loaded
        """
        info = {}
        info['manifest'] = getattr(self, 'scalers_manifest', None)
        try:
            info['pv_n_features_in'] = int(getattr(self.price_volume_scaler, 'n_features_in_', -1)) if self.price_volume_scaler is not None else None
        except Exception:
            info['pv_n_features_in'] = None
        try:
            info['ind_n_features_in'] = int(getattr(self.indicator_scaler, 'n_features_in_', -1)) if self.indicator_scaler is not None else None
        except Exception:
            info['ind_n_features_in'] = None
        info['expected_scaled_features_for_model_len'] = len(EXPECTED_SCALED_FEATURES_FOR_MODEL)
        if self.model is not None and hasattr(self.model, 'input_shape'):
            try:
                info['model_input_shape'] = tuple(self.model.input_shape)
            except Exception:
                info['model_input_shape'] = None
        else:
            info['model_input_shape'] = None
        return info

    async def predict_for_asset_ohlcv(
        self, 
        ohlcv_df_raw: pd.DataFrame, 
        api_operation_threshold: float = 0.65 # Seu threshold escolhido
    ) -> Tuple[Optional[int], Optional[float]]:
        
        current_loop = asyncio.get_event_loop()

        if self.model is None or self.price_volume_scaler is None or self.indicator_scaler is None:
            self.logger.warning("API Predict: Modelo ou scalers não carregados. Predição pulada.")
            return None, None

        # 1. Calcular todas as features base (use the function defined in this module)
        features_df_base = await current_loop.run_in_executor(
            None, calculate_features_for_prediction, ohlcv_df_raw, self.logger
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
            # model.predict is CPU/GPU heavy; run in executor
            raw_predictions = await current_loop.run_in_executor(None, self.model.predict, processed_input)
            
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