#!/usr/bin/env python3
"""
Verificar se a conta é Binance US ou tem restrições
"""

import json
import requests
from moises_estrategias_avancadas import TradingAvancado

def verificar_conta_restricoes():
    print("=== VERIFICAÇÃO DE RESTRIÇÕES ===")
    
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    dados_paulo = list(config.values())[0]
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="VERIFICACAO"
    )
    
    # 1. Testar se consegue obter status do sistema
    print("1. Status do sistema Binance:")
    try:
        r = requests.get('https://api.binance.com/api/v3/systemStatus', timeout=5)
        if r.status_code == 200:
            status = r.json()
            print(f"   Status: {status}")
        else:
            print(f"   Erro: {r.status_code}")
    except Exception as e:
        print(f"   Erro: {e}")
    
    # 2. Verificar informações da conta
    print("\n2. Informações detalhadas da conta:")
    account = trader._request('GET', '/api/v3/account', {}, signed=True)
    
    if account.get('error'):
        print(f"   Erro: {account}")
    else:
        print(f"   Account Type: {account.get('accountType', 'N/A')}")
        print(f"   Can Trade: {account.get('canTrade', False)}")
        print(f"   Can Deposit: {account.get('canDeposit', False)}")
        print(f"   Can Withdraw: {account.get('canWithdraw', False)}")
        print(f"   Buyer Commission: {account.get('buyerCommission', 0)}")
        print(f"   Seller Commission: {account.get('sellerCommission', 0)}")
        print(f"   Taker Commission: {account.get('takerCommission', 0)}")
        print(f"   Maker Commission: {account.get('makerCommission', 0)}")
        
        # Verificar permissões
        permissions = account.get('permissions', [])
        print(f"   Permissions: {permissions}")
        
        if 'SPOT' not in permissions:
            print("   ❌ SPOT trading não permitido!")
        else:
            print("   ✅ SPOT trading permitido")
    
    # 3. Testar diferentes endpoints
    print("\n3. Testando diferentes endpoints:")
    
    # Testar ordem OCO (mais restritiva)
    print("   Testando capacidade OCO...")
    try:
        # Não executar, apenas ver se o endpoint responde
        params_oco = {
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'quantity': '0.001',
            'price': '30000',
            'stopPrice': '25000',
            'stopLimitPrice': '24000',
            'stopLimitTimeInForce': 'GTC',
            'timeInForce': 'GTC'
        }
        
        # Usar test endpoint
        resultado_oco = trader._request('POST', '/api/v3/order/oco/test', params_oco, signed=True)
        
        if resultado_oco.get('error'):
            if '400' in str(resultado_oco):
                print("   OCO: Endpoint existe, mas parâmetros rejeitados (normal)")
            else:
                print(f"   OCO Error: {resultado_oco}")
        else:
            print("   OCO: OK")
            
    except Exception as e:
        print(f"   OCO Error: {e}")
    
    # 4. Verificar se precisa de headers especiais
    print("\n4. Testando com headers adicionais:")
    
    import time
    import hmac
    import hashlib
    from urllib.parse import urlencode
    
    # Tentar requisição manual com todos os headers
    try:
        timestamp = int(time.time() * 1000)
        params = {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '1.0',
            'recvWindow': 5000,
            'timestamp': timestamp
        }
        
        query_string = urlencode(params)
        signature = hmac.new(
            dados_paulo['api_secret'].encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        params['signature'] = signature
        
        headers = {
            'X-MBX-APIKEY': dados_paulo['api_key'],
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        url = 'https://api.binance.com/api/v3/order/test'
        
        r = requests.post(url, data=params, headers=headers, timeout=10)
        
        print(f"   Status Code: {r.status_code}")
        print(f"   Response: {r.text}")
        
        if r.status_code == 200:
            print("   ✅ Requisição manual funcionou!")
        else:
            print(f"   ❌ Erro na requisição manual")
            
    except Exception as e:
        print(f"   Erro na requisição manual: {e}")

if __name__ == "__main__":
    verificar_conta_restricoes()