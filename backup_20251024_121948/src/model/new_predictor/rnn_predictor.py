
# rnn_predictor.py

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Any, Optional, Dict, List, Tuple

# Biblioteca para indicadores técnicos
try:
    import pandas_ta as ta
except ImportError:
    print("AVISO: Biblioteca pandas_ta não instalada. Indicadores técnicos não serão calculados.")
    ta = None # Define como None se não puder importar

# Biblioteca para carregar scalers
try:
    import joblib
except ImportError:
    print("AVISO: Biblioteca joblib não instalada. Scalers não poderão ser carregados de arquivos.")
    joblib = None

# Importar configurações
from config import (
    WINDOW_SIZE, NUM_FEATURES, EXPECTED_FEATURES_ORDER,
    MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME, INDICATOR_SCALER_NAME,
    BASE_FEATURE_COLS # Para determinar as colunas de escalonamento
)

# Caminhos para os scalers salvos
SCALER_DIR = MODEL_SAVE_DIR # Agora vem do config
PRICE_VOL_SCALER_PATH = os.path.join(SCALER_DIR, PRICE_VOL_SCALER_NAME)
INDICATOR_SCALER_PATH = os.path.join(SCALER_DIR, INDICATOR_SCALER_NAME)

def calculate_technical_indicators(ohlcv_df: pd.DataFrame, logger_instance) -> pd.DataFrame:
    """
    Calcula indicadores técnicos a partir de um DataFrame OHLCV pandas.
    """
    if ta is None:
        logger_instance.warning("TA: pandas_ta não disponível, pulando cálculo de indicadores.")
        return ohlcv_df # Retorna o DataFrame original

    df_with_indicators = ohlcv_df.copy()
    try:
        df_with_indicators.ta.sma(length=10, close=\'close\', append=True, col_names=(\'sma_10\'))
        df_with_indicators.ta.rsi(length=14, close=\'close\', append=True, col_names=(\'rsi_14\'))
        df_with_indicators.ta.macd(close=\'close\', append=True, col_names=(\'macd\', \'macdh\', \'macds\'))
        df_with_indicators.ta.atr(length=14, append=True, col_names=(\'atr\',))
        df_with_indicators.ta.bbands(length=20, close=\'close\', append=True, col_names=(\'bbl\', \'bbm\', \'bbu\', \'bbb\', \'bbp\'))

        # Normalização por ATR (consistente com data_handler.py)
        epsilon = 1e-6 # Ajustado para um valor um pouco maior para robustez
        df_with_indicators[\'close_div_atr\'] = df_with_indicators[\'close\'] / (df_with_indicators[\'atr\'] + epsilon)
        df_with_indicators[\'volume_div_atr\'] = df_with_indicators[\'volume\'] / (df_with_indicators[\'atr\'] + epsilon)
        df_with_indicators[\'sma_10_div_atr\'] = df_with_indicators[\'sma_10\'] / (df_with_indicators[\'atr\'] + epsilon)
        df_with_indicators[\'macd_div_atr\'] = df_with_indicators[\'macd\'] / (df_with_indicators[\'atr\'] + epsilon)

        logger_instance.info("TA: Indicadores SMA(10), RSI(14), MACD, ATR, BBANDS calculados.")
    except Exception as e:
        logger_instance.error(f"TA: Erro ao calcular indicadores técnicos: {e}", exc_info=True)
        return ohlcv_df
        
    return df_with_indicators

def preprocess_input_data_for_asset(
    asset_market_data: Dict[str, Any], 
    window_size: int = WINDOW_SIZE, # Usa do config
    expected_features_order: List[str] = EXPECTED_FEATURES_ORDER, # Usa do config
    price_vol_scaler = None, 
    indicator_scaler = None, 
    logger_instance = None
) -> np.ndarray:
    """
    Pré-processa os dados de mercado de UM ÚNICO ATIVO para o formato esperado pela RNN.
    """
    if logger_instance is None:
        import logging
        logger_instance = logging.getLogger(__name__)

    ohlcv_raw = asset_market_data.get(\'ohlcv_1h\', [])
    
    if not ohlcv_raw or len(ohlcv_raw) < window_size: 
        min_data_needed = window_size + 15 # Exemplo: SMA10 e RSI14 precisam de alguns pontos antes da janela de 60
        if len(ohlcv_raw) < min_data_needed:
            logger_instance.warning(f"Preprocessing: Dados OHLCV insuficientes para {asset_market_data.get(\'symbol\', \'ativo\')}. "
                                    f"Necessário (para janela+indicadores): ~{min_data_needed}, Disponível: {len(ohlcv_raw)}")
            return np.array([])

    try:
        ohlcv_df = pd.DataFrame(ohlcv_raw, columns=[\'timestamp\', \'open\', \'high\', \'low\', \'close\', \'volume\'])
        ohlcv_df.set_index(pd.to_datetime(ohlcv_df[\'timestamp\'], unit=\'ms\'), inplace=True)
        ohlcv_df.drop(\'timestamp\', axis=1, inplace=True)
    except Exception as e_df:
        logger_instance.error(f"Preprocessing: Erro ao criar DataFrame OHLCV: {e_df}", exc_info=True)
        return np.array([])

    df_with_ta = calculate_technical_indicators(ohlcv_df, logger_instance)
    df_with_ta.dropna(inplace=True)

    if len(df_with_ta) < window_size:
        logger_instance.warning(f"Preprocessing: Dados insuficientes para {asset_market_data.get(\'symbol\', \'ativo\')} após TA e dropna. "
                                f"Necessário: {window_size}, Disponível: {len(df_with_ta)}")
        return np.array([])
    
    final_window_df = df_with_ta.tail(window_size).copy()

    scaled_df = pd.DataFrame(index=final_window_df.index)

    # Definir as colunas para cada scaler, consistente com train_rnn_model.py
    price_volume_cols_for_scaler = [col for col in BASE_FEATURE_COLS if \'close\' in col or \'volume\' in col]
    indicator_cols_for_scaler = [col for col in BASE_FEATURE_COLS if col not in price_volume_cols_for_scaler]

    # Scaler para Preço/Volume
    if all(col in final_window_df.columns for col in price_volume_cols_for_scaler):
        if price_vol_scaler:
            try:
                scaled_pv_data = price_vol_scaler.transform(final_window_df[price_volume_cols_for_scaler])
                for i, col_name in enumerate(price_volume_cols_for_scaler):
                    scaled_df[col_name.replace(\'_div_atr\', \'_scaled\')] = scaled_pv_data[:, i]
                logger_instance.info("Preprocessing: Features de preço/volume escaladas.")
            except Exception as e_pv_scale:
                logger_instance.error(f"Preprocessing: Erro ao escalar features de preço/volume: {e_pv_scale}", exc_info=True)
                return np.array([])
        else:
            logger_instance.warning("Preprocessing: Scaler de Preço/Volume não fornecido. Usando dados originais (NÃO RECOMENDADO).")
            for col_name in price_volume_cols_for_scaler:
                scaled_df[col_name.replace(\'_div_atr\', \'_scaled\')] = final_window_df[col_name]
    else:
        logger_instance.error(f"Preprocessing: Colunas de preço/volume {price_volume_cols_for_scaler} não encontradas.")
        return np.array([])

    # Scaler para Indicadores
    if all(col in final_window_df.columns for col in indicator_cols_for_scaler):
        if indicator_scaler:
            try:
                if final_window_df[indicator_cols_for_scaler].isnull().values.any():
                    logger_instance.error(f"Preprocessing: NaNs encontrados nas colunas de indicadores {indicator_cols_for_scaler} ANTES de escalar.")
                    return np.array([])

                scaled_ind_data = indicator_scaler.transform(final_window_df[indicator_cols_for_scaler])
                for i, col_name in enumerate(indicator_cols_for_scaler):
                    scaled_df[col_name.replace(\'_div_atr\', \'_scaled\')] = scaled_ind_data[:, i]
                logger_instance.info("Preprocessing: Features de indicadores escaladas.")
            except Exception as e_ind_scale:
                logger_instance.error(f"Preprocessing: Erro ao escalar features de indicadores: {e_ind_scale}", exc_info=True)
                return np.array([])
        else:
            logger_instance.warning("Preprocessing: Scaler de Indicadores não fornecido. Usando dados originais (NÃO RECOMENDADO).")
            for col_name in indicator_cols_for_scaler:
                scaled_df[col_name.replace(\'_div_atr\', \'_scaled\')] = final_window_df[col_name]
    else:
        logger_instance.error(f"Preprocessing: Colunas de indicadores {indicator_cols_for_scaler} não encontradas.")
        return np.array([])
        
    missing_final_features = [feat for feat in expected_features_order if feat not in scaled_df.columns]
    if missing_final_features:
        logger_instance.error(f"Preprocessing: Features FINAIS esperadas ausentes no DataFrame escalado: {missing_final_features}. "
                              f"Disponíveis: {scaled_df.columns.tolist()}")
        return np.array([])
        
    final_features_array = scaled_df[expected_features_order].values 

    reshaped_data = np.reshape(final_features_array, (1, window_size, NUM_FEATURES))
    
    logger_instance.info(f"Preprocessing: Dados pré-processados para {asset_market_data.get(\'symbol\', \'ativo\')} com shape: {reshaped_data.shape}")
    return reshaped_data


class RNNModelPredictor:
    def __init__(self, model_path: str, logger_instance):
        self.model_path = model_path
        self.model: Optional[tf.keras.Model] = None
        self.logger = logger_instance
        
        self.price_volume_scaler = self._load_scaler(PRICE_VOL_SCALER_PATH, "Price/Volume")
        self.indicator_scaler = self._load_scaler(INDICATOR_SCALER_PATH, "Indicator") # Corrigido self_load_scaler para _load_scaler
        
        self._load_model()

    def _load_scaler(self, scaler_path: str, scaler_name: str):
        if joblib is None:
            self.logger.warning(f"ScalerLoader: Joblib não disponível, não é possível carregar scaler {scaler_name} de {scaler_path}.")
            return None
        try:
            if os.path.exists(scaler_path):
                scaler = joblib.load(scaler_path)
                self.logger.info(f"ScalerLoader: Scaler {scaler_name} carregado de {scaler_path}.")
                return scaler
            else:
                self.logger.warning(f"ScalerLoader: Arquivo do scaler {scaler_name} não encontrado em {scaler_path}. "
                                 "O pré-processamento pode usar dados não escalados (NÃO RECOMENDADO).")
                return None
        except Exception as e:
            self.logger.error(f"ScalerLoader: Erro ao carregar scaler {scaler_name} de {scaler_path}: {e}", exc_info=True)
            return None

    def _load_model(self):
        try:
            self.logger.info(f"RNNPredictor: Carregando modelo de {self.model_path}...")
            self.model = tf.keras.models.load_model(self.model_path)
            self.logger.info(f"RNNPredictor: Modelo carregado com sucesso. Input shape esperado pelo modelo: {self.model.input_shape}")
            
            if self.model.input_shape != (None, WINDOW_SIZE, NUM_FEATURES):
                self.logger.warning(f"RNNPredictor: Discrepância no input shape! "
                                    f"Modelo espera: {self.model.input_shape}, "
                                    f"Configurado para: (None, {WINDOW_SIZE}, {NUM_FEATURES}). "
                                    f"Verifique WINDOW_SIZE e EXPECTED_FEATURES_ORDER no config.py.")
        except Exception as e:
            self.logger.error(f"RNNPredictor: Falha ao carregar modelo de {self.model_path}: {e}", exc_info=True)
            self.model = None

    async def predict_for_asset(
        self, 
        asset_market_data: Dict[str, Any], 
        loop=None,
    ) -> Tuple[Optional[int], Optional[float]]:
        if not self.model:
            self.logger.warning(f"RNNPredictor: Modelo não carregado, predição pulada para {asset_market_data.get(\'symbol\', \'ativo\')}.")
            return None, None
        
        if self.price_volume_scaler is None or self.indicator_scaler is None:
            self.logger.warning(f"RNNPredictor: Scalers não carregados. A predição para {asset_market_data.get(\'symbol\', \'ativo\')} pode ser imprecisa ou falhar.")

        try:
            processed_input = preprocess_input_data_for_asset(
                asset_market_data,
                window_size=WINDOW_SIZE, 
                expected_features_order=EXPECTED_FEATURES_ORDER, 
                price_vol_scaler=self.price_volume_scaler,
                indicator_scaler=self.indicator_scaler,
                logger_instance=self.logger
            )

            if processed_input.size == 0:
                self.logger.warning(f"RNNPredictor: Pré-processamento falhou para {asset_market_data.get(\'symbol\', \'ativo\')}.")
                return None, None

            if loop is None:
                import asyncio
                loop = asyncio.get_running_loop()
            
            raw_predictions = await loop.run_in_executor(None, self.model.predict, processed_input)
            
            if raw_predictions.ndim == 2 and raw_predictions.shape[0] == 1 and raw_predictions.shape[1] == 1:
                prediction_prob = float(raw_predictions[0, 0])
                signal = int(prediction_prob > 0.50) 
                self.logger.info(f"RNNPredictor: Predição para {asset_market_data.get(\'symbol\', \'ativo\')} - Prob: {prediction_prob:.4f}, Sinal: {signal}")
                return signal, prediction_prob
            else:
                self.logger.warning(f"RNNPredictor: Formato de predição inesperado para {asset_market_data.get(\'symbol\', \'ativo\')}: {raw_predictions.shape}")
                return None, None

        except Exception as e:
            self.logger.error(f"RNNPredictor: Erro durante a predição para {asset_market_data.get(\'symbol\', \'ativo\')}: {e}", exc_info=True)
            return None, None


