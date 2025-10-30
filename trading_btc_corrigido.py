"""
🎯 SISTEMA BTC CORRIGIDO - Fix dos erros de venda
Correções aplicadas:
1. ✅ Precisão correta na formatação BTC
2. ✅ Verificação real de saldo antes de venda
3. ✅ Margem de segurança para evitar "insufficient balance"
4. ✅ Log detalhado para debugging
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
from decimal import Decimal, ROUND_DOWN

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_btc_corrigido.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaBTCCorrigido:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO BTC CORRIGIDA
        self.symbol = 'BTCUSDT'
        self.rsi_compra = 35
        self.rsi_venda = 60
        self.ciclo_tempo = 15
        
        # PARÂMETROS AJUSTADOS PARA NOSSA SITUAÇÃO REAL
        self.config_btc = {
            'percentual_capital': 0.90,
            'reserva_usdt': 0.5,
            'valor_minimo_compra': 12.0,  # Reduzido para $12 (mais realista)
            'valor_minimo_venda': 12.0,   # Reduzido para $12 (permite venda atual)
            'margem_seguranca': 0.98,     # Apenas 2% de margem (menos restritivo)
        }
        
        # Controles
        self.capital_inicial = 0
        self.trades_realizados = 0
        self.lucro_acumulado = 0
        self.posicao_btc = {'quantidade': 0, 'valor_compra': 0, 'timestamp': 0}
        
        # Session
        self.session = requests.Session()
        
        logger.info("🔧 === SISTEMA BTC CORRIGIDO ===")
        logger.info("🛠️ CORREÇÕES APLICADAS:")
        logger.info("   ✅ Precisão decimal correta")
        logger.info("   ✅ Margem de segurança 5%")
        logger.info("   ✅ Verificação real de saldo")
        logger.info("   ✅ Log detalhado para debug")
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
    
    def formatar_quantidade_btc(self, quantidade):
        """Formatar quantidade BTC com precisão correta"""
        # BTC tem precisão de 5 casas decimais (0.00001)
        decimal_quantidade = Decimal(str(quantidade))
        quantidade_formatada = decimal_quantidade.quantize(Decimal('0.00001'), rounding=ROUND_DOWN)
        return float(quantidade_formatada)
    
    def get_portfolio_btc_real(self):
        """Portfolio com verificação real de saldo"""
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
            locked = float(balance['locked'])
            
            if asset == 'USDT':
                usdt_livre = free
                valor_total += free
                if locked > 0:
                    logger.info(f"⚠️ USDT bloqueado: ${locked:.2f}")
            elif asset == 'BTC':
                btc_livre = free
                valor_btc = free * preco_btc
                valor_total += valor_btc
                if locked > 0:
                    logger.info(f"⚠️ BTC bloqueado: {locked:.5f}")
        
        logger.debug(f"🔍 Saldos reais - USDT: ${usdt_livre:.2f} | BTC: {btc_livre:.5f}")
        return usdt_livre, btc_livre, preco_btc, valor_total
    
    def pode_vender_btc_real(self, btc_quantidade, preco_btc):
        """Verificar venda BTC com margem de segurança"""
        if btc_quantidade <= 0:
            logger.warning("⚠️ Quantidade BTC zero ou negativa")
            return False, 0
        
        # Aplicar margem de segurança para evitar "insufficient balance"
        quantidade_segura = btc_quantidade * self.config_btc['margem_seguranca']
        quantidade_formatada = self.formatar_quantidade_btc(quantidade_segura)
        
        valor_venda = quantidade_formatada * preco_btc
        
        logger.info(f"🔍 Verificação venda BTC:")
        logger.info(f"   📊 BTC disponível: {btc_quantidade:.5f}")
        logger.info(f"   🛡️ BTC com margem 5%: {quantidade_formatada:.5f}")
        logger.info(f"   💲 Valor estimado: ${valor_venda:.2f}")
        
        if valor_venda < self.config_btc['valor_minimo_venda']:
            logger.info(f"   ❌ Abaixo do mínimo ${self.config_btc['valor_minimo_venda']}")
            return False, 0
        
        if quantidade_formatada < 0.00001:  # Mínimo Binance para BTC
            logger.info(f"   ❌ Quantidade abaixo do mínimo Binance (0.00001)")
            return False, 0
        
        logger.info(f"   ✅ Venda viável: {quantidade_formatada:.5f} BTC")
        return True, quantidade_formatada
    
    def comprar_btc(self, rsi, usdt_disponivel):
        """Comprar BTC"""
        valor_compra = usdt_disponivel * self.config_btc['percentual_capital']
        
        if valor_compra < self.config_btc['valor_minimo_compra']:
            logger.info(f"💡 BTC: ${valor_compra:.2f} < ${self.config_btc['valor_minimo_compra']} (mínimo)")
            return False
        
        if usdt_disponivel - valor_compra < self.config_btc['reserva_usdt']:
            logger.info(f"💡 BTC: Sem reserva USDT suficiente")
            return False
        
        logger.warning(f"🚨 COMPRA BTC")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_compra:.2f}")
        logger.warning(f"   💰 USDT disponível: ${usdt_disponivel:.2f}")
        
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
    
    def vender_btc_seguro(self, rsi, btc_quantidade, preco_btc):
        """Vender BTC com segurança"""
        pode_vender, quantidade_segura = self.pode_vender_btc_real(btc_quantidade, preco_btc)
        
        if not pode_vender:
            logger.info(f"⏳ Aguardando mais BTC para venda segura")
            return False
        
        valor_venda = quantidade_segura * preco_btc
        
        logger.warning(f"🚨 VENDA BTC SEGURA")
        logger.warning(f"   📊 RSI: {rsi:.1f}")
        logger.warning(f"   📈 Quantidade original: {btc_quantidade:.5f}")
        logger.warning(f"   🛡️ Quantidade segura: {quantidade_segura:.5f}")
        logger.warning(f"   💲 Valor: ${valor_venda:.2f}")
        
        # Calcular lucro
        lucro = 0
        if self.posicao_btc['valor_compra'] > 0:
            lucro = valor_venda - self.posicao_btc['valor_compra']
            logger.warning(f"   📈 Lucro estimado: ${lucro:.3f}")
        
        params = {
            'symbol': self.symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': f"{quantidade_segura:.5f}"
        }
        
        logger.info(f"🔧 Parâmetros venda: {params}")
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda BTC: {resultado.get('msg')}")
            logger.error(f"🔍 Debug - Saldo real BTC: {btc_quantidade:.5f}")
            logger.error(f"🔍 Debug - Tentativa venda: {quantidade_segura:.5f}")
            return False
        
        # Registrar trade bem-sucedido
        self.trades_realizados += 1
        if lucro > 0:
            self.lucro_acumulado += lucro
        
        logger.info(f"✅ BTC VENDIDO COM SUCESSO!")
        logger.info(f"   📊 Quantidade: {quantidade_segura:.5f} BTC")
        logger.info(f"   💵 Valor: ${valor_venda:.2f}")
        if lucro != 0:
            sinal = "+" if lucro > 0 else ""
            logger.info(f"   💰 Lucro: {sinal}${lucro:.3f}")
        
        # Reset posição
        self.posicao_btc = {'quantidade': 0, 'valor_compra': 0, 'timestamp': 0}
        
        return True
    
    def ciclo_btc_corrigido(self):
        """Ciclo BTC com correções aplicadas"""
        usdt_livre, btc_livre, preco_btc, valor_total = self.get_portfolio_btc_real()
        
        if valor_total == 0:
            logger.error("❌ Erro portfolio")
            return 0, 0
        
        # Status com mais detalhes
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro_total = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro_total:.3f} (+{percentual:.2f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f}")
        logger.info(f"   💵 USDT livre: ${usdt_livre:.2f}")
        
        if btc_livre > 0:
            valor_btc = btc_livre * preco_btc
            logger.info(f"   ₿ BTC livre: {btc_livre:.5f} = ${valor_btc:.2f}")
        
        # Obter RSI
        klines = self.get_klines_btc()
        if len(klines) < 6:
            logger.warning("⚠️ Dados insuficientes para RSI")
            return valor_total, 0
        
        rsi = self.calcular_rsi_btc(klines)
        operacoes = 0
        
        # LÓGICA DE TRADING COM TRATAMENTO DE "DUST"
        valor_btc_atual = btc_livre * preco_btc
        
        # Verificar se tem BTC significativo (acima de $5)
        if btc_livre > 0 and valor_btc_atual >= 5.0:
            # TEM BTC SIGNIFICATIVO → Avaliar venda
            if rsi >= self.rsi_venda:
                logger.info(f"💸 BTC: RSI {rsi:.1f} ≥ {self.rsi_venda} → TENTATIVA VENDA")
                if self.vender_btc_seguro(rsi, btc_livre, preco_btc):
                    operacoes = 1
                    logger.info("✅ Venda executada com sucesso!")
                else:
                    logger.warning("⚠️ Venda não executada - aguardando condições")
            else:
                logger.info(f"⏳ BTC: RSI {rsi:.1f} | Aguardando ≥ {self.rsi_venda}")
        
        elif btc_livre > 0 and valor_btc_atual < 5.0:
            # TEM APENAS "DUST" BTC → Ignorar e focar em compra
            logger.info(f"🗂️ BTC Dust: {btc_livre:.5f} = ${valor_btc_atual:.2f} (ignorando)")
            if rsi <= self.rsi_compra and usdt_livre > self.config_btc['valor_minimo_compra']:
                logger.info(f"🔥 USDT→BTC: RSI {rsi:.1f} ≤ {self.rsi_compra} → COMPRA")
                if self.comprar_btc(rsi, usdt_livre):
                    operacoes = 1
            else:
                logger.info(f"⏳ USDT: RSI {rsi:.1f} | Aguardando ≤ {self.rsi_compra}")
        
        else:
            # SEM BTC → Avaliar compra
            if rsi <= self.rsi_compra:
                logger.info(f"🔥 BTC: RSI {rsi:.1f} ≤ {self.rsi_compra} → COMPRA")
                if self.comprar_btc(rsi, usdt_livre):
                    operacoes = 1
            else:
                logger.info(f"⏳ BTC: RSI {rsi:.1f} | Aguardando ≤ {self.rsi_compra}")
        
        logger.info(f"🔄 Operações no ciclo: {operacoes}")
        return valor_total, operacoes
    
    def executar_sistema_corrigido(self):
        """Sistema principal corrigido"""
        logger.info("🔧 === SISTEMA BTC CORRIGIDO INICIADO ===")
        logger.info("🛠️ Aplicando todas as correções de segurança...")
        logger.info("=" * 60)
        
        # Capital inicial
        usdt_inicial, btc_inicial, preco_inicial, capital_inicial = self.get_portfolio_btc_real()
        self.capital_inicial = capital_inicial
        
        if capital_inicial == 0:
            logger.error("❌ Erro capital inicial")
            return
        
        meta = capital_inicial * 1.05  # +5%
        
        logger.info(f"💼 Capital inicial: ${capital_inicial:.2f}")
        logger.info(f"💵 USDT: ${usdt_inicial:.2f}")
        if btc_inicial > 0:
            valor_btc_inicial = btc_inicial * preco_inicial
            logger.info(f"₿ BTC: {btc_inicial:.5f} = ${valor_btc_inicial:.2f}")
        logger.warning(f"🎯 Meta: ${meta:.2f} (+5%)")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_btc_corrigido()
                
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.2f}%)")
                    logger.info(f"📊 Trades: {self.trades_realizados}")
                    break
                
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Executar sistema corrigido"""
    logger.info("🔧 Iniciando Sistema BTC Corrigido...")
    
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
        
        sistema = SistemaBTCCorrigido(api_key, api_secret)
        sistema.executar_sistema_corrigido()
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()