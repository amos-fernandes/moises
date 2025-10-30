"""
🎯 SISTEMA FOCO BTC - Estratégia Simples
Objetivo: Comprar e vender APENAS BTC para crescer o capital
Estratégia: RSI baixo → Compra BTC | RSI alto → Vende BTC → USDT
Capital disponível: ~$17 USDT
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
        logging.FileHandler('trading_foco_btc.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaFocoBTC:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO SIMPLES - APENAS BTC
        self.symbol = 'BTCUSDT'
        self.rsi_compra = 35              # RSI baixo para compra
        self.rsi_venda = 60               # RSI alto para venda
        self.ciclo_tempo = 15             # Ciclos de 15s
        
        # PARÂMETROS BTC AJUSTADOS
        self.config_btc = {
            'percentual_capital': 0.90,       # 90% do capital por compra (mais agressivo)
            'reserva_usdt': 0.5,             # $0.5 de reserva (menor)
            'valor_minimo_compra': 15.0,     # Mínimo $15 para compra BTC (seguro)
            'valor_minimo_venda': 15.0,      # Mínimo $15 para venda BTC (seguro)
        }
        
        # Controles
        self.capital_inicial = 0
        self.trades_realizados = 0
        self.lucro_acumulado = 0
        self.posicao_btc = {'quantidade': 0, 'valor_compra': 0, 'timestamp': 0}
        
        # Session
        self.session = requests.Session()
        
        logger.info("🎯 === SISTEMA FOCO BTC ===")
        logger.info("💰 ESTRATÉGIA: Apenas BTC - Simples e eficaz")
        logger.info("🔥 FOCO TOTAL: Compra BTC + Venda BTC = Lucro USDT")
        logger.info("=" * 60)
        logger.info(f"📊 RSI: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda}")
        logger.info(f"💵 Capital por trade: {self.config_btc['percentual_capital']*100}%")
        logger.info(f"💲 Mínimo: ${self.config_btc['valor_minimo_compra']} (Binance)")
        logger.info("=" * 60)
    
    def get_server_time(self):
        """Timestamp do servidor"""
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
        
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = self.session.get(url, params=params, headers=headers, timeout=20)
                else:
                    r = self.session.post(url, params=params, headers=headers, timeout=20)
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    error_msg = error_data.get('msg', r.text)
                    logger.warning(f"❌ Binance: {error_msg}")
                    return {'error': True, 'msg': error_msg}
                else:
                    logger.warning(f"HTTP {r.status_code}")
            except Exception as e:
                logger.warning(f"Erro req (tent {tentativa+1}): {e}")
                if tentativa < 2:
                    time.sleep(2)
        
        return {'error': True, 'msg': 'Falha conectividade'}
    
    def get_account_info(self):
        """Info da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_preco_btc(self):
        """Preço atual do BTC"""
        try:
            r = self.session.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': self.symbol}, timeout=10)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception:
            pass
        return 0
    
    def get_klines_btc(self, limit=10):
        """Klines BTC"""
        try:
            params = {'symbol': self.symbol, 'interval': '1m', 'limit': limit}
            r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=15)
            if r.status_code == 200:
                return [float(k[4]) for k in r.json()]
        except Exception:
            pass
        return []
    
    def calcular_rsi_btc(self, precos, periodo=6):
        """RSI do BTC"""
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
    
    def get_portfolio_btc(self):
        """Portfolio focado em BTC + USDT"""
        conta = self.get_account_info()
        if conta.get('error'):
            return 0, 0, 0, 0
        
        usdt_livre = 0
        btc_livre = 0
        valor_total = 0
        preco_btc = self.get_preco_btc()
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            
            if asset == 'USDT':
                usdt_livre = free
                valor_total += free
            elif asset == 'BTC':
                btc_livre = free
                valor_btc = free * preco_btc
                valor_total += valor_btc
        
        return usdt_livre, btc_livre, preco_btc, valor_total
    
    def pode_comprar_btc(self, usdt_disponivel):
        """Verificar se pode comprar BTC"""
        valor_compra = usdt_disponivel * self.config_btc['percentual_capital']
        
        # Verificar mínimo + reserva
        if valor_compra < self.config_btc['valor_minimo_compra']:
            logger.info(f"💡 BTC: ${valor_compra:.2f} < ${self.config_btc['valor_minimo_compra']} (mínimo)")
            return False
        
        if usdt_disponivel - valor_compra < self.config_btc['reserva_usdt']:
            logger.info(f"💡 BTC: Sem reserva USDT suficiente")
            return False
        
        return valor_compra
    
    def pode_vender_btc(self, btc_quantidade, preco_btc):
        """Verificar se pode vender BTC"""
        valor_venda = btc_quantidade * preco_btc
        
        if valor_venda < self.config_btc['valor_minimo_venda']:
            logger.info(f"🔄 BTC: ${valor_venda:.2f} < ${self.config_btc['valor_minimo_venda']} (acumulando)")
            return False
        
        return True
    
    def comprar_btc(self, rsi, usdt_disponivel):
        """Comprar BTC"""
        valor_compra = self.pode_comprar_btc(usdt_disponivel)
        
        if not valor_compra:
            return False
        
        logger.warning(f"🚨 COMPRA BTC")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_compra:.2f}")
        
        params = {
            'symbol': self.symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_compra:.2f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra BTC: {resultado.get('msg')}")
            return False
        
        # Registrar posição
        self.posicao_btc = {
            'valor_compra': valor_compra,
            'timestamp': time.time(),
            'rsi_entrada': rsi
        }
        
        logger.info(f"✅ BTC COMPRADO: ${valor_compra:.2f}")
        return True
    
    def vender_btc(self, rsi, btc_quantidade, preco_btc):
        """Vender BTC"""
        if not self.pode_vender_btc(btc_quantidade, preco_btc):
            return False
        
        valor_venda = btc_quantidade * preco_btc
        
        logger.warning(f"🚨 VENDA BTC")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_venda:.2f}")
        
        # Calcular lucro
        lucro = 0
        if self.posicao_btc['valor_compra'] > 0:
            lucro = valor_venda - self.posicao_btc['valor_compra']
            logger.warning(f"   📈 Lucro: ${lucro:.3f}")
        
        params = {
            'symbol': self.symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': f"{btc_quantidade:.5f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda BTC: {resultado.get('msg')}")
            return False
        
        # Registrar trade
        self.trades_realizados += 1
        if lucro > 0:
            self.lucro_acumulado += lucro
        
        logger.info(f"✅ BTC VENDIDO: ${valor_venda:.2f} → USDT")
        if lucro != 0:
            sinal = "+" if lucro > 0 else ""
            logger.info(f"💰 Lucro: {sinal}${lucro:.3f}")
        
        # Reset posição
        self.posicao_btc = {'quantidade': 0, 'valor_compra': 0, 'timestamp': 0}
        
        return True
    
    def ciclo_btc(self):
        """Ciclo principal BTC"""
        usdt_livre, btc_livre, preco_btc, valor_total = self.get_portfolio_btc()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Status
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro_total = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro_total:.3f} (+{percentual:.2f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        if btc_livre > 0:
            valor_btc = btc_livre * preco_btc
            logger.info(f"   ₿ BTC: {btc_livre:.5f} = ${valor_btc:.2f}")
        
        # Stats
        if self.trades_realizados > 0:
            logger.info(f"📊 Trades: {self.trades_realizados} | Lucro acumulado: ${self.lucro_acumulado:.3f}")
        
        # Obter RSI
        klines = self.get_klines_btc()
        if len(klines) < 6:
            logger.warning("⚠️ Dados insuficientes para RSI")
            return valor_total, 0
        
        rsi = self.calcular_rsi_btc(klines)
        operacoes = 0
        
        # LÓGICA SIMPLES
        if btc_livre > 0:
            # TEM BTC → Avaliar venda
            if rsi >= self.rsi_venda:
                logger.info(f"💸 BTC: RSI {rsi:.1f} ≥ {self.rsi_venda} → VENDA")
                if self.vender_btc(rsi, btc_livre, preco_btc):
                    operacoes = 1
            else:
                logger.info(f"⏳ BTC: RSI {rsi:.1f} | Aguardando ≥ {self.rsi_venda}")
        else:
            # SEM BTC → Avaliar compra
            if rsi <= self.rsi_compra:
                logger.info(f"🔥 BTC: RSI {rsi:.1f} ≤ {self.rsi_compra} → COMPRA")
                if self.comprar_btc(rsi, usdt_livre):
                    operacoes = 1
            else:
                logger.info(f"⏳ BTC: RSI {rsi:.1f} | Aguardando ≤ {self.rsi_compra}")
        
        logger.info(f"🔄 Ciclo: {operacoes} operação")
        return valor_total, operacoes
    
    def executar_sistema_btc(self):
        """Sistema principal BTC"""
        logger.info("🎯 === SISTEMA FOCO BTC INICIADO ===")
        logger.info("💰 ESTRATÉGIA: Crescimento através de BTC apenas")
        logger.info("🔄 CICLO: USDT → BTC → USDT → Lucro")
        logger.info("=" * 60)
        
        # Capital inicial
        usdt_inicial, btc_inicial, preco_inicial, capital_inicial = self.get_portfolio_btc()
        self.capital_inicial = capital_inicial
        
        if capital_inicial == 0:
            logger.error("❌ Erro capital inicial")
            return
        
        meta = capital_inicial * 1.05  # +5% (meta mais ambiciosa!)
        
        logger.info(f"💼 Capital inicial: ${capital_inicial:.2f}")
        logger.info(f"💵 USDT: ${usdt_inicial:.2f}")
        if btc_inicial > 0:
            valor_btc_inicial = btc_inicial * preco_inicial
            logger.info(f"₿ BTC: {btc_inicial:.5f} = ${valor_btc_inicial:.2f}")
        logger.warning(f"🎯 Nova Meta: +5% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO BTC {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_btc()
                
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.2f}%)")
                    logger.info(f"📊 Trades realizados: {self.trades_realizados}")
                    break
                
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")

def main():
    """Executar sistema BTC"""
    logger.info("🎯 Iniciando Sistema Foco BTC...")
    
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
        
        sistema = SistemaFocoBTC(api_key, api_secret)
        sistema.executar_sistema_btc()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()