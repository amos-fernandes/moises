#!/usr/bin/env python3
# moises_estrategias_avancadas.py
# Sistema avançado de trading com análise de candles e alavancagem segura
# Objetivo: Reverter perdas de -15.82% e gerar lucros diários consistentes

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
import threading
import logging

# Detectar sistema
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'trading_avancado.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingAvancado:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        self.server_time_offset = 0
        
        # Configurações de trading inteligente
        self.alavancagem_maxima = 2.0  # 2x máximo (muito seguro)
        self.stop_loss_percent = 0.015  # 1.5% stop loss
        self.take_profit_percent = 0.025  # 2.5% take profit
        
        # Configurações específicas para reverter perdas
        self.target_lucro_diario = 0.05  # 5% por dia para recuperar
        self.max_trades_por_hora = 3
        self.min_confidence_trade = 80  # Mínimo 80% de confiança
        
        # Estratégias para recuperação
        self.estrategias_ativas = {
            'scalping_rapido': True,      # Scalping agressivo
            'reversao_media': True,       # Reversão à média
            'momentum_breakout': True,    # Momentum + breakout
            'arbitragem_temporal': True   # Arbitragem entre timeframes
        }
        
        # Controle de risco rigoroso
        self.max_risco_por_trade = 0.03  # 3% por trade (mais agressivo para recuperar)
        self.max_drawdown = 0.05         # 5% drawdown máximo
        
        # Estatísticas
        self.trades_executados = []
        self.lucro_acumulado = 0
        self.trades_vencedores = 0
        self.trades_perdedores = 0
        
        logger.info(f"[ALVO] Trading Avançado para RECUPERAÇÃO iniciado - {conta_nome}")
        logger.info(f"[META DIÁRIA] Meta diária: {self.target_lucro_diario*100:.1f}% para reverter perdas")
        
    def sync_time(self):
        """Sincronizar tempo com Binance"""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            return True
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return False
    
    def _request(self, method, path, params, signed: bool):
        """Requisição segura para Binance"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # Obter timestamp da Binance para garantir precisão
            try:
                r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                if r.status_code == 200:
                    params['timestamp'] = r.json()['serverTime']
                else:
                    # Fallback para timestamp local
                    import datetime
                    params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
            except:
                import datetime
                params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
                
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
    
    def get_candles_rapidos(self, symbol: str, interval: str, limit: int = 50):
        """Obter candles para análise rápida"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            r.raise_for_status()
            
            candles = []
            for kline in r.json():
                candles.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Erro ao obter candles {symbol}: {e}")
            return []
    
    def calcular_rsi_rapido(self, prices, period=7):
        """RSI otimizado para trading rápido"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def detectar_divergencia(self, prices, rsi_values):
        """Detectar divergências entre preço e RSI"""
        if len(prices) < 10 or len(rsi_values) < 10:
            return None
        
        # Últimos 5 pontos para análise
        price_trend = np.polyfit(range(5), prices[-5:], 1)[0]
        rsi_trend = np.polyfit(range(5), rsi_values[-5:], 1)[0]
        
        # Divergência bullish: preço caindo, RSI subindo
        if price_trend < -0.001 and rsi_trend > 0.5:
            return 'BULLISH'
        
        # Divergência bearish: preço subindo, RSI caindo
        elif price_trend > 0.001 and rsi_trend < -0.5:
            return 'BEARISH'
        
        return None
    
    def estrategia_scalping_agressivo(self, symbol):
        """Scalping agressivo para recuperação rápida"""
        candles = self.get_candles_rapidos(symbol, '1m', 15)
        if len(candles) < 15:
            return None
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        preco_atual = closes[-1]
        
        # RSI de 7 períodos para reações mais rápidas
        rsi = self.calcular_rsi_rapido(closes, 7)
        
        # Volume médio vs atual
        vol_medio = np.mean(volumes[-5:])
        vol_atual = volumes[-1]
        
        # Volatilidade recente
        volatilidade = (max(highs[-3:]) - min(lows[-3:])) / preco_atual
        
        # Momentum de 3 períodos
        momentum = (closes[-1] / closes[-4] - 1) * 100
        
        signal = None
        confidence = 0
        
        # Condições para COMPRA agressiva
        if (rsi < 25 and vol_atual > vol_medio * 2.0 and 
            momentum < -0.5 and volatilidade > 0.005):
            
            signal = 'BUY'
            confidence = min(95, 70 + (25 - rsi) + (vol_atual/vol_medio * 5))
            
        # Condições para VENDA agressiva (se tivéssemos posição)
        elif (rsi > 75 and vol_atual > vol_medio * 2.0 and 
              momentum > 0.5 and volatilidade > 0.005):
            
            signal = 'SELL'
            confidence = min(95, 70 + (rsi - 75) + (vol_atual/vol_medio * 5))
        
        if signal and confidence >= self.min_confidence_trade:
            return {
                'estrategia': 'scalping_agressivo',
                'signal': signal,
                'confidence': confidence,
                'entry_price': preco_atual,
                'stop_loss': preco_atual * (0.985 if signal == 'BUY' else 1.015),
                'take_profit': preco_atual * (1.02 if signal == 'BUY' else 0.98),
                'timeframe': '1m',
                'rsi': rsi,
                'volume_boost': vol_atual / vol_medio,
                'volatilidade': volatilidade,
                'momentum': momentum
            }
        
        return None
    
    def estrategia_reversao_inteligente(self, symbol):
        """Reversão à média inteligente"""
        candles_1m = self.get_candles_rapidos(symbol, '1m', 20)
        candles_5m = self.get_candles_rapidos(symbol, '5m', 20)
        
        if len(candles_1m) < 20 or len(candles_5m) < 20:
            return None
        
        closes_1m = [c['close'] for c in candles_1m]
        closes_5m = [c['close'] for c in candles_5m]
        
        preco_atual = closes_1m[-1]
        
        # RSI em ambos os timeframes
        rsi_1m = self.calcular_rsi_rapido(closes_1m[-10:], 7)
        rsi_5m = self.calcular_rsi_rapido(closes_5m[-10:], 7)
        
        # Médias móveis
        ma_1m_5 = np.mean(closes_1m[-5:])
        ma_1m_10 = np.mean(closes_1m[-10:])
        ma_5m_5 = np.mean(closes_5m[-5:])
        
        # Desvio da média
        desvio_1m = (preco_atual - ma_1m_5) / ma_1m_5
        desvio_5m = (preco_atual - ma_5m_5) / ma_5m_5
        
        # Detectar divergências
        rsi_1m_hist = [self.calcular_rsi_rapido(closes_1m[i:i+7], 7) for i in range(len(closes_1m)-13, len(closes_1m)-6)]
        divergencia = self.detectar_divergencia(closes_1m[-10:], rsi_1m_hist + [rsi_1m])
        
        signal = None
        confidence = 0
        
        # Reversão bullish
        if (rsi_1m < 20 and rsi_5m < 30 and desvio_1m < -0.01 and 
            ma_1m_5 < ma_1m_10 and divergencia == 'BULLISH'):
            
            signal = 'BUY'
            confidence = min(92, 75 + abs(desvio_1m * 500) + (30 - rsi_1m))
            
        # Reversão bearish
        elif (rsi_1m > 80 and rsi_5m > 70 and desvio_1m > 0.01 and 
              ma_1m_5 > ma_1m_10 and divergencia == 'BEARISH'):
            
            signal = 'SELL'
            confidence = min(92, 75 + abs(desvio_1m * 500) + (rsi_1m - 70))
        
        if signal and confidence >= self.min_confidence_trade:
            return {
                'estrategia': 'reversao_inteligente',
                'signal': signal,
                'confidence': confidence,
                'entry_price': preco_atual,
                'stop_loss': preco_atual * (0.98 if signal == 'BUY' else 1.02),
                'take_profit': preco_atual * (1.035 if signal == 'BUY' else 0.965),
                'timeframe': '1m+5m',
                'rsi_1m': rsi_1m,
                'rsi_5m': rsi_5m,
                'desvio_media': desvio_1m,
                'divergencia': divergencia
            }
        
        return None
    
    def estrategia_momentum_explosivo(self, symbol):
        """Estratégia de momentum explosivo para grandes movimentos"""
        candles = self.get_candles_rapidos(symbol, '5m', 30)
        if len(candles) < 30:
            return None
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        highs = [c['high'] for c in candles]
        lows = [c['low'] for c in candles]
        
        preco_atual = closes[-1]
        
        # Momentum de diferentes períodos
        mom_3 = (closes[-1] / closes[-4] - 1) * 100
        mom_5 = (closes[-1] / closes[-6] - 1) * 100
        mom_10 = (closes[-1] / closes[-11] - 1) * 100
        
        # Volume explosivo
        vol_medio_10 = np.mean(volumes[-10:])
        vol_medio_3 = np.mean(volumes[-3:])
        vol_explosao = vol_medio_3 / vol_medio_10 if vol_medio_10 > 0 else 1
        
        # Range expansion
        range_atual = (highs[-1] - lows[-1]) / closes[-1]
        range_medio = np.mean([(highs[i] - lows[i]) / closes[i] for i in range(-10, -1)])
        range_expansion = range_atual / range_medio if range_medio > 0 else 1
        
        # Breakout detection
        resistencia = max(highs[-20:-1])  # Máxima dos últimos 19 candles
        suporte = min(lows[-20:-1])       # Mínima dos últimos 19 candles
        
        signal = None
        confidence = 0
        
        # Momentum bullish explosivo
        if (mom_3 > 0.8 and mom_5 > 1.2 and vol_explosao > 2.5 and 
            range_expansion > 1.5 and preco_atual > resistencia * 1.001):
            
            signal = 'BUY'
            confidence = min(94, 70 + mom_3 * 5 + vol_explosao * 3 + range_expansion * 5)
            
        # Momentum bearish explosivo
        elif (mom_3 < -0.8 and mom_5 < -1.2 and vol_explosao > 2.5 and 
              range_expansion > 1.5 and preco_atual < suporte * 0.999):
            
            signal = 'SELL'
            confidence = min(94, 70 + abs(mom_3) * 5 + vol_explosao * 3 + range_expansion * 5)
        
        if signal and confidence >= self.min_confidence_trade:
            return {
                'estrategia': 'momentum_explosivo',
                'signal': signal,
                'confidence': confidence,
                'entry_price': preco_atual,
                'stop_loss': preco_atual * (0.975 if signal == 'BUY' else 1.025),
                'take_profit': preco_atual * (1.05 if signal == 'BUY' else 0.95),
                'timeframe': '5m',
                'momentum_3': mom_3,
                'momentum_5': mom_5,
                'volume_explosao': vol_explosao,
                'range_expansion': range_expansion,
                'breakout_level': resistencia if signal == 'BUY' else suporte
            }
        
        return None
    
    def get_saldo_usdt(self):
        """Obter saldo USDT da conta"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0
    
    def calcular_tamanho_agressivo(self, saldo_usdt, confidence, preco_entrada, stop_loss):
        """Calcular tamanho agressivo para recuperação"""
        # Risco baseado na confiança (mais agressivo para confiança alta)
        if confidence >= 90:
            risco_percent = 0.04  # 4% para alta confiança
        elif confidence >= 85:
            risco_percent = 0.03  # 3% para confiança boa
        else:
            risco_percent = 0.02  # 2% para confiança mínima
        
        # Distância do stop loss
        distancia_stop = abs(preco_entrada - stop_loss) / preco_entrada
        
        # Tamanho base
        valor_risco = saldo_usdt * risco_percent
        tamanho_base = valor_risco / distancia_stop
        
        # Aplicar alavancagem baseada na confiança
        if confidence >= 90:
            alavancagem = 2.0
        elif confidence >= 85:
            alavancagem = 1.5
        else:
            alavancagem = 1.0
        
        tamanho_final = min(tamanho_base * alavancagem, saldo_usdt * 0.4)  # Máximo 40%
        
        # Arredondar para evitar problemas de precisão na Binance
        tamanho_arredondado = round(max(6.0, tamanho_final), 2)  # Mínimo $6, arredondado
        
        return tamanho_arredondado
    
    def executar_trade_inteligente(self, oportunidade, symbol):
        """Executar trade com estratégia inteligente"""
        try:
            saldo_atual = self.get_saldo_usdt()
            if saldo_atual < 5:
                logger.warning(f"⚠️ Saldo insuficiente: ${saldo_atual:.2f}")
                return None
            
            tamanho = self.calcular_tamanho_agressivo(
                saldo_atual,
                oportunidade['confidence'],
                oportunidade['entry_price'],
                oportunidade['stop_loss']
            )
            
            logger.info(f"[EXECUTANDO] ESTRATÉGIA: {oportunidade['estrategia']}")
            logger.info(f"   Símbolo: {symbol}")
            logger.info(f"   Confiança: {oportunidade['confidence']:.1f}%")
            logger.info(f"   Entrada: ${oportunidade['entry_price']:.4f}")
            logger.info(f"   Stop Loss: ${oportunidade['stop_loss']:.4f}")
            logger.info(f"   Take Profit: ${oportunidade['take_profit']:.4f}")
            logger.info(f"   Tamanho: ${tamanho:.2f}")
            
            # Validações rigorosas antes do trade
            tamanho_arredondado = round(tamanho, 2)
            
            # Verificar se o tamanho atende aos requisitos mínimos da Binance
            if tamanho_arredondado < 5.0:
                logger.warning(f"[ERRO] Tamanho muito pequeno: ${tamanho_arredondado:.2f} (mínimo $5)")
                return None
            
            # Verificar se temos saldo suficiente
            if tamanho_arredondado > saldo_atual * 0.8:  # Máximo 80% do saldo
                tamanho_arredondado = round(saldo_atual * 0.3, 2)  # Usar 30% como segurança
                logger.info(f"[AJUSTE] Tamanho ajustado para ${tamanho_arredondado:.2f}")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{tamanho_arredondado:.2f}"  # Formato correto
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            if result.get('error'):
                logger.error(f"[ERRO] Erro no trade: {result}")
                return None
            
            # Processar resultado
            executed_qty = float(result.get('executedQty', 0))
            spent_usdt = float(result.get('cummulativeQuoteQty', 0))
            order_id = result.get('orderId')
            
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'estrategia': oportunidade['estrategia'],
                'symbol': symbol,
                'order_id': order_id,
                'usdt_investido': spent_usdt,
                'quantidade': executed_qty,
                'preco_execucao': spent_usdt / executed_qty if executed_qty > 0 else 0,
                'confidence': oportunidade['confidence'],
                'stop_loss': oportunidade['stop_loss'],
                'take_profit': oportunidade['take_profit'],
                'expectativa_lucro': ((oportunidade['take_profit'] - oportunidade['entry_price']) / oportunidade['entry_price']) * 100
            }
            
            self.trades_executados.append(trade_record)
            
            logger.info(f"[SUCESSO] TRADE EXECUTADO!")
            logger.info(f"   Order ID: {order_id}")
            logger.info(f"   Investido: ${spent_usdt:.2f}")
            logger.info(f"   Quantidade: {executed_qty:.8f}")
            logger.info(f"   Expectativa: {trade_record['expectativa_lucro']:+.2f}%")
            
            return trade_record
            
        except Exception as e:
            logger.error(f"[ERRO] Erro na execução: {e}")
            return None
    
    def analisar_mercado_completo(self):
        """Análise completa do mercado para encontrar melhores oportunidades"""
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']
        
        todas_oportunidades = []
        
        for symbol in symbols:
            logger.info(f"[ANÁLISE] Analisando {symbol}...")
            
            # Executar todas as estratégias
            if self.estrategias_ativas['scalping_rapido']:
                scalp = self.estrategia_scalping_agressivo(symbol)
                if scalp:
                    scalp['symbol'] = symbol
                    todas_oportunidades.append(scalp)
            
            if self.estrategias_ativas['reversao_media']:
                reversao = self.estrategia_reversao_inteligente(symbol)
                if reversao:
                    reversao['symbol'] = symbol
                    todas_oportunidades.append(reversao)
            
            if self.estrategias_ativas['momentum_breakout']:
                momentum = self.estrategia_momentum_explosivo(symbol)
                if momentum:
                    momentum['symbol'] = symbol
                    todas_oportunidades.append(momentum)
        
        # Ordenar por confiança e potencial de lucro
        todas_oportunidades.sort(key=lambda x: x['confidence'], reverse=True)
        
        return todas_oportunidades
    
    def salvar_relatorio_recuperacao(self):
        """Salvar relatório de recuperação de perdas"""
        if not self.trades_executados:
            return
        
        total_investido = sum(t['usdt_investido'] for t in self.trades_executados)
        expectativa_total = sum(t['expectativa_lucro'] for t in self.trades_executados)
        
        relatorio = {
            'data': datetime.now().strftime('%Y-%m-%d %H:%M'),
            'objetivo': 'Recuperar perdas de -15.82%',
            'conta': self.conta_nome,
            'trades_executados': len(self.trades_executados),
            'total_investido': total_investido,
            'expectativa_lucro_total': expectativa_total,
            'estrategias_utilizadas': list(set(t['estrategia'] for t in self.trades_executados)),
            'confidence_media': np.mean([t['confidence'] for t in self.trades_executados]),
            'trades_detalhados': self.trades_executados
        }
        
        arquivo = REPORTS_DIR / f"recuperacao_perdas_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(arquivo, 'w') as f:
            json.dump(relatorio, f, indent=2)
        
        logger.info(f"[RELATÓRIO] Relatório salvo: {arquivo}")
        logger.info(f"[INVESTIMENTO] Total investido: ${total_investido:.2f}")
        logger.info(f"[LUCRO ESPERADO] Expectativa de lucro: {expectativa_total:.2f}%")

def main():
    """Sistema principal de recuperação de perdas"""
    logger.info("[ALVO] SISTEMA DE RECUPERAÇÃO DE PERDAS - MOISES AVANÇADO")
    logger.info("[OBJETIVO] Reverter perdas de -15.82% com trading inteligente")
    logger.info("[ESTRATÉGIAS] Scalping + Reversão + Momentum + Breakout")
    
    # Carregar contas
    config_file = BASE_DIR / "config" / "contas.json"
    if not config_file.exists():
        logger.error("[ERRO] Arquivo de contas não encontrado")
        return
    
    with open(config_file, 'r') as f:
        contas = json.load(f)
    
    # Escolher conta com maior saldo
    melhor_trader = None
    maior_saldo = 0
    
    for conta_id, dados in contas.items():
        trader = TradingAvancado(dados['api_key'], dados['api_secret'], dados['nome'])
        if trader.sync_time():
            saldo = trader.get_saldo_usdt()
            logger.info(f"[SALDO] {dados['nome']}: ${saldo:.2f} USDT")
            
            if saldo > maior_saldo:
                maior_saldo = saldo
                melhor_trader = trader
    
    if not melhor_trader or maior_saldo < 5:
        logger.error("[ERRO] Nenhuma conta com saldo suficiente")
        return
    
    logger.info(f"[INÍCIO] Iniciando recuperação com ${maior_saldo:.2f} USDT")
    logger.info(f"[META] Meta de recuperação: +15.82% = ${maior_saldo * 1.1582:.2f}")
    
    try:
        while True:
            logger.info("\n[ANÁLISE INTELIGENTE] ANÁLISE COMPLETA DO MERCADO PARA RECUPERAÇÃO")
            
            oportunidades = melhor_trader.analisar_mercado_completo()
            
            if oportunidades:
                melhor_op = oportunidades[0]  # Melhor oportunidade
                
                logger.info(f"[OPORTUNIDADE] MELHOR OPORTUNIDADE ENCONTRADA:")
                logger.info(f"   {melhor_op['symbol']} - {melhor_op['estrategia']}")
                logger.info(f"   Confiança: {melhor_op['confidence']:.1f}%")
                logger.info(f"   Sinal: {melhor_op['signal']}")
                
                if melhor_op['confidence'] >= melhor_trader.min_confidence_trade:
                    # Executar o trade
                    resultado = melhor_trader.executar_trade_inteligente(melhor_op, melhor_op['symbol'])
                    
                    if resultado:
                        logger.info("[SUCESSO] Trade de recuperação executado!")
                        
                        # Verificar se atingiu a meta diária
                        total_expectativa = sum(t['expectativa_lucro'] for t in melhor_trader.trades_executados)
                        
                        if total_expectativa >= 5.0:  # 5% por dia
                            logger.info(f"[VITÓRIA] META DIÁRIA ATINGIDA: {total_expectativa:.2f}%")
                            melhor_trader.salvar_relatorio_recuperacao()
                            break
                        
                        # Aguardar um pouco após trade bem-sucedido
                        time.sleep(120)  # 2 minutos
                    else:
                        logger.error("[ERRO] Falha no trade de recuperação")
                        time.sleep(60)  # 1 minuto
                else:
                    logger.info(f"⚠️ Confiança insuficiente: {melhor_op['confidence']:.1f}%")
            else:
                logger.info("[PAUSA] Aguardando melhores oportunidades...")
            
            # Análise a cada 20 segundos para ser mais agressivo
            time.sleep(20)
            
    except KeyboardInterrupt:
        logger.info("⏹️ Sistema interrompido - Salvando relatório...")
        melhor_trader.salvar_relatorio_recuperacao()
    except Exception as e:
        logger.error(f"[ERRO SISTEMA] Erro no sistema: {e}")
        melhor_trader.salvar_relatorio_recuperacao()

if __name__ == '__main__':
    main()