"""
🛡️ SISTEMA DEFINITIVO FOCO ETH - SEM ERROS NOTIONAL
Estratégia: SOMENTE ETH com valores seguros acima de $5
Objetivo: Zero erros + Aproveitar posições atuais + Crescer capital
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

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_foco_eth.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaFocoETH:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO DEFINITIVA - FOCO ETH APENAS
        self.rsi_compra = 25              # RSI mais baixo para compras
        self.rsi_venda = 55               # RSI mais alto para vendas
        self.ciclo_tempo = 12             # Ciclos mais longos
        
        # CONFIGURAÇÃO SEGURA PARA ETH
        self.config_definitiva = {
            'percentual_trade': 0.35,         # 35% do capital (mais agressivo)
            'reserva_usdt': 0.3,             # Reserva menor
            'valor_minimo_compra': 5.0,      # MÍNIMO $5 para compras ETH
            'valor_minimo_venda': 5.0,       # MÍNIMO $5 para vendas ETH  
            'timeout_conexao': 20,           
        }
        
        # FOCO EXCLUSIVO EM ETH
        self.ativo_foco = 'ETHUSDT'
        
        # Controle
        self.trades_ativos = {}
        self.capital_inicial = 0
        self.lucro_consolidado = 0
        self.vendas_executadas = 0
        self.compras_executadas = 0
        self.tentativas_bloqueadas = 0
        
        # Session
        self.session = requests.Session()
        
        logger.info("🛡️ === SISTEMA FOCO ETH ATIVADO ===")
        logger.info("🎯 ESTRATÉGIA: SOMENTE ETH - Zero erros NOTIONAL")
        logger.info("💰 Valores seguros: Mín $5 para compra/venda")
        logger.info("🔄 Aproveitamento: Posições BTC/ETH atuais + novas compras ETH")
        logger.info("=" * 80)
        logger.info(f"🔥 RSI ETH: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda}")
        logger.info(f"💵 Trade ETH: {self.config_definitiva['percentual_trade']*100}% do capital")
        logger.info(f"💰 Mínimos: ${self.config_definitiva['valor_minimo_compra']} compra | ${self.config_definitiva['valor_minimo_venda']} venda")
        logger.info("=" * 80)
    
    def get_server_time(self):
        """Timestamp"""
        try:
            response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except Exception:
            pass
        return int(time.time() * 1000)
    
    def fazer_requisicao(self, method, endpoint, params=None, signed=False):
        """Requisição"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_server_time()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                r = self.session.get(url, params=params, headers=headers, timeout=self.config_definitiva['timeout_conexao'])
            else:
                r = self.session.post(url, params=params, headers=headers, timeout=self.config_definitiva['timeout_conexao'])
            
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 400:
                error_data = r.json() if r.text else {}
                return {'error': True, 'msg': error_data.get('msg', r.text)}
            else:
                return {'error': True, 'msg': f'HTTP {r.status_code}'}
                
        except Exception as e:
            return {'error': True, 'msg': str(e)}
    
    def get_account_info(self):
        """Info da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_preco_atual(self, symbol):
        """Preço atual"""
        try:
            r = self.session.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=10)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception:
            pass
        return 0
    
    def get_klines(self, symbol, limit=8):
        """Klines"""
        try:
            params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
            r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=10)
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
    
    def get_portfolio(self):
        """Portfolio"""
        conta = self.get_account_info()
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
    
    def pode_comprar_eth(self, usdt_disponivel):
        """Verificar se pode comprar ETH"""
        valor_necessario = usdt_disponivel * self.config_definitiva['percentual_trade']
        
        # Verificar mínimo
        if valor_necessario < self.config_definitiva['valor_minimo_compra']:
            return False
        
        # Verificar reserva
        if usdt_disponivel - valor_necessario < self.config_definitiva['reserva_usdt']:
            return False
        
        return True
    
    def calcular_valor_compra_eth(self, usdt_disponivel):
        """Calcular valor para compra ETH"""
        if not self.pode_comprar_eth(usdt_disponivel):
            return 0
        
        valor_ideal = usdt_disponivel * self.config_definitiva['percentual_trade']
        valor_final = max(valor_ideal, self.config_definitiva['valor_minimo_compra'])
        
        # Garantir reserva
        if usdt_disponivel - valor_final < self.config_definitiva['reserva_usdt']:
            valor_final = usdt_disponivel - self.config_definitiva['reserva_usdt']
            if valor_final < self.config_definitiva['valor_minimo_compra']:
                return 0
        
        return valor_final
    
    def pode_vender_ativo(self, symbol, valor_usdt):
        """Verificar se pode vender"""
        if symbol == 'ETHUSDT':
            return valor_usdt >= self.config_definitiva['valor_minimo_venda']
        elif symbol == 'BTCUSDT':
            return valor_usdt >= 10.0  # BTC precisa $10
        else:
            return valor_usdt >= 5.0  # Outros $5
    
    def executar_compra_eth(self, rsi, usdt_disponivel):
        """Comprar ETH com valor seguro"""
        valor_trade = self.calcular_valor_compra_eth(usdt_disponivel)
        
        if valor_trade <= 0:
            return False
        
        logger.warning(f"🚨 COMPRA ETH SEGURA")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_trade:.2f}")
        logger.warning(f"   ✅ VALOR SEGURO: ≥ ${self.config_definitiva['valor_minimo_compra']}")
        
        params = {
            'symbol': self.ativo_foco,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_trade:.2f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra ETH: {resultado.get('msg')}")
            return False
        
        # Registrar
        self.trades_ativos[self.ativo_foco] = {
            'timestamp': time.time(),
            'valor_investido': valor_trade,
            'rsi_entrada': rsi
        }
        
        self.compras_executadas += 1
        logger.info(f"✅ COMPRA ETH: ${valor_trade:.2f}")
        return True
    
    def executar_venda_ativo(self, symbol, rsi, portfolio):
        """Venda de qualquer ativo (ETH, BTC, etc)"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        info_asset = portfolio[asset]
        quantidade_livre = info_asset['free']
        valor_atual = info_asset['valor_usdt']
        
        if quantidade_livre <= 0:
            return False
        
        # Verificar se pode vender
        if not self.pode_vender_ativo(symbol, valor_atual):
            return False
        
        # Calcular lucro
        trade_info = self.trades_ativos.get(symbol)
        lucro_estimado = 0
        
        if trade_info:
            lucro_estimado = valor_atual - trade_info['valor_investido']
        
        logger.warning(f"🚨 VENDA {asset}")
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
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda {symbol}: {resultado.get('msg')}")
            return False
        
        logger.info(f"✅ VENDA {asset}: ~${valor_atual:.2f} → USDT")
        
        if trade_info:
            logger.info(f"🎉 LUCRO: ${lucro_estimado:.3f}")
            self.lucro_consolidado += lucro_estimado
            del self.trades_ativos[symbol]
        
        self.vendas_executadas += 1
        return True
    
    def analisar_todas_posicoes(self, portfolio, usdt_livre):
        """Analisar todas as posições - ETH, BTC, etc"""
        operacoes = 0
        
        # 1. VERIFICAR VENDAS DE TODAS AS POSIÇÕES
        for asset, info in portfolio.items():
            if asset == 'USDT':
                continue
            
            symbol = f"{asset}USDT"
            valor = info['valor_usdt']
            
            # Obter RSI do ativo
            klines = self.get_klines(symbol)
            if len(klines) < 4:
                continue
            
            rsi = self.calcular_rsi(klines)
            
            # Verificar se deve vender
            if self.pode_vender_ativo(symbol, valor) and rsi >= self.rsi_venda:
                logger.info(f"💸 {asset}: RSI {rsi:.1f} | VENDA | ${valor:.2f}")
                if self.executar_venda_ativo(symbol, rsi, portfolio):
                    operacoes += 1
                    time.sleep(3)
            elif not self.pode_vender_ativo(symbol, valor):
                logger.info(f"🔄 {asset}: ${valor:.2f} ACUMULANDO (mín: ${10.0 if asset == 'BTC' else 5.0})")
            else:
                logger.info(f"⏳ {asset}: RSI {rsi:.1f} | ${valor:.2f} | AGUARDANDO")
        
        # 2. VERIFICAR COMPRA ETH (FOCO PRINCIPAL)
        klines_eth = self.get_klines(self.ativo_foco)
        if len(klines_eth) >= 4:
            rsi_eth = self.calcular_rsi(klines_eth)
            
            if rsi_eth <= self.rsi_compra and self.pode_comprar_eth(usdt_livre):
                logger.info(f"🔥 ETH: RSI {rsi_eth:.1f} | COMPRA | ${self.calcular_valor_compra_eth(usdt_livre):.2f}")
                if self.executar_compra_eth(rsi_eth, usdt_livre):
                    operacoes += 1
            elif not self.pode_comprar_eth(usdt_livre):
                logger.info(f"⏳ ETH: RSI {rsi_eth:.1f} | USDT insuficiente para compra segura")
            else:
                logger.info(f"⏳ ETH: RSI {rsi_eth:.1f} | AGUARDANDO")
        
        return operacoes
    
    def ciclo_definitivo(self):
        """Ciclo principal definitivo"""
        usdt_livre, portfolio, valor_total = self.get_portfolio()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Status
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO: +${lucro:.3f} (+{percentual:.3f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        # Status das posições
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.1:
                symbol = f"{asset}USDT"
                pode_vender = self.pode_vender_ativo(symbol, info['valor_usdt'])
                status = "✅ VENDÁVEL" if pode_vender else "🔄 ACUMULANDO"
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f} {status}")
        
        # Estatísticas
        if self.tentativas_bloqueadas > 0:
            logger.info(f"📊 Stats: {self.compras_executadas} compras | {self.vendas_executadas} vendas | {self.tentativas_bloqueadas} bloqueadas")
        
        # Analisar todas as oportunidades
        operacoes = self.analisar_todas_posicoes(portfolio, usdt_livre)
        
        logger.info(f"🔄 Ciclo: {operacoes} operações")
        return valor_total, operacoes
    
    def executar_sistema_definitivo(self):
        """Sistema principal definitivo"""
        logger.info("🛡️ === SISTEMA FOCO ETH INICIADO ===")
        logger.info("🎯 ESTRATÉGIA: SOMENTE ETH + Aproveitar posições atuais")
        logger.info("💰 VALORES SEGUROS: Sem erros NOTIONAL")
        logger.info("=" * 80)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio()
        self.capital_inicial = valor_inicial
        
        meta = valor_inicial * 1.02  # +2%
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +2% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO DEFINITIVO {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_definitivo()
                
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
    """Executar sistema definitivo"""
    logger.info("🔧 Iniciando Sistema Foco ETH...")
    
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
        
        sistema = SistemaFocoETH(api_key, api_secret)
        sistema.executar_sistema_definitivo()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()