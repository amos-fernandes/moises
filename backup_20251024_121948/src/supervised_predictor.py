# src/model/supervised_predictor.py
import os
import joblib
import numpy as np
from tensorflow.keras.models import load_model
from src.utils.logger import get_logger

class SupervisedPredictor:
    def __init__(self, model_dir="src/model", logger_instance=None):
        self.model_dir = model_dir
        self.logger = logger_instance or get_logger()
        self.model = None
        self.pv_scaler = None
        self.ind_scaler = None
        self.expected_features = [
            'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 'volume_div_atr',
            'log_return', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37',
            'body_size_norm_atr', 'body_vs_avg_body', 'macd', 'sma_10_div_atr',
            'adx_14', 'volume_zscore', 'buy_condition_v1'
        ]
        self.scaled_features = [f"{col}_scaled" for col in self.expected_features]

    def load_model(self):
        try:
            # Carregar modelo
            model_path = os.path.join(self.model_dir, "model.h5")
            if not os.path.exists(model_path):
                self.logger.error(f"❌ Arquivo do modelo não encontrado: {model_path}")
                return False
            self.model = load_model(model_path)
            self.logger.info("✅ Modelo Keras (model.h5) carregado com sucesso.")

            # Carregar scalers
            pv_path = os.path.join(self.model_dir, "price_volume_atr_norm_scaler.joblib")
            ind_path = os.path.join(self.model_dir, "other_indicators_scaler.joblib")
            self.pv_scaler = joblib.load(pv_path)
            self.ind_scaler = joblib.load(ind_path)
            self.logger.info("✅ Scalers carregados com sucesso.")

            return True
        except Exception as e:
            self.logger.error(f"❌ Falha ao carregar modelo ou scalers: {e}")
            return False

    def predict(self, data):
        """
        data: dict com dados de um ativo (ex: {'BTC/USDT': {...}})
        Retorna: (sinal, confiança)
        """
        if not self.model:
            self.logger.error("❌ Modelo não carregado.")
            return None, None

        try:
            # Extrair dados
            asset_data = list(data.values())[0]
            ohlcv_df = self._create_dataframe(asset_data)
            X = self._prepare_features(ohlcv_df)
            X = X.reshape(1, X.shape[0], X.shape[1])  # (1, 60, 18)

            # Predição
            pred = self.model.predict(X, verbose=0)
            confidence = float(pred[0][0])
            signal = 1 if confidence > 0.5 else 0

            self.logger.info(f"📊 Predição: {signal} (confiança: {confidence:.3f})")
            return signal, confidence

        except Exception as e:
            self.logger.error(f"❌ Erro na predição: {e}")
            return None, None

    def _create_dataframe(self, asset_data):
        # Cria um DataFrame com as colunas esperadas
        import pandas as pd
        df = pd.DataFrame(asset_data["ohlcv_1h"], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def _prepare_features(self, df):
        # Aqui você replica a lógica do data_handler_multi_asset.py
        # Por simplicidade, retornamos um array aleatório para teste
        return np.random.rand(60, 18).astype(np.float32)