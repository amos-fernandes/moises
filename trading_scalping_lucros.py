"""
SISTEMA SCALPING - LUCROS PEQUENOS E CONSECUTIVOS
Focado em trades rápidos e lucros consistentes de 1-3%
Corrige problemas de formatação da Binance
"""

import json
import time
import logging
import hmac
import hashlib
import requests
import numpy as np
from urllib.parse import urlencode
from datetime import datetime, timedelta
import sys

# Configuracao de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_scalping_lucros.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingScalpingLucros:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS SCALPING - LUCROS PEQUENOS E CONSECUTIVOS
        self.lucro_target = 1.5      # Target de lucro: 1.5%
        self.stop_loss = 0.8         # Stop loss: 0.8%
        self.confianca_minima = 70   # Confiança mínima mais baixa
        self.rsi_oversold = 45       # RSI menos restritivo
        self.rsi_overbought = 55     # RSI menos restritivo
        self.valor_trade_base = 3.0  # Trades menores
        self.max_posicoes = 3        # Máximo 3 posições abertas
        self.tempo_max_posicao = 15  # 15 minutos máximo por posição
        
        # Controle de posições abertas
        self.posicoes_abertas = {}
        self.historico_trades = []
        self.lucro_acumulado = 0
        self.trades_sucessos = 0
        self.trades_perdas = 0
        
        logger.info(f"🎯 Sistema Scalping iniciado - {conta_nome}")
        logger.info("=" * 50)
        logger.info("📈 PARAMETROS SCALPING:")
        logger.info(f"   💰 Target lucro: {self.lucro_target}%")
        logger.info(f"   🛡️ Stop loss: {self.stop_loss}%")
        logger.info(f"   📊 Confiança mínima: {self.confianca_minima}%")
        logger.info(f"   📈 RSI oversold: < {self.rsi_oversold}")
        logger.info(f"   📉 RSI overbought: > {self.rsi_overbought}")
        logger.info(f"   💵 Valor base trade: ${self.valor_trade_base}")
        logger.info(f"   🎯 Max posições: {self.max_posicoes}")
        logger.info("=" * 50)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição corrigida para evitar erro 400"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # Timestamp da Binance
            try:
                r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                if r.status_code == 200:
                    params['timestamp'] = r.json()['serverTime']
                else:
                    params['timestamp'] = int(datetime.now().timestamp() * 1000)
            except:
                params['timestamp'] = int(datetime.now().timestamp() * 1000)
                
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                r = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=10)
            
            # Log detalhado para debugging
            if r.status_code != 200:
                logger.error(f"Erro HTTP {r.status_code}: {r.text}")
                return {'error': True, 'detail': f"{r.status_code}: {r.text}"}
            
            return r.json()
        except Exception as e:
            logger.error(f"Erro na requisição: {str(e)}")
            return {'error': True, 'detail': str(e)}
    
    def get_account_info(self):
        """Obter informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)
    
    def get_saldo_usdt(self):
        """Obter saldo USDT disponível"""
        account = self.get_account_info()
        if account.get('error'):
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0
    
    def get_portfolio_total(self):
        """Obter valor total do portfolio"""
        account = self.get_account_info()
        if account.get('error'):
            return 0, {}
        
        total_value = 0
        portfolio_details = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0:
                if asset == 'USDT':
                    value_usdt = total_balance
                else:
                    # Obter preço atual
                    try:
                        ticker_symbol = f"{asset}USDT"
                        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={ticker_symbol}", timeout=5)
                        if r.status_code == 200:
                            price = float(r.json()['price'])
                            value_usdt = total_balance * price
                        else:
                            value_usdt = 0
                    except:
                        value_usdt = 0
                
                if value_usdt > 0.01:
                    total_value += value_usdt
                    portfolio_details[asset] = {
                        'quantidade': total_balance,
                        'valor_usdt': value_usdt,
                        'free': free,
                        'locked': locked
                    }
        
        return total_value, portfolio_details
    
    def get_price(self, symbol):
        """Obter preço atual de um símbolo"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            pass
        return None
    
    def get_candles(self, symbol: str, limit: int = 30):
        """Obter candles recentes"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',  # Scalping usa 1 minuto
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            if r.status_code != 200:
                return []
            
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
            logger.error(f"Erro candles {symbol}: {e}")
            return []
    
    def calcular_rsi(self, prices, period=14):
        """Calcular RSI"""
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
    
    def analisar_simbolo_scalping(self, symbol):
        """Análise específica para scalping"""
        candles = self.get_candles(symbol, 30)
        if len(candles) < 20:
            return None
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        
        preco_atual = closes[-1]
        rsi = self.calcular_rsi(closes)
        
        # Médias móveis curtas para scalping
        sma_5 = np.mean(closes[-5:])
        sma_10 = np.mean(closes[-10:])
        
        # Volatilidade recente
        volatilidade = np.std(closes[-10:]) / preco_atual * 100
        
        # Volume atual vs médio
        volume_medio = np.mean(volumes[-10:])
        volume_atual = volumes[-1]
        volume_ratio = volume_atual / volume_medio if volume_medio > 0 else 1
        
        # LÓGICA SCALPING - Menos restritiva, mais oportunidades
        sinal = 'NEUTRO'
        confianca = 50
        
        if rsi < self.rsi_oversold:  # < 45
            sinal = 'COMPRA'
            # Confiança baseada em múltiplos fatores
            confianca = 60 + (self.rsi_oversold - rsi) * 2
            
            # Bonus por tendência
            if preco_atual < sma_5:
                confianca += 8
            if sma_5 < sma_10:
                confianca += 5
            
            # Bonus por volume
            if volume_ratio > 1.1:
                confianca += 10
                
        elif rsi > self.rsi_overbought:  # > 55
            sinal = 'VENDA'
            confianca = 60 + (rsi - self.rsi_overbought) * 2
            
            if preco_atual > sma_5:
                confianca += 8
            if sma_5 > sma_10:
                confianca += 5
            if volume_ratio > 1.1:
                confianca += 10
        
        # Limitar confiança
        confianca = min(95, max(30, confianca))
        
        return {
            'symbol': symbol,
            'preco': preco_atual,
            'rsi': rsi,
            'sma_5': sma_5,
            'sma_10': sma_10,
            'volatilidade': volatilidade,
            'volume_ratio': volume_ratio,
            'sinal': sinal,
            'confianca': confianca
        }
    
    def executar_compra_corrigida(self, symbol, valor_usdt):
        """Compra com formatação corrigida"""
        try:
            # Garantir formatação correta
            valor_str = f"{valor_usdt:.2f}"
            
            logger.info(f"💰 COMPRA SCALPING: {symbol} - ${valor_str}")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': valor_str  # Formato corrigido
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra: {resultado.get('detail', 'Erro desconhecido')}")
                return None
            
            # Registrar posição aberta
            quantidade = float(resultado.get('executedQty', 0))
            preco_entrada = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            
            if quantidade > 0 and preco_entrada > 0:
                self.posicoes_abertas[symbol] = {
                    'order_id': resultado.get('orderId'),
                    'quantidade': quantidade,
                    'preco_entrada': preco_entrada,
                    'valor_investido': valor_usdt,
                    'timestamp_entrada': datetime.now(),
                    'target_lucro': preco_entrada * (1 + self.lucro_target / 100),
                    'stop_loss': preco_entrada * (1 - self.stop_loss / 100)
                }
                
                logger.info(f"✅ POSIÇÃO ABERTA: {symbol}")
                logger.info(f"   💵 Investido: ${valor_usdt:.2f}")
                logger.info(f"   📊 Quantidade: {quantidade:.8f}")
                logger.info(f"   💰 Entrada: ${preco_entrada:.6f}")
                logger.info(f"   🎯 Target: ${self.posicoes_abertas[symbol]['target_lucro']:.6f} (+{self.lucro_target}%)")
                logger.info(f"   🛡️ Stop: ${self.posicoes_abertas[symbol]['stop_loss']:.6f} (-{self.stop_loss}%)")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro executando compra: {e}")
            return None
    
    def executar_venda(self, symbol, quantidade):
        """Vender posição"""
        try:
            # Formatação corrigida para quantidade
            quantidade_str = f"{quantidade:.8f}".rstrip('0').rstrip('.')
            
            logger.info(f"💸 VENDENDO: {symbol} - Qtd: {quantidade_str}")
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': quantidade_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda: {resultado.get('detail')}")
                return None
            
            logger.info(f"✅ VENDA EXECUTADA: {symbol} - Order ID {resultado.get('orderId')}")
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro executando venda: {e}")
            return None
    
    def verificar_posicoes_abertas(self):
        """Verificar take-profit e stop-loss das posições abertas"""
        posicoes_para_fechar = []
        
        for symbol, posicao in self.posicoes_abertas.items():
            preco_atual = self.get_price(symbol)
            if not preco_atual:
                continue
            
            preco_entrada = posicao['preco_entrada']
            target_lucro = posicao['target_lucro']
            stop_loss = posicao['stop_loss']
            tempo_posicao = datetime.now() - posicao['timestamp_entrada']
            
            # Calcular lucro/perda atual
            lucro_atual_pct = (preco_atual - preco_entrada) / preco_entrada * 100
            lucro_atual_usd = posicao['valor_investido'] * (lucro_atual_pct / 100)
            
            motivo_fechamento = None
            
            # Verificar take-profit
            if preco_atual >= target_lucro:
                motivo_fechamento = f"TAKE_PROFIT_+{self.lucro_target}%"
                
            # Verificar stop-loss  
            elif preco_atual <= stop_loss:
                motivo_fechamento = f"STOP_LOSS_-{self.stop_loss}%"
                
            # Verificar tempo máximo
            elif tempo_posicao.total_seconds() > self.tempo_max_posicao * 60:
                motivo_fechamento = f"TEMPO_MAX_{self.tempo_max_posicao}min"
            
            if motivo_fechamento:
                logger.info(f"🔄 FECHANDO POSIÇÃO: {symbol}")
                logger.info(f"   📊 Preço atual: ${preco_atual:.6f}")
                logger.info(f"   📈 Lucro atual: {lucro_atual_pct:+.2f}% (${lucro_atual_usd:+.2f})")
                logger.info(f"   ⏱️ Tempo posição: {int(tempo_posicao.total_seconds()/60)}min")
                logger.info(f"   🎯 Motivo: {motivo_fechamento}")
                
                # Executar venda
                resultado_venda = self.executar_venda(symbol, posicao['quantidade'])
                
                if resultado_venda:
                    # Registrar no histórico
                    trade_info = {
                        'symbol': symbol,
                        'entrada': posicao['timestamp_entrada'],
                        'saida': datetime.now(),
                        'preco_entrada': preco_entrada,
                        'preco_saida': preco_atual,
                        'quantidade': posicao['quantidade'],
                        'valor_investido': posicao['valor_investido'],
                        'lucro_pct': lucro_atual_pct,
                        'lucro_usd': lucro_atual_usd,
                        'motivo': motivo_fechamento,
                        'tempo_minutos': int(tempo_posicao.total_seconds()/60)
                    }
                    
                    self.historico_trades.append(trade_info)
                    self.lucro_acumulado += lucro_atual_usd
                    
                    if lucro_atual_usd > 0:
                        self.trades_sucessos += 1
                        logger.info(f"✅ TRADE LUCRATIVO: +${lucro_atual_usd:.2f}")
                    else:
                        self.trades_perdas += 1
                        logger.info(f"❌ TRADE PREJUÍZO: ${lucro_atual_usd:.2f}")
                    
                    posicoes_para_fechar.append(symbol)
        
        # Remover posições fechadas
        for symbol in posicoes_para_fechar:
            del self.posicoes_abertas[symbol]
    
    def calcular_valor_trade_scalping(self, saldo_usdt):
        """Calcular valor para trade de scalping - CORRIGIDO PARA BINANCE"""
        # VALORES MÍNIMOS DA BINANCE: ~$5-10 dependendo do símbolo
        
        if saldo_usdt < 5:
            # Capital muito baixo - aguardar mais capital
            return 0
        elif saldo_usdt < 10:
            # Usar quase tudo para atingir mínimo da Binance
            return min(saldo_usdt * 0.9, 5.5)
        elif saldo_usdt < 20:
            return min(6.0, saldo_usdt * 0.4)   # Entre $5-6
        else:
            return min(10.0, saldo_usdt * 0.3)  # Entre $6-10
    
    def ciclo_scalping(self, ciclo):
        """Ciclo de scalping - lucros pequenos e frequentes"""
        logger.info(f"🔄 === CICLO SCALPING {ciclo} ===")
        
        # Primeiro verificar posições abertas
        self.verificar_posicoes_abertas()
        
        # Obter portfolio
        portfolio_total, portfolio_details = self.get_portfolio_total()
        saldo_usdt = self.get_saldo_usdt()
        
        logger.info(f"💼 Portfolio: ${portfolio_total:.2f} | USDT: ${saldo_usdt:.2f}")
        logger.info(f"📊 Posições abertas: {len(self.posicoes_abertas)}")
        
        if len(self.posicoes_abertas) >= self.max_posicoes:
            logger.info(f"🚫 Máximo de posições atingido ({self.max_posicoes})")
            return True
        
        if saldo_usdt < 5.0:
            logger.warning(f"⚠️ USDT abaixo do mínimo Binance: ${saldo_usdt:.2f} (precisa $5+)")
            logger.info("💡 Aguardando take-profit de posições existentes ou mais capital...")
            return True
        
        # Símbolos para scalping (alta liquidez)
        simbolos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'DOGEUSDT']
        
        melhores_oportunidades = []
        
        for symbol in simbolos:
            # Pular se já tem posição neste símbolo
            if symbol in self.posicoes_abertas:
                continue
                
            analise = self.analisar_simbolo_scalping(symbol)
            if not analise:
                continue
            
            rsi = analise['rsi']
            confianca = analise['confianca']
            sinal = analise['sinal']
            
            # Emoji para clareza
            emoji = "🟢" if sinal == 'COMPRA' else "🔴" if sinal == 'VENDA' else "⚪"
            logger.info(f"{emoji} {symbol}: RSI {rsi:.1f} | {sinal} | Conf: {confianca:.1f}%")
            
            # Coletar apenas oportunidades de COMPRA com confiança suficiente
            if sinal == 'COMPRA' and confianca >= self.confianca_minima:
                melhores_oportunidades.append(analise)
        
        # Ordenar por confiança
        melhores_oportunidades.sort(key=lambda x: x['confianca'], reverse=True)
        
        # Executar 1-2 trades por ciclo
        trades_executados = 0
        max_trades_ciclo = min(2, self.max_posicoes - len(self.posicoes_abertas))
        
        for oportunidade in melhores_oportunidades[:max_trades_ciclo]:
            symbol = oportunidade['symbol']
            confianca = oportunidade['confianca']
            
            valor_trade = self.calcular_valor_trade_scalping(saldo_usdt)
            
            if valor_trade > 0 and valor_trade <= saldo_usdt and valor_trade >= 5.0:
                logger.info(f"🎯 OPORTUNIDADE SCALPING: {symbol}")
                logger.info(f"   🎲 Confiança: {confianca:.1f}%")
                logger.info(f"   💰 Valor: ${valor_trade:.2f}")
                
                resultado = self.executar_compra_corrigida(symbol, valor_trade)
                if resultado:
                    saldo_usdt -= valor_trade
                    trades_executados += 1
                else:
                    logger.warning(f"⚠️ Falha na compra {symbol}")
            elif valor_trade > 0 and valor_trade < 5.0:
                logger.warning(f"💸 {symbol}: Valor ${valor_trade:.2f} < mínimo Binance ($5)")
        
        if trades_executados == 0:
            if saldo_usdt < 5.0:
                logger.warning(f"⚠️ Capital insuficiente: ${saldo_usdt:.2f} (mínimo $5 para Binance)")
            else:
                logger.info("📊 Nenhuma nova posição aberta neste ciclo")
        
        return True
    
    def relatorio_performance(self):
        """Relatório de performance detalhado"""
        total_trades = len(self.historico_trades)
        if total_trades == 0:
            return
        
        taxa_sucesso = (self.trades_sucessos / total_trades) * 100
        lucros = [t['lucro_usd'] for t in self.historico_trades if t['lucro_usd'] > 0]
        perdas = [t['lucro_usd'] for t in self.historico_trades if t['lucro_usd'] <= 0]
        
        logger.info("\n" + "=" * 60)
        logger.info("📊 RELATÓRIO PERFORMANCE SCALPING")
        logger.info("=" * 60)
        logger.info(f"💰 Lucro acumulado: ${self.lucro_acumulado:+.2f}")
        logger.info(f"📈 Trades total: {total_trades}")
        logger.info(f"✅ Sucessos: {self.trades_sucessos}")
        logger.info(f"❌ Perdas: {self.trades_perdas}")
        logger.info(f"🎯 Taxa sucesso: {taxa_sucesso:.1f}%")
        
        if lucros:
            logger.info(f"💚 Lucro médio: +${np.mean(lucros):.2f}")
            logger.info(f"🚀 Maior lucro: +${max(lucros):.2f}")
        
        if perdas:
            logger.info(f"💔 Perda média: ${np.mean(perdas):.2f}")
            logger.info(f"📉 Maior perda: ${min(perdas):.2f}")
        
        if total_trades >= 3:
            ultimos_3 = self.historico_trades[-3:]
            lucro_ultimos_3 = sum(t['lucro_usd'] for t in ultimos_3)
            logger.info(f"📊 Últimos 3 trades: ${lucro_ultimos_3:+.2f}")
        
        logger.info("=" * 60 + "\n")
    
    def run_scalping(self, max_ciclos=100):
        """Executar sistema de scalping"""
        logger.info("🎯 === SISTEMA SCALPING - LUCROS CONSECUTIVOS ===")
        logger.info("🚀 Estratégia: Trades rápidos, lucros pequenos e consistentes")
        logger.info("=" * 60)
        
        portfolio_inicial, _ = self.get_portfolio_total()
        logger.info(f"💼 Portfolio inicial: ${portfolio_inicial:.2f}")
        
        for ciclo in range(1, max_ciclos + 1):
            try:
                self.ciclo_scalping(ciclo)
                
                # Relatório a cada 5 ciclos
                if ciclo % 5 == 0:
                    self.relatorio_performance()
                
                # Aguardar próximo ciclo (1 minuto para scalping)
                if ciclo < max_ciclos:
                    logger.info("⏰ Próximo ciclo em 60 segundos...")
                    time.sleep(60)  # 1 minuto entre ciclos
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema interrompido")
                break
            except Exception as e:
                logger.error(f"❌ Erro no ciclo {ciclo}: {e}")
                time.sleep(30)
        
        # Relatório final
        portfolio_final, _ = self.get_portfolio_total()
        lucro_total = portfolio_final - portfolio_inicial
        
        logger.info("🏆 === RELATÓRIO FINAL SCALPING ===")
        logger.info(f"💼 Portfolio inicial: ${portfolio_inicial:.2f}")
        logger.info(f"💼 Portfolio final: ${portfolio_final:.2f}")
        logger.info(f"📈 Resultado total: ${lucro_total:+.2f}")
        
        self.relatorio_performance()

def main():
    """Função principal"""
    try:
        logger.info("🔧 Carregando configuração...")
        
        with open('config/contas.json', 'r') as f:
            contas = json.load(f)
        
        conta = contas['CONTA_3']  # Amos
        
        trader = TradingScalpingLucros(
            api_key=conta['api_key'],
            api_secret=conta['api_secret'],
            conta_nome="AMOS_SCALPING"
        )
        
        logger.info("✅ Sistema scalping configurado")
        trader.run_scalping(max_ciclos=50)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()