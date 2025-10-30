"""
🩺 SISTEMA DIAGNÓSTICO - VERIFICAÇÃO REAL DA CONTA
Objetivo: Descobrir o estado real dos ativos e corrigir inconsistências
"""

import json
import time
import logging
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('diagnostico_conta.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class DiagnosticoConta:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        logger.info("🩺 === SISTEMA DIAGNÓSTICO ATIVADO ===")
        logger.info("🔍 Verificando estado real da conta...")
        logger.info("=" * 80)
    
    def get_server_time(self):
        """Obter timestamp do servidor"""
        try:
            response = requests.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except Exception as e:
            logger.warning(f"Erro timestamp: {e}")
        
        return int(time.time() * 1000)
    
    def fazer_requisicao(self, method, endpoint, params=None, signed=False):
        """Requisição segura"""
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
                r = requests.get(url, params=params, headers=headers, timeout=15)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=15)
            
            if r.status_code == 200:
                return r.json()
            else:
                logger.error(f"HTTP {r.status_code}: {r.text}")
                return {'error': True, 'msg': r.text}
                
        except Exception as e:
            logger.error(f"Erro requisição: {e}")
            return {'error': True, 'msg': str(e)}
    
    def get_account_info_completa(self):
        """Informações completas da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_precos_atuais(self):
        """Preços atuais de todos os símbolos"""
        try:
            response = requests.get(f"{BASE_URL}/api/v3/ticker/price", timeout=10)
            if response.status_code == 200:
                precos = {}
                for item in response.json():
                    precos[item['symbol']] = float(item['price'])
                return precos
        except Exception as e:
            logger.error(f"Erro preços: {e}")
        
        return {}
    
    def diagnosticar_conta_completo(self):
        """Diagnóstico completo da conta"""
        logger.info("🔍 === INICIANDO DIAGNÓSTICO COMPLETO ===")
        
        # 1. Informações da conta
        conta = self.get_account_info_completa()
        if conta.get('error'):
            logger.error(f"❌ Erro ao obter conta: {conta.get('msg')}")
            return
        
        # 2. Preços atuais
        precos = self.get_precos_atuais()
        
        # 3. Análise detalhada
        logger.info("📊 === ANÁLISE DETALHADA DOS ATIVOS ===")
        
        total_usdt = 0
        ativos_importantes = ['USDT', 'BTC', 'ETH', 'SOL']
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    valor_usdt = total
                    preco_unitario = 1.0
                else:
                    symbol = f"{asset}USDT"
                    preco_unitario = precos.get(symbol, 0)
                    valor_usdt = total * preco_unitario
                
                # Log detalhado para ativos importantes ou com valor > $0.01
                if asset in ativos_importantes or valor_usdt >= 0.01:
                    logger.info(f"💰 {asset}:")
                    logger.info(f"   📈 Livre: {free:.8f}")
                    logger.info(f"   🔒 Bloqueado: {locked:.8f}")
                    logger.info(f"   📊 Total: {total:.8f}")
                    logger.info(f"   💵 Preço: ${preco_unitario:.8f}")
                    logger.info(f"   💲 Valor USDT: ${valor_usdt:.8f}")
                    logger.info("")
                
                total_usdt += valor_usdt
        
        logger.info(f"🏆 VALOR TOTAL DA CONTA: ${total_usdt:.8f}")
        logger.info("")
        
        # 4. Verificar problemas específicos
        logger.info("🔍 === VERIFICAÇÃO DE PROBLEMAS ===")
        
        # Verificar BTC especificamente
        for balance in conta.get('balances', []):
            if balance['asset'] == 'BTC':
                btc_free = float(balance['free'])
                btc_locked = float(balance['locked'])
                btc_total = btc_free + btc_locked
                
                logger.info(f"🔍 ANÁLISE BTC DETALHADA:")
                logger.info(f"   📊 BTC Livre: {btc_free:.8f}")
                logger.info(f"   🔒 BTC Bloqueado: {btc_locked:.8f}")
                logger.info(f"   📈 BTC Total: {btc_total:.8f}")
                
                if btc_total > 0:
                    btc_preco = precos.get('BTCUSDT', 0)
                    btc_valor = btc_total * btc_preco
                    logger.info(f"   💵 Preço BTC: ${btc_preco:.2f}")
                    logger.info(f"   💲 Valor Total: ${btc_valor:.8f}")
                    
                    # Verificar quantidade mínima
                    logger.info(f"   🔍 Verificação de venda:")
                    if btc_free > 0:
                        # Tentar simular venda
                        logger.info(f"   ✅ BTC disponível para venda: {btc_free:.8f}")
                        
                        # Verificar valor mínimo (normalmente $10 para BTC)
                        if btc_valor < 10:
                            logger.warning(f"   ⚠️ PROBLEMA: Valor ${btc_valor:.8f} < $10 (mínimo Binance)")
                        else:
                            logger.info(f"   ✅ Valor acima do mínimo")
                    else:
                        logger.warning(f"   ⚠️ PROBLEMA: Sem BTC livre para venda")
                else:
                    logger.warning(f"   ⚠️ PROBLEMA: Sem BTC na conta!")
                
                break
        
        # 5. Informações da conta
        logger.info("")
        logger.info("📋 === INFORMAÇÕES DA CONTA ===")
        logger.info(f"🔹 Pode negociar: {conta.get('canTrade', False)}")
        logger.info(f"🔹 Pode sacar: {conta.get('canWithdraw', False)}")
        logger.info(f"🔹 Pode depositar: {conta.get('canDeposit', False)}")
        logger.info(f"🔹 Taxa de trading: {conta.get('makerCommission', 0) / 10000}%")
        
        return conta
    
    def testar_ordem_minima_btc(self):
        """Testar qual a quantidade mínima para BTC"""
        logger.info("🧪 === TESTE DE QUANTIDADE MÍNIMA BTC ===")
        
        # Obter informações do símbolo
        try:
            response = requests.get(f"{BASE_URL}/api/v3/exchangeInfo", timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for symbol_info in data['symbols']:
                    if symbol_info['symbol'] == 'BTCUSDT':
                        logger.info("📋 Regras BTCUSDT:")
                        
                        for filter_info in symbol_info['filters']:
                            if filter_info['filterType'] == 'LOT_SIZE':
                                logger.info(f"   📏 Quantidade mín: {filter_info['minQty']}")
                                logger.info(f"   📏 Quantidade máx: {filter_info['maxQty']}")
                                logger.info(f"   📏 Step size: {filter_info['stepSize']}")
                            
                            elif filter_info['filterType'] == 'NOTIONAL':
                                logger.info(f"   💰 Valor mín (NOTIONAL): ${filter_info['minNotional']}")
                            
                            elif filter_info['filterType'] == 'MIN_NOTIONAL':
                                logger.info(f"   💰 Valor mín (MIN_NOTIONAL): ${filter_info['minNotional']}")
                        
                        logger.info(f"   📊 Status: {symbol_info['status']}")
                        break
                        
        except Exception as e:
            logger.error(f"Erro ao obter info do símbolo: {e}")

def main():
    """Executar diagnóstico"""
    logger.info("🩺 Iniciando Diagnóstico da Conta...")
    
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
        
        # Executar diagnóstico
        diagnostico = DiagnosticoConta(api_key, api_secret)
        diagnostico.diagnosticar_conta_completo()
        diagnostico.testar_ordem_minima_btc()
        
        logger.info("✅ Diagnóstico concluído!")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()