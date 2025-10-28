#!/usr/bin/env python3
"""
Debug detalhado da API Binance
"""

import requests
import json
from moises_estrategias_avancadas import TradingAvancado

def debug_binance_api():
    print("=== DEBUG API BINANCE ===")
    
    # 1. Testar informações do símbolo
    print("1. Informações do ADAUSDT:")
    try:
        r = requests.get('https://api.binance.com/api/v3/exchangeInfo?symbol=ADAUSDT', timeout=5)
        if r.status_code == 200:
            info = r.json()
            symbol_info = info['symbols'][0]
            
            print(f"   Status: {symbol_info['status']}")
            print(f"   Permissions: {symbol_info['permissions']}")
            
            # Filtros importantes
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'NOTIONAL':
                    print(f"   Min Notional: {filter_item.get('minNotional', 'N/A')}")
                elif filter_item['filterType'] == 'MIN_NOTIONAL':
                    print(f"   Min Notional: {filter_item.get('minNotional', 'N/A')}")
                elif filter_item['filterType'] == 'LOT_SIZE':
                    print(f"   Min Qty: {filter_item.get('minQty', 'N/A')}")
                    print(f"   Step Size: {filter_item.get('stepSize', 'N/A')}")
        else:
            print(f"   Erro: {r.status_code}")
    except Exception as e:
        print(f"   Erro: {e}")
    
    # 2. Testar preço atual
    print("\n2. Preço atual ADAUSDT:")
    try:
        r = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=ADAUSDT', timeout=5)
        if r.status_code == 200:
            price_data = r.json()
            print(f"   Preço: ${float(price_data['price']):.4f}")
        else:
            print(f"   Erro: {r.status_code}")
    except Exception as e:
        print(f"   Erro: {e}")
    
    # 3. Testar conexão da conta
    print("\n3. Teste de conta:")
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    dados_paulo = list(config.values())[0]
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="DEBUG"
    )
    
    # Testar account info
    account = trader._request('GET', '/api/v3/account', {}, signed=True)
    if account.get('error'):
        print(f"   Erro na conta: {account}")
    else:
        print(f"   Conta OK - Can Trade: {account.get('canTrade', False)}")
        print(f"   Can Deposit: {account.get('canDeposit', False)}")
        print(f"   Can Withdraw: {account.get('canWithdraw', False)}")
    
    # 4. Testar ordem de teste (não executa)
    print("\n4. Teste de ordem (TEST):")
    try:
        params = {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': '5.00'
        }
        
        # Usar endpoint de teste
        resultado_teste = trader._request('POST', '/api/v3/order/test', params, signed=True)
        
        if resultado_teste.get('error'):
            print(f"   Erro no teste: {resultado_teste}")
        else:
            print(f"   Teste OK: {resultado_teste}")
            
    except Exception as e:
        print(f"   Erro: {e}")

if __name__ == "__main__":
    debug_binance_api()