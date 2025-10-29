#!/usr/bin/env python3
"""
TREINADOR NEURAL PARA DAY TRADING
Sistema que coleta dados históricos e treina a CNN para melhorar as predições
"""

import json
import numpy as np
import pandas as pd
import logging
import sys
from datetime import datetime, timedelta
import os
import requests
import time

try:
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.utils import to_categorical
    from sklearn.preprocessing import MinMaxScaler
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow não disponível!")

from moises_estrategias_avancadas import TradingAvancado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'neural_training_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class NeuralTrainer:
    """Classe para treinar a rede neural com dados históricos"""
    
    def __init__(self):
        """Inicializar treinador neural"""
        logger.info("=== NEURAL TRAINER - APRENDIZADO DE MÁQUINA ===")
        
        # Configurações
        self.window_size = 60  # 60 períodos de 5min = 5 horas
        self.simbolos = ['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT']
        self.scaler = MinMaxScaler()
        
        # Carregar trader
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        dados_amos = config['CONTA_3']
        self.trader = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="NEURAL_TRAINER"
        )
        
        # Dados para treinamento
        self.dados_treinamento = []
        self.labels_treinamento = []
        
        logger.info("[TRAINER] Inicializado com sucesso!")
    
    def coletar_dados_historicos(self, symbol, dias=30):
        """Coletar dados históricos de um símbolo"""
        try:
            logger.info(f"[DADOS] Coletando {symbol} - {dias} dias...")
            
            # Coletar candles históricos
            candles = []
            
            # Usar API pública da Binance para dados históricos
            url = "https://api.binance.com/api/v3/klines"
            
            # Calcular timestamp
            end_time = int(time.time() * 1000)
            start_time = end_time - (dias * 24 * 60 * 60 * 1000)
            
            params = {
                'symbol': symbol,
                'interval': '5m',
                'startTime': start_time,
                'endTime': end_time,
                'limit': 1000
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for kline in data:
                    candle = {
                        'timestamp': int(kline[0]),
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5])
                    }
                    candles.append(candle)
                
                logger.info(f"[DADOS] Coletados {len(candles)} candles de {symbol}")
                return candles
            else:
                logger.error(f"[ERRO] API: {response.status_code} - {symbol}")
                return []
                
        except Exception as e:
            logger.error(f"[ERRO] Coleta {symbol}: {e}")
            return []
    
    def calcular_indicadores(self, candles):
        """Calcular indicadores técnicos"""
        try:
            if len(candles) < 50:
                return None
            
            df = pd.DataFrame(candles)
            
            # Indicadores básicos
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['ema_26'] = df['close'].ewm(span=26).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
            bb_std_dev = df['close'].rolling(window=bb_period).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std_dev * bb_std)
            df['bb_lower'] = df['bb_middle'] - (bb_std_dev * bb_std)
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price change
            df['price_change'] = df['close'].pct_change()
            df['volatility'] = df['price_change'].rolling(window=20).std()
            
            # Remover NaN
            df = df.dropna()
            
            return df
            
        except Exception as e:
            logger.error(f"[ERRO] Indicadores: {e}")
            return None
    
    def criar_labels_movimento(self, df, look_ahead=12):
        """Criar labels de movimento futuro (12 períodos = 1 hora)"""
        try:
            labels = []
            
            for i in range(len(df) - look_ahead):
                preco_atual = df.iloc[i]['close']
                preco_futuro = df.iloc[i + look_ahead]['close']
                
                mudanca_pct = ((preco_futuro - preco_atual) / preco_atual) * 100
                
                # Classificação de movimento
                if mudanca_pct > 1.5:  # Subida significativa (>1.5%)
                    label = 2  # COMPRA
                elif mudanca_pct < -1.0:  # Descida significativa (<-1%)
                    label = 0  # VENDA  
                else:
                    label = 1  # HOLD
                
                labels.append(label)
            
            return np.array(labels)
            
        except Exception as e:
            logger.error(f"[ERRO] Labels: {e}")
            return np.array([])
    
    def preparar_sequencias(self, df, labels):
        """Preparar sequências para a CNN"""
        try:
            # Features para a CNN
            feature_cols = [
                'open', 'high', 'low', 'close', 'volume',
                'sma_20', 'sma_50', 'ema_12', 'ema_26',
                'rsi', 'macd', 'macd_signal', 'macd_hist',
                'bb_upper', 'bb_middle', 'bb_lower',
                'volume_ratio', 'price_change', 'volatility'
            ]
            
            # Verificar se todas as colunas existem
            available_cols = [col for col in feature_cols if col in df.columns]
            if len(available_cols) < 10:
                logger.warning(f"[SEQUENCIAS] Poucas features: {len(available_cols)}")
                return None, None
            
            # Normalizar dados
            dados = df[available_cols].values
            dados_norm = self.scaler.fit_transform(dados)
            
            # Criar sequências
            X, y = [], []
            
            for i in range(self.window_size, len(dados_norm)):
                if i < len(labels):
                    X.append(dados_norm[i-self.window_size:i])
                    y.append(labels[i])
            
            return np.array(X), np.array(y)
            
        except Exception as e:
            logger.error(f"[ERRO] Sequências: {e}")
            return None, None
    
    def treinar_modelo_completo(self):
        """Treinar modelo com dados de todos os símbolos"""
        try:
            logger.info("[TREINAMENTO] Iniciando coleta de dados...")
            
            all_X, all_y = [], []
            
            # Coletar dados de todos os símbolos
            for symbol in self.simbolos:
                logger.info(f"[PROCESSANDO] {symbol}...")
                
                # Coletar dados históricos
                candles = self.coletar_dados_historicos(symbol, dias=30)
                if not candles:
                    continue
                
                # Calcular indicadores
                df = self.calcular_indicadores(candles)
                if df is None or len(df) < self.window_size + 20:
                    continue
                
                # Criar labels
                labels = self.criar_labels_movimento(df)
                if len(labels) == 0:
                    continue
                
                # Preparar sequências
                X, y = self.preparar_sequencias(df, labels)
                if X is None or len(X) == 0:
                    continue
                
                all_X.extend(X)
                all_y.extend(y)
                
                logger.info(f"[DADOS] {symbol}: {len(X)} sequências")
            
            if len(all_X) == 0:
                logger.error("[ERRO] Nenhum dado coletado!")
                return False
            
            # Converter para arrays numpy
            X_train = np.array(all_X)
            y_train = np.array(all_y)
            
            logger.info(f"[DATASET] Total: {len(X_train)} sequências")
            logger.info(f"[SHAPE] X: {X_train.shape}, y: {y_train.shape}")
            
            # Verificar distribuição das classes
            unique, counts = np.unique(y_train, return_counts=True)
            logger.info(f"[CLASSES] Distribuição: {dict(zip(unique, counts))}")
            
            # Converter labels para categorical
            y_train_cat = to_categorical(y_train, num_classes=3)
            
            # Criar modelo CNN
            model = self.criar_modelo_cnn(X_train.shape[1:])
            
            # Treinar modelo
            logger.info("[TREINAMENTO] Iniciando treino da CNN...")
            
            history = model.fit(
                X_train, y_train_cat,
                epochs=100,
                batch_size=64,
                validation_split=0.2,
                verbose=1,
                shuffle=True
            )
            
            # Salvar modelo
            os.makedirs('models', exist_ok=True)
            model.save('models/cnn_trading_model.keras')
            
            # Mostrar resultados
            final_acc = history.history['accuracy'][-1]
            final_val_acc = history.history['val_accuracy'][-1]
            
            logger.info(f"[SUCESSO] Modelo treinado!")
            logger.info(f"[ACURÁCIA] Treino: {final_acc:.4f}, Validação: {final_val_acc:.4f}")
            
            # Testar modelo
            self.testar_modelo(model, X_train[:100], y_train[:100])
            
            return True
            
        except Exception as e:
            logger.error(f"[ERRO] Treinamento: {e}")
            return False
    
    def criar_modelo_cnn(self, input_shape):
        """Criar modelo CNN otimizado"""
        if not TENSORFLOW_AVAILABLE:
            return None
        
        model = Sequential([
            # Primeira camada convolucional
            Conv1D(filters=64, kernel_size=3, activation='relu', input_shape=input_shape),
            MaxPooling1D(pool_size=2),
            
            # Segunda camada convolucional
            Conv1D(filters=128, kernel_size=3, activation='relu'),
            MaxPooling1D(pool_size=2),
            
            # Terceira camada convolucional
            Conv1D(filters=64, kernel_size=3, activation='relu'),
            
            # Flatten e Dense
            Flatten(),
            
            # Camadas totalmente conectadas
            Dense(128, activation='relu'),
            Dropout(0.3),
            
            Dense(64, activation='relu'),
            Dropout(0.2),
            
            Dense(32, activation='relu'),
            Dropout(0.1),
            
            # Saída (3 classes: VENDA, HOLD, COMPRA)
            Dense(3, activation='softmax')
        ])
        
        # Compilar modelo
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        logger.info("[MODELO] CNN criada com sucesso!")
        logger.info(f"[ARQUITETURA] Input: {input_shape}")
        
        return model
    
    def testar_modelo(self, model, X_test, y_test):
        """Testar modelo treinado"""
        try:
            # Fazer predições
            predictions = model.predict(X_test, verbose=0)
            pred_classes = np.argmax(predictions, axis=1)
            
            # Calcular acurácia
            accuracy = np.mean(pred_classes == y_test)
            
            logger.info(f"[TESTE] Acurácia no teste: {accuracy:.4f}")
            
            # Mostrar algumas predições
            for i in range(min(10, len(X_test))):
                confianca = np.max(predictions[i])
                classe_pred = pred_classes[i]
                classe_real = y_test[i]
                
                classes = ['VENDA', 'HOLD', 'COMPRA']
                logger.info(f"[PRED {i+1}] Real: {classes[classe_real]}, "
                          f"Pred: {classes[classe_pred]} ({confianca:.2f})")
            
            return accuracy
            
        except Exception as e:
            logger.error(f"[ERRO] Teste: {e}")
            return 0.0
    
    def executar_treinamento_continuo(self):
        """Executar treinamento contínuo"""
        try:
            logger.info("[CONTINUO] Iniciando treinamento contínuo...")
            
            ciclo = 1
            while True:
                logger.info(f"[CICLO {ciclo}] Treinamento neural...")
                
                # Treinar modelo
                sucesso = self.treinar_modelo_completo()
                
                if sucesso:
                    logger.info(f"[CICLO {ciclo}] Treinamento concluído com sucesso!")
                else:
                    logger.warning(f"[CICLO {ciclo}] Falha no treinamento!")
                
                # Aguardar 6 horas para próximo treinamento
                logger.info("[AGUARDA] Próximo treinamento em 6 horas...")
                time.sleep(6 * 60 * 60)  # 6 horas
                
                ciclo += 1
                
        except KeyboardInterrupt:
            logger.info("[PARADO] Treinamento interrompido pelo usuário")
        except Exception as e:
            logger.error(f"[ERRO] Treinamento contínuo: {e}")

def main():
    """Função principal"""
    if not TENSORFLOW_AVAILABLE:
        logger.error("TensorFlow não disponível! Instale: pip install tensorflow")
        return
    
    trainer = NeuralTrainer()
    
    # Executar um treinamento único
    logger.info("Executando treinamento único...")
    sucesso = trainer.treinar_modelo_completo()
    
    if sucesso:
        logger.info("✅ TREINAMENTO CONCLUÍDO COM SUCESSO!")
        logger.info("📈 Modelo salvo em: models/cnn_trading_model.keras")
        logger.info("🧠 A rede neural está agora mais inteligente!")
    else:
        logger.error("❌ FALHA NO TREINAMENTO!")

if __name__ == "__main__":
    main()