"""
🎯 SISTEMA NEURAL TRADER - Técnico Simples e Lucrativo
Estratégia Multi-Indicador para Maximizar Lucros
- RSI + MACD + Bollinger Bands + Volume
- Stop Loss inteligente
- Take Profit progressivo
- Gestão de risco avançada
"""

import json
import time
import logging
import hmac
import hashlib
import requests
import numpy as np
from urllib.parse import urlencode
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('neural_trader.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class NeuralTrader:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO LUCRATIVA
        self.symbol = 'BTCUSDT'
        self.ciclo_tempo = 10  # Ciclos mais rápidos = mais oportunidades
        
        # ESTRATÉGIA MULTI-INDICADOR
        self.strategy = {
            # RSI mais flexível para mais trades
            'rsi_oversold': 45,      # Compra quando RSI < 45 (mais oportunidades)
            'rsi_overbought': 70,    # Vende quando RSI > 70
            
            # Bollinger Bands para volatilidade
            'bb_std': 2.0,          # Desvio padrão das bandas
            'bb_period': 20,        # Período das bandas
            
            # MACD para momentum
            'macd_fast': 12,         # EMA rápida
            'macd_slow': 26,         # EMA lenta
            'macd_signal': 9,        # Sinal MACD
            
            # Gestão de risco
            'stop_loss': 0.015,      # 1.5% stop loss
            'take_profit_1': 0.02,   # 2% primeiro take profit
            'take_profit_2': 0.04,   # 4% segundo take profit
            'max_position': 0.85,    # Máximo 85% do capital por trade
        }
        
        # Controles
        self.capital_inicial = 0
        self.trades_realizados = 0
        self.lucro_acumulado = 0
        self.trades_ganhos = 0
        self.trades_perdas = 0
        self.posicao_ativa = None
        
        # Histórico para cálculos
        self.price_history = []
        self.volume_history = []
        
        # Session
        self.session = requests.Session()
        
        logger.info("🧠 === NEURAL TRADER ATIVADO ===")
        logger.info("🎯 ESTRATÉGIA: Multi-indicador para lucros consistentes")
        logger.info("📊 INDICADORES: RSI + MACD + Bollinger + Volume")
        logger.info("🛡️ PROTEÇÃO: Stop Loss 1.5% | Take Profit 2%/4%")
        logger.info("⚡ VELOCIDADE: Ciclos de 10s para máximas oportunidades")
        logger.info("=" * 60)
    
    def get_server_time(self):
        """Timestamp do servidor"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except Exception:
            pass
        return int(time.time() * 1000)
    
    def fazer_requisicao(self, method, endpoint, params=None, signed=False):
        """Requisição otimizada"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_server_time()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = self.session.get(url, params=params, headers=headers, timeout=15)
                else:
                    r = self.session.post(url, params=params, headers=headers, timeout=15)
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    error_msg = error_data.get('msg', r.text)
                    logger.warning(f"❌ Binance: {error_msg}")
                    return {'error': True, 'msg': error_msg}
                else:
                    logger.warning(f"HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Erro req (tent {tentativa+1}): {e}")
                if tentativa < 2:
                    time.sleep(1)
        
        return {'error': True, 'msg': 'Falha conectividade'}
    
    def get_account_info(self):
        """Info da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_klines_avancado(self, limit=50):
        """Klines para análise técnica avançada"""
        try:
            params = {'symbol': self.symbol, 'interval': '1m', 'limit': limit}
            r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=15)
            if r.status_code == 200:
                klines = r.json()
                
                # Extrair dados OHLCV
                data = {
                    'open': [float(k[1]) for k in klines],
                    'high': [float(k[2]) for k in klines],
                    'low': [float(k[3]) for k in klines],
                    'close': [float(k[4]) for k in klines],
                    'volume': [float(k[5]) for k in klines]
                }
                
                return data
        except Exception as e:
            logger.error(f"Erro klines: {e}")
        return None
    
    def calcular_rsi(self, prices, period=14):
        """RSI otimizado"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        if avg_gain == 0:
            return 0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def calcular_bollinger_bands(self, prices, period=20, std_mult=2):
        """Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        upper_band = sma + (std * std_mult)
        lower_band = sma - (std * std_mult)
        
        return upper_band, sma, lower_band
    
    def calcular_macd(self, prices, fast=12, slow=26, signal=9):
        """MACD para momentum"""
        if len(prices) < slow:
            return 0, 0, 0
        
        # EMAs
        ema_fast = self.calcular_ema(prices, fast)
        ema_slow = self.calcular_ema(prices, slow)
        
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA do MACD)
        if hasattr(self, 'macd_history'):
            self.macd_history.append(macd_line)
            if len(self.macd_history) > 50:
                self.macd_history = self.macd_history[-50:]
        else:
            self.macd_history = [macd_line] * signal
        
        signal_line = self.calcular_ema(self.macd_history, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calcular_ema(self, prices, period):
        """EMA otimizada"""
        if len(prices) < period:
            return np.mean(prices)
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return ema
    
    def analisar_mercado_avancado(self):
        """Análise técnica completa"""
        data = self.get_klines_avancado()
        if not data or len(data['close']) < 30:
            return None
        
        prices = data['close']
        volumes = data['volume']
        current_price = prices[-1]
        
        # Indicadores técnicos
        rsi = self.calcular_rsi(prices)
        macd_line, macd_signal, macd_hist = self.calcular_macd(prices)
        bb_upper, bb_middle, bb_lower = self.calcular_bollinger_bands(prices)
        
        # Volume médio
        avg_volume = np.mean(volumes[-10:])
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Análise de tendência
        sma_short = np.mean(prices[-5:])   # SMA 5
        sma_long = np.mean(prices[-20:])   # SMA 20
        trend = "UP" if sma_short > sma_long else "DOWN"
        
        return {
            'price': current_price,
            'rsi': rsi,
            'macd': {'line': macd_line, 'signal': macd_signal, 'hist': macd_hist},
            'bollinger': {'upper': bb_upper, 'middle': bb_middle, 'lower': bb_lower},
            'volume_ratio': volume_ratio,
            'trend': trend,
            'sma_short': sma_short,
            'sma_long': sma_long
        }
    
    def calcular_score_compra(self, analise):
        """Score de compra baseado em múltiplos indicadores"""
        score = 0
        sinais = []
        
        # RSI Score (peso 30%)
        if analise['rsi'] < self.strategy['rsi_oversold']:
            score += 30
            sinais.append(f"RSI {analise['rsi']:.1f} < {self.strategy['rsi_oversold']} ✓")
        elif analise['rsi'] < 55:
            score += 15
            sinais.append(f"RSI {analise['rsi']:.1f} neutro ~")
        
        # MACD Score (peso 25%)
        if analise['macd']['hist'] > 0 and analise['macd']['line'] > analise['macd']['signal']:
            score += 25
            sinais.append("MACD bullish ✓")
        elif analise['macd']['hist'] > -0.1:
            score += 10
            sinais.append("MACD neutro ~")
        
        # Bollinger Score (peso 20%)
        if analise['price'] <= analise['bollinger']['lower']:
            score += 20
            sinais.append("Price ≤ BB Lower ✓")
        elif analise['price'] < analise['bollinger']['middle']:
            score += 10
            sinais.append("Price < BB Middle ~")
        
        # Volume Score (peso 15%)
        if analise['volume_ratio'] > 1.5:
            score += 15
            sinais.append(f"Volume {analise['volume_ratio']:.1f}x ✓")
        elif analise['volume_ratio'] > 1.0:
            score += 8
            sinais.append(f"Volume {analise['volume_ratio']:.1f}x ~")
        
        # Trend Score (peso 10%)
        if analise['trend'] == 'UP':
            score += 10
            sinais.append("Trend UP ✓")
        else:
            score += 5
            sinais.append("Trend DOWN ~")
        
        return score, sinais
    
    def calcular_score_venda(self, analise):
        """Score de venda baseado em múltiplos indicadores"""
        score = 0
        sinais = []
        
        # RSI Score
        if analise['rsi'] > self.strategy['rsi_overbought']:
            score += 30
            sinais.append(f"RSI {analise['rsi']:.1f} > {self.strategy['rsi_overbought']} ✓")
        elif analise['rsi'] > 65:
            score += 15
            sinais.append(f"RSI {analise['rsi']:.1f} alto ~")
        
        # MACD Score
        if analise['macd']['hist'] < 0 and analise['macd']['line'] < analise['macd']['signal']:
            score += 25
            sinais.append("MACD bearish ✓")
        elif analise['macd']['hist'] < 0.1:
            score += 10
            sinais.append("MACD neutro ~")
        
        # Bollinger Score
        if analise['price'] >= analise['bollinger']['upper']:
            score += 20
            sinais.append("Price ≥ BB Upper ✓")
        elif analise['price'] > analise['bollinger']['middle']:
            score += 10
            sinais.append("Price > BB Middle ~")
        
        # Volume Score
        if analise['volume_ratio'] > 1.5:
            score += 15
            sinais.append(f"Volume {analise['volume_ratio']:.1f}x ✓")
        
        return score, sinais
    
    def get_portfolio(self):
        """Portfolio atual"""
        conta = self.get_account_info()
        if conta.get('error'):
            return 0, 0, 0, 0
        
        usdt_livre = 0
        btc_livre = 0
        preco_btc = 0
        
        # Obter preço atual
        analise = self.analisar_mercado_avancado()
        if analise:
            preco_btc = analise['price']
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            
            if asset == 'USDT':
                usdt_livre = free
            elif asset == 'BTC':
                btc_livre = free
        
        valor_total = usdt_livre + (btc_livre * preco_btc)
        return usdt_livre, btc_livre, preco_btc, valor_total
    
    def executar_compra_inteligente(self, analise):
        """Compra baseada em análise técnica"""
        usdt_livre, btc_livre, preco_btc, valor_total = self.get_portfolio()
        
        if usdt_livre < 12:
            logger.info(f"💡 USDT insuficiente: ${usdt_livre:.2f}")
            return False
        
        # Calcular valor da compra
        valor_compra = usdt_livre * self.strategy['max_position']
        
        if valor_compra < 12:
            valor_compra = usdt_livre - 1  # Deixar $1 de reserva
        
        logger.warning(f"🚨 COMPRA INTELIGENTE")
        logger.warning(f"   💰 Valor: ${valor_compra:.2f}")
        logger.warning(f"   📊 Preço BTC: ${preco_btc:.2f}")
        logger.warning(f"   🎯 Estratégia: Multi-indicador")
        
        params = {
            'symbol': self.symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_compra:.2f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra: {resultado.get('msg')}")
            return False
        
        # Registrar posição com stop loss e take profit
        self.posicao_ativa = {
            'tipo': 'BUY',
            'preco_entrada': preco_btc,
            'valor': valor_compra,
            'timestamp': time.time(),
            'stop_loss': preco_btc * (1 - self.strategy['stop_loss']),
            'take_profit_1': preco_btc * (1 + self.strategy['take_profit_1']),
            'take_profit_2': preco_btc * (1 + self.strategy['take_profit_2']),
        }
        
        logger.info(f"✅ COMPRA EXECUTADA: ${valor_compra:.2f}")
        logger.info(f"   🛡️ Stop Loss: ${self.posicao_ativa['stop_loss']:.2f}")
        logger.info(f"   🎯 Take Profit: ${self.posicao_ativa['take_profit_1']:.2f}")
        
        return True
    
    def executar_venda_inteligente(self, analise, motivo="Sinais técnicos"):
        """Venda baseada em análise técnica"""
        usdt_livre, btc_livre, preco_btc, valor_total = self.get_portfolio()
        
        if btc_livre == 0 or btc_livre < 0.00001:
            return False
        
        # Calcular quantidade com margem de segurança
        quantidade_venda = btc_livre * 0.99  # 1% de margem
        quantidade_formatada = round(quantidade_venda, 5)
        
        valor_venda = quantidade_formatada * preco_btc
        
        if valor_venda < 10:
            logger.info(f"💡 Valor muito baixo para venda: ${valor_venda:.2f}")
            return False
        
        logger.warning(f"🚨 VENDA INTELIGENTE")
        logger.warning(f"   💰 Valor: ${valor_venda:.2f}")
        logger.warning(f"   📊 Quantidade: {quantidade_formatada:.5f} BTC")
        logger.warning(f"   🎯 Motivo: {motivo}")
        
        params = {
            'symbol': self.symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': f"{quantidade_formatada:.5f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda: {resultado.get('msg')}")
            return False
        
        # Calcular lucro/prejuízo
        if self.posicao_ativa and self.posicao_ativa['tipo'] == 'BUY':
            lucro = valor_venda - self.posicao_ativa['valor']
            percentual = (lucro / self.posicao_ativa['valor']) * 100
            
            self.trades_realizados += 1
            self.lucro_acumulado += lucro
            
            if lucro > 0:
                self.trades_ganhos += 1
                logger.info(f"🟢 LUCRO: +${lucro:.3f} (+{percentual:.2f}%)")
            else:
                self.trades_perdas += 1
                logger.info(f"🔴 PREJUÍZO: ${lucro:.3f} ({percentual:.2f}%)")
        
        self.posicao_ativa = None
        logger.info(f"✅ VENDA EXECUTADA: ${valor_venda:.2f}")
        
        return True
    
    def verificar_stop_loss_take_profit(self, preco_atual):
        """Verificar stop loss e take profit"""
        if not self.posicao_ativa or self.posicao_ativa['tipo'] != 'BUY':
            return False
        
        # Stop Loss
        if preco_atual <= self.posicao_ativa['stop_loss']:
            logger.warning(f"🛡️ STOP LOSS ATIVADO: ${preco_atual:.2f} ≤ ${self.posicao_ativa['stop_loss']:.2f}")
            return self.executar_venda_inteligente(None, "Stop Loss")
        
        # Take Profit 1
        if preco_atual >= self.posicao_ativa['take_profit_1']:
            logger.warning(f"🎯 TAKE PROFIT 1: ${preco_atual:.2f} ≥ ${self.posicao_ativa['take_profit_1']:.2f}")
            return self.executar_venda_inteligente(None, "Take Profit 1")
        
        # Take Profit 2 (opcional, mais agressivo)
        if preco_atual >= self.posicao_ativa['take_profit_2']:
            logger.warning(f"🚀 TAKE PROFIT 2: ${preco_atual:.2f} ≥ ${self.posicao_ativa['take_profit_2']:.2f}")
            return self.executar_venda_inteligente(None, "Take Profit 2")
        
        return False
    
    def ciclo_neural_trading(self):
        """Ciclo principal de trading inteligente"""
        analise = self.analisar_mercado_avancado()
        if not analise:
            logger.warning("⚠️ Erro na análise do mercado")
            return 0, 0
        
        usdt_livre, btc_livre, preco_btc, valor_total = self.get_portfolio()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Mostrar status
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro_total = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro_total:.3f} (+{percentual:.2f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f}")
        logger.info(f"   💵 USDT: ${usdt_livre:.2f}")
        if btc_livre > 0.00001:
            valor_btc = btc_livre * preco_btc
            logger.info(f"   ₿ BTC: {btc_livre:.5f} = ${valor_btc:.2f}")
        
        # Stats de performance
        if self.trades_realizados > 0:
            taxa_sucesso = (self.trades_ganhos / self.trades_realizados) * 100
            logger.info(f"📊 Trades: {self.trades_realizados} | ✅ {self.trades_ganhos} | ❌ {self.trades_perdas} | 🎯 {taxa_sucesso:.1f}%")
        
        operacoes = 0
        
        # 1. Verificar Stop Loss/Take Profit primeiro
        if self.verificar_stop_loss_take_profit(preco_btc):
            operacoes = 1
            return valor_total, operacoes
        
        # 2. Lógica de trading baseada em scores
        if btc_livre > 0.00001:
            # TEM BTC - Avaliar venda
            score_venda, sinais_venda = self.calcular_score_venda(analise)
            
            logger.info(f"📊 ANÁLISE VENDA:")
            logger.info(f"   🎯 Score: {score_venda}/100")
            for sinal in sinais_venda[:3]:  # Mostrar top 3 sinais
                logger.info(f"   {sinal}")
            
            if score_venda >= 70:  # Score alto para venda
                logger.info(f"💸 SINAL FORTE DE VENDA (Score: {score_venda})")
                if self.executar_venda_inteligente(analise, f"Score {score_venda}"):
                    operacoes = 1
            elif score_venda >= 50:
                logger.info(f"⚠️ Sinal moderado de venda (Score: {score_venda})")
            else:
                logger.info(f"✋ Manter posição (Score venda: {score_venda})")
        
        else:
            # SEM BTC - Avaliar compra
            score_compra, sinais_compra = self.calcular_score_compra(analise)
            
            logger.info(f"📊 ANÁLISE COMPRA:")
            logger.info(f"   🎯 Score: {score_compra}/100")
            for sinal in sinais_compra[:3]:  # Mostrar top 3 sinais
                logger.info(f"   {sinal}")
            
            if score_compra >= 60:  # Score alto para compra
                logger.info(f"🔥 SINAL FORTE DE COMPRA (Score: {score_compra})")
                if self.executar_compra_inteligente(analise):
                    operacoes = 1
            elif score_compra >= 40:
                logger.info(f"👀 Sinal moderado de compra (Score: {score_compra})")
            else:
                logger.info(f"⏳ Aguardando melhor oportunidade (Score: {score_compra})")
        
        logger.info(f"🔄 Operações no ciclo: {operacoes}")
        return valor_total, operacoes
    
    def executar_neural_trader(self):
        """Sistema principal Neural Trader"""
        logger.info("🧠 === NEURAL TRADER INICIADO ===")
        logger.info("🎯 OBJETIVO: Lucros consistentes com técnica avançada")
        logger.info("📈 FOCO: Qualidade > Quantidade de trades")
        logger.info("=" * 60)
        
        # Capital inicial
        usdt_inicial, btc_inicial, preco_inicial, capital_inicial = self.get_portfolio()
        self.capital_inicial = capital_inicial
        
        if capital_inicial == 0:
            logger.error("❌ Erro capital inicial")
            return
        
        # Meta mais realista: +3% consistente
        meta = capital_inicial * 1.03
        
        logger.info(f"💼 Capital inicial: ${capital_inicial:.2f}")
        logger.info(f"💵 USDT: ${usdt_inicial:.2f}")
        if btc_inicial > 0.00001:
            valor_btc_inicial = btc_inicial * preco_inicial
            logger.info(f"₿ BTC: {btc_inicial:.5f} = ${valor_btc_inicial:.2f}")
        logger.warning(f"🎯 Meta: ${meta:.2f} (+3%)")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🧠 === CICLO NEURAL {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_neural_trading()
                
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    taxa_sucesso = (self.trades_ganhos / max(1, self.trades_realizados)) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.2f}%)")
                    logger.info(f"📊 Trades: {self.trades_realizados} | Taxa sucesso: {taxa_sucesso:.1f}%")
                    break
                
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
            # Relatório final
            if self.trades_realizados > 0:
                taxa_sucesso = (self.trades_ganhos / self.trades_realizados) * 100
                logger.info(f"📋 RELATÓRIO FINAL:")
                logger.info(f"   💰 Lucro acumulado: ${self.lucro_acumulado:.3f}")
                logger.info(f"   📊 Trades: {self.trades_realizados}")
                logger.info(f"   ✅ Ganhos: {self.trades_ganhos}")
                logger.info(f"   ❌ Perdas: {self.trades_perdas}")
                logger.info(f"   🎯 Taxa sucesso: {taxa_sucesso:.1f}%")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")

def main():
    """Executar Neural Trader"""
    logger.info("🧠 Iniciando Neural Trader...")
    
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        api_key = None
        api_secret = None
        
        for line in env_content.split('\n'):
            if line.startswith('BINANCE_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"\'')
            elif line.startswith('BINANCE_API_SECRET='):
                api_secret = line.split('=', 1)[1].strip().strip('"\'')
        
        if not api_key or not api_secret:
            logger.error("❌ Chaves API não encontradas")
            return
        
        trader = NeuralTrader(api_key, api_secret)
        trader.executar_neural_trader()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()