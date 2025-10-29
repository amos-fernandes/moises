"""
SISTEMA ULTRA-CONSERVADOR - APENAS USDT
Trabalha exclusivamente com USDT disponível para evitar erros de saldo
ESTRATÉGIA: Compra pequena → Venda rápida → Lucro micro
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
        logging.FileHandler('trading_ultra_conservador.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingUltraConservador:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS ULTRA-CONSERVADORES AJUSTADOS
        self.rsi_compra_extrema = 30         # Mais acessível
        self.rsi_venda_rapida = 55           # Vende rapidamente
        self.valor_minimo_trade = 1.0        # $1.0 mínimo (mais realista)
        self.ciclo_tempo = 15                # Ciclos muito rápidos
        
        # CONFIGURAÇÃO SEGURA AJUSTADA
        self.config_segura = {
            'usar_apenas_usdt': True,         # SÓ trabalha com USDT
            'percentual_trade': 0.85,         # Usa 85% do USDT (menos conservador)
            'margem_seguranca': 0.3,          # Deixa $0.3 sempre (menor margem)
            'verificar_saldo_real': True      # Verifica saldo antes de cada trade
        }
        
        # Filtros mínimos
        self.min_quantities = {
            'BTCUSDT': 0.00001,     
            'ETHUSDT': 0.0001,      
            'SOLUSDT': 0.01,        
        }
        
        # Cache e controle
        self.precos_cache = {}
        self.ultimo_trade = {'timestamp': 0, 'symbol': '', 'tipo': ''}
        self.trades_hoje = []
        self.valor_inicial = 0
        
        logger.info(f"🎯 Sistema ULTRA-CONSERVADOR - {conta_nome}")
        logger.info("=" * 60)
        logger.info("💰 MODO APENAS USDT - ZERO ERROS!")
        logger.info("🔥 ESTRATÉGIA ULTRA-SEGURA:")
        logger.info(f"   🎯 RSI {self.rsi_compra_extrema}/{self.rsi_venda_rapida} (extremos)")
        logger.info(f"   💵 Mínimo: ${self.valor_minimo_trade} USDT apenas")
        logger.info(f"   🛡️ Margem: ${self.config_segura['margem_seguranca']} USDT sempre")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (ultra-rápido)")
        logger.info("   ⚡ FOCO: COMPRAR → VENDER → LUCRAR!")
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

    def get_candles(self, symbol: str, limit: int = 8):
        """Obter candles - PERÍODO MÍNIMO"""
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
    
    def calcular_rsi(self, prices, period=5):
        """Calcular RSI - PERÍODO MÍNIMO"""
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
        
        return self.precos_cache.get(symbol, 0)
    
    def get_usdt_disponivel(self):
        """Obter USDT disponível REAL"""
        info = self.get_account_info()
        if info.get('error'):
            return 0
        
        for balance in info.get('balances', []):
            if balance['asset'] == 'USDT':
                free = float(balance['free'])
                logger.info(f"💵 USDT real disponível: ${free:.3f}")
                return free
        
        return 0
    
    def get_portfolio_completo(self):
        """Portfolio completo para monitoramento"""
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
                
                if valor_usdt > 0.001:
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total += valor_usdt
        
        return valor_total, portfolio
    
    def pode_executar_compra(self, symbol, valor_usdt):
        """Verificar se pode executar compra"""
        usdt_real = self.get_usdt_disponivel()
        
        # Verificar se tem USDT suficiente (mínimo $5 para evitar erro NOTIONAL)
        if usdt_real < 5.0:
            logger.warning(f"⚠️ USDT insuficiente: ${usdt_real:.3f} < $5.0 (mín. Binance)")
            return False, 0
        
        # Calcular valor seguro para compra
        valor_seguro = min(
            usdt_real - self.config_segura['margem_seguranca'],  # Deixa margem
            usdt_real * self.config_segura['percentual_trade']   # Usa 85%
        )
        
        if valor_seguro < 5.0:
            logger.warning(f"⚠️ Valor seguro insuficiente: ${valor_seguro:.3f} < $5.0")
            return False, 0
        
        return True, valor_seguro
    
    def executar_compra_conservadora(self, symbol, rsi):
        """Executar compra ultra-conservadora"""
        pode, valor_compra = self.pode_executar_compra(symbol, 0)
        
        if not pode:
            return False
        
        logger.warning(f"🚨 COMPRA CONSERVADORA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (EXTREMO)")
        logger.warning(f"   💰 Valor: ${valor_compra:.3f}")
        
        try:
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_compra:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra {symbol}: {resultado.get('detail')}")
                return False
            
            logger.info(f"✅ COMPRA EXECUTADA!")
            logger.info(f"   💰 Investido: ${valor_compra:.3f}")
            
            # Registrar trade
            self.ultimo_trade = {
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'COMPRA',
                'valor': valor_compra
            }
            
            self.trades_hoje.append(self.ultimo_trade.copy())
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução compra: {e}")
            return False
    
    def pode_executar_venda(self, symbol):
        """Verificar se pode executar venda"""
        # Verificar se fez compra recente deste símbolo
        if (self.ultimo_trade.get('symbol') == symbol and 
            self.ultimo_trade.get('tipo') == 'COMPRA' and
            time.time() - self.ultimo_trade.get('timestamp', 0) < 300):  # 5 minutos
            
            # Obter saldo atual do ativo
            info = self.get_account_info()
            if info.get('error'):
                return False, 0
            
            asset = symbol.replace('USDT', '')
            
            for balance in info.get('balances', []):
                if balance['asset'] == asset:
                    quantidade = float(balance['free'])
                    if quantidade > 0:
                        preco = self.get_preco_atual(symbol)
                        valor = quantidade * preco
                        return True, quantidade
            
        return False, 0
    
    def executar_venda_rapida(self, symbol, rsi):
        """Executar venda rápida"""
        pode, quantidade = self.pode_executar_venda(symbol)
        
        if not pode:
            logger.info(f"⏳ {symbol}: Aguardando compra ou sem saldo para venda")
            return False
        
        logger.warning(f"🚨 VENDA RÁPIDA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (LUCRO)")
        logger.warning(f"   🔢 Quantidade: {quantidade:.8f}")
        
        try:
            # Formatação baseada no ativo
            asset = symbol.replace('USDT', '')
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
            
            # Registrar trade
            self.ultimo_trade = {
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'VENDA',
                'valor': 0
            }
            
            self.trades_hoje.append(self.ultimo_trade.copy())
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução venda: {e}")
            return False

    def analisar_oportunidade(self, symbol, rsi):
        """Analisar oportunidade conservadora"""
        # PRIORIDADE 1: VENDA se temos o ativo (mesmo com RSI baixo)
        asset = symbol.replace('USDT', '')
        pode_vender, _ = self.pode_executar_venda(symbol)
        
        if pode_vender and rsi >= 40:  # Vende com RSI mais baixo para garantir lucro
            confianca = min(90, 50 + (rsi - 40) * 2)
            logger.info(f"� {symbol}: RSI {rsi:.1f} | VENDA_LUCRO | Conf: {confianca:.1f}%")
            return self.executar_venda_rapida(symbol, rsi)
        
        # PRIORIDADE 2: COMPRA apenas se tem USDT suficiente e RSI extremo
        elif rsi <= self.rsi_compra_extrema:
            usdt_disponivel = self.get_usdt_disponivel()
            
            # Só compra se tem pelo menos $5 USDT (valor mínimo Binance)
            if usdt_disponivel >= 5.0:
                confianca = min(95, 50 + (self.rsi_compra_extrema - rsi) * 4)
                logger.info(f"� {symbol}: RSI {rsi:.1f} | COMPRA_EXTREMA | Conf: {confianca:.1f}%")
                return self.executar_compra_conservadora(symbol, rsi)
            else:
                logger.warning(f"⚠️ {symbol}: RSI {rsi:.1f} extremo, mas USDT insuficiente: ${usdt_disponivel:.3f}")
        
        # AGUARDAR em outros casos
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDAR")
        
        return False

    def ciclo_conservador(self):
        """Ciclo principal conservador"""
        simbolos = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        # Portfolio atual
        valor_total, portfolio = self.get_portfolio_completo()
        usdt_disponivel = self.get_usdt_disponivel()
        
        # Status
        if valor_total > self.valor_inicial:
            lucro = valor_total - self.valor_inicial
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.info(f"📈 LUCRO: +${lucro:.3f} (+{percentual:.2f}%)")
        else:
            prejuizo = self.valor_inicial - valor_total
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.warning(f"📉 PREJUÍZO: -${prejuizo:.3f} ({percentual:.2f}%)")
        
        # Portfolio resumido
        for asset, info in portfolio.items():
            if info['valor_usdt'] > 0.01:
                logger.info(f"   {asset}: ${info['valor_usdt']:.3f}")
        
        logger.info(f"💵 USDT disponível: ${usdt_disponivel:.3f}")
        
        # Último trade
        if self.ultimo_trade.get('timestamp', 0) > 0:
            tempo_desde = time.time() - self.ultimo_trade['timestamp']
            logger.info(f"⏱️ Último: {self.ultimo_trade['tipo']} {self.ultimo_trade['symbol']} ({tempo_desde:.0f}s atrás)")
        
        # Analisar símbolos
        trades_executados = 0
        
        for symbol in simbolos:
            try:
                candles = self.get_candles(symbol)
                if len(candles) < 3:
                    continue
                
                rsi = self.calcular_rsi(candles)
                
                if self.analisar_oportunidade(symbol, rsi):
                    trades_executados += 1
                    time.sleep(2)  # Pausa entre trades
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        logger.info(f"📊 Trades executados: {trades_executados}")
        logger.info(f"📈 Total trades hoje: {len(self.trades_hoje)}")
        
        return valor_total, trades_executados

    def executar_sistema_conservador(self):
        """Sistema principal conservador"""
        logger.info("🎯 === SISTEMA ULTRA-CONSERVADOR ATIVADO ===")
        logger.info("💰 OBJETIVO: APENAS USDT → COMPRA → VENDA → LUCRO")
        logger.info("🛡️ ESTRATÉGIA: ZERO ERROS + LUCROS PEQUENOS")
        logger.info("=" * 60)
        
        # Portfolio inicial
        self.valor_inicial, _ = self.get_portfolio_completo()
        meta_conservadora = self.valor_inicial * 1.01  # +1% (ultra realista)
        
        logger.info(f"💼 Portfolio inicial: ${self.valor_inicial:.3f}")
        logger.warning(f"🎯 Meta conservadora: +1% = ${meta_conservadora:.3f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO CONSERVADOR {ciclo} ===")
                
                valor_atual, trades = self.ciclo_conservador()
                
                # Verificar meta ultra-baixa
                if valor_atual >= meta_conservadora:
                    lucro = valor_atual - self.valor_inicial
                    percentual = ((valor_atual / self.valor_inicial) - 1) * 100
                    logger.info("🎉 === META CONSERVADORA ATINGIDA! ===")
                    logger.info(f"🏆 Portfolio final: ${valor_atual:.3f}")
                    logger.info(f"💰 Lucro: +${lucro:.3f} (+{percentual:.2f}%)")
                    break
                
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema conservador interrompido")
        except Exception as e:
            logger.error(f"❌ Erro no sistema: {e}")
        finally:
            valor_final, _ = self.get_portfolio_completo()
            logger.info("🏆 === RESULTADO CONSERVADOR ===")
            logger.info(f"💼 Inicial: ${self.valor_inicial:.3f}")
            logger.info(f"💼 Final: ${valor_final:.3f}")
            
            if valor_final > self.valor_inicial:
                lucro = valor_final - self.valor_inicial
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO: +${lucro:.3f} (+{percentual:.2f}%)")

def main():
    """Função principal"""
    logger.info("🔧 Carregando configuração ultra-conservadora...")
    
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
        sistema = TradingUltraConservador(api_key, api_secret, "AMOS_CONSERVADOR")
        sistema.executar_sistema_conservador()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()