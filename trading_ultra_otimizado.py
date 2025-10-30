"""
🛡️ SISTEMA ULTRA-OTIMIZADO - VALORES CORRETOS
Ajustes: Valores mínimos corretos para $17.47 USDT
FOCO: ETH e SOL (menores valores mínimos que BTC)
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
import sys
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Logging otimizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_ultra_otimizado.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaUltraOtimizado:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO OTIMIZADA PARA SEU SALDO
        self.rsi_compra = 30              # RSI para compra
        self.rsi_venda_rapida = 45        # Venda rápida
        self.rsi_venda_normal = 55        # Venda normal
        self.ciclo_tempo = 8              # Ciclos de 8s
        
        # PARÂMETROS AJUSTADOS PARA $17.47
        self.config_otimizada = {
            'percentual_trade': 0.25,         # 25% do capital por trade (mais agressivo)
            'reserva_usdt': 0.5,             # $0.5 de reserva (menor)
            'valor_minimo_trade': 2.5,       # Mínimo $2.5 (menor para seu saldo)
            'max_tentativas_conexao': 8,     # Tentativas conexão
            'timeout_conexao': 25,           # Timeout otimizado
            'delay_retry': 4,                # Delay menor
        }
        
        # ATIVOS OTIMIZADOS PARA SEU CAPITAL
        self.ativos_otimizados = {
            'ETHUSDT': {'min_valor': 2.5, 'peso': 0.50, 'step_size': 0.0001, 'prioridade': 1}, 
            'SOLUSDT': {'min_valor': 2.5, 'peso': 0.35, 'step_size': 0.01, 'prioridade': 2},
            'BTCUSDT': {'min_valor': 8.0, 'peso': 0.15, 'step_size': 0.00001, 'prioridade': 3},  # Valor maior
        }
        
        # Controle otimizado
        self.trades_ativos = {}
        self.historico_operacoes = []
        self.capital_inicial = 0
        self.lucro_consolidado = 0
        self.vendas_executadas = 0
        self.compras_executadas = 0
        self.erros_conexao = 0
        self.ultima_conexao_ok = time.time()
        
        # Configurar session
        self.session = self.configurar_session_resistente()
        
        logger.info("🛡️ === SISTEMA ULTRA-OTIMIZADO ATIVADO ===")
        logger.info("🎯 FOCO: ETH + SOL (valores mínimos menores)")
        logger.info("💰 OTIMIZADO PARA: $17.47 USDT")
        logger.info("=" * 80)
        logger.info(f"🔥 RSI: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda_rapida}")
        logger.info(f"💵 Trade: {self.config_otimizada['percentual_trade']*100}% | Mín: ${self.config_otimizada['valor_minimo_trade']}")
        logger.info(f"⏱️ Ciclos: {self.ciclo_tempo}s | Timeout: {self.config_otimizada['timeout_conexao']}s")
        logger.info("🎯 PRIORIDADES: ETH > SOL > BTC")
        logger.info("=" * 80)
    
    def configurar_session_resistente(self):
        """Configurar session HTTP resistente"""
        session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1.5,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers otimizados
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def verificar_conectividade(self):
        """Verificar conectividade básica"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                self.ultima_conexao_ok = time.time()
                self.erros_conexao = 0
                return True
        except Exception as e:
            self.erros_conexao += 1
            logger.warning(f"⚠️ Conectividade: {e}")
        
        return False
    
    def get_server_time_otimizado(self):
        """Timestamp otimizado"""
        try:
            if self.verificar_conectividade():
                response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
                if response.status_code == 200:
                    return response.json()['serverTime']
        except Exception as e:
            logger.warning(f"Timestamp local: {e}")
        
        return int(time.time() * 1000)
    
    def fazer_requisicao_otimizada(self, method, endpoint, params=None, signed=False):
        """Requisição otimizada"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_server_time_otimizado()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Estratégia otimizada
        for tentativa in range(self.config_otimizada['max_tentativas_conexao']):
            try:
                if method == 'GET':
                    r = self.session.get(url, params=params, headers=headers, 
                                       timeout=self.config_otimizada['timeout_conexao'])
                else:
                    r = self.session.post(url, params=params, headers=headers, 
                                        timeout=self.config_otimizada['timeout_conexao'])
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    error_msg = error_data.get('msg', r.text)
                    
                    # Erros que não devem repetir
                    if any(code in error_msg for code in ['insufficient balance', 'MIN_NOTIONAL', 'NOTIONAL', '-2010']):
                        logger.warning(f"❌ Erro Binance: {error_msg}")
                        return {'error': True, 'code': error_data.get('code'), 'msg': error_msg}
                else:
                    logger.warning(f"HTTP {r.status_code} (tent {tentativa+1})")
                
            except Exception as e:
                logger.warning(f"Erro req (tent {tentativa+1}): {e}")
            
            if tentativa < self.config_otimizada['max_tentativas_conexao'] - 1:
                time.sleep(self.config_otimizada['delay_retry'])
        
        return {'error': True, 'msg': 'Falha de conectividade'}
    
    def get_account_info_otimizada(self):
        """Info da conta otimizada"""
        return self.fazer_requisicao_otimizada('GET', '/api/v3/account', signed=True)
    
    def get_preco_atual_otimizado(self, symbol):
        """Preço otimizado"""
        try:
            r = self.session.get(f"{BASE_URL}/api/v3/ticker/price", 
                               params={'symbol': symbol}, timeout=12)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception as e:
            logger.warning(f"Erro preço {symbol}: {e}")
        
        return 0
    
    def get_klines_otimizadas(self, symbol, limit=8):
        """Klines otimizadas"""
        try:
            params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
            r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=12)
            if r.status_code == 200:
                return [float(k[4]) for k in r.json()]
        except Exception as e:
            logger.warning(f"Erro klines {symbol}: {e}")
        
        return []
    
    def calcular_rsi_otimizado(self, precos, periodo=5):
        """RSI otimizado"""
        if len(precos) < periodo + 1:
            return 50
        
        deltas = np.diff(precos)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-periodo:])
        avg_loss = np.mean(losses[-periodo:])
        
        if avg_loss == 0:
            return 100
        if avg_gain == 0:
            return 0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_portfolio_otimizado(self):
        """Portfolio otimizado"""
        conta = self.get_account_info_otimizada()
        if conta.get('error'):
            logger.error(f"❌ Erro conta: {conta.get('msg')}")
            return 0, {}, 0
        
        portfolio = {}
        usdt_livre = 0
        valor_total = 0
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    usdt_livre = free
                    valor_usdt = total
                else:
                    symbol = f"{asset}USDT"
                    preco = self.get_preco_atual_otimizado(symbol)
                    valor_usdt = total * preco
                
                if valor_usdt >= 0.01:
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt,
                        'preco_atual': preco if asset != 'USDT' else 1.0
                    }
                    valor_total += valor_usdt
        
        return usdt_livre, portfolio, valor_total
    
    def calcular_valor_trade_otimizado(self, symbol, usdt_disponivel):
        """Cálculo otimizado para seu saldo"""
        config = self.ativos_otimizados.get(symbol, {'peso': 0.2, 'min_valor': 2.5})
        
        # Verificar USDT suficiente
        if usdt_disponivel < self.config_otimizada['valor_minimo_trade']:
            return 0
        
        # Valor baseado no percentual
        valor_ideal = usdt_disponivel * self.config_otimizada['percentual_trade'] * config['peso']
        
        # Garantir valor mínimo
        valor_minimo = config['min_valor']
        
        # Verificar se pode fazer trade
        if valor_ideal < valor_minimo:
            if usdt_disponivel >= valor_minimo + self.config_otimizada['reserva_usdt']:
                valor_final = valor_minimo
            else:
                logger.info(f"💡 {symbol}: USDT ${usdt_disponivel:.2f} < mín ${valor_minimo:.2f}")
                return 0
        else:
            valor_final = valor_ideal
        
        # Verificar reserva
        if usdt_disponivel - valor_final < self.config_otimizada['reserva_usdt']:
            valor_final = usdt_disponivel - self.config_otimizada['reserva_usdt']
            if valor_final < valor_minimo:
                return 0
        
        logger.info(f"💰 {symbol}: ${valor_final:.2f} (USDT: ${usdt_disponivel:.2f})")
        return valor_final
    
    def executar_compra_otimizada(self, symbol, rsi, usdt_disponivel):
        """Compra otimizada"""
        valor_trade = self.calcular_valor_trade_otimizado(symbol, usdt_disponivel)
        
        if valor_trade <= 0:
            return False
        
        logger.warning(f"🚨 COMPRA OTIMIZADA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_trade:.2f}")
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_trade:.2f}"
        }
        
        resultado = self.fazer_requisicao_otimizada('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            msg = resultado.get('msg', 'Erro desconhecido')
            logger.error(f"❌ Erro compra {symbol}: {msg}")
            
            # Se for NOTIONAL, tentar com valor maior
            if 'NOTIONAL' in msg and valor_trade < 10:
                logger.info(f"🔄 Tentando {symbol} com valor maior...")
                novo_valor = min(10.0, usdt_disponivel - 1.0)
                if novo_valor >= 5.0:
                    params['quoteOrderQty'] = f"{novo_valor:.2f}"
                    resultado2 = self.fazer_requisicao_otimizada('POST', '/api/v3/order', params, signed=True)
                    if not resultado2.get('error'):
                        valor_trade = novo_valor
                        resultado = resultado2
                        logger.info(f"✅ Sucesso com ${novo_valor:.2f}")
                    else:
                        return False
                else:
                    return False
            else:
                return False
        
        # Registrar trade
        self.trades_ativos[symbol] = {
            'timestamp': time.time(),
            'valor_investido': valor_trade,
            'rsi_entrada': rsi
        }
        
        self.compras_executadas += 1
        logger.info(f"✅ COMPRA: ${valor_trade:.2f}")
        return True
    
    def executar_venda_otimizada(self, symbol, rsi, portfolio):
        """Venda otimizada"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        info_asset = portfolio[asset]
        quantidade_livre = info_asset['free']
        valor_atual = info_asset['valor_usdt']
        
        if quantidade_livre <= 0 or valor_atual < 1.0:
            return False
        
        # Calcular lucro
        trade_info = self.trades_ativos.get(symbol)
        lucro_estimado = 0
        
        if trade_info:
            lucro_estimado = valor_atual - trade_info['valor_investido']
        
        logger.warning(f"🚨 VENDA OTIMIZADA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | ${valor_atual:.2f}")
        if trade_info:
            logger.warning(f"   📈 Lucro: ${lucro_estimado:.3f}")
        
        # Formatação quantidade
        if asset == 'BTC':
            qty = f"{quantidade_livre:.5f}"
        elif asset == 'ETH':
            qty = f"{quantidade_livre:.4f}"
        else:
            qty = f"{quantidade_livre:.2f}"
        
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': qty
        }
        
        resultado = self.fazer_requisicao_otimizada('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda {symbol}: {resultado.get('msg')}")
            return False
        
        logger.info(f"✅ VENDA: ~${valor_atual:.2f} → USDT")
        
        if trade_info:
            logger.info(f"🎉 LUCRO: ${lucro_estimado:.3f}")
            self.lucro_consolidado += lucro_estimado
            del self.trades_ativos[symbol]
        
        self.vendas_executadas += 1
        return True
    
    def analisar_oportunidade_otimizada(self, symbol, rsi, portfolio, usdt_livre):
        """Análise otimizada por prioridade"""
        asset = symbol.replace('USDT', '')
        config = self.ativos_otimizados.get(symbol, {})
        
        # PRIORIDADE 1: VENDA (se tem posição)
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor = portfolio[asset]['valor_usdt']
            
            if rsi >= self.rsi_venda_rapida:
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA | ${valor:.2f}")
                return self.executar_venda_otimizada(symbol, rsi, portfolio)
            elif rsi >= self.rsi_venda_normal:
                logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_NORMAL | ${valor:.2f}")
                return self.executar_venda_otimizada(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRA (se RSI favorável)
        elif rsi <= self.rsi_compra:
            # Verificar se tem capital suficiente
            valor_necessario = self.calcular_valor_trade_otimizado(symbol, usdt_livre)
            
            if valor_necessario > 0:
                prioridade = config.get('prioridade', 99)
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | P{prioridade} | ${valor_necessario:.2f}")
                return self.executar_compra_otimizada(symbol, rsi, usdt_livre)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, capital limitado")
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDANDO")
        
        return False
    
    def ciclo_otimizado(self):
        """Ciclo principal otimizado"""
        # Portfolio
        usdt_livre, portfolio, valor_total = self.get_portfolio_otimizado()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Status
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO: +${lucro:.3f} (+{percentual:.3f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        # Posições ativas
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f}")
        
        # Análise por prioridade
        operacoes = 0
        simbolos_ordenados = sorted(self.ativos_otimizados.items(), 
                                   key=lambda x: x[1].get('prioridade', 99))
        
        for symbol, config in simbolos_ordenados:
            try:
                klines = self.get_klines_otimizadas(symbol)
                if len(klines) < 4:
                    continue
                
                rsi = self.calcular_rsi_otimizado(klines)
                
                if self.analisar_oportunidade_otimizada(symbol, rsi, portfolio, usdt_livre):
                    operacoes += 1
                    time.sleep(2)  # Pausa entre operações
                
            except Exception as e:
                logger.error(f"❌ Erro {symbol}: {e}")
                continue
        
        logger.info(f"🔄 Ciclo: {operacoes} operações")
        return valor_total, operacoes
    
    def executar_sistema_otimizado(self):
        """Sistema principal otimizado"""
        logger.info("🛡️ === SISTEMA ULTRA-OTIMIZADO INICIADO ===")
        logger.info("🎯 FOCO: ETH + SOL (menores valores mínimos)")
        logger.info("💰 CAPITAL: $17.47 USDT")
        logger.info("=" * 80)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_otimizado()
        self.capital_inicial = valor_inicial
        
        if valor_inicial == 0:
            logger.error("❌ Erro capital inicial")
            return
        
        meta = valor_inicial * 1.015  # +1.5% (meta mais realista)
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +1.5% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO OTIMIZADO {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_otimizado()
                
                if valor_atual == 0:
                    time.sleep(self.ciclo_tempo * 2)
                    continue
                
                # Verificar meta
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.3f}%)")
                    break
                
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            # Resultado final
            try:
                _, _, valor_final = self.get_portfolio_otimizado()
                
                logger.info("🏆 === RESULTADO OTIMIZADO ===")
                logger.info(f"💼 Inicial: ${self.capital_inicial:.2f}")
                logger.info(f"💼 Final: ${valor_final:.2f}")
                
                if valor_final > self.capital_inicial:
                    lucro = valor_final - self.capital_inicial
                    perc = ((valor_final / self.capital_inicial) - 1) * 100
                    logger.info(f"🎉 LUCRO: +${lucro:.3f} (+{perc:.3f}%)")
                
                logger.info(f"📊 Operações: {self.compras_executadas + self.vendas_executadas}")
            except:
                pass

def main():
    """Executar sistema otimizado"""
    logger.info("🔧 Iniciando Sistema Ultra-Otimizado...")
    
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
        
        sistema = SistemaUltraOtimizado(api_key, api_secret)
        sistema.executar_sistema_otimizado()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()