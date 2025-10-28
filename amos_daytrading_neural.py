#!/usr/bin/env python3
"""
AMOS DAY TRADING COM REDE NEURAL CNN
Sistema avançado: Análise técnica + Rede Neural = Decisões inteligentes
"""

import json
import time
import logging
import sys
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler
import os

try:
    from tensorflow.keras.models import load_model, Sequential
    from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    TENSORFLOW_AVAILABLE = True
except ImportError:
    TENSORFLOW_AVAILABLE = False
    print("TensorFlow não disponível. Usando apenas análise técnica.")

from moises_estrategias_avancadas import TradingAvancado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amos_neural_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class CNNPredictor:
    """Rede Neural CNN para predições de trading"""
    
    def __init__(self):
        self.model = None
        self.scaler = MinMaxScaler()
        self.model_path = 'models/cnn_trading_model.keras'
        self.is_trained = False
        
        # Tentar carregar modelo existente
        if os.path.exists(self.model_path) and TENSORFLOW_AVAILABLE:
            try:
                self.model = load_model(self.model_path)
                self.is_trained = True
                logger.info("[CNN] Modelo carregado com sucesso!")
            except Exception as e:
                logger.warning(f"[CNN] Erro ao carregar modelo: {e}")
    
    def criar_modelo(self, input_shape):
        """Criar novo modelo CNN"""
        if not TENSORFLOW_AVAILABLE:
            return None
            
        model = Sequential([
            Conv1D(64, 3, activation='relu', input_shape=input_shape),
            MaxPooling1D(2),
            Conv1D(128, 3, activation='relu'),
            MaxPooling1D(2),
            Conv1D(64, 3, activation='relu'),
            Flatten(),
            Dense(128, activation='relu'),
            Dropout(0.3),
            Dense(64, activation='relu'),
            Dropout(0.2),
            Dense(3, activation='softmax')  # 3 classes: COMPRA, VENDA, HOLD
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def preparar_dados_trading(self, candles, window_size=60):
        """Preparar dados de candles para a CNN"""
        try:
            if len(candles) < window_size + 1:
                return None, None
            
            # Converter para DataFrame
            df = pd.DataFrame(candles)
            
            # Features básicas
            features = ['open', 'high', 'low', 'close', 'volume']
            
            # Adicionar indicadores técnicos
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['ema_12'] = df['close'].ewm(span=12).mean()
            df['rsi'] = self.calcular_rsi(df['close'].values)
            df['bb_upper'], df['bb_lower'] = self.calcular_bollinger_bands(df['close'].values)
            
            # Remover NaN
            df = df.dropna()
            
            if len(df) < window_size:
                return None, None
            
            # Selecionar features para CNN
            feature_cols = ['open', 'high', 'low', 'close', 'volume', 
                          'sma_20', 'ema_12', 'rsi', 'bb_upper', 'bb_lower']
            
            dados = df[feature_cols].values
            
            # Normalizar dados
            dados_norm = self.scaler.fit_transform(dados)
            
            # Criar sequências
            X = []
            for i in range(len(dados_norm) - window_size + 1):
                X.append(dados_norm[i:i+window_size])
            
            return np.array(X), dados_norm
            
        except Exception as e:
            logger.error(f"[CNN] Erro ao preparar dados: {e}")
            return None, None
    
    def calcular_rsi(self, prices, period=14):
        """Calcular RSI"""
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
        avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
        
        rs = avg_gains / (avg_losses + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        # Preencher valores iniciais
        rsi_full = np.full(len(prices), 50.0)
        rsi_full[period:] = rsi
        
        return rsi_full
    
    def calcular_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calcular Bollinger Bands"""
        sma = pd.Series(prices).rolling(window=period).mean()
        std = pd.Series(prices).rolling(window=period).std()
        
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        
        return upper.fillna(prices[0]).values, lower.fillna(prices[0]).values
    
    def treinar_com_dados(self, dados_historicos, labels):
        """Treinar modelo com dados históricos"""
        if not TENSORFLOW_AVAILABLE or dados_historicos is None:
            return False
            
        try:
            X, _ = dados_historicos
            if X is None:
                return False
            
            # Criar modelo se não existir
            if self.model is None:
                input_shape = (X.shape[1], X.shape[2])
                self.model = self.criar_modelo(input_shape)
            
            # Treinar modelo
            history = self.model.fit(
                X[:-1], labels,
                epochs=50,
                batch_size=32,
                validation_split=0.2,
                verbose=0
            )
            
            # Salvar modelo
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            self.model.save(self.model_path)
            self.is_trained = True
            
            logger.info(f"[CNN] Modelo treinado! Acurácia: {history.history['accuracy'][-1]:.4f}")
            return True
            
        except Exception as e:
            logger.error(f"[CNN] Erro no treinamento: {e}")
            return False
    
    def prever_movimento(self, candles):
        """Prever movimento do preço (COMPRA, VENDA, HOLD)"""
        if not self.is_trained or not TENSORFLOW_AVAILABLE:
            return None, 0.0
        
        try:
            dados, _ = self.preparar_dados_trading(candles)
            if dados is None:
                return None, 0.0
            
            # Usar apenas a última sequência
            ultima_sequencia = dados[-1:] if len(dados) > 0 else None
            if ultima_sequencia is None:
                return None, 0.0
            
            # Fazer predição
            pred = self.model.predict(ultima_sequencia, verbose=0)[0]
            
            # Interpretar resultado
            classes = ['COMPRA', 'HOLD', 'VENDA']
            classe_pred = classes[np.argmax(pred)]
            confianca = float(np.max(pred))
            
            return classe_pred, confianca
            
        except Exception as e:
            logger.error(f"[CNN] Erro na predição: {e}")
            return None, 0.0

class AmosNeuralTrading:
    def __init__(self):
        """Sistema de Day Trading com Rede Neural"""
        logger.info("=== AMOS NEURAL TRADING - IA + ANÁLISE TÉCNICA ===")
        
        # Carregar conta Amos
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        dados_amos = config['CONTA_3']
        
        self.trader = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="AMOS_NEURAL"
        )
        
        # Inicializar CNN
        self.cnn = CNNPredictor()
        
        # Estado inicial
        self.saldo_inicial = self.trader.get_saldo_usdt()
        self.portfolio = {}
        
        logger.info(f"[SISTEMA] Saldo USDT: ${self.saldo_inicial:.2f}")
        logger.info(f"[CNN] Disponível: {self.cnn.is_trained}")
    
    def analisar_com_ia(self, symbol):
        """Análise combinada: Técnica + IA"""
        try:
            # Obter dados históricos
            candles = self.trader.get_candles_rapidos(symbol, '5m', 100)
            if not candles:
                return None
            
            prices = [c['close'] for c in candles]
            preco_atual = candles[-1]['close']
            
            # Análise técnica tradicional
            rsi = self.trader.calcular_rsi_rapido(prices)
            sma_20 = sum(prices[-20:]) / 20
            
            # Análise com IA (se disponível)
            pred_ia, confianca_ia = self.cnn.prever_movimento(candles)
            
            # Score combinado
            score_tecnico = 0
            razoes = []
            
            # RSI
            if rsi < 30:
                score_tecnico += 30
                razoes.append("RSI oversold")
            elif rsi > 70:
                score_tecnico += 30
                razoes.append("RSI overbought")
            
            # SMA
            if preco_atual > sma_20:
                score_tecnico += 10
                razoes.append("Acima SMA")
            
            # Integrar predição da IA
            score_ia = 0
            if pred_ia:
                if pred_ia == 'COMPRA' and confianca_ia > 0.7:
                    score_ia += int(confianca_ia * 40)
                    razoes.append(f"IA: {pred_ia} ({confianca_ia:.2f})")
                elif pred_ia == 'VENDA' and confianca_ia > 0.7:
                    score_ia += int(confianca_ia * 40)
                    razoes.append(f"IA: {pred_ia} ({confianca_ia:.2f})")
            
            score_final = score_tecnico + score_ia
            
            return {
                'symbol': symbol,
                'preco': preco_atual,
                'rsi': rsi,
                'score_tecnico': score_tecnico,
                'score_ia': score_ia,
                'score_total': score_final,
                'pred_ia': pred_ia,
                'confianca_ia': confianca_ia,
                'razoes': razoes
            }
            
        except Exception as e:
            logger.error(f"[ERRO] Análise {symbol}: {e}")
            return None
    
    def executar_ciclo_neural(self):
        """Ciclo principal com IA"""
        try:
            logger.info("=== CICLO NEURAL TRADING ===")
            
            # 1. Verificar portfolio atual
            self.verificar_portfolio()
            
            # 2. Analisar oportunidades de venda (posições atuais)
            for asset, dados in self.portfolio.items():
                if dados['quantidade'] > 0:
                    symbol = f"{asset}USDT"
                    analise = self.analisar_com_ia(symbol)
                    
                    if analise:
                        logger.info(f"[ANÁLISE {asset}] Score: {analise['score_total']}")
                        logger.info(f"  Técnico: {analise['score_tecnico']}, IA: {analise['score_ia']}")
                        logger.info(f"  Predição IA: {analise['pred_ia']} ({analise['confianca_ia']:.2f})")
                        logger.info(f"  RSI: {analise['rsi']:.1f}")
                        
                        # Critério de venda inteligente
                        vender = False
                        if analise['pred_ia'] == 'VENDA' and analise['confianca_ia'] > 0.8:
                            vender = True
                            logger.info(f"[VENDA IA] Alta confiança de venda!")
                        elif analise['score_total'] > 80:
                            vender = True
                            logger.info(f"[VENDA TÉCNICA] Score alto!")
                        
                        if vender:
                            self.executar_venda(asset, analise)
            
            # 3. Buscar oportunidades de compra
            simbolos = ['ADAUSDT', 'DOGEUSDT', 'SOLUSDT', 'BNBUSDT']
            melhor_compra = None
            melhor_score = 0
            
            for symbol in simbolos:
                analise = self.analisar_com_ia(symbol)
                if analise:
                    logger.info(f"[ANÁLISE {symbol}] Score: {analise['score_total']}")
                    
                    # Critério de compra inteligente
                    comprar = False
                    if analise['pred_ia'] == 'COMPRA' and analise['confianca_ia'] > 0.8:
                        comprar = True
                    elif analise['rsi'] < 25 and analise['score_total'] > 40:
                        comprar = True
                    
                    if comprar and analise['score_total'] > melhor_score:
                        melhor_compra = analise
                        melhor_score = analise['score_total']
            
            # 4. Executar melhor compra
            if melhor_compra:
                self.executar_compra(melhor_compra)
            
            # 5. Status final
            self.mostrar_status()
            
        except Exception as e:
            logger.error(f"[ERRO] Ciclo neural: {e}")
    
    def verificar_portfolio(self):
        """Verificar posições atuais"""
        try:
            account = self.trader._request('GET', '/api/v3/account', {}, signed=True)
            self.portfolio = {}
            
            for balance in account.get('balances', []):
                asset = balance['asset']
                quantidade = float(balance['free']) + float(balance['locked'])
                
                if asset != 'USDT' and quantidade > 0:
                    # Obter preço atual
                    import requests
                    r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT')
                    if r.status_code == 200:
                        preco = float(r.json()['price'])
                        valor = quantidade * preco
                        
                        self.portfolio[asset] = {
                            'quantidade': quantidade,
                            'preco': preco,
                            'valor': valor
                        }
                        
                        logger.info(f"[POSIÇÃO] {asset}: {quantidade:.6f} = ${valor:.2f}")
                        
        except Exception as e:
            logger.error(f"[ERRO] Verificar portfolio: {e}")
    
    def executar_venda(self, asset, analise):
        """Executar venda inteligente"""
        try:
            symbol = f"{asset}USDT"
            quantidade = self.portfolio[asset]['quantidade']
            
            # Ajustar quantidade
            if asset == 'SOL':
                qty = round(quantidade, 3)
            elif asset == 'ADA':
                qty = round(quantidade, 1)
            else:
                qty = round(quantidade, 4)
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': str(qty)
            }
            
            logger.info(f"[EXECUTANDO VENDA NEURAL] {params}")
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if not resultado.get('error'):
                logger.info(f"[SUCESSO VENDA] {asset} vendido!")
                logger.info(f"  Razão: {', '.join(analise['razoes'])}")
                logger.info(f"  Order ID: {resultado.get('orderId')}")
                return True
            else:
                logger.error(f"[ERRO VENDA] {resultado}")
                
        except Exception as e:
            logger.error(f"[ERRO] Venda {asset}: {e}")
        
        return False
    
    def executar_compra(self, analise):
        """Executar compra inteligente"""
        try:
            symbol = analise['symbol']
            asset = symbol.replace('USDT', '')
            
            saldo = self.trader.get_saldo_usdt()
            valor_compra = min(8.0, saldo * 0.4)  # Máximo $8 ou 40% do saldo
            
            if valor_compra < 5 or saldo < 5:
                logger.info("[COMPRA] Saldo insuficiente")
                return False
            
            quantidade = valor_compra / analise['preco']
            
            # Ajustar quantidade
            if asset == 'SOL':
                qty = round(quantidade, 3)
            elif asset == 'ADA':
                qty = round(quantidade, 1)
            elif asset == 'DOGE':
                qty = round(quantidade)
            else:
                qty = round(quantidade, 4)
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': str(qty)
            }
            
            logger.info(f"[EXECUTANDO COMPRA NEURAL] {params}")
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if not resultado.get('error'):
                logger.info(f"[SUCESSO COMPRA] {asset} comprado!")
                logger.info(f"  Razão: {', '.join(analise['razoes'])}")
                logger.info(f"  Order ID: {resultado.get('orderId')}")
                return True
            else:
                logger.error(f"[ERRO COMPRA] {resultado}")
                
        except Exception as e:
            logger.error(f"[ERRO] Compra: {e}")
        
        return False
    
    def mostrar_status(self):
        """Mostrar status do sistema"""
        saldo_atual = self.trader.get_saldo_usdt()
        
        valor_total_crypto = sum(pos['valor'] for pos in self.portfolio.values())
        patrimonio_total = saldo_atual + valor_total_crypto
        
        logger.info(f"[STATUS] USDT: ${saldo_atual:.2f}")
        logger.info(f"[STATUS] Criptos: ${valor_total_crypto:.2f}")
        logger.info(f"[STATUS] Total: ${patrimonio_total:.2f}")
        logger.info(f"[STATUS] Variação: ${patrimonio_total - self.saldo_inicial:.2f}")

def main():
    """Função principal"""
    logger.info("Iniciando Amos Neural Trading...")
    
    neural_trader = AmosNeuralTrading()
    
    # Executar ciclos
    for ciclo in range(1, 21):  # 20 ciclos
        logger.info(f"[CICLO {ciclo}/20] Neural Trading")
        
        neural_trader.executar_ciclo_neural()
        
        if ciclo < 20:
            logger.info("Próximo ciclo neural em 5 minutos...")
            time.sleep(300)  # 5 minutos
    
    logger.info("=== NEURAL TRADING CONCLUÍDO ===")

if __name__ == "__main__":
    main()