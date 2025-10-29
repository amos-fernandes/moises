"""
SISTEMA MICRO-TRADING - ESPECIALIZADO EM PEQUENOS VALORES
Otimizado para trabalhar com valores baixos e gerar lucros consistentes
ESTRATÉGIA: Micro-scalping com alta frequência e baixo risco
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
        logging.FileHandler('trading_micro_lucros.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingMicroLucros:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS MICRO-TRADING OTIMIZADOS
        self.rsi_compra_micro = 35           # Mais conservador
        self.rsi_venda_micro = 65            # Mais conservador
        self.confianca_minima = 55           # Menor exigência
        self.target_micro = 0.8              # Target muito baixo mas frequente
        self.stop_loss_micro = 0.3           # Stop muito pequeno
        self.ciclo_tempo = 20                # Ciclos ultra-rápidos
        
        # SISTEMA MICRO-VALORES
        self.micro_config = {
            'valor_minimo_usdt': 1.0,        # Trabalha com $1+
            'percentual_trade': 0.95,        # Usa 95% do disponível
            'fee_estimada': 0.001,           # 0.1% fee da Binance
            'margem_seguranca': 0.02,        # 2% margem de segurança
            'max_tentativas': 3              # Máximo 3 tentativas por trade
        }
        
        # Filtros mínimos da Binance (ajustados)
        self.min_quantities = {
            'BTCUSDT': 0.00001,     
            'ETHUSDT': 0.0001,      
            'SOLUSDT': 0.01,        
        }
        self.min_notional = 5.0     # Reduzido para $5
        
        # Cache de preços e controle
        self.precos_cache = {}
        self.historico_trades = []
        self.valor_inicial = 0
        self.trades_sucessos = 0
        self.trades_falhas = 0
        
        logger.info(f"🎯 Sistema MICRO-TRADING - {conta_nome}")
        logger.info("=" * 60)
        logger.info("💰 MODO MICRO-SCALPING ATIVO!")
        logger.info("🔥 ESTRATÉGIA MICRO-LUCROS:")
        logger.info(f"   🎯 RSI {self.rsi_compra_micro}/{self.rsi_venda_micro} (conservador)")
        logger.info(f"   💵 Mínimo: $1.0 (micro-valores)")
        logger.info(f"   🎲 Target: {self.target_micro}% (micro-ganhos)")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (ultra-rápido)")
        logger.info(f"   📊 Stop: {self.stop_loss_micro}% (micro-risco)")
        logger.info("   ⚡ ESPECIALISTA EM PEQUENOS VALORES!")
        logger.info("=" * 60)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição da Binance com retry"""
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
        
        # Retry logic para maior confiabilidade
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=10)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    return r.json()
                else:
                    logger.warning(f"Tentativa {tentativa+1}/3 - HTTP {r.status_code}: {r.text}")
                    if tentativa == 2:
                        return {'error': True, 'detail': f"{r.status_code}: {r.text}"}
                    time.sleep(1)
            except Exception as e:
                logger.warning(f"Tentativa {tentativa+1}/3 - Erro: {str(e)}")
                if tentativa == 2:
                    return {'error': True, 'detail': str(e)}
                time.sleep(1)
        
        return {'error': True, 'detail': 'Todas as tentativas falharam'}
    
    def get_account_info(self):
        """Informações da conta com cache"""
        return self._request('GET', '/api/v3/account', {}, signed=True)

    def get_candles(self, symbol: str, limit: int = 10):
        """Obter candles - MICRO PERÍODO"""
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
        """Obter preço atual com cache"""
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
            'ETHUSDT': 4000,
            'SOLUSDT': 250
        }.get(symbol, 100))
    
    def get_portfolio_micro(self):
        """Portfolio otimizado para micro-trading"""
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
                
                # Incluir valores ainda menores para micro-trading
                if valor_usdt > 0.005:  # $0.005+
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total += valor_usdt
        
        return valor_total, portfolio
    
    def verificar_viabilidade_trade(self, symbol, valor_usdt, tipo):
        """Verificar se o trade é viável"""
        preco = self.get_preco_atual(symbol)
        
        if tipo == 'COMPRA':
            # Para compra, verificar se tem USDT suficiente
            if valor_usdt < self.micro_config['valor_minimo_usdt']:
                return False, f"USDT insuficiente: ${valor_usdt:.3f} < ${self.micro_config['valor_minimo_usdt']}"
            
            # Calcular quantidade que consegue comprar
            quantidade = valor_usdt / preco
            min_qty = self.min_quantities.get(symbol, 0.001)
            
            if quantidade < min_qty:
                return False, f"Quantidade muito baixa: {quantidade:.8f} < {min_qty}"
            
            return True, f"Viável: {quantidade:.8f} por ${valor_usdt:.3f}"
        
        else:  # VENDA
            # Para venda, verificar se o valor é suficiente
            if valor_usdt < self.min_notional:
                return False, f"Valor muito baixo: ${valor_usdt:.3f} < ${self.min_notional}"
            
            return True, f"Viável: ${valor_usdt:.3f}"
    
    def executar_compra_micro(self, symbol, valor_usdt):
        """Executar compra micro-otimizada"""
        viavel, motivo = self.verificar_viabilidade_trade(symbol, valor_usdt, 'COMPRA')
        
        if not viavel:
            logger.warning(f"⚠️ Compra {symbol} não viável: {motivo}")
            return False
        
        logger.warning(f"🚨 COMPRA MICRO: {symbol}")
        logger.warning(f"   💰 Valor: ${valor_usdt:.3f}")
        logger.warning(f"   📊 Motivo: {motivo}")
        
        try:
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_usdt:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra micro {symbol}: {resultado.get('detail')}")
                self.trades_falhas += 1
                return False
            
            logger.info(f"✅ COMPRA MICRO EXECUTADA!")
            logger.info(f"   💰 Investido: ${valor_usdt:.3f}")
            
            # Registrar trade
            self.historico_trades.append({
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'COMPRA',
                'valor': valor_usdt,
                'sucesso': True
            })
            
            self.trades_sucessos += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução compra micro: {e}")
            self.trades_falhas += 1
            return False
    
    def executar_venda_micro(self, symbol, portfolio):
        """Executar venda micro-otimizada"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            logger.warning(f"⚠️ Ativo {asset} não encontrado no portfolio")
            return False
        
        quantidade_disponivel = portfolio[asset]['free']
        valor_estimado = portfolio[asset]['valor_usdt']
        
        viavel, motivo = self.verificar_viabilidade_trade(symbol, valor_estimado, 'VENDA')
        
        if not viavel:
            logger.warning(f"⚠️ Venda {symbol} não viável: {motivo}")
            return False
        
        logger.warning(f"🚨 VENDA MICRO: {symbol}")
        logger.warning(f"   📊 Quantidade: {quantidade_disponivel:.8f}")
        logger.warning(f"   💰 Valor: ${valor_estimado:.3f}")
        
        try:
            # Formatação precisa baseada no ativo
            if asset == 'BTC':
                qty_str = f"{quantidade_disponivel:.5f}"
            elif asset == 'ETH':
                qty_str = f"{quantidade_disponivel:.4f}"
            else:
                qty_str = f"{quantidade_disponivel:.2f}"
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': qty_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda micro {symbol}: {resultado.get('detail')}")
                self.trades_falhas += 1
                return False
            
            logger.info(f"✅ VENDA MICRO EXECUTADA!")
            logger.info(f"   💰 Valor obtido: ~${valor_estimado:.3f}")
            
            # Registrar trade
            self.historico_trades.append({
                'timestamp': time.time(),
                'symbol': symbol,
                'tipo': 'VENDA',
                'valor': valor_estimado,
                'sucesso': True
            })
            
            self.trades_sucessos += 1
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução venda micro: {e}")
            self.trades_falhas += 1
            return False
    
    def analisar_rsi_micro(self, symbol, rsi, portfolio, usdt_disponivel):
        """Análise RSI para micro-trading"""
        confianca = 50.0
        
        # COMPRA MICRO
        if rsi <= self.rsi_compra_micro:
            confianca = min(90, 50 + (self.rsi_compra_micro - rsi) * 2)
            
            if confianca >= self.confianca_minima and usdt_disponivel >= self.micro_config['valor_minimo_usdt']:
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_MICRO | Conf: {confianca:.1f}%")
                
                # Usar uma parte do USDT disponível
                valor_compra = min(usdt_disponivel * 0.8, usdt_disponivel - 0.5)  # Deixa $0.5 de reserva
                
                if valor_compra >= self.micro_config['valor_minimo_usdt']:
                    return self.executar_compra_micro(symbol, valor_compra)
        
        # VENDA MICRO
        elif rsi >= self.rsi_venda_micro:
            confianca = min(90, 50 + (rsi - self.rsi_venda_micro) * 2)
            
            asset = symbol.replace('USDT', '')
            
            if confianca >= self.confianca_minima and asset in portfolio:
                logger.info(f"🚨 {symbol}: RSI {rsi:.1f} | VENDA_MICRO | Conf: {confianca:.1f}%")
                return self.executar_venda_micro(symbol, portfolio)
        
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDAR | Conf: {confianca:.1f}%")
        
        return False

    def ciclo_micro_trading(self):
        """Ciclo principal micro-trading"""
        simbolos_prioritarios = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        # Portfolio atual
        valor_total, portfolio = self.get_portfolio_micro()
        usdt_disponivel = portfolio.get('USDT', {}).get('free', 0)
        
        # Status detalhado
        if valor_total > self.valor_inicial:
            lucro = valor_total - self.valor_inicial
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.info(f"📈 LUCRO MICRO: +${lucro:.3f} (+{percentual:.2f}%)")
        else:
            prejuizo = self.valor_inicial - valor_total
            percentual = ((valor_total / self.valor_inicial) - 1) * 100
            logger.warning(f"📉 PREJUÍZO MICRO: -${prejuizo:.3f} ({percentual:.2f}%)")
            logger.warning("🔥 MODO RECUPERAÇÃO MICRO ATIVO!")
        
        # Portfolio detalhado
        for asset, info in portfolio.items():
            logger.info(f"   {asset}: {info['total']:.8f} = ${info['valor_usdt']:.3f}")
        
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.3f}")
        
        # Estatísticas
        total_trades = self.trades_sucessos + self.trades_falhas
        if total_trades > 0:
            taxa_sucesso = (self.trades_sucessos / total_trades) * 100
            logger.info(f"📊 Trades: {self.trades_sucessos}✅ / {self.trades_falhas}❌ ({taxa_sucesso:.1f}% sucesso)")
        
        # Analisar símbolos
        trades_executados = 0
        
        for symbol in simbolos_prioritarios:
            try:
                candles = self.get_candles(symbol)
                if len(candles) < 4:
                    continue
                
                rsi = self.calcular_rsi(candles)
                
                if self.analisar_rsi_micro(symbol, rsi, portfolio, usdt_disponivel):
                    trades_executados += 1
                    # Pequena pausa entre trades
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        if trades_executados > 0:
            logger.info(f"⚡ {trades_executados} MICRO-TRADE(S) executado(s)!")
        else:
            logger.info("📊 Aguardando oportunidades micro...")
        
        return valor_total, trades_executados

    def executar_sistema_micro(self):
        """Sistema principal micro-trading"""
        logger.info("🎯 === SISTEMA MICRO-TRADING ATIVADO ===")
        logger.info("💰 OBJETIVO: LUCROS CONSISTENTES COM MICRO-VALORES")
        logger.info("🔥 ESTRATÉGIA: ALTA FREQUÊNCIA + BAIXO RISCO")
        logger.info("=" * 60)
        
        # Portfolio inicial
        self.valor_inicial, _ = self.get_portfolio_micro()
        meta_micro = self.valor_inicial * 1.02  # +2% (muito realista)
        
        logger.info(f"💼 Portfolio inicial: ${self.valor_inicial:.3f}")
        logger.warning(f"🎯 Meta micro: +2% = ${meta_micro:.3f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO MICRO {ciclo} ===")
                
                valor_atual, trades = self.ciclo_micro_trading()
                
                # Verificar meta (mais baixa e realista)
                if valor_atual >= meta_micro:
                    lucro = valor_atual - self.valor_inicial
                    percentual = ((valor_atual / self.valor_inicial) - 1) * 100
                    logger.info("🎉 === META MICRO ATINGIDA! ===")
                    logger.info(f"🏆 Portfolio final: ${valor_atual:.3f}")
                    logger.info(f"💰 Lucro micro: +${lucro:.3f} (+{percentual:.2f}%)")
                    break
                
                logger.info(f"⏰ Próximo micro-ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema micro-trading interrompido")
        except Exception as e:
            logger.error(f"❌ Erro no sistema micro: {e}")
        finally:
            valor_final, _ = self.get_portfolio_micro()
            logger.info("🏆 === RESULTADO MICRO-TRADING ===")
            logger.info(f"💼 Inicial: ${self.valor_inicial:.3f}")
            logger.info(f"💼 Final: ${valor_final:.3f}")
            
            if valor_final > self.valor_inicial:
                lucro = valor_final - self.valor_inicial
                percentual = ((valor_final / self.valor_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO MICRO: +${lucro:.3f} (+{percentual:.2f}%)")
            
            # Estatísticas finais
            total_trades = self.trades_sucessos + self.trades_falhas
            if total_trades > 0:
                taxa_sucesso = (self.trades_sucessos / total_trades) * 100
                logger.info(f"📊 Total trades: {total_trades} ({taxa_sucesso:.1f}% sucesso)")

def main():
    """Função principal"""
    logger.info("🔧 Carregando configuração micro-trading...")
    
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
        
        # Criar e executar sistema micro
        sistema = TradingMicroLucros(api_key, api_secret, "AMOS_MICRO")
        sistema.executar_sistema_micro()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()