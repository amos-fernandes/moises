"""
SISTEMA CONSOLIDADOR DE LUCROS - SOLUÇÃO PARA PEQUENOS VALORES
Agrupa múltiplas oportunidades em trades maiores e viáveis
ESTRATÉGIA: Acumular sinais + Executar em lote quando viável
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
        logging.FileHandler('trading_consolidador_lucros.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingConsolidadorLucros:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS CONSOLIDADORES PARA LUCROS MÁXIMOS
        self.rsi_compra_agressiva = 30       
        self.rsi_venda_agressiva = 70        
        self.confianca_minima = 60           
        self.target_consolidado = 1.5        # Target menor mas mais frequente
        self.stop_loss_rapido = 0.8          # Stop menor para preservar capital
        self.ciclo_tempo = 25                # Ciclos ainda mais rápidos
        
        # SISTEMA DE CONSOLIDAÇÃO - CHAVE DA SOLUÇÃO
        self.acumulador_oportunidades = {
            'compras_pendentes': [],
            'vendas_pendentes': [],
            'valor_minimo_trade': 12.0,      # $12 mínimo por trade
            'max_acumulacao': 5,             # Máximo 5 oportunidades por lote
            'timeout_acumulacao': 300        # 5 minutos para acumular
        }
        
        # Filtros mínimos da Binance
        self.min_quantities = {
            'BTCUSDT': 0.00001,     
            'ETHUSDT': 0.0001,      
            'SOLUSDT': 0.01,        
        }
        self.min_notional = 10.0    
        
        # Cache de preços
        self.precos_cache = {}
        
        # Controle de recuperação
        self.trades_recuperacao = []
        self.valor_inicial = 0
        self.meta_recuperacao = 0
        
        logger.info(f"🎯 Sistema CONSOLIDADOR DE LUCROS - {conta_nome}")
        logger.info("=" * 60)
        logger.info("💰 MODO ACUMULAÇÃO E EXECUÇÃO INTELIGENTE!")
        logger.info("🔥 ESTRATÉGIA CONSOLIDADORA:")
        logger.info(f"   🎯 RSI < {self.rsi_compra_agressiva} = ACUMULAR COMPRA")
        logger.info(f"   💸 RSI > {self.rsi_venda_agressiva} = ACUMULAR VENDA")
        logger.info(f"   📦 Valor mínimo: ${self.acumulador_oportunidades['valor_minimo_trade']}")
        logger.info(f"   🎲 Target: {self.target_consolidado}% (frequente)")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (alta velocidade)")
        logger.info("   ⚡ AGRUPA PEQUENOS = GRANDES LUCROS!")
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

    def get_candles(self, symbol: str, limit: int = 12):
        """Obter candles - ULTRA RÁPIDO"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=2)
            if r.status_code != 200:
                return []
            
            candles = []
            for kline in r.json():
                candles.append(float(kline[4]))  # close price
            
            return candles
        except Exception as e:
            logger.error(f"Erro candles {symbol}: {e}")
            return []
    
    def calcular_rsi(self, prices, period=8):
        """Calcular RSI - PERÍODO ULTRA SENSÍVEL"""
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
        """Obter preço atual"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=2)
            if r.status_code == 200:
                preco = float(r.json()['price'])
                self.precos_cache[symbol] = preco
                return preco
        except:
            pass
        
        return self.precos_cache.get(symbol, {
            'BTCUSDT': 113000,
            'ETHUSDT': 3988,
            'SOLUSDT': 250
        }.get(symbol, 100))
    
    def get_portfolio_completo(self):
        """Portfolio completo"""
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
                
                if valor_usdt > 0.01:
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total += valor_usdt
        
        return valor_total, portfolio
    
    def adicionar_oportunidade_compra(self, symbol, rsi, confianca, valor_estimado):
        """SISTEMA DE ACUMULAÇÃO - COMPRAS"""
        oportunidade = {
            'symbol': symbol,
            'tipo': 'COMPRA',
            'rsi': rsi,
            'confianca': confianca,
            'valor': valor_estimado,
            'timestamp': time.time()
        }
        
        self.acumulador_oportunidades['compras_pendentes'].append(oportunidade)
        
        logger.info(f"📦 ACUMULANDO COMPRA: {symbol} RSI {rsi:.1f} - ${valor_estimado:.2f}")
        logger.info(f"   🎯 Total acumulado: {len(self.acumulador_oportunidades['compras_pendentes'])} oportunidades")
        
        return self.verificar_execucao_lote('COMPRA')
    
    def adicionar_oportunidade_venda(self, symbol, rsi, confianca, portfolio):
        """SISTEMA DE ACUMULAÇÃO - VENDAS"""
        asset = symbol.replace('USDT', '')
        if asset not in portfolio:
            return False
            
        valor_estimado = portfolio[asset]['valor_usdt']
        
        oportunidade = {
            'symbol': symbol,
            'asset': asset,
            'tipo': 'VENDA',
            'rsi': rsi,
            'confianca': confianca,
            'valor': valor_estimado,
            'quantidade': portfolio[asset]['free'],
            'timestamp': time.time()
        }
        
        self.acumulador_oportunidades['vendas_pendentes'].append(oportunidade)
        
        logger.info(f"📦 ACUMULANDO VENDA: {symbol} RSI {rsi:.1f} - ${valor_estimado:.2f}")
        logger.info(f"   🎯 Total acumulado: {len(self.acumulador_oportunidades['vendas_pendentes'])} oportunidades")
        
        return self.verificar_execucao_lote('VENDA')
    
    def verificar_execucao_lote(self, tipo):
        """VERIFICA SE PODE EXECUTAR UM LOTE"""
        lista = self.acumulador_oportunidades[f'{tipo.lower()}s_pendentes']
        
        if not lista:
            return False
        
        # Calcular valor total acumulado
        valor_total = sum(op['valor'] for op in lista)
        
        # Limpar oportunidades muito antigas
        agora = time.time()
        timeout = self.acumulador_oportunidades['timeout_acumulacao']
        lista[:] = [op for op in lista if agora - op['timestamp'] < timeout]
        
        # Verificar se deve executar
        deve_executar = (
            valor_total >= self.acumulador_oportunidades['valor_minimo_trade'] or
            len(lista) >= self.acumulador_oportunidades['max_acumulacao'] or
            (lista and agora - lista[0]['timestamp'] > timeout * 0.8)
        )
        
        if deve_executar:
            logger.warning(f"🚀 EXECUTANDO LOTE {tipo}!")
            logger.warning(f"   💰 Valor total: ${valor_total:.2f}")
            logger.warning(f"   📊 Oportunidades: {len(lista)}")
            
            if tipo == 'COMPRA':
                return self.executar_lote_compras(lista)
            else:
                return self.executar_lote_vendas(lista)
        
        return False
    
    def executar_lote_compras(self, lista_compras):
        """EXECUTA LOTE DE COMPRAS CONSOLIDADO"""
        if not lista_compras:
            return False
        
        # Escolher o símbolo com maior confiança
        melhor_op = max(lista_compras, key=lambda x: x['confianca'])
        symbol = melhor_op['symbol']
        
        # Calcular capital total disponível
        _, portfolio = self.get_portfolio_completo()
        usdt_disponivel = portfolio.get('USDT', {}).get('free', 0)
        
        if usdt_disponivel < 5.0:
            logger.warning("⚠️ USDT insuficiente para lote de compras")
            self.acumulador_oportunidades['compras_pendentes'].clear()
            return False
        
        # Usar 90% do USDT disponível
        valor_compra = usdt_disponivel * 0.90
        
        logger.warning(f"🚨 COMPRA CONSOLIDADA: {symbol}")
        logger.warning(f"   💰 Valor: ${valor_compra:.2f}")
        logger.warning(f"   🎯 RSI médio: {np.mean([op['rsi'] for op in lista_compras]):.1f}")
        
        try:
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_compra:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra consolidada: {resultado.get('detail')}")
                return False
            
            logger.info(f"✅ COMPRA CONSOLIDADA EXECUTADA!")
            logger.info(f"   💰 Valor investido: ${valor_compra:.2f}")
            
            # Limpar lista após execução
            self.acumulador_oportunidades['compras_pendentes'].clear()
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução lote compra: {e}")
            return False
    
    def executar_lote_vendas(self, lista_vendas):
        """EXECUTA LOTE DE VENDAS CONSOLIDADO"""
        if not lista_vendas:
            return False
        
        trades_executados = 0
        valor_total_vendido = 0
        
        # Executar todas as vendas do lote
        for venda in lista_vendas:
            symbol = venda['symbol']
            asset = venda['asset']
            quantidade = venda['quantidade']
            
            # Verificar se ainda tem o ativo
            _, portfolio_atual = self.get_portfolio_completo()
            if asset not in portfolio_atual:
                continue
                
            quantidade_atual = portfolio_atual[asset]['free']
            if quantidade_atual < self.min_quantities.get(symbol, 0.001):
                continue
            
            logger.warning(f"🚨 VENDA CONSOLIDADA: {symbol}")
            logger.warning(f"   📊 Quantidade: {quantidade_atual}")
            logger.warning(f"   💰 Valor estimado: ${venda['valor']:.2f}")
            
            try:
                # Formatação correta baseada no ativo
                if asset == 'BTC':
                    quantidade_str = f"{quantidade_atual:.5f}"
                elif asset == 'ETH':
                    quantidade_str = f"{quantidade_atual:.4f}"
                else:
                    quantidade_str = f"{quantidade_atual:.2f}"
                
                params = {
                    'symbol': symbol,
                    'side': 'SELL',
                    'type': 'MARKET',
                    'quantity': quantidade_str
                }
                
                resultado = self._request('POST', '/api/v3/order', params, signed=True)
                
                if resultado.get('error'):
                    logger.error(f"❌ Erro venda {symbol}: {resultado.get('detail')}")
                    continue
                
                valor_total_vendido += venda['valor']
                trades_executados += 1
                
                logger.info(f"✅ VENDA {symbol} EXECUTADA!")
                
            except Exception as e:
                logger.error(f"❌ Erro venda {symbol}: {e}")
                continue
        
        if trades_executados > 0:
            logger.info(f"🎉 LOTE DE VENDAS CONCLUÍDO!")
            logger.info(f"   📊 Trades: {trades_executados}")
            logger.info(f"   💰 Valor total: ${valor_total_vendido:.2f}")
            
        # Limpar lista após execução
        self.acumulador_oportunidades['vendas_pendentes'].clear()
        return trades_executados > 0
    
    def analisar_rsi_consolidado(self, symbol, rsi, portfolio, usdt_disponivel):
        """Análise RSI com sistema de consolidação"""
        confianca = 50.0
        
        # COMPRA CONSOLIDADA
        if rsi <= self.rsi_compra_agressiva:
            confianca = min(95, 50 + (self.rsi_compra_agressiva - rsi) * 3)
            
            if confianca >= self.confianca_minima:
                logger.info(f"🔥🔥 {symbol}: RSI {rsi:.1f} | COMPRA_CONSOLIDADA | Conf: {confianca:.1f}%")
                return self.adicionar_oportunidade_compra(symbol, rsi, confianca, usdt_disponivel)
        
        # VENDA CONSOLIDADA
        elif rsi >= self.rsi_venda_agressiva:
            confianca = min(95, 50 + (rsi - self.rsi_venda_agressiva) * 3)
            
            if confianca >= self.confianca_minima:
                logger.info(f"🚨🚨🚨 {symbol}: RSI {rsi:.1f} | VENDA_CONSOLIDADA | Conf: {confianca:.1f}%")
                return self.adicionar_oportunidade_venda(symbol, rsi, confianca, portfolio)
        
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDAR | Conf: {confianca:.1f}%")
        
        return False

    def ciclo_consolidador(self):
        """Ciclo principal consolidador"""
        simbolos_prioritarios = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        # Portfolio atual
        valor_total, portfolio = self.get_portfolio_completo()
        usdt_disponivel = portfolio.get('USDT', {}).get('free', 0)
        
        # Status
        if valor_total > self.valor_inicial:
            status = f"📈 LUCRO: +${valor_total - self.valor_inicial:.2f} (+{((valor_total/self.valor_inicial)-1)*100:.2f}%)"
            logger.info(status)
        else:
            status = f"📉 PREJUÍZO: ${valor_total - self.valor_inicial:.2f} ({((valor_total/self.valor_inicial)-1)*100:.2f}%)"
            logger.warning(status)
            logger.warning("🔥 MODO CONSOLIDAÇÃO ATIVO!")
        
        # Portfolio
        for asset, info in portfolio.items():
            logger.info(f"   {asset}: {info['total']:.8f} = ${info['valor_usdt']:.2f}")
        
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.2f}")
        
        # Status do acumulador
        compras_acum = len(self.acumulador_oportunidades['compras_pendentes'])
        vendas_acum = len(self.acumulador_oportunidades['vendas_pendentes'])
        
        if compras_acum > 0 or vendas_acum > 0:
            logger.info(f"📦 ACUMULADOR: {compras_acum} compras, {vendas_acum} vendas pendentes")
        
        # Analisar símbolos
        trades_executados = 0
        
        for symbol in simbolos_prioritarios:
            try:
                candles = self.get_candles(symbol)
                if len(candles) < 5:
                    continue
                
                rsi = self.calcular_rsi(candles)
                
                if self.analisar_rsi_consolidado(symbol, rsi, portfolio, usdt_disponivel):
                    trades_executados += 1
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        # Verificar execuções pendentes por timeout
        self.verificar_execucao_lote('COMPRA')
        self.verificar_execucao_lote('VENDA')
        
        if trades_executados > 0:
            logger.info(f"⚡ {trades_executados} lote(s) CONSOLIDADO(S) executado(s)!")
        else:
            logger.info("📊 Acumulando oportunidades para próximo lote...")
        
        return valor_total, trades_executados

    def executar_sistema_consolidador(self):
        """Sistema principal consolidador"""
        logger.info("🎯 === SISTEMA CONSOLIDADOR ATIVADO ===")
        logger.info("💰 OBJETIVO: AGREGAR PEQUENOS EM GRANDES LUCROS")
        logger.info("🔥 ESTRATÉGIA: ACUMULAÇÃO + EXECUÇÃO INTELIGENTE")
        logger.info("=" * 60)
        
        # Portfolio inicial
        self.valor_inicial, _ = self.get_portfolio_completo()
        self.meta_recuperacao = self.valor_inicial * 1.03  # +3% (mais realista)
        
        logger.info(f"💼 Portfolio inicial: ${self.valor_inicial:.2f}")
        logger.warning(f"🎯 Meta: +3% = ${self.meta_recuperacao:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO CONSOLIDADOR {ciclo} ===")
                
                valor_atual, trades = self.ciclo_consolidador()
                
                # Verificar meta
                if valor_atual >= self.meta_recuperacao:
                    lucro = valor_atual - self.valor_inicial
                    percentual = ((valor_atual / self.valor_inicial) - 1) * 100
                    logger.info("🎉 === META ATINGIDA! ===")
                    logger.info(f"🏆 Portfolio final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro total: +${lucro:.2f} (+{percentual:.2f}%)")
                    break
                
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema consolidador interrompido")
        except Exception as e:
            logger.error(f"❌ Erro no sistema: {e}")
        finally:
            valor_final, _ = self.get_portfolio_completo()
            logger.info("🏆 === RESULTADO CONSOLIDADOR ===")
            logger.info(f"💼 Inicial: ${self.valor_inicial:.2f}")
            logger.info(f"💼 Final: ${valor_final:.2f}")
            
            if valor_final > self.valor_inicial:
                lucro = valor_final - self.valor_inicial
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO: +${lucro:.2f} (+{percentual:.2f}%)")

def main():
    """Função principal"""
    logger.info("🔧 Carregando configuração consolidadora...")
    
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
        sistema = TradingConsolidadorLucros(api_key, api_secret, "AMOS_CONSOLIDADOR")
        sistema.executar_sistema_consolidador()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()