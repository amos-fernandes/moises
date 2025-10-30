"""
🔄 CONVERSOR PARA USDT - Limpar posições
Objetivo: Vender BTC e ETH para ficar 100% USDT
Estratégia: Reset total para focar apenas em BTC
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
        logging.FileHandler('conversao_usdt.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class ConversaoUSDT:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        logger.info("🔄 === CONVERSÃO PARA USDT ===")
        logger.info("🎯 Objetivo: 100% USDT para focar em BTC")
        logger.info("=" * 50)
    
    def get_server_time(self):
        """Timestamp do servidor"""
        try:
            response = requests.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except Exception:
            pass
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
    
    def get_account_info(self):
        """Info da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_preco(self, symbol):
        """Preço atual"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=10)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception:
            pass
        return 0
    
    def vender_ativo(self, asset, quantidade):
        """Vender ativo específico"""
        symbol = f"{asset}USDT"
        
        logger.warning(f"🔄 Vendendo {asset}: {quantidade}")
        
        # Formatação por ativo
        if asset == 'BTC':
            qty = f"{quantidade:.5f}"
        elif asset == 'ETH':
            qty = f"{quantidade:.4f}"
        else:
            qty = f"{quantidade:.2f}"
        
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': qty
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda {asset}: {resultado.get('msg')}")
            return False
        
        # Calcular valor aproximado
        preco = self.get_preco(symbol)
        valor_usdt = quantidade * preco
        
        logger.info(f"✅ {asset} vendido: ~${valor_usdt:.2f} USDT")
        return True
    
    def converter_tudo_usdt(self):
        """Converter todas as posições para USDT"""
        logger.info("🔍 Verificando posições atuais...")
        
        conta = self.get_account_info()
        if conta.get('error'):
            logger.error(f"❌ Erro conta: {conta.get('msg')}")
            return False
        
        # Analisar ativos
        vendas_realizadas = 0
        valor_total_vendido = 0
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            
            # Pular USDT e ativos com saldo zero
            if asset == 'USDT' or free <= 0:
                continue
            
            # Verificar se vale a pena vender
            symbol = f"{asset}USDT"
            preco = self.get_preco(symbol)
            valor_usdt = free * preco
            
            if valor_usdt >= 1.0:  # Só vender se > $1
                logger.info(f"📊 {asset}: {free} = ${valor_usdt:.2f}")
                
                if self.vender_ativo(asset, free):
                    vendas_realizadas += 1
                    valor_total_vendido += valor_usdt
                    time.sleep(2)  # Pausa entre vendas
                else:
                    logger.warning(f"⚠️ Falha ao vender {asset}")
            else:
                logger.info(f"📊 {asset}: ${valor_usdt:.2f} (muito pequeno, ignorando)")
        
        # Resultado final
        logger.info("=" * 50)
        logger.info(f"✅ Vendas realizadas: {vendas_realizadas}")
        logger.info(f"💰 Valor total convertido: ~${valor_total_vendido:.2f}")
        
        # Verificar saldo final
        time.sleep(3)
        conta_final = self.get_account_info()
        
        if not conta_final.get('error'):
            for balance in conta_final.get('balances', []):
                if balance['asset'] == 'USDT':
                    usdt_final = float(balance['free'])
                    logger.info(f"🎯 USDT final: ${usdt_final:.2f}")
                    break
        
        return True

def main():
    """Executar conversão"""
    logger.info("🔄 Iniciando conversão para USDT...")
    
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
        
        conversor = ConversaoUSDT(api_key, api_secret)
        
        # Confirmar com usuário
        logger.warning("⚠️ ATENÇÃO: Vai converter TODAS as posições para USDT!")
        logger.warning("⚠️ BTC e ETH serão vendidos!")
        logger.warning("⚠️ Digite 'SIM' para continuar ou qualquer coisa para cancelar:")
        
        # Executar conversão (removendo input para automático)
        logger.info("🚀 Executando conversão automática...")
        conversor.converter_tudo_usdt()
        
        logger.info("✅ Conversão concluída!")
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()