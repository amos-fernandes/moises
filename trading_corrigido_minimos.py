"""
🛡️ SISTEMA ULTRA-CORRIGIDO - VALORES MÍNIMOS RESPEITADOS
Correção: Não vende se abaixo do valor mínimo da Binance
FOCO: Acumular até valor vendável + ETH/SOL prioritários
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

# Logging otimizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_corrigido_minimos.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaCorrigidoMinimos:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO CORRIGIDA PARA VALORES MÍNIMOS
        self.rsi_compra = 30              
        self.rsi_venda_rapida = 50        
        self.rsi_venda_normal = 60        
        self.ciclo_tempo = 10             # Ciclos mais espaçados
        
        # VALORES MÍNIMOS REAIS DA BINANCE (CORRIGIDOS!)
        self.config_corrigida = {
            'percentual_trade': 0.25,         # 25% do capital
            'reserva_usdt': 0.5,             # $0.5 reserva
            'valor_minimo_trade': 2.5,       # Mínimo para compra
            'timeout_conexao': 25,           
            'delay_retry': 4,                
        }
        
        # ATIVOS COM VALORES MÍNIMOS REAIS
        self.ativos_corrigidos = {
            'ETHUSDT': {'min_venda': 5.0, 'min_compra': 2.5, 'peso': 0.60, 'prioridade': 1}, 
            'SOLUSDT': {'min_venda': 5.0, 'min_compra': 2.5, 'peso': 0.30, 'prioridade': 2},
            'BTCUSDT': {'min_venda': 10.0, 'min_compra': 5.0, 'peso': 0.10, 'prioridade': 3},  # BTC: $10 mín!
        }
        
        # Controle
        self.trades_ativos = {}
        self.capital_inicial = 0
        self.lucro_consolidado = 0
        self.vendas_executadas = 0
        self.compras_executadas = 0
        self.vendas_bloqueadas = 0  # NOVO: contar vendas bloqueadas
        
        # Session
        self.session = requests.Session()
        
        logger.info("🛡️ === SISTEMA CORRIGIDO PARA MÍNIMOS ===")
        logger.info("🚫 CORREÇÃO: Respeita valores mínimos da Binance")
        logger.info("💰 BTC mínimo venda: $10 | ETH/SOL: $5")
        logger.info("🎯 ESTRATÉGIA: Acumular até valor vendável")
        logger.info("=" * 80)
        logger.info(f"🔥 RSI: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda_rapida}")
        logger.info(f"💵 Trade: {self.config_corrigida['percentual_trade']*100}%")
        logger.info("🎯 PRIORIDADES: ETH > SOL > BTC")
        logger.info("=" * 80)
    
    def get_server_time_otimizado(self):
        """Timestamp otimizado"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except Exception:
            pass
        
        return int(time.time() * 1000)
    
    def fazer_requisicao_corrigida(self, method, endpoint, params=None, signed=False):
        """Requisição corrigida"""
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
        
        # Retry simples
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = self.session.get(url, params=params, headers=headers, timeout=self.config_corrigida['timeout_conexao'])
                else:
                    r = self.session.post(url, params=params, headers=headers, timeout=self.config_corrigida['timeout_conexao'])
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    error_msg = error_data.get('msg', r.text)
                    logger.warning(f"❌ Erro Binance: {error_msg}")
                    return {'error': True, 'msg': error_msg}
                else:
                    logger.warning(f"HTTP {r.status_code}")
                
            except Exception as e:
                logger.warning(f"Erro req (tent {tentativa+1}): {e}")
                if tentativa < 2:
                    time.sleep(2)
        
        return {'error': True, 'msg': 'Falha de conectividade'}
    
    def get_account_info_corrigida(self):
        """Info da conta"""
        return self.fazer_requisicao_corrigida('GET', '/api/v3/account', signed=True)
    
    def get_preco_atual(self, symbol):
        """Preço atual"""
        try:
            r = self.session.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=12)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception:
            pass
        return 0
    
    def get_klines(self, symbol, limit=8):
        """Klines"""
        try:
            params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
            r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=12)
            if r.status_code == 200:
                return [float(k[4]) for k in r.json()]
        except Exception:
            pass
        return []
    
    def calcular_rsi(self, precos, periodo=5):
        """RSI"""
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
    
    def get_portfolio_corrigido(self):
        """Portfolio corrigido"""
        conta = self.get_account_info_corrigida()
        if conta.get('error'):
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
                    preco = self.get_preco_atual(symbol)
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
    
    def pode_vender_ativo(self, symbol, valor_usdt):
        """NOVA FUNÇÃO: Verificar se pode vender (acima do mínimo)"""
        config = self.ativos_corrigidos.get(symbol, {'min_venda': 10.0})
        min_venda = config['min_venda']
        
        pode_vender = valor_usdt >= min_venda
        
        if not pode_vender:
            logger.info(f"🚫 {symbol}: ${valor_usdt:.3f} < ${min_venda} (mín venda)")
        
        return pode_vender
    
    def calcular_valor_compra(self, symbol, usdt_disponivel):
        """Cálculo para compras"""
        config = self.ativos_corrigidos.get(symbol, {'peso': 0.2, 'min_compra': 2.5})
        
        if usdt_disponivel < config['min_compra']:
            return 0
        
        valor_ideal = usdt_disponivel * self.config_corrigida['percentual_trade'] * config['peso']
        valor_minimo = config['min_compra']
        
        if valor_ideal < valor_minimo:
            if usdt_disponivel >= valor_minimo + self.config_corrigida['reserva_usdt']:
                return valor_minimo
            else:
                return 0
        else:
            valor_final = valor_ideal
        
        # Verificar reserva
        if usdt_disponivel - valor_final < self.config_corrigida['reserva_usdt']:
            valor_final = usdt_disponivel - self.config_corrigida['reserva_usdt']
            if valor_final < valor_minimo:
                return 0
        
        return valor_final
    
    def executar_compra_corrigida(self, symbol, rsi, usdt_disponivel):
        """Compra corrigida"""
        valor_trade = self.calcular_valor_compra(symbol, usdt_disponivel)
        
        if valor_trade <= 0:
            return False
        
        logger.warning(f"🚨 COMPRA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | ${valor_trade:.2f}")
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_trade:.2f}"
        }
        
        resultado = self.fazer_requisicao_corrigida('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra {symbol}: {resultado.get('msg')}")
            return False
        
        # Registrar
        self.trades_ativos[symbol] = {
            'timestamp': time.time(),
            'valor_investido': valor_trade,
            'rsi_entrada': rsi
        }
        
        self.compras_executadas += 1
        logger.info(f"✅ COMPRA: ${valor_trade:.2f}")
        return True
    
    def executar_venda_corrigida(self, symbol, rsi, portfolio):
        """VENDA CORRIGIDA - Respeita valores mínimos"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        info_asset = portfolio[asset]
        quantidade_livre = info_asset['free']
        valor_atual = info_asset['valor_usdt']
        
        if quantidade_livre <= 0:
            return False
        
        # ⚠️ VERIFICAÇÃO CRÍTICA: Valor mínimo
        if not self.pode_vender_ativo(symbol, valor_atual):
            self.vendas_bloqueadas += 1
            logger.info(f"⏳ {symbol}: Acumulando para atingir mínimo")
            return False
        
        # Calcular lucro
        trade_info = self.trades_ativos.get(symbol)
        lucro_estimado = 0
        
        if trade_info:
            lucro_estimado = valor_atual - trade_info['valor_investido']
        
        logger.warning(f"🚨 VENDA: {symbol}")
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
        
        resultado = self.fazer_requisicao_corrigida('POST', '/api/v3/order', params, signed=True)
        
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
    
    def analisar_oportunidade_corrigida(self, symbol, rsi, portfolio, usdt_livre):
        """Análise corrigida com verificação de mínimos"""
        asset = symbol.replace('USDT', '')
        config = self.ativos_corrigidos.get(symbol, {})
        
        # VENDA (se tem e pode vender)
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor = portfolio[asset]['valor_usdt']
            
            if rsi >= self.rsi_venda_rapida:
                if self.pode_vender_ativo(symbol, valor):
                    logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA | ${valor:.2f}")
                    return self.executar_venda_corrigida(symbol, rsi, portfolio)
                else:
                    logger.info(f"🔄 {symbol}: RSI {rsi:.1f} | ACUMULANDO | ${valor:.2f}")
            elif rsi >= self.rsi_venda_normal:
                if self.pode_vender_ativo(symbol, valor):
                    logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_NORMAL | ${valor:.2f}")
                    return self.executar_venda_corrigida(symbol, rsi, portfolio)
            else:
                logger.info(f"⏳ {symbol}: Posição ${valor:.2f} | RSI {rsi:.1f}")
        
        # COMPRA
        elif rsi <= self.rsi_compra:
            valor_necessario = self.calcular_valor_compra(symbol, usdt_livre)
            
            if valor_necessario > 0:
                prioridade = config.get('prioridade', 99)
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | P{prioridade} | ${valor_necessario:.2f}")
                return self.executar_compra_corrigida(symbol, rsi, usdt_livre)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, USDT limitado")
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDANDO")
        
        return False
    
    def ciclo_corrigido(self):
        """Ciclo principal corrigido"""
        usdt_livre, portfolio, valor_total = self.get_portfolio_corrigido()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Status
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO: +${lucro:.3f} (+{percentual:.3f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        # Posições com status de vendabilidade
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.1:
                symbol = f"{asset}USDT"
                pode_vender = self.pode_vender_ativo(symbol, info['valor_usdt'])
                status = "✅ VENDÁVEL" if pode_vender else "🔄 ACUMULANDO"
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f} {status}")
        
        # Estatísticas
        if self.vendas_bloqueadas > 0:
            logger.info(f"📊 Stats: {self.compras_executadas} compras | {self.vendas_executadas} vendas | {self.vendas_bloqueadas} bloqueadas")
        
        # Análise por prioridade
        operacoes = 0
        simbolos_ordenados = sorted(self.ativos_corrigidos.items(), 
                                   key=lambda x: x[1].get('prioridade', 99))
        
        for symbol, config in simbolos_ordenados:
            try:
                klines = self.get_klines(symbol)
                if len(klines) < 4:
                    continue
                
                rsi = self.calcular_rsi(klines)
                
                if self.analisar_oportunidade_corrigida(symbol, rsi, portfolio, usdt_livre):
                    operacoes += 1
                    time.sleep(3)
                
            except Exception as e:
                logger.error(f"❌ Erro {symbol}: {e}")
        
        logger.info(f"🔄 Ciclo: {operacoes} operações")
        return valor_total, operacoes
    
    def executar_sistema_corrigido(self):
        """Sistema principal corrigido"""
        logger.info("🛡️ === SISTEMA CORRIGIDO INICIADO ===")
        logger.info("🚫 CORREÇÃO: Respeita valores mínimos Binance")
        logger.info("🎯 ESTRATÉGIA: Acumular até valor vendável")
        logger.info("=" * 80)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_corrigido()
        self.capital_inicial = valor_inicial
        
        meta = valor_inicial * 1.015  # +1.5%
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +1.5% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO CORRIGIDO {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_corrigido()
                
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

def main():
    """Executar sistema corrigido"""
    logger.info("🔧 Iniciando Sistema Corrigido...")
    
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
        
        sistema = SistemaCorrigidoMinimos(api_key, api_secret)
        sistema.executar_sistema_corrigido()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()