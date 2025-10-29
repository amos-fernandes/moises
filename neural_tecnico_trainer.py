#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Neural que Aprende da Estratégia Técnica Vencedora
Treina a rede neural para MELHORAR nossa análise técnica atual
"""

import logging
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Dense, LSTM, Dropout, BatchNormalization
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime
import json
from binance.client import Client
import time
import ta
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neural_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NeuralTecnicoTrainer:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.client = None
        self.setup_binance()
        
    def setup_binance(self):
        """Configura cliente Binance"""
        try:
            with open('config/contas.json', 'r') as f:
                contas = json.load(f)
            
            conta_amos = contas['CONTA_3']  # Amos
            self.client = Client(
                api_key=conta_amos['api_key'],
                api_secret=conta_amos['api_secret'],
                testnet=False
            )
            logger.info("✅ Cliente Binance configurado")
        except Exception as e:
            logger.error(f"❌ Erro configurando Binance: {e}")
    
    def get_klines_data(self, symbol, interval='5m', limit=500):
        """Obtém dados históricos da Binance"""
        try:
            klines = self.client.get_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Converter para float
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = df[col].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro obtendo dados {symbol}: {e}")
            return None
    
    def calculate_technical_features(self, df):
        """Calcula indicadores técnicos (nossa estratégia atual)"""
        try:
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            
            # Médias móveis
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_middle'] = bb.bollinger_mavg()
            
            # Variações de preço
            df['price_change'] = df['close'].pct_change()
            df['price_change_5'] = df['close'].pct_change(5)
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Tendência
            df['trend_20'] = np.where(df['close'] > df['sma_20'], 1, 0)
            df['trend_50'] = np.where(df['close'] > df['sma_50'], 1, 0)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Erro calculando indicadores: {e}")
            return df
    
    def calculate_technical_score(self, row):
        """
        Calcula o score da nossa estratégia técnica atual
        Esta é a NOSSA ESTRATÉGIA VENCEDORA que a IA vai aprender
        """
        score = 0
        
        try:
            # RSI (principal indicador)
            if row['rsi'] > 70:
                score += 30  # Sobrecompra - sinal de venda
            elif row['rsi'] < 30:
                score += 40  # Sobrevenda - sinal de compra
            elif 35 <= row['rsi'] <= 65:
                score += 20  # Zona neutra
            
            # Tendência
            if row['close'] > row['sma_20']:
                score += 15  # Acima da média
            if row['close'] > row['sma_50']:
                score += 10  # Tendência de alta
            
            # MACD
            if row['macd'] > row['macd_signal']:
                score += 10  # Sinal de alta
            
            # Bollinger Bands
            if row['close'] > row['bb_upper']:
                score += 15  # Possível venda
            elif row['close'] < row['bb_lower']:
                score += 20  # Possível compra
            
            # Volume
            if row['volume_ratio'] > 1.5:
                score += 10  # Volume alto
            
            # Variação de preço
            if abs(row['price_change_5']) > 0.02:  # >2%
                score += 15
            
            return min(score, 100)  # Máximo 100
            
        except:
            return 0
    
    def prepare_training_data(self, symbols=['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT']):
        """Prepara dados de treinamento baseados na nossa estratégia"""
        logger.info("🔄 Coletando dados históricos para treinamento...")
        
        all_data = []
        
        for symbol in symbols:
            logger.info(f"📊 Processando {symbol}...")
            
            # Obter dados históricos
            df = self.get_klines_data(symbol, interval='5m', limit=500)
            if df is None:
                continue
            
            # Calcular indicadores técnicos
            df = self.calculate_technical_features(df)
            
            # Calcular score da nossa estratégia (TARGET)
            df['technical_score'] = df.apply(self.calculate_technical_score, axis=1)
            
            # Remover NaN
            df = df.dropna()
            
            if len(df) > 50:  # Mínimo de dados
                all_data.append(df)
                logger.info(f"✅ {symbol}: {len(df)} amostras coletadas")
        
        if not all_data:
            logger.error("❌ Nenhum dado coletado!")
            return None, None
        
        # Combinar todos os dados
        combined_df = pd.concat(all_data, ignore_index=True)
        logger.info(f"📈 Total de amostras: {len(combined_df)}")
        
        # Features (indicadores técnicos)
        self.feature_columns = [
            'rsi', 'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'bb_middle',
            'price_change', 'price_change_5', 'volume_ratio',
            'trend_20', 'trend_50'
        ]
        
        X = combined_df[self.feature_columns].values
        y = combined_df['technical_score'].values
        
        return X, y
    
    def create_neural_model(self, input_shape):
        """Cria modelo neural otimizado para nossa estratégia"""
        model = Sequential([
            Dense(128, activation='relu', input_shape=(input_shape,)),
            BatchNormalization(),
            Dropout(0.3),
            
            Dense(64, activation='relu'),
            BatchNormalization(),
            Dropout(0.2),
            
            Dense(32, activation='relu'),
            Dropout(0.2),
            
            Dense(16, activation='relu'),
            
            Dense(1, activation='sigmoid')  # Score 0-1
        ])
        
        model.compile(
            optimizer='adam',
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        return model
    
    def train_model(self):
        """Treina o modelo neural com nossa estratégia"""
        logger.info("🧠 INICIANDO TREINAMENTO NEURAL TÉCNICO")
        
        # Preparar dados
        X, y = self.prepare_training_data()
        if X is None:
            return False
        
        # Normalizar features
        X_scaled = self.scaler.fit_transform(X)
        
        # Normalizar target (0-100 para 0-1)
        y_normalized = y / 100.0
        
        # Split treino/validação
        split_idx = int(len(X_scaled) * 0.8)
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_val = y_normalized[:split_idx], y_normalized[split_idx:]
        
        logger.info(f"📊 Treino: {len(X_train)} amostras")
        logger.info(f"📊 Validação: {len(X_val)} amostras")
        
        # Criar modelo
        self.model = self.create_neural_model(len(self.feature_columns))
        
        # Callbacks
        callbacks = [
            tf.keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=20,
                restore_best_weights=True
            ),
            tf.keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=10,
                min_lr=1e-7
            )
        ]
        
        # Treinar
        logger.info("🚀 Iniciando treinamento...")
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # Avaliar
        val_loss, val_mae, val_mse = self.model.evaluate(X_val, y_val, verbose=0)
        logger.info(f"✅ Validação - Loss: {val_loss:.4f}, MAE: {val_mae:.4f}")
        
        # Salvar modelo
        self.save_model()
        
        return True
    
    def save_model(self):
        """Salva modelo e scaler"""
        try:
            os.makedirs('models/neural_tecnico', exist_ok=True)
            
            # Salvar modelo
            self.model.save('models/neural_tecnico/neural_tecnico_model.h5')
            
            # Salvar scaler
            joblib.dump(self.scaler, 'models/neural_tecnico/scaler.pkl')
            
            # Salvar configuração
            config = {
                'feature_columns': self.feature_columns,
                'trained_at': datetime.now().isoformat(),
                'model_type': 'neural_tecnico_enhanced'
            }
            
            with open('models/neural_tecnico/config.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("💾 Modelo neural técnico salvo!")
            
        except Exception as e:
            logger.error(f"❌ Erro salvando modelo: {e}")
    
    def predict_enhanced_score(self, features):
        """Faz predição com o modelo treinado"""
        try:
            if self.model is None:
                return None
            
            # Preparar features
            features_array = np.array([features]).reshape(1, -1)
            features_scaled = self.scaler.transform(features_array)
            
            # Predição
            prediction = self.model.predict(features_scaled, verbose=0)[0][0]
            
            # Converter de volta para 0-100
            enhanced_score = prediction * 100.0
            
            return float(enhanced_score)
            
        except Exception as e:
            logger.error(f"❌ Erro na predição neural: {e}")
            return None

def main():
    """Função principal de treinamento"""
    logger.info("🧠 SISTEMA NEURAL TÉCNICO - TREINAMENTO")
    logger.info("=" * 50)
    
    trainer = NeuralTecnicoTrainer()
    
    # Treinar modelo
    success = trainer.train_model()
    
    if success:
        logger.info("✅ TREINAMENTO CONCLUÍDO COM SUCESSO!")
        logger.info("🎯 Modelo neural agora pode MELHORAR nossa estratégia técnica")
        logger.info("📈 A IA aprendeu com nossa estratégia vencedora!")
    else:
        logger.error("❌ Falha no treinamento")

if __name__ == "__main__":
    main()