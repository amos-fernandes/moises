"""
SISTEMA HIPER-OTIMIZADO - MÁXIMA PERFORMANCE
RSI 30 = COMPRA | RSI 70 = VENDA | Ciclos de 30s
MELHORIAS: Thresholds mais agressivos + Maior frequência
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
        logging.FileHandler('trading_hiper_otimizado.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingHiperOtimizado:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS HIPER-OTIMIZADOS PARA MÁXIMA PERFORMANCE
        self.rsi_compra_agressiva = 30       # RSI < 30 = COMPRA (era 25)
        self.rsi_venda_agressiva = 70        # RSI > 70 = VENDA (era 75)  
        self.rsi_venda_btc = 45              # BTC: RSI > 45 = VENDER PARA TER USDT (era 50)
        self.confianca_minima = 60           # Menor para mais trades (era 65)
        self.usar_todo_capital = True        # Usar 100% em oportunidades
        self.stop_loss_rapido = 1.0          # Stop: 1.0% (mais agressivo)
        self.target_rapido = 2.0             # Target: 2.0% (mais atingível)
        self.ciclo_tempo = 30                # 30 segundos (era 45)
        
        # Filtros mínimos da Binance - CORRIGIDO PARA LOT_SIZE
        self.min_quantities = {
            'BTCUSDT': 0.00001,     
            'ETHUSDT': 0.0001,      
            'SOLUSDT': 0.01,        
        }
        self.min_notional = 10.0    
        
        # Cache de preços para cálculos
        self.precos_cache = {}
        
        # Controle de recuperação
        self.trades_recuperacao = []
        self.valor_inicial = 0
        self.meta_recuperacao = 0
        self.modo_emergencia = True
        
        logger.info(f"🚀 Sistema HIPER-OTIMIZADO - {conta_nome}")
        logger.info("=" * 60)
        logger.info("⚡ MODO MÁXIMA PERFORMANCE ATIVADO!")
        logger.info("🔥 ESTRATÉGIA HIPER-AGRESSIVA:")
        logger.info(f"   🎯 RSI < {self.rsi_compra_agressiva} = COMPRA TOTAL")
        logger.info(f"   💸 RSI > {self.rsi_venda_agressiva} = VENDA TOTAL")
        logger.info(f"   🔄 BTC RSI > {self.rsi_venda_btc} = VENDA PARCIAL")
        logger.info(f"   🎲 Target: {self.target_rapido}% (otimizado)")
        logger.info(f"   🛡️ Stop: {self.stop_loss_rapido}% (rápido)")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (alta frequência)")
        logger.info("   ⚡ MÁXIMA VELOCIDADE - MÁXIMOS LUCROS!")
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

    def get_candles(self, symbol: str, limit: int = 15):
        """Obter candles - MENOS DADOS PARA MAIOR VELOCIDADE"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=3)
            if r.status_code != 200:
                return []
            
            candles = []
            for kline in r.json():
                candles.append(float(kline[4]))  # close price
            
            return candles
        except Exception as e:
            logger.error(f"Erro candles {symbol}: {e}")
            return []
    
    def calcular_rsi(self, prices, period=10):
        """Calcular RSI - PERÍODO MENOR PARA MAIOR SENSIBILIDADE"""
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
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=2)
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
    
    def get_portfolio_completo(self):
        """Portfolio completo com valores"""
        info = self.get_account_info()
        if info.get('error'):
            return 0, {}
        
        portfolio = {}
        valor_total = 0
        
        for balance in info.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    valor_usdt = total
                else:
                    try:
                        symbol = f"{asset}USDT"
                        preco = self.get_preco_atual(symbol)
                        valor_usdt = total * preco
                    except:
                        continue
                
                if valor_usdt > 0.1:  # Só incluir se > $0.10
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total += valor_usdt
        
        return valor_total, portfolio
    
    def compra_emergencial_total(self, symbol, valor_usdt):
        """COMPRA EMERGENCIAL - TODO O CAPITAL DISPONÍVEL"""
        try:
            # Usar 95% para evitar problemas de arredondamento
            valor_compra = valor_usdt * 0.95
            
            logger.info(f"🚨 COMPRA HIPER-AGRESSIVA: {symbol}")
            logger.info(f"   💰 INVESTINDO TODO CAPITAL: ${valor_compra:.2f}")
            logger.info(f"   🎯 Estratégia: ALL-IN na reversão!")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_compra:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra emergencial: {resultado.get('detail')}")
                return None
            
            # Calcular informações da compra
            fills = resultado.get('fills', [])
            if fills:
                preco_medio = sum(float(f['price']) * float(f['qty']) for f in fills) / sum(float(f['qty']) for f in fills)
                quantidade_total = sum(float(f['qty']) for f in fills)
                
                logger.info(f"✅ COMPRA HIPER-AGRESSIVA EXECUTADA!")
                logger.info(f"   📊 Quantidade: {quantidade_total:.8f}")
                logger.info(f"   💰 Preço entrada: ${preco_medio:.6f}")
                logger.info(f"   🎯 Target: ${preco_medio * (1 + self.target_rapido/100):.6f} (+{self.target_rapido}%)")
                
                return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro compra emergencial: {e}")
            return None
    
    def executar_venda_btc_parcial(self, quantidade):
        """Venda parcial do BTC para ter USDT - OTIMIZADA"""
        try:
            # VERIFICAR SE QUANTIDADE É VÁLIDA
            min_qty = self.min_quantities['BTCUSDT']
            if quantidade < min_qty:
                if quantidade * 2 >= min_qty:  # Se dobrar der certo, usar mínimo
                    quantidade = min_qty
                    logger.info(f"📊 Ajustando para quantidade mínima: {min_qty:.5f} BTC")
                else:
                    logger.warning(f"⚠️ BTC {quantidade:.8f} < mínimo {min_qty:.5f} - PULANDO")
                    return None
            
            # Verificar valor mínimo em USDT (preço real)
            preco_atual = self.get_preco_atual('BTCUSDT')
            valor_estimado = quantidade * preco_atual
            
            if valor_estimado < self.min_notional:
                quantidade_minima = self.min_notional / preco_atual
                if quantidade_minima < quantidade * 3:  # Se não for muito maior
                    quantidade = quantidade_minima
                    logger.info(f"🔄 Ajustando para valor mínimo: {quantidade:.8f} BTC")
                else:
                    logger.warning(f"⚠️ Valor muito baixo - PULANDO venda BTC")
                    return None
            
            # Formatação correta (5 casas decimais para BTC)
            quantidade_str = f"{quantidade:.5f}"
            
            logger.info(f"💰 VENDA OTIMIZADA BTC: {quantidade_str}")
            logger.info(f"   💵 Valor: ${valor_estimado:.2f}")
            
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
            
            fills = resultado.get('fills', [])
            if fills:
                preco_venda = float(fills[0]['price'])
                valor_recebido = quantidade * preco_venda
                
                logger.info(f"✅ BTC VENDIDO COM SUCESSO!")
                logger.info(f"   💰 Preço: ${preco_venda:.2f}")
                logger.info(f"   💵 USDT recebido: ${valor_recebido:.2f}")
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro venda BTC: {e}")
            return None

    def vender_tudo_disponivel(self, asset, portfolio_info):
        """VENDA TOTAL OTIMIZADA"""
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
            
            logger.info(f"🚨 VENDA TOTAL HIPER-OTIMIZADA: {symbol}")
            logger.info(f"   📊 Quantidade: {quantidade_str}")
            logger.info(f"   💰 Valor: ${valor_estimado:.2f}")
            
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
            
            fills = resultado.get('fills', [])
            if fills:
                preco_venda = float(fills[0]['price'])
                valor_recebido = quantidade_disponivel * preco_venda
                
                logger.info(f"✅ VENDA TOTAL EXECUTADA!")
                logger.info(f"   💰 Preço: ${preco_venda:.6f}")
                logger.info(f"   💵 USDT recebido: ${valor_recebido:.2f}")
                
                return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro venda total {asset}: {e}")
            return None

    def analisar_rsi_otimizado(self, symbol, rsi):
        """Análise otimizada do RSI"""
        confianca = 50.0
        
        if symbol == 'BTCUSDT' and rsi >= self.rsi_venda_btc:
            confianca = min(95, 50 + (rsi - self.rsi_venda_btc) * 2)
            return 'VENDA_PARCIAL_BTC', confianca
        
        # COMPRA HIPER-AGRESSIVA
        if rsi <= self.rsi_compra_agressiva:
            confianca = min(95, 50 + (self.rsi_compra_agressiva - rsi) * 3)
            if rsi <= 20:
                return 'COMPRA_EMERGENCIAL', confianca
            else:
                return 'COMPRA_FORTE', confianca
        
        # VENDA HIPER-AGRESSIVA  
        elif rsi >= self.rsi_venda_agressiva:
            confianca = min(95, 50 + (rsi - self.rsi_venda_agressiva) * 3)
            return 'VENDA_EMERGENCIAL', confianca
        
        # HOLD BTC em RSI muito baixo
        elif symbol == 'BTCUSDT' and rsi <= 25:
            confianca = min(95, 50 + (25 - rsi) * 2)
            return 'HOLD_BTC', confianca
        
        return 'AGUARDAR', 50.0

    def ciclo_hiper_otimizado(self):
        """Ciclo principal otimizado"""
        # Símbolos prioritários (sem ADAUSDT que dá erro)
        simbolos_prioritarios = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        # Portfolio inicial
        valor_total, portfolio = self.get_portfolio_completo()
        usdt_disponivel = portfolio.get('USDT', {}).get('free', 0)
        
        # Status do portfolio
        if valor_total > self.valor_inicial:
            status = f"📈 LUCRO: +${valor_total - self.valor_inicial:.2f} (+{((valor_total/self.valor_inicial)-1)*100:.2f}%)"
            logger.info(status)
        else:
            status = f"📉 PREJUÍZO: ${valor_total - self.valor_inicial:.2f} ({((valor_total/self.valor_inicial)-1)*100:.2f}%)"
            logger.warning(status)
            logger.warning("🔥 MODO HIPER-RECUPERAÇÃO ATIVO!")
        
        # Mostrar portfolio
        for asset, info in portfolio.items():
            logger.info(f"   {asset}: {info['total']:.8f} = ${info['valor_usdt']:.2f}")
        
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.2f}")
        
        # Analisar cada símbolo
        acoes_executadas = 0
        
        for symbol in simbolos_prioritarios:
            try:
                # Obter RSI
                candles = self.get_candles(symbol)
                if len(candles) < 5:
                    continue
                
                rsi = self.calcular_rsi(candles)
                acao, confianca = self.analisar_rsi_otimizado(symbol, rsi)
                
                # Log da análise
                if acao != 'AGUARDAR':
                    if acao in ['COMPRA_EMERGENCIAL', 'VENDA_EMERGENCIAL']:
                        logger.info(f"🚨🚨🚨 {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
                    elif acao in ['COMPRA_FORTE', 'VENDA_PARCIAL_BTC']:
                        logger.info(f"🔥🔥 {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
                    else:
                        logger.info(f"⚡ {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
                else:
                    logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
                
                # Executar ações apenas se confiança for alta
                if confianca < self.confianca_minima:
                    continue
                
                # VENDA PARCIAL DO BTC - Estratégia para ter USDT
                if acao == 'VENDA_PARCIAL_BTC' and 'BTC' in portfolio:
                    quantidade_btc = portfolio['BTC']['free']
                    if quantidade_btc > 0:
                        # Calcular quantidade a vender (50% ou quantidade viável)
                        quantidade_vender = quantidade_btc * 0.5
                        min_btc = self.min_quantities['BTCUSDT']
                        
                        if quantidade_vender < min_btc and quantidade_btc >= min_btc:
                            quantidade_vender = min_btc
                        
                        preco_btc_atual = self.get_preco_atual('BTCUSDT')
                        valor_estimado = quantidade_vender * preco_btc_atual
                        
                        if valor_estimado >= self.min_notional and quantidade_vender >= min_btc:
                            logger.warning(f"💰 BTC RSI {rsi:.1f} - GERANDO USDT!")
                            logger.info(f"   📊 Vendendo: {quantidade_vender:.8f} BTC (${valor_estimado:.2f})")
                            
                            resultado = self.executar_venda_btc_parcial(quantidade_vender)
                            if resultado:
                                acoes_executadas += 1
                                # Recalcular USDT após venda
                                valor_total_novo, portfolio_novo = self.get_portfolio_completo()
                                usdt_disponivel = portfolio_novo.get('USDT', {}).get('free', 0)
                                logger.info(f"💵 NOVO USDT disponível: ${usdt_disponivel:.2f}")
                        else:
                            logger.warning("⚠️ Venda BTC não viável - valor/quantidade muito baixo")
                
                # COMPRA EMERGENCIAL - RSI baixo
                elif acao in ['COMPRA_EMERGENCIAL', 'COMPRA_FORTE'] and usdt_disponivel >= 5.0:
                    logger.warning(f"🚨 RSI HIPER-BAIXO: {rsi:.1f} em {symbol}!")
                    logger.warning("⚡ COMPRA HIPER-AGRESSIVA COM TODO CAPITAL!")
                    
                    resultado = self.compra_emergencial_total(symbol, usdt_disponivel)
                    if resultado:
                        acoes_executadas += 1
                        usdt_disponivel = 0
                        break
                
                # VENDA EMERGENCIAL - RSI alto  
                elif acao == 'VENDA_EMERGENCIAL':
                    asset = symbol.replace('USDT', '')
                    if asset in portfolio and portfolio[asset]['free'] > 0:
                        logger.warning(f"💸 RSI HIPER-ALTO: {rsi:.1f}!")
                        logger.warning("🚨 VENDA TOTAL PARA LUCRO MÁXIMO!")
                        
                        resultado = self.vender_tudo_disponivel(asset, portfolio)
                        if resultado:
                            acoes_executadas += 1
                            # Recalcular após venda
                            valor_total_novo, portfolio_novo = self.get_portfolio_completo()
                            usdt_disponivel = portfolio_novo.get('USDT', {}).get('free', 0)
                            logger.info(f"💵 NOVO USDT: ${usdt_disponivel:.2f}")
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        if acoes_executadas > 0:
            logger.info(f"⚡ {acoes_executadas} ação(ões) HIPER-AGRESSIVA(S) executada(s)!")
        else:
            logger.info("📊 Aguardando oportunidade hiper-agressiva...")
        
        return valor_total, acoes_executadas

    def executar_sistema_hiper_otimizado(self):
        """Sistema principal hiper-otimizado"""
        logger.info("🚀 === SISTEMA HIPER-OTIMIZADO ATIVADO ===")
        logger.info("⚡ OBJETIVO: MÁXIMA PERFORMANCE E LUCROS")
        logger.info("🔥 ESTRATÉGIA: RSI OTIMIZADO + ALTA FREQUÊNCIA")
        logger.info("=" * 60)
        
        # Portfolio inicial
        self.valor_inicial, _ = self.get_portfolio_completo()
        self.meta_recuperacao = self.valor_inicial * 1.05  # +5%
        
        logger.info(f"💼 Portfolio inicial: ${self.valor_inicial:.2f}")
        logger.warning(f"🎯 Meta: +5% = ${self.meta_recuperacao:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO HIPER-OTIMIZADO {ciclo} ===")
                
                valor_atual, acoes = self.ciclo_hiper_otimizado()
                
                # Verificar se atingiu a meta
                if valor_atual >= self.meta_recuperacao:
                    lucro = valor_atual - self.valor_inicial
                    percentual = ((valor_atual / self.valor_inicial) - 1) * 100
                    logger.info("🎉 === META ATINGIDA! ===")
                    logger.info(f"🏆 Portfolio final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro total: +${lucro:.2f} (+{percentual:.2f}%)")
                    logger.info("🎯 Sistema hiper-otimizado FINALIZADO COM SUCESSO!")
                    break
                
                # Próximo ciclo mais rápido
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema interrompido")
        except Exception as e:
            logger.error(f"❌ Erro no sistema: {e}")
        finally:
            # Resultado final
            valor_final, _ = self.get_portfolio_completo()
            logger.info("🏆 === RESULTADO HIPER-OTIMIZADO ===")
            logger.info(f"💼 Inicial: ${self.valor_inicial:.2f}")
            logger.info(f"💼 Final: ${valor_final:.2f}")
            
            if valor_final > self.valor_inicial:
                lucro = valor_final - self.valor_inicial
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO: +${lucro:.2f} (+{percentual:.2f}%)")
            else:
                prejuizo = self.valor_inicial - valor_final
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.warning(f"📉 Resultado: -${prejuizo:.2f} ({percentual:.2f}%)")

def main():
    """Função principal"""
    logger.info("🔧 Carregando configuração...")
    
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
            logger.error("❌ Chaves da API não encontradas no .env")
            return
        
        # Criar e executar sistema
        sistema = TradingHiperOtimizado(api_key, api_secret, "AMOS_HIPER_OTIMIZADO")
        sistema.executar_sistema_hiper_otimizado()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()