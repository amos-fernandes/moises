"""
ESTRATÉGIA COMPLETA USDT - MÁXIMA EFICIÊNCIA
Sistema inteligente para trabalhar com todo capital USDT disponível
FOCO: Compra inteligente → Venda rápida → Reinvestimento automático
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
        logging.FileHandler('trading_estrategia_completa.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class EstrategiaCompletaUST:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS ESTRATÉGIA COMPLETA
        self.rsi_compra_forte = 35           # Compra em RSI baixo
        self.rsi_venda_lucro = 50            # Vende mais cedo para lucro rápido
        self.rsi_venda_emergencia = 65       # Venda emergencial
        self.ciclo_tempo = 12                # Ciclos super rápidos
        
        # CONFIGURAÇÃO INTELIGENTE
        self.config_inteligente = {
            'capital_inicial': 0,             # Será calculado automaticamente
            'percentual_por_trade': 0.3,     # 30% do capital por trade
            'reserva_emergencia': 0.1,       # 10% sempre em USDT
            'lucro_minimo': 0.005,           # 0.5% mínimo por trade
            'max_perdas_consecutivas': 3,    # Máximo 3 perdas seguidas
        }
        
        # DIVERSIFICAÇÃO INTELIGENTE
        self.simbolos_prioritarios = {
            'BTCUSDT': {'peso': 0.4, 'min_valor': 6.0},    # 40% - Bitcoin (mín $6)
            'ETHUSDT': {'peso': 0.35, 'min_valor': 5.0},   # 35% - Ethereum (mín $5)
            'SOLUSDT': {'peso': 0.25, 'min_valor': 5.0},   # 25% - Solana (mín $5)
        }
        
        # Filtros Binance
        self.min_quantities = {
            'BTCUSDT': 0.00001,     
            'ETHUSDT': 0.0001,      
            'SOLUSDT': 0.01,        
        }
        
        # Controle e cache
        self.precos_cache = {}
        self.trades_ativos = {}  # Controla trades em andamento
        self.historico_completo = []
        self.perdas_consecutivas = 0
        self.valor_inicial = 0
        self.lucro_acumulado = 0
        
        logger.info(f"🎯 ESTRATÉGIA COMPLETA USDT - {conta_nome}")
        logger.info("=" * 70)
        logger.info("💰 MODO CAPITAL TOTAL - MÁXIMA EFICIÊNCIA!")
        logger.info("🔥 ESTRATÉGIA INTELIGENTE:")
        logger.info(f"   🎯 RSI Compra: ≤{self.rsi_compra_forte} | Venda: ≥{self.rsi_venda_lucro}")
        logger.info(f"   💵 Por trade: {self.config_inteligente['percentual_por_trade']*100}% do capital")
        logger.info(f"   🛡️ Reserva: {self.config_inteligente['reserva_emergencia']*100}% sempre em USDT")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (ultra-rápido)")
        logger.info("   🎲 DIVERSIFICAÇÃO: BTC 40% | ETH 35% | SOL 25%")
        logger.info("   ⚡ FOCO: LUCROS RÁPIDOS + REINVESTIMENTO!")
        logger.info("=" * 70)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição Binance com retry"""
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
        
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=10)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    return r.json()
                else:
                    if tentativa == 2:
                        logger.error(f"Erro HTTP {r.status_code}: {r.text}")
                        return {'error': True, 'detail': f"{r.status_code}: {r.text}"}
                    time.sleep(1)
            except Exception as e:
                if tentativa == 2:
                    logger.error(f"Erro requisição: {e}")
                    return {'error': True, 'detail': str(e)}
                time.sleep(1)
        
        return {'error': True, 'detail': 'Falha em todas tentativas'}
    
    def get_account_info(self):
        """Informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)

    def get_candles(self, symbol: str, limit: int = 8):
        """Obter candles rápidos"""
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
    
    def calcular_rsi(self, prices, period=6):
        """RSI ultra sensível"""
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
        """Preço atual com cache"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=2)
            if r.status_code == 200:
                preco = float(r.json()['price'])
                self.precos_cache[symbol] = preco
                return preco
        except:
            pass
        
        return self.precos_cache.get(symbol, 0)
    
    def get_capital_disponivel(self):
        """Capital USDT disponível"""
        info = self.get_account_info()
        if info.get('error'):
            return 0, {}
        
        portfolio = {}
        usdt_total = 0
        valor_total = 0
        
        for balance in info.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    usdt_total = total
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
        
        return usdt_total, portfolio
    
    def calcular_valor_trade(self, symbol, usdt_disponivel):
        """Calcular valor ideal para trade"""
        config_symbol = self.simbolos_prioritarios.get(symbol, {'peso': 0.2, 'min_valor': 5.0})
        
        # Valor baseado no peso e percentual configurado
        valor_ideal = usdt_disponivel * self.config_inteligente['percentual_por_trade'] * config_symbol['peso']
        
        # Garantir valor mínimo
        valor_minimo = max(config_symbol['min_valor'], 5.0)
        
        if valor_ideal < valor_minimo:
            # Se valor ideal é muito baixo, usar mínimo se possível
            if usdt_disponivel >= valor_minimo + 1.0:  # +$1 margem
                return valor_minimo
            else:
                return 0  # Não fazer trade
        
        return valor_ideal
    
    def executar_compra_inteligente(self, symbol, rsi, usdt_disponivel):
        """Compra inteligente com gestão de capital"""
        valor_trade = self.calcular_valor_trade(symbol, usdt_disponivel)
        
        if valor_trade < 5.0:
            logger.warning(f"⚠️ {symbol}: Valor insuficiente para trade: ${valor_trade:.2f}")
            return False
        
        logger.warning(f"🚨 COMPRA INTELIGENTE: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (OPORTUNIDADE)")
        logger.warning(f"   💰 Valor: ${valor_trade:.2f}")
        logger.warning(f"   📈 Capital total: ${usdt_disponivel:.2f}")
        
        try:
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_trade:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra {symbol}: {resultado.get('detail')}")
                self.perdas_consecutivas += 1
                return False
            
            logger.info(f"✅ COMPRA EXECUTADA!")
            logger.info(f"   💰 Investido: ${valor_trade:.2f}")
            
            # Registrar trade ativo
            self.trades_ativos[symbol] = {
                'timestamp': time.time(),
                'tipo': 'COMPRA',
                'valor_investido': valor_trade,
                'rsi_entrada': rsi
            }
            
            self.historico_completo.append({
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'COMPRA',
                'valor': valor_trade,
                'rsi': rsi,
                'sucesso': True
            })
            
            self.perdas_consecutivas = 0
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução compra: {e}")
            self.perdas_consecutivas += 1
            return False
    
    def executar_venda_inteligente(self, symbol, rsi, portfolio):
        """Venda inteligente com controle de lucro"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        quantidade = portfolio[asset]['free']
        valor_atual = portfolio[asset]['valor_usdt']
        
        if quantidade <= 0 or valor_atual < 1.0:
            return False
        
        # Verificar se é um trade nosso
        trade_info = self.trades_ativos.get(symbol)
        
        lucro_esperado = 0
        if trade_info:
            lucro_esperado = valor_atual - trade_info['valor_investido']
            tempo_trade = time.time() - trade_info['timestamp']
        
        logger.warning(f"🚨 VENDA INTELIGENTE: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (LUCRO)")
        logger.warning(f"   💰 Valor atual: ${valor_atual:.2f}")
        if trade_info:
            logger.warning(f"   📈 Lucro estimado: ${lucro_esperado:.3f}")
        
        try:
            # Formatação baseada no ativo
            if asset == 'BTC':
                qty_str = f"{quantidade:.5f}"
            elif asset == 'ETH':
                qty_str = f"{quantidade:.4f}"
            else:
                qty_str = f"{quantidade:.2f}"
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': qty_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda {symbol}: {resultado.get('detail')}")
                return False
            
            logger.info(f"✅ VENDA EXECUTADA!")
            logger.info(f"   💰 Valor obtido: ~${valor_atual:.2f}")
            
            if trade_info:
                logger.info(f"   📊 Lucro realizado: ${lucro_esperado:.3f}")
                self.lucro_acumulado += lucro_esperado
                
                # Remover trade ativo
                del self.trades_ativos[symbol]
            
            self.historico_completo.append({
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'VENDA',
                'valor': valor_atual,
                'rsi': rsi,
                'lucro': lucro_esperado,
                'sucesso': True
            })
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução venda: {e}")
            return False
    
    def analisar_oportunidade_inteligente(self, symbol, rsi, portfolio, usdt_disponivel):
        """Análise inteligente de oportunidades"""
        asset = symbol.replace('USDT', '')
        
        # PRIORIDADE 1: VENDA se temos o ativo
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor_ativo = portfolio[asset]['valor_usdt']
            
            # Venda rápida para lucro (RSI mais baixo)
            if rsi >= self.rsi_venda_lucro:
                confianca = min(95, 50 + (rsi - self.rsi_venda_lucro) * 3)
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA_LUCRO | Conf: {confianca:.1f}% | Valor: ${valor_ativo:.2f}")
                return self.executar_venda_inteligente(symbol, rsi, portfolio)
            
            # Venda emergencial
            elif rsi >= self.rsi_venda_emergencia:
                logger.warning(f"🚨 {symbol}: RSI {rsi:.1f} | VENDA_EMERGENCIAL | Valor: ${valor_ativo:.2f}")
                return self.executar_venda_inteligente(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRA se RSI favorável e capital suficiente
        elif rsi <= self.rsi_compra_forte:
            # Verificar se não estamos com muitas perdas consecutivas
            if self.perdas_consecutivas >= self.config_inteligente['max_perdas_consecutivas']:
                logger.warning(f"⚠️ {symbol}: RSI {rsi:.1f} favorável, mas pausado por perdas consecutivas ({self.perdas_consecutivas})")
                return False
            
            valor_necessario = self.calcular_valor_trade(symbol, usdt_disponivel)
            
            if valor_necessario >= 5.0:
                confianca = min(95, 50 + (self.rsi_compra_forte - rsi) * 3)
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_INTELIGENTE | Conf: {confianca:.1f}% | Valor: ${valor_necessario:.2f}")
                return self.executar_compra_inteligente(symbol, rsi, usdt_disponivel)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, mas capital insuficiente")
        
        # AGUARDAR em outros casos
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDAR")
        
        return False

    def ciclo_estrategia_completa(self):
        """Ciclo principal da estratégia"""
        # Capital disponível
        usdt_disponivel, portfolio = self.get_capital_disponivel()
        valor_total = sum(info['valor_usdt'] for info in portfolio.values())
        
        # Status
        if valor_total > self.valor_inicial:
            lucro = valor_total - self.valor_inicial
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro:.3f} (+{percentual:.2f}%)")
        else:
            prejuizo = self.valor_inicial - valor_total
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.warning(f"📉 PREJUÍZO TOTAL: -${prejuizo:.3f} ({percentual:.2f}%)")
        
        # Portfolio atual
        logger.info(f"💼 Capital total: ${valor_total:.2f}")
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.2f}")
        
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                logger.info(f"   {asset}: ${info['valor_usdt']:.2f}")
        
        # Trades ativos
        if self.trades_ativos:
            logger.info(f"⚡ Trades ativos: {len(self.trades_ativos)}")
        
        # Estatísticas
        if self.historico_completo:
            sucessos = sum(1 for t in self.historico_completo if t['sucesso'])
            taxa_sucesso = (sucessos / len(self.historico_completo)) * 100
            logger.info(f"📊 Trades hoje: {len(self.historico_completo)} ({taxa_sucesso:.1f}% sucesso)")
        
        # Analisar símbolos
        trades_executados = 0
        
        for symbol in self.simbolos_prioritarios.keys():
            try:
                candles = self.get_candles(symbol)
                if len(candles) < 4:
                    continue
                
                rsi = self.calcular_rsi(candles)
                
                if self.analisar_oportunidade_inteligente(symbol, rsi, portfolio, usdt_disponivel):
                    trades_executados += 1
                    time.sleep(1)  # Pequena pausa
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        logger.info(f"📊 Ciclo concluído: {trades_executados} trades executados")
        
        return valor_total, trades_executados

    def executar_estrategia_completa(self):
        """Sistema principal da estratégia"""
        logger.info("🎯 === ESTRATÉGIA COMPLETA USDT ATIVADA ===")
        logger.info("💰 OBJETIVO: MÁXIMA EFICIÊNCIA COM TODO CAPITAL")
        logger.info("🔥 ESTRATÉGIA: COMPRA INTELIGENTE → VENDA RÁPIDA → REINVESTE")
        logger.info("=" * 70)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial = self.get_capital_disponivel()
        self.valor_inicial = sum(info['valor_usdt'] for info in portfolio_inicial.values())
        self.config_inteligente['capital_inicial'] = self.valor_inicial
        
        meta_inteligente = self.valor_inicial * 1.05  # +5% (realista e agressiva)
        
        logger.info(f"💼 Capital inicial: ${self.valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +5% = ${meta_inteligente:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO ESTRATÉGIA {ciclo} ===")
                
                valor_atual, trades = self.ciclo_estrategia_completa()
                
                # Verificar meta
                if valor_atual >= meta_inteligente:
                    lucro = valor_atual - self.valor_inicial
                    percentual = ((valor_atual / self.valor_inicial) - 1) * 100
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro total: +${lucro:.3f} (+{percentual:.2f}%)")
                    break
                
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Estratégia interrompida pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro na estratégia: {e}")
        finally:
            # Resultado final
            usdt_final, portfolio_final = self.get_capital_disponivel()
            valor_final = sum(info['valor_usdt'] for info in portfolio_final.values())
            
            logger.info("🏆 === RESULTADO ESTRATÉGIA COMPLETA ===")
            logger.info(f"💼 Capital inicial: ${self.valor_inicial:.2f}")
            logger.info(f"💼 Capital final: ${valor_final:.2f}")
            
            if valor_final > self.valor_inicial:
                lucro = valor_final - self.valor_inicial
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO: +${lucro:.3f} (+{percentual:.2f}%)")
            
            # Estatísticas finais
            if self.historico_completo:
                sucessos = sum(1 for t in self.historico_completo if t['sucesso'])
                taxa_sucesso = (sucessos / len(self.historico_completo)) * 100
                lucros = [t.get('lucro', 0) for t in self.historico_completo if t.get('lucro')]
                lucro_medio = np.mean(lucros) if lucros else 0
                
                logger.info(f"📊 Total trades: {len(self.historico_completo)}")
                logger.info(f"📈 Taxa sucesso: {taxa_sucesso:.1f}%")
                logger.info(f"💰 Lucro médio: ${lucro_medio:.3f}")

def main():
    """Função principal"""
    logger.info("🔧 Carregando ESTRATÉGIA COMPLETA USDT...")
    
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
        
        # Criar e executar estratégia completa
        estrategia = EstrategiaCompletaUST(api_key, api_secret, "AMOS_ESTRATEGIA_COMPLETA")
        estrategia.executar_estrategia_completa()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()