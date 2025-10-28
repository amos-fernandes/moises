#!/usr/bin/env python3
# moises_trading_inteligente.py
# Sistema de trading inteligente com análise de candles e estratégias de lucro

import os
import json
import time
import hmac
import hashlib
import requests
import numpy as np
from urllib.parse import urlencode
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Detectar sistema
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"

# Criar diretórios
LOGS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'moises_inteligente.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingInteligente:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        self.server_time_offset = 0
        
        # Configurações de trading inteligente
        self.min_profit_percent = 0.008  # 0.8% mínimo de lucro
        self.stop_loss_percent = 0.005   # 0.5% stop loss
        self.take_profit_percent = 0.015 # 1.5% take profit
        self.leverage_safe = 1.5         # Alavancagem segura
        self.candle_timeframe = '5m'     # Timeframe dos candles
        
        # Estratégia
        self.posicoes_abertas = {}
        self.trades_diarios = []
        self.lucro_diario_meta = 50.0    # Meta de $50 por dia
        self.lucro_diario_atual = 0.0
        
        # Indicadores técnicos
        self.rsi_period = 14
        self.ma_short = 9
        self.ma_long = 21
        
        logger.info(f"🎯 Trading Inteligente iniciado para {conta_nome}")

    def sync_time(self):
        """Sincronizar tempo com servidor Binance"""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            return True
        except Exception as e:
            logger.error(f"Erro na sincronização de tempo: {e}")
            return False

    def _request(self, method, path, params, signed: bool):
        """Requisição segura para Binance API"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = int(time.time() * 1000) + int(self.server_time_offset)
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                r = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': True, 'detail': str(e)}

    def get_klines(self, symbol, interval='5m', limit=100):
        """Obter dados de candlesticks"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            r = requests.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=10)
            if r.status_code == 200:
                klines = r.json()
                candles = []
                for k in klines:
                    candles.append({
                        'timestamp': int(k[0]),
                        'open': float(k[1]),
                        'high': float(k[2]),
                        'low': float(k[3]),
                        'close': float(k[4]),
                        'volume': float(k[5])
                    })
                return candles
            return []
        except Exception as e:
            logger.error(f"Erro ao obter klines para {symbol}: {e}")
            return []

    def calcular_rsi(self, precos, period=14):
        """Calcular RSI (Relative Strength Index)"""
        if len(precos) < period + 1:
            return 50  # Valor neutro se não há dados suficientes
        
        deltas = np.diff(precos)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calcular_medias_moveis(self, precos, short_period=9, long_period=21):
        """Calcular médias móveis"""
        if len(precos) < long_period:
            return None, None
        
        ma_short = np.mean(precos[-short_period:])
        ma_long = np.mean(precos[-long_period:])
        return ma_short, ma_long

    def detectar_suporte_resistencia(self, candles):
        """Detectar níveis de suporte e resistência"""
        highs = [c['high'] for c in candles[-20:]]  # Últimos 20 candles
        lows = [c['low'] for c in candles[-20:]]
        
        resistencia = max(highs)
        suporte = min(lows)
        
        return suporte, resistencia

    def analisar_candles_inteligente(self, symbol):
        """Análise inteligente baseada em candles e indicadores técnicos"""
        candles = self.get_klines(symbol, self.candle_timeframe, 100)
        
        if len(candles) < 50:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Dados insuficientes'}
        
        # Extrair preços de fechamento
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        # Calcular indicadores
        rsi = self.calcular_rsi(closes)
        ma_short, ma_long = self.calcular_medias_moveis(closes)
        suporte, resistencia = self.detectar_suporte_resistencia(candles)
        
        preco_atual = closes[-1]
        volume_medio = np.mean(volumes[-10:])
        volume_atual = volumes[-1]
        
        # Análise do último candle
        ultimo_candle = candles[-1]
        penultimo_candle = candles[-2]
        
        # Verificar padrões de candles
        is_bullish = ultimo_candle['close'] > ultimo_candle['open']
        is_bearish = ultimo_candle['close'] < ultimo_candle['open']
        
        # Corpo do candle
        corpo = abs(ultimo_candle['close'] - ultimo_candle['open'])
        amplitude = ultimo_candle['high'] - ultimo_candle['low']
        corpo_percent = (corpo / amplitude) * 100 if amplitude > 0 else 0
        
        # Lógica de decisão inteligente
        score = 0
        razoes = []
        
        # 1. RSI Analysis
        if rsi < 30:  # Oversold - possível compra
            score += 25
            razoes.append(f"RSI oversold ({rsi:.1f})")
        elif rsi > 70:  # Overbought - possível venda
            score -= 25
            razoes.append(f"RSI overbought ({rsi:.1f})")
        
        # 2. Médias móveis
        if ma_short and ma_long:
            if ma_short > ma_long:  # Tendência de alta
                score += 15
                razoes.append("MA curta > longa (alta)")
            else:  # Tendência de baixa
                score -= 15
                razoes.append("MA curta < longa (baixa)")
        
        # 3. Suporte e resistência
        if preco_atual <= suporte * 1.002:  # Próximo ao suporte
            score += 20
            razoes.append(f"Próximo ao suporte ({suporte:.2f})")
        elif preco_atual >= resistencia * 0.998:  # Próximo à resistência
            score -= 20
            razoes.append(f"Próximo à resistência ({resistencia:.2f})")
        
        # 4. Volume
        if volume_atual > volume_medio * 1.5:  # Volume alto
            score += 10
            razoes.append("Volume alto")
        
        # 5. Padrão do candle
        if is_bullish and corpo_percent > 60:  # Candle bullish forte
            score += 15
            razoes.append("Candle bullish forte")
        elif is_bearish and corpo_percent > 60:  # Candle bearish forte
            score -= 15
            razoes.append("Candle bearish forte")
        
        # Determinar ação
        if score >= 40:
            action = 'BUY'
            confidence = min(95, 60 + score)
        elif score <= -40:
            action = 'SELL'
            confidence = min(95, 60 + abs(score))
        else:
            action = 'HOLD'
            confidence = 30
        
        return {
            'action': action,
            'confidence': confidence,
            'price': preco_atual,
            'rsi': rsi,
            'ma_short': ma_short,
            'ma_long': ma_long,
            'suporte': suporte,
            'resistencia': resistencia,
            'volume_ratio': volume_atual / volume_medio if volume_medio > 0 else 1,
            'score': score,
            'reasons': razoes,
            'candle_pattern': 'bullish' if is_bullish else 'bearish'
        }

    def calcular_tamanho_posicao_inteligente(self, saldo_usdt, confianca, volatilidade):
        """Calcular tamanho da posição baseado em gestão de risco"""
        # Base: 10% do saldo
        base_size = saldo_usdt * 0.1
        
        # Ajustar pela confiança (60-95% -> 0.5x a 2x)
        confidence_multiplier = ((confianca - 60) / 35) * 1.5 + 0.5
        confidence_multiplier = max(0.5, min(2.0, confidence_multiplier))
        
        # Ajustar pela volatilidade (mais volátil = menor posição)
        volatility_multiplier = max(0.5, 1.0 - (volatilidade * 0.5))
        
        # Tamanho final
        position_size = base_size * confidence_multiplier * volatility_multiplier
        
        # Limites de segurança
        position_size = max(5.0, min(position_size, saldo_usdt * 0.25))  # Entre $5 e 25% do saldo
        
        return position_size

    def executar_compra_inteligente(self, symbol, analise, saldo_usdt):
        """Executar compra com análise inteligente"""
        try:
            # Calcular volatilidade baseada no RSI e amplitude de preço
            volatilidade = abs(analise['rsi'] - 50) / 50  # 0 a 1
            
            position_size = self.calcular_tamanho_posicao_inteligente(
                saldo_usdt, 
                analise['confidence'], 
                volatilidade
            )
            
            logger.info(f"💰 COMPRA INTELIGENTE {symbol}:")
            logger.info(f"   Preço: ${analise['price']:,.2f}")
            logger.info(f"   Confiança: {analise['confidence']:.1f}%")
            logger.info(f"   RSI: {analise['rsi']:.1f}")
            logger.info(f"   Razões: {', '.join(analise['reasons'])}")
            logger.info(f"   Valor: ${position_size:.2f}")
            
            # Executar ordem
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': str(position_size)
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            if result.get('error'):
                logger.error(f"❌ Erro na compra: {result}")
                return None
            
            executed_qty = float(result.get('executedQty', 0))
            spent_usdt = float(result.get('cummulativeQuoteQty', 0))
            avg_price = spent_usdt / executed_qty if executed_qty > 0 else 0
            
            # Registrar posição
            self.posicoes_abertas[symbol] = {
                'side': 'BUY',
                'quantity': executed_qty,
                'avg_price': avg_price,
                'spent_usdt': spent_usdt,
                'timestamp': datetime.now().isoformat(),
                'target_profit': avg_price * (1 + self.take_profit_percent),
                'stop_loss': avg_price * (1 - self.stop_loss_percent),
                'order_id': result.get('orderId'),
                'analise': analise
            }
            
            logger.info(f"✅ COMPRA EXECUTADA:")
            logger.info(f"   Quantidade: {executed_qty:.8f}")
            logger.info(f"   Preço médio: ${avg_price:,.2f}")
            logger.info(f"   Take Profit: ${self.posicoes_abertas[symbol]['target_profit']:,.2f}")
            logger.info(f"   Stop Loss: ${self.posicoes_abertas[symbol]['stop_loss']:,.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na compra inteligente: {e}")
            return None

    def verificar_vendas_inteligentes(self):
        """Verificar se alguma posição deve ser vendida"""
        for symbol, posicao in list(self.posicoes_abertas.items()):
            try:
                # Obter preço atual
                r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5)
                if r.status_code != 200:
                    continue
                
                preco_atual = float(r.json()['price'])
                
                # Calcular lucro/prejuízo
                if posicao['side'] == 'BUY':
                    lucro_percent = (preco_atual - posicao['avg_price']) / posicao['avg_price']
                    lucro_usdt = posicao['quantity'] * (preco_atual - posicao['avg_price'])
                    
                    deve_vender = False
                    motivo = ""
                    
                    # Take Profit
                    if preco_atual >= posicao['target_profit']:
                        deve_vender = True
                        motivo = f"Take Profit atingido (${preco_atual:,.2f} >= ${posicao['target_profit']:,.2f})"
                    
                    # Stop Loss
                    elif preco_atual <= posicao['stop_loss']:
                        deve_vender = True
                        motivo = f"Stop Loss atingido (${preco_atual:,.2f} <= ${posicao['stop_loss']:,.2f})"
                    
                    # Análise técnica para venda
                    else:
                        analise = self.analisar_candles_inteligente(symbol)
                        if analise['action'] == 'SELL' and analise['confidence'] > 70:
                            deve_vender = True
                            motivo = f"Sinal técnico de venda (conf: {analise['confidence']:.1f}%)"
                    
                    if deve_vender:
                        logger.info(f"🔴 VENDENDO {symbol}: {motivo}")
                        self.executar_venda_inteligente(symbol, posicao, preco_atual, motivo)
                    else:
                        logger.info(f"📊 {symbol}: ${preco_atual:,.2f} | Lucro: {lucro_percent*100:+.2f}% (${lucro_usdt:+.2f})")
                
            except Exception as e:
                logger.error(f"❌ Erro ao verificar {symbol}: {e}")

    def executar_venda_inteligente(self, symbol, posicao, preco_atual, motivo):
        """Executar venda inteligente"""
        try:
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': f"{posicao['quantity']:.8f}"
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            if result.get('error'):
                logger.error(f"❌ Erro na venda: {result}")
                return None
            
            executed_qty = float(result.get('executedQty', 0))
            received_usdt = float(result.get('cummulativeQuoteQty', 0))
            
            # Calcular lucro real
            lucro_real = received_usdt - posicao['spent_usdt']
            lucro_percent = (lucro_real / posicao['spent_usdt']) * 100
            
            # Registrar trade
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'side': 'SELL',
                'buy_price': posicao['avg_price'],
                'sell_price': received_usdt / executed_qty,
                'quantity': executed_qty,
                'spent_usdt': posicao['spent_usdt'],
                'received_usdt': received_usdt,
                'profit_usdt': lucro_real,
                'profit_percent': lucro_percent,
                'motivo': motivo,
                'conta': self.conta_nome
            }
            
            self.trades_diarios.append(trade_record)
            self.lucro_diario_atual += lucro_real
            
            logger.info(f"✅ VENDA EXECUTADA:")
            logger.info(f"   Motivo: {motivo}")
            logger.info(f"   Preço venda: ${trade_record['sell_price']:,.2f}")
            logger.info(f"   USDT recebido: ${received_usdt:.2f}")
            logger.info(f"   Lucro: ${lucro_real:+.2f} ({lucro_percent:+.2f}%)")
            logger.info(f"   Lucro diário: ${self.lucro_diario_atual:+.2f}")
            
            # Remover posição
            del self.posicoes_abertas[symbol]
            
            # Salvar trade
            self.salvar_trade_record(trade_record)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Erro na venda inteligente: {e}")
            return None

    def salvar_trade_record(self, trade_record):
        """Salvar registro do trade"""
        trades_file = REPORTS_DIR / f"trades_inteligentes_{datetime.now().strftime('%Y%m%d')}.json"
        
        trades = []
        if trades_file.exists():
            try:
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
            except:
                pass
        
        trades.append(trade_record)
        
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)

    def get_saldo_usdt(self):
        """Obter saldo USDT disponível"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0

def carregar_contas():
    """Carregar contas do config"""
    config_file = CONFIG_DIR / "contas.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def main():
    """Função principal do trading inteligente"""
    logger.info("🎂💰 INICIANDO TRADING INTELIGENTE - LUCRO DIÁRIO 💰🎂")
    logger.info("=" * 70)
    
    # Carregar contas
    contas_config = carregar_contas()
    
    if not contas_config:
        logger.error("❌ Nenhuma conta configurada!")
        return
    
    # Inicializar traders para cada conta
    traders = {}
    for conta_id, dados in contas_config.items():
        trader = TradingInteligente(
            dados['api_key'],
            dados['api_secret'],
            dados['nome']
        )
        
        if trader.sync_time():
            traders[conta_id] = trader
            saldo = trader.get_saldo_usdt()
            logger.info(f"✅ {conta_id} ({dados['nome']}): ${saldo:.2f} USDT")
        else:
            logger.error(f"❌ Falha na inicialização da conta {conta_id}")
    
    if not traders:
        logger.error("❌ Nenhum trader inicializado!")
        return
    
    # Pares para trading
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
    
    logger.info(f"\n🎯 Meta diária: ${50.0} por conta")
    logger.info(f"📊 Pares: {', '.join(symbols)}")
    logger.info(f"🕐 Análise a cada 2 minutos")
    logger.info("=" * 70)
    
    try:
        while True:
            for conta_id, trader in traders.items():
                try:
                    # Verificar vendas primeiro
                    trader.verificar_vendas_inteligentes()
                    
                    # Verificar se atingiu meta diária
                    if trader.lucro_diario_atual >= trader.lucro_diario_meta:
                        logger.info(f"🎉 {trader.conta_nome}: Meta diária atingida (${trader.lucro_diario_atual:.2f})")
                        continue
                    
                    # Obter saldo atual
                    saldo_usdt = trader.get_saldo_usdt()
                    
                    if saldo_usdt < 5:
                        logger.warning(f"⚠️ {trader.conta_nome}: Saldo insuficiente (${saldo_usdt:.2f})")
                        continue
                    
                    # Analisar oportunidades de compra
                    for symbol in symbols:
                        if symbol in trader.posicoes_abertas:
                            continue  # Já tem posição neste par
                        
                        analise = trader.analisar_candles_inteligente(symbol)
                        
                        if analise['action'] == 'BUY' and analise['confidence'] > 75:
                            logger.info(f"\n🎯 OPORTUNIDADE DETECTADA - {symbol}:")
                            logger.info(f"   Confiança: {analise['confidence']:.1f}%")
                            logger.info(f"   Razões: {', '.join(analise['reasons'])}")
                            
                            trader.executar_compra_inteligente(symbol, analise, saldo_usdt)
                            break  # Só uma compra por ciclo
                
                except Exception as e:
                    logger.error(f"❌ Erro na conta {conta_id}: {e}")
            
            # Aguardar próximo ciclo
            time.sleep(120)  # 2 minutos
            
    except KeyboardInterrupt:
        logger.info("\n⏹️ Trading interrompido pelo usuário")
        
        # Relatório final
        logger.info("\n📊 RELATÓRIO FINAL:")
        logger.info("=" * 50)
        
        for conta_id, trader in traders.items():
            logger.info(f"{trader.conta_nome}:")
            logger.info(f"  Lucro diário: ${trader.lucro_diario_atual:+.2f}")
            logger.info(f"  Trades: {len(trader.trades_diarios)}")
            logger.info(f"  Posições abertas: {len(trader.posicoes_abertas)}")

if __name__ == '__main__':
    main()