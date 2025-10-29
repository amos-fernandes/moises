#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Day Trading Neural MELHORADO
- Estratégia Técnica como BASE (nossa estratégia vencedora)
- IA Neural para POTENCIALIZAR os resultados
- Correção dos erros de dimensão da CNN
"""

import json
import logging
import time
import numpy as np
import pandas as pd
import ta
from datetime import datetime, timedelta
from binance.client import Client
import os
import tensorflow as tf
from tensorflow.keras.models import load_model
import joblib
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daytrading_neural.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DayTradingNeuralMelhorado:
    def __init__(self):
        self.client = None
        self.saldo_inicial = 0
        self.neural_model = None
        self.neural_scaler = None
        self.neural_features = []
        self.setup_binance()
        self.load_neural_model()
        
    def setup_binance(self):
        """Configura cliente Binance para CONTA_3 (Amos)"""
        try:
            with open('config/contas.json', 'r', encoding='utf-8') as f:
                contas = json.load(f)
            
            # Usar CONTA_3 (Amos) - autorizada para trading real
            conta_amos = contas['CONTA_3']
            
            self.client = Client(
                api_key=conta_amos['api_key'],
                api_secret=conta_amos['api_secret'],
                testnet=False
            )
            
            # Sincronizar tempo
            server_time = self.client.get_server_time()
            
            # Ajustar timestamp do sistema
            import time
            local_time = int(time.time() * 1000)
            time_diff = server_time['serverTime'] - local_time
            
            logger.info(f"Cliente Binance configurado - CONTA_3 (Amos)")
            logger.info(f"Diferença de tempo: {time_diff}ms")
            
        except Exception as e:
            logger.error(f"❌ Erro configurando Binance: {e}")
    
    def load_neural_model(self):
        """Carrega modelo neural treinado com nossa estratégia"""
        try:
            model_path = 'models/neural_tecnico/neural_tecnico_model.h5'
            scaler_path = 'models/neural_tecnico/scaler.pkl'
            config_path = 'models/neural_tecnico/config.json'
            
            if os.path.exists(model_path):
                try:
                    # Carregar modelo com custom_objects para resolver problemas de deserialização
                    self.neural_model = load_model(model_path, compile=False)
                    
                    # Recompilar modelo
                    self.neural_model.compile(
                        optimizer='adam',
                        loss='mse',
                        metrics=['mae']
                    )
                    
                    self.neural_scaler = joblib.load(scaler_path)
                    
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        self.neural_features = config['feature_columns']
                    
                    logger.info("Modelo neural carregado com sucesso!")
                    logger.info(f"Features: {len(self.neural_features)}")
                except Exception as e:
                    logger.warning(f"Erro carregando modelo neural: {e}")
                    logger.warning("Usando apenas analise tecnica")
                    self.neural_model = None
            else:
                logger.warning("Modelo neural nao encontrado - usando apenas analise tecnica")
                
        except Exception as e:
            logger.error(f"❌ Erro carregando modelo neural: {e}")
            self.neural_model = None
    
    def get_account_balance(self):
        """Obtém saldo da conta"""
        try:
            account = self.client.get_account()
            
            usdt_balance = 0
            crypto_value = 0
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if balance['asset'] == 'USDT' and total > 0:
                    usdt_balance = total
                elif total > 0.001:  # Ignora valores muito pequenos
                    # Calcular valor em USDT para outras cryptos
                    try:
                        symbol = f"{balance['asset']}USDT"
                        ticker = self.client.get_symbol_ticker(symbol=symbol)
                        price = float(ticker['price'])
                        value = total * price
                        crypto_value += value
                        
                        logger.info(f"[{balance['asset']}] {total:.6f} = ${value:.2f} (${price:.6f})")
                    except:
                        pass
            
            logger.info(f"[PORTFOLIO] Total em criptos: ${crypto_value:.2f}")
            logger.info(f"[PORTFOLIO] Total USDT: ${usdt_balance:.2f}")
            logger.info(f"[PORTFOLIO] Patrimônio total: ${usdt_balance + crypto_value:.2f}")
            
            return usdt_balance, crypto_value
            
        except Exception as e:
            logger.error(f"❌ Erro obtendo saldo: {e}")
            return 0, 0
    
    def get_klines(self, symbol, interval='5m', limit=100):
        """Obtém dados de candlesticks"""
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
            logger.error(f"❌ Erro obtendo klines {symbol}: {e}")
            return None
    
    def calculate_technical_indicators(self, df):
        """Calcula indicadores técnicos (nossa estratégia base)"""
        try:
            # RSI (principal)
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
            
            # Variações
            df['price_change'] = df['close'].pct_change()
            df['price_change_5'] = df['close'].pct_change(5)
            
            # Volume
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
        NOSSA ESTRATÉGIA TÉCNICA VENCEDORA
        Score baseado em análise técnica comprovada
        """
        score = 0
        reasons = []
        
        try:
            current_price = row['close']
            rsi = row['rsi']
            
            # RSI - Indicador principal
            if rsi > 75:
                score += 30
                reasons.append(f"RSI {rsi:.1f} (sobrecompra)")
            elif rsi > 60:
                score += 20
                reasons.append(f"RSI {rsi:.1f} (alta)")
            elif rsi < 25:
                score += 40
                reasons.append(f"RSI {rsi:.1f} (sobrevenda)")
            elif rsi < 35:
                score += 25
                reasons.append(f"RSI {rsi:.1f} (baixa)")
            
            # Tendência - Médias móveis
            if current_price > row['sma_50']:
                score += 10
                reasons.append("Tendência alta")
            
            if current_price > row['sma_20']:
                score += 10
                reasons.append("Acima média")
            
            # MACD
            if row['macd'] > row['macd_signal']:
                score += 5
                reasons.append("MACD positivo")
            
            # Bollinger Bands
            if current_price > row['bb_upper']:
                score += 15
                reasons.append("Acima BB superior")
            elif current_price < row['bb_lower']:
                score += 20
                reasons.append("Abaixo BB inferior")
            
            # Variação de preço
            price_change_5min = row['price_change'] * 100
            if abs(price_change_5min) > 0.5:  # >0.5%
                score += 5
                reasons.append(f"Variação 5min: {price_change_5min:+.2f}%")
            
            # Volume
            if row['volume_ratio'] > 1.2:
                score += 5
                reasons.append("Volume alto")
            
            return min(score, 100), reasons
            
        except Exception as e:
            return 0, []
    
    def get_neural_enhancement(self, row):
        """
        Usa IA Neural para MELHORAR nossa análise técnica
        A rede neural foi treinada com nossa estratégia vencedora
        """
        try:
            if self.neural_model is None or self.neural_scaler is None:
                return 0, 0.0
            
            # Preparar features exatamente como no treinamento
            features = []
            for feature in self.neural_features:
                if feature in row.index:
                    features.append(row[feature])
                else:
                    features.append(0)
            
            # Normalizar
            features_array = np.array([features]).reshape(1, -1)
            features_scaled = self.neural_scaler.transform(features_array)
            
            # Predição
            prediction = self.neural_model.predict(features_scaled, verbose=0)[0][0]
            
            # Converter para score (0-100)
            neural_score = prediction * 100.0
            confidence = min(abs(prediction - 0.5) * 200, 50)  # Confiança baseada na distância de 0.5
            
            return int(neural_score), confidence
            
        except Exception as e:
            logger.error(f"❌ Erro na predição neural: {e}")
            return 0, 0.0
    
    def analyze_symbol(self, symbol, for_selling=False):
        """Analisa um símbolo combinando técnico + neural"""
        try:
            # Obter dados
            df = self.get_klines(symbol, interval='5m', limit=100)
            if df is None or len(df) < 50:
                return 0
            
            # Calcular indicadores
            df = self.calculate_technical_indicators(df)
            
            # Pegar última linha
            latest = df.iloc[-1]
            
            # Score técnico (nossa estratégia base)
            technical_score, reasons = self.calculate_technical_score(latest)
            
            # Enhancement neural
            neural_score, neural_confidence = self.get_neural_enhancement(latest)
            
            # Score final combinado
            # Técnico tem peso maior (70%), Neural complementa (30%)
            if neural_confidence > 20:  # Só usar IA se confiança > 20%
                final_score = int(technical_score * 0.7 + neural_score * 0.3)
                neural_bonus = int(neural_score * 0.3)
            else:
                final_score = technical_score
                neural_bonus = 0
            
            # Log detalhado
            logger.info(f"[ANALISE {symbol}] Score: {final_score}")
            logger.info(f"  Tecnico: {technical_score}, IA: {neural_bonus}")
            logger.info(f"  Predicao IA: {neural_score:.1f} ({neural_confidence:.2f})")
            logger.info(f"  RSI: {latest['rsi']:.1f}")
            if reasons:
                logger.info(f"  Razoes: {', '.join(reasons)}")
            
            return final_score
            
        except Exception as e:
            logger.error(f"❌ Erro analisando {symbol}: {e}")
            return 0
    
    def execute_buy_order(self, symbol, usdt_amount):
        """Executa ordem de compra"""
        try:
            # Obter preço atual
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            price = float(ticker['price'])
            
            # Calcular quantidade
            quantity = usdt_amount / price
            
            # Obter info do símbolo para precisão
            symbol_info = self.client.get_symbol_info(symbol)
            step_size = float(symbol_info['filters'][1]['stepSize'])
            
            # Ajustar quantidade para precisão
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
            quantity = round(quantity, precision)
            
            # Executar ordem
            order = self.client.order_market_buy(
                symbol=symbol,
                quantity=quantity
            )
            
            logger.info(f"COMPRA EXECUTADA: {quantity} {symbol.replace('USDT','')} por ${usdt_amount:.2f}")
            logger.info(f"Order ID: {order['orderId']}")
            
            return True, order
            
        except Exception as e:
            logger.error(f"❌ Erro executando compra {symbol}: {e}")
            return False, None
    
    def execute_sell_order(self, symbol, quantity):
        """Executa ordem de venda"""
        try:
            # Obter info do símbolo
            symbol_info = self.client.get_symbol_info(symbol)
            step_size = float(symbol_info['filters'][1]['stepSize'])
            
            # Ajustar precisão
            precision = len(str(step_size).split('.')[-1].rstrip('0'))
            quantity = round(quantity, precision)
            
            # Executar venda
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            logger.info(f"VENDA EXECUTADA: {quantity} {symbol.replace('USDT','')}")
            logger.info(f"Order ID: {order['orderId']}")
            
            return True, order
            
        except Exception as e:
            logger.error(f"❌ Erro executando venda {symbol}: {e}")
            return False, None
    
    def run_cycle(self, cycle_num, max_cycles):
        """Executa um ciclo de day trading"""
        logger.info(f"[CICLO {cycle_num}/{max_cycles}] Day Trading Neural Melhorado")
        logger.info("=" * 50)
        
        try:
            # Verificar saldos
            usdt_balance, crypto_value = self.get_account_balance()
            
            # Verificar posições existentes para venda
            account = self.client.get_account()
            
            for balance in account['balances']:
                free = float(balance['free'])
                if free > 0.001 and balance['asset'] != 'USDT':
                    symbol = f"{balance['asset']}USDT"
                    
                    # Analisar para venda
                    sell_score = self.analyze_symbol(symbol, for_selling=True)
                    
                    # Critério de venda: Score >= 85 (muito alto)
                    if sell_score >= 85:
                        logger.info(f"🚀 SINAL DE VENDA FORTE: {symbol} (Score: {sell_score})")
                        success, order = self.execute_sell_order(symbol, free)
                        if success:
                            time.sleep(2)  # Aguardar processamento
            
            # Buscar oportunidades de compra
            if usdt_balance >= 6:  # Mínimo para operar
                symbols_to_analyze = ['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT', 'AVAXUSDT']
                
                best_symbol = None
                best_score = 0
                
                for symbol in symbols_to_analyze:
                    score = self.analyze_symbol(symbol)
                    
                    # Critério de compra: RSI < 35 E Score > 60
                    if score > best_score and score >= 60:
                        # Verificar RSI adicional
                        df = self.get_klines(symbol, interval='5m', limit=50)
                        if df is not None:
                            df = self.calculate_technical_indicators(df)
                            current_rsi = df.iloc[-1]['rsi']
                            
                            if current_rsi < 35:  # RSI baixo (sobrevenda)
                                best_symbol = symbol
                                best_score = score
                
                # Executar compra se encontrou oportunidade
                if best_symbol and best_score >= 60:
                    buy_amount = min(usdt_balance * 0.3, 8.0)  # Máximo 30% do saldo ou $8
                    logger.info(f"🚀 COMPRANDO {best_symbol} - Score: {best_score}")
                    
                    success, order = self.execute_buy_order(best_symbol, buy_amount)
                    if success:
                        time.sleep(2)
                else:
                    logger.info("[INFO] Nenhuma oportunidade de compra (aguardando RSI < 35 E Score > 60)")
            
            # Status final
            usdt_final, crypto_final = self.get_account_balance()
            logger.info(f"[STATUS] USDT: ${usdt_final:.2f}")
            logger.info(f"[STATUS] Criptos: ${crypto_final:.2f}")
            logger.info(f"[STATUS] Total: ${usdt_final + crypto_final:.2f}")
            logger.info(f"[STATUS] Variação: ${crypto_final:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Erro no ciclo: {e}")
    
    def run_trading_loop(self, max_cycles=20):
        """Loop principal de trading"""
        logger.info("SISTEMA DAY TRADING NEURAL MELHORADO")
        logger.info("Estrategia Tecnica + IA Neural Enhancement")
        logger.info("=" * 60)
        
        # Saldo inicial
        initial_usdt, initial_crypto = self.get_account_balance()
        self.saldo_inicial = initial_usdt + initial_crypto
        
        for cycle in range(1, max_cycles + 1):
            try:
                self.run_cycle(cycle, max_cycles)
                
                if cycle < max_cycles:
                    logger.info("Próximo ciclo neural em 5 minutos...")
                    time.sleep(300)  # 5 minutos
                    
            except KeyboardInterrupt:
                logger.info("🛑 Interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro no loop: {e}")
                time.sleep(60)  # Aguardar 1 minuto em caso de erro
        
        # Relatório final
        final_usdt, final_crypto = self.get_account_balance()
        final_total = final_usdt + final_crypto
        
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO FINAL - DAY TRADING NEURAL")
        logger.info(f"💰 Saldo inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"💰 Saldo final: ${final_total:.2f}")
        logger.info(f"📈 Variação: ${final_total - self.saldo_inicial:+.2f}")
        logger.info(f"📊 Performance: {((final_total / self.saldo_inicial - 1) * 100):+.2f}%")

def main():
    """Função principal"""
    trader = DayTradingNeuralMelhorado()
    trader.run_trading_loop(max_cycles=20)

if __name__ == "__main__":
    main()