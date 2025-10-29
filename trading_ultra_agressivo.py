"""
SISTEMA ULTRA-AGRESSIVO - RECUPERAÇÃO DE PREJUÍZOS
RSI 14-18 = COMPRA EMERGENCIAL COM TODO CAPITAL
Foco em reversão rápida de prejuízos
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

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_ultra_agressivo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingUltraAgressivo:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS ULTRA-AGRESSIVOS PARA RECUPERAÇÃO - AJUSTADOS
        self.rsi_venda_btc = 50           # BTC: RSI > 50 = VENDER PARA TER USDT
        self.rsi_extremo_compra = 25      # RSI < 25 = COMPRA EMERGENCIAL  
        self.rsi_extremo_venda = 75       # RSI > 75 = VENDA IMEDIATA
        self.confianca_minima = 65        # Baixa para mais trades
        self.usar_todo_capital = True     # Usar 100% em oportunidades
        self.stop_loss_emergencial = 1.5 # Stop: 1.5%
        self.target_rapido = 2.5          # Target: 2.5% (mais realista)
        
        # Controle de recuperação
        self.trades_recuperacao = []
        self.valor_inicial = 0
        self.meta_recuperacao = 0
        self.modo_emergencia = True
        
        # Filtros mínimos da Binance - CORRIGIDO PARA LOT_SIZE
        self.min_quantities = {
            'BTCUSDT': 0.00001,     # Mínimo BTC: 0.00001 (era 0.00001998)
            'ETHUSDT': 0.0001,      # Mínimo ETH: 0.0001
            'SOLUSDT': 0.01,        # Mínimo SOL: 0.01
        }
        self.min_notional = 10.0    # Valor mínimo em USDT: $10
        
        # Cache de preços para cálculos
        self.precos_cache = {}
        
        logger.info(f"🚨 Sistema ULTRA-AGRESSIVO - {conta_nome}")
        logger.info("=" * 60)
        logger.info("🔥 MODO RECUPERAÇÃO DE PREJUÍZOS ATIVADO!")
        logger.info("⚡ ESTRATÉGIA EMERGENCIAL:")
        logger.info(f"   🎯 RSI < {self.rsi_extremo_compra} = COMPRA COM TODO CAPITAL")
        logger.info(f"   💸 RSI > {self.rsi_extremo_venda} = VENDA IMEDIATA")
        logger.info(f"   🎲 Target: {self.target_rapido}% (rápido)")
        logger.info(f"   🛡️ Stop: {self.stop_loss_emergencial}% (amplo)")
        logger.info("   🚀 SEM HESITAÇÃO - AÇÃO IMEDIATA!")
        logger.info("=" * 60)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição da Binance"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
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
            
            if r.status_code != 200:
                logger.error(f"Erro HTTP {r.status_code}: {r.text}")
                return {'error': True, 'detail': f"{r.status_code}: {r.text}"}
            
            return r.json()
        except Exception as e:
            logger.error(f"Erro na requisição: {str(e)}")
            return {'error': True, 'detail': str(e)}
    
    def get_account_info(self):
        """Informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)
    
    def get_portfolio_completo(self):
        """Portfolio completo"""
        account = self.get_account_info()
        if account.get('error'):
            return 0, {}
        
        total_value = 0
        portfolio = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0:
                if asset == 'USDT':
                    value_usdt = total_balance
                    price = 1.0
                else:
                    try:
                        ticker_symbol = f"{asset}USDT"
                        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={ticker_symbol}", timeout=5)
                        if r.status_code == 200:
                            price = float(r.json()['price'])
                            value_usdt = total_balance * price
                        else:
                            price = 0
                            value_usdt = 0
                    except:
                        price = 0
                        value_usdt = 0
                
                if value_usdt > 0.01:
                    total_value += value_usdt
                    portfolio[asset] = {
                        'quantidade': total_balance,
                        'free': free,
                        'locked': locked,
                        'preco_atual': price,
                        'valor_usdt': value_usdt
                    }
        
        return total_value, portfolio
    
    def get_candles(self, symbol: str, limit: int = 20):
        """Obter candles"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            if r.status_code != 200:
                return []
            
            candles = []
            for kline in r.json():
                candles.append(float(kline[4]))  # close price
            
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
    
    def get_preco_atual(self, symbol):
        """Obter preço atual de um símbolo"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=3)
            if r.status_code == 200:
                preco = float(r.json()['price'])
                self.precos_cache[symbol] = preco
                return preco
        except:
            pass
        
        # Usar cache se disponível, senão valores padrão
        return self.precos_cache.get(symbol, {
            'BTCUSDT': 113000,
            'ETHUSDT': 3988,
            'SOLUSDT': 250
        }.get(symbol, 100))
    
    def executar_venda_btc_parcial(self, quantidade):
        """Venda parcial do BTC para ter USDT - CORRIGIDO LOT_SIZE"""
        try:
            # VERIFICAR SE QUANTIDADE É VÁLIDA
            min_qty = self.min_quantities['BTCUSDT']
            if quantidade < min_qty:
                logger.warning(f"⚠️ Quantidade BTC {quantidade:.8f} < mínimo {min_qty:.5f}")
                logger.warning(f"🔄 Ajustando para quantidade mínima...")
                quantidade = min_qty
            
            # Verificar valor mínimo em USDT (preço real)
            preco_atual = self.get_preco_atual('BTCUSDT')
            valor_estimado = quantidade * preco_atual
            
            if valor_estimado < self.min_notional:
                logger.warning(f"⚠️ Valor ${valor_estimado:.2f} < mínimo ${self.min_notional}")
                quantidade = self.min_notional / preco_atual
                logger.warning(f"🔄 Ajustando quantidade para: {quantidade:.8f} BTC")
            
            # Formatação correta (5 casas decimais para BTC)
            quantidade_str = f"{quantidade:.5f}"
            
            logger.info(f"💰 VENDA PARCIAL BTC: {quantidade_str}")
            logger.info(f"   💵 Valor estimado: ${valor_estimado:.2f}")
            
            params = {
                'symbol': 'BTCUSDT',
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': quantidade_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda BTC: {resultado.get('detail')}")
                return None
            
            preco_venda = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            valor_recebido = quantidade * preco_venda
            
            logger.info(f"✅ BTC VENDIDO!")
            logger.info(f"   💰 Preço: ${preco_venda:.2f}")
            logger.info(f"   💵 USDT recebido: ${valor_recebido:.2f}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro venda BTC: {e}")
            return None

    def vender_tudo_disponivel(self, asset, portfolio_info):
        """VENDA EMERGENCIAL - TODO o ativo - CORRIGIDO LOT_SIZE"""
        if asset not in portfolio_info:
            return None
            
        quantidade_disponivel = portfolio_info[asset]['free']
        if quantidade_disponivel <= 0:
            return None
        
        symbol = f"{asset}USDT"
        
        try:
            # VERIFICAR QUANTIDADE MÍNIMA
            if symbol in self.min_quantities:
                min_qty = self.min_quantities[symbol]
                if quantidade_disponivel < min_qty:
                    logger.warning(f"⚠️ {asset} quantidade {quantidade_disponivel} < mínimo {min_qty}")
                    return None
            
            # Verificar valor mínimo
            valor_estimado = portfolio_info[asset]['valor_usdt']
            if valor_estimado < self.min_notional:
                logger.warning(f"⚠️ {asset} valor ${valor_estimado:.2f} < mínimo ${self.min_notional}")
                return None
            
            # Formatação baseada no ativo
            if asset == 'BTC':
                quantidade_str = f"{quantidade_disponivel:.5f}"
            elif asset == 'ETH':
                quantidade_str = f"{quantidade_disponivel:.4f}"
            else:
                quantidade_str = f"{quantidade_disponivel:.2f}"
            
            logger.info(f"🚨 VENDA EMERGENCIAL TOTAL: {symbol}")
            logger.info(f"   📊 Quantidade: {quantidade_str}")
            logger.info(f"   💰 Valor estimado: ${valor_estimado:.2f}")
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': quantidade_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda total: {resultado.get('detail')}")
                return None
            
            preco_venda = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            valor_recebido = quantidade_disponivel * preco_venda
            
            logger.info(f"✅ VENDA TOTAL EXECUTADA!")
            logger.info(f"   💵 USDT recebido: ${valor_recebido:.2f}")
            logger.info(f"   🎯 Agora temos capital para comprar no fundo!")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro venda total: {e}")
            return None
    
    def compra_emergencial_total(self, symbol, usdt_disponivel):
        """COMPRA EMERGENCIAL - TODO o USDT"""
        try:
            # Usar 95% do USDT disponível (deixar pequena reserva)
            valor_investir = usdt_disponivel * 0.95
            
            if valor_investir < 5.0:
                logger.warning(f"💸 USDT insuficiente: ${valor_investir:.2f}")
                return None
            
            valor_str = f"{valor_investir:.2f}"
            
            logger.info(f"🚨 COMPRA EMERGENCIAL TOTAL: {symbol}")
            logger.info(f"   💰 INVESTINDO TODO CAPITAL: ${valor_str}")
            logger.info(f"   🎯 Estratégia: ALL-IN na reversão!")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': valor_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra emergencial: {resultado.get('detail')}")
                return None
            
            quantidade = float(resultado.get('executedQty', 0))
            preco_compra = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            
            logger.info(f"✅ COMPRA EMERGENCIAL EXECUTADA!")
            logger.info(f"   📊 Quantidade: {quantidade:.8f}")
            logger.info(f"   💰 Preço entrada: ${preco_compra:.6f}")
            logger.info(f"   🎯 Target: ${preco_compra * (1 + self.target_rapido/100):.6f} (+{self.target_rapido}%)")
            
            # Registrar para monitoramento
            self.trades_recuperacao.append({
                'symbol': symbol,
                'tipo': 'COMPRA_EMERGENCIAL',
                'quantidade': quantidade,
                'preco_entrada': preco_compra,
                'valor_investido': float(valor_str),
                'target_preco': preco_compra * (1 + self.target_rapido/100),
                'stop_preco': preco_compra * (1 - self.stop_loss_emergencial/100),
                'timestamp': datetime.now()
            })
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro compra emergencial: {e}")
            return None
    
    def analisar_rsi_extremo(self, symbol):
        """Análise focada em RSI extremo"""
        candles = self.get_candles(symbol, 30)
        if len(candles) < 20:
            return None
        
        rsi = self.calcular_rsi(candles)
        preco_atual = candles[-1]
        
        # LÓGICA ULTRA-AGRESSIVA AJUSTADA
        acao = 'AGUARDAR'
        urgencia = 'NORMAL'
        confianca = 50
        
        # ESTRATÉGIA ESPECIAL PARA BTC (que já temos)
        if symbol == 'BTCUSDT':
            if rsi >= self.rsi_venda_btc:  # RSI >= 50 - VENDER BTC para ter USDT
                acao = 'VENDA_PARCIAL_BTC'
                urgencia = 'ALTA'
                confianca = 70 + (rsi - self.rsi_venda_btc) * 1.0
                
            elif rsi <= 30:  # RSI <= 30 - BTC muito baixo, hold
                acao = 'HOLD_BTC'
                urgencia = 'MEDIA'
                confianca = 80 + (30 - rsi) * 1.0
        else:
            # PARA OUTROS SÍMBOLOS (ETH, SOL)
            if rsi <= self.rsi_extremo_compra:  # RSI <= 25
                acao = 'COMPRA_EMERGENCIAL'
                urgencia = 'EXTREMA'
                confianca = 90 + (self.rsi_extremo_compra - rsi) * 0.5
                
            elif rsi >= self.rsi_extremo_venda:  # RSI >= 75
                acao = 'VENDA_EMERGENCIAL'
                urgencia = 'EXTREMA'
                confianca = 85 + (rsi - self.rsi_extremo_venda) * 0.5
                
            elif rsi <= 35:  # RSI 25-35
                acao = 'COMPRA_FORTE'
                urgencia = 'ALTA'
                confianca = 75 + (35 - rsi) * 1.5
        
        confianca = min(95, max(50, confianca))
        
        return {
            'symbol': symbol,
            'rsi': rsi,
            'preco': preco_atual,
            'acao': acao,
            'urgencia': urgencia,
            'confianca': confianca
        }
    
    def ciclo_ultra_agressivo(self, ciclo):
        """Ciclo ultra-agressivo para recuperação"""
        logger.info(f"🚨 === CICLO ULTRA-AGRESSIVO {ciclo} ===")
        
        # Portfolio atual
        valor_total, portfolio = self.get_portfolio_completo()
        
        logger.info(f"💼 Portfolio: ${valor_total:.2f}")
        
        # Mostrar perdas/ganhos
        if self.valor_inicial > 0:
            diferenca = valor_total - self.valor_inicial
            percentual = (diferenca / self.valor_inicial) * 100
            
            if diferenca < 0:
                logger.warning(f"📉 PREJUÍZO: ${diferenca:.2f} ({percentual:.2f}%)")
                logger.warning("🔥 MODO RECUPERAÇÃO ATIVO!")
            else:
                logger.info(f"📈 LUCRO: +${diferenca:.2f} (+{percentual:.2f}%)")
        
        # Log portfolio
        usdt_disponivel = 0
        for asset, info in portfolio.items():
            if info['valor_usdt'] > 1.0:
                logger.info(f"   {asset}: {info['quantidade']:.8f} = ${info['valor_usdt']:.2f}")
                if asset == 'USDT':
                    usdt_disponivel = info['free']
        
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.2f}")
        
        # Símbolos para análise agressiva (apenas permitidos pela API)
        simbolos_prioritarios = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']  # Removido ADAUSDT
        
        acoes_executadas = 0
        
        for symbol in simbolos_prioritarios:
            analise = self.analisar_rsi_extremo(symbol)
            if not analise:
                continue
            
            rsi = analise['rsi']
            acao = analise['acao']
            urgencia = analise['urgencia']
            confianca = analise['confianca']
            
            # Emoji por urgência
            if urgencia == 'EXTREMA':
                emoji = "🚨🚨🚨"
            elif urgencia == 'ALTA':
                emoji = "🔥🔥"
            elif urgencia == 'MEDIA':
                emoji = "⚡"
            else:
                emoji = "⏳"
            
            logger.info(f"{emoji} {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
            
            # EXECUTAR AÇÕES EMERGENCIAIS
            if confianca >= self.confianca_minima:
                
                # VENDA PARCIAL DO BTC - Estratégia para ter USDT
                if acao == 'VENDA_PARCIAL_BTC' and 'BTC' in portfolio:
                    quantidade_btc = portfolio['BTC']['free']
                    if quantidade_btc > 0:
                        # Calcular quantidade a vender (50% ou quantidade mínima viável)
                        quantidade_vender = quantidade_btc * 0.5
                        min_btc = self.min_quantities['BTCUSDT']
                        
                        # Se 50% é muito pouco, tentar vender quantidade mínima
                        if quantidade_vender < min_btc:
                            if quantidade_btc >= min_btc:
                                quantidade_vender = min_btc
                                logger.info(f"📊 Ajustando para quantidade mínima: {min_btc:.5f} BTC")
                            else:
                                logger.warning(f"⚠️ BTC total {quantidade_btc:.8f} < mínimo {min_btc:.5f}")
                                logger.warning("   📊 Pulando venda BTC - quantidade insuficiente")
                                continue
                        
                        # Verificar se vale a pena (> $10)
                        preco_btc_atual = self.get_preco_atual('BTCUSDT')
                        valor_estimado = quantidade_vender * preco_btc_atual
                        if valor_estimado < self.min_notional:
                            logger.warning(f"⚠️ Valor venda ${valor_estimado:.2f} < ${self.min_notional}")
                            logger.warning("   📊 Pulando venda BTC - valor muito baixo")
                            continue
                        
                        logger.warning(f"💰 BTC RSI {rsi:.1f} - VENDENDO PARA TER USDT!")
                        logger.info(f"   📊 Vendendo: {quantidade_vender:.8f} BTC (${valor_estimado:.2f})")
                        
                        resultado = self.executar_venda_btc_parcial(quantidade_vender)
                        if resultado:
                            acoes_executadas += 1
                            # Recalcular USDT após venda
                            valor_total_novo, portfolio_novo = self.get_portfolio_completo()
                            usdt_disponivel = portfolio_novo.get('USDT', {}).get('free', 0)
                            logger.info(f"💵 NOVO USDT disponível: ${usdt_disponivel:.2f}")
                        else:
                            logger.warning("❌ Falha na venda BTC - tentativa pulada")
                
                # COMPRA EMERGENCIAL - RSI < 25
                elif acao == 'COMPRA_EMERGENCIAL' and usdt_disponivel >= 5.0:
                    logger.warning(f"🚨 RSI EXTREMO: {rsi:.1f} em {symbol}!")
                    logger.warning("⚡ COMPRA EMERGENCIAL COM TODO CAPITAL!")
                    
                    resultado = self.compra_emergencial_total(symbol, usdt_disponivel)
                    if resultado:
                        acoes_executadas += 1
                        usdt_disponivel = 0
                        break
                
                # VENDA EMERGENCIAL - RSI > 75  
                elif acao == 'VENDA_EMERGENCIAL':
                    asset = symbol.replace('USDT', '')
                    if asset in portfolio and portfolio[asset]['free'] > 0:
                        logger.warning(f"💸 RSI EXTREMO ALTO: {rsi:.1f}!")
                        logger.warning("🚨 VENDA TOTAL PARA LUCRO!")
                        
                        resultado = self.vender_tudo_disponivel(asset, portfolio)
                        if resultado:
                            acoes_executadas += 1
                            valor_total_novo, portfolio_novo = self.get_portfolio_completo()
                            usdt_disponivel = portfolio_novo.get('USDT', {}).get('free', 0)
                
                # COMPRA FORTE - RSI 25-35
                elif acao == 'COMPRA_FORTE' and usdt_disponivel >= 5.0:
                    valor_investir = min(usdt_disponivel * 0.8, 12.0)
                    
                    logger.info(f"🔥 COMPRA FORTE: {symbol} RSI {rsi:.1f}")
                    resultado = self.compra_emergencial_total(symbol, valor_investir)
                    if resultado:
                        acoes_executadas += 1
                        usdt_disponivel -= valor_investir
                
                # HOLD BTC - RSI muito baixo, não vender
                elif acao == 'HOLD_BTC':
                    logger.info(f"🛡️ HOLD BTC: RSI {rsi:.1f} - Muito baixo para vender!")
        
        if acoes_executadas == 0:
            logger.info("📊 Nenhuma ação emergencial executada")
            logger.info("⏳ Aguardando RSI extremo para ação...")
        else:
            logger.info(f"⚡ {acoes_executadas} ação(ões) AGRESSIVA(S) executada(s)!")
        
        return True
    
    def relatorio_recuperacao(self):
        """Relatório de recuperação"""
        if len(self.trades_recuperacao) == 0:
            return
        
        logger.info("\n" + "🚨" * 20)
        logger.info("📊 RELATÓRIO RECUPERAÇÃO ULTRA-AGRESSIVA")
        logger.info("🚨" * 20)
        
        for trade in self.trades_recuperacao[-3:]:  # Últimos 3
            symbol = trade['symbol']
            preco_atual = self.get_candles(symbol, 1)
            if preco_atual:
                preco_atual = preco_atual[-1]
                lucro_atual = (preco_atual - trade['preco_entrada']) / trade['preco_entrada'] * 100
                
                logger.info(f"🎯 {symbol}:")
                logger.info(f"   Entrada: ${trade['preco_entrada']:.6f}")
                logger.info(f"   Atual: ${preco_atual:.6f}")
                logger.info(f"   Lucro: {lucro_atual:+.2f}%")
                logger.info(f"   Target: ${trade['target_preco']:.6f} (+{self.target_rapido}%)")
        
        logger.info("🚨" * 20 + "\n")
    
    def run_ultra_agressivo(self, max_ciclos=20):
        """Sistema ultra-agressivo"""
        logger.info("🚨 === SISTEMA ULTRA-AGRESSIVO ATIVADO ===")
        logger.info("🔥 OBJETIVO: RECUPERAÇÃO RÁPIDA DE PREJUÍZOS")
        logger.info("⚡ ESTRATÉGIA: RSI EXTREMO = AÇÃO IMEDIATA")
        logger.info("=" * 60)
        
        self.valor_inicial, _ = self.get_portfolio_completo()
        logger.info(f"💼 Portfolio inicial: ${self.valor_inicial:.2f}")
        logger.warning(f"🎯 Meta: Recuperar prejuízos e gerar +5% = ${self.valor_inicial * 1.05:.2f}")
        
        for ciclo in range(1, max_ciclos + 1):
            try:
                self.ciclo_ultra_agressivo(ciclo)
                
                # Relatório a cada 3 ciclos
                if ciclo % 3 == 0:
                    self.relatorio_recuperacao()
                
                # Verificar se atingiu meta
                valor_atual, _ = self.get_portfolio_completo()
                if valor_atual >= self.valor_inicial * 1.05:  # +5%
                    logger.info("🎉 META DE RECUPERAÇÃO ATINGIDA!")
                    logger.info(f"💰 Lucro gerado: +${valor_atual - self.valor_inicial:.2f}")
                    break
                
                # Ciclo rápido: 45 segundos
                if ciclo < max_ciclos:
                    logger.info("⏰ Próximo ciclo em 45 segundos...")
                    time.sleep(45)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema interrompido")
                break
            except Exception as e:
                logger.error(f"❌ Erro no ciclo {ciclo}: {e}")
                time.sleep(30)
        
        # Resultado final
        valor_final, _ = self.get_portfolio_completo()
        resultado = valor_final - self.valor_inicial
        
        logger.info("🏆 === RESULTADO ULTRA-AGRESSIVO ===")
        logger.info(f"💼 Inicial: ${self.valor_inicial:.2f}")
        logger.info(f"💼 Final: ${valor_final:.2f}")
        
        if resultado > 0:
            logger.info(f"🎉 SUCESSO: +${resultado:.2f} (+{(resultado/self.valor_inicial)*100:.2f}%)")
        else:
            logger.warning(f"📉 Ainda em prejuízo: ${resultado:.2f}")
            logger.warning("🔄 Considere continuar o sistema...")

def main():
    """Função principal"""
    try:
        logger.info("🔧 Carregando configuração...")
        
        with open('config/contas.json', 'r') as f:
            contas = json.load(f)
        
        conta = contas['CONTA_3']
        
        trader = TradingUltraAgressivo(
            api_key=conta['api_key'],
            api_secret=conta['api_secret'],
            conta_nome="AMOS_ULTRA_AGRESSIVO"
        )
        
        logger.info("🚨 Sistema ultra-agressivo configurado")
        trader.run_ultra_agressivo(max_ciclos=30)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()