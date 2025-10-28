#!/usr/bin/env python3
"""
Teste com quantity em vez de quoteOrderQty
"""

import json
from moises_estrategias_avancadas import TradingAvancado

def trade_com_quantity():
    print("=== TESTE COM QUANTITY ===")
    
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    dados_paulo = list(config.values())[0]
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="QUANTITY_TEST"
    )
    
    # Preço atual: $0.6747
    # Para $5, precisamos: 5 / 0.6747 = 7.41 ADA
    # Arredondado para múltiplo de 0.1: 7.4 ADA
    
    quantidade = 7.4  # ADA
    preco_estimado = quantidade * 0.6747
    
    print(f"Quantidade: {quantidade} ADA")
    print(f"Valor estimado: ${preco_estimado:.2f}")
    
    # Primeiro, teste
    params_teste = {
        'symbol': 'ADAUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'quantity': f"{quantidade:.1f}"
    }
    
    print(f"Parâmetros teste: {params_teste}")
    
    resultado_teste = trader._request('POST', '/api/v3/order/test', params_teste, signed=True)
    
    if resultado_teste.get('error'):
        print(f"❌ Erro no teste: {resultado_teste}")
        
        # Tentar com quantidade menor
        print("\nTentando com 1.0 ADA...")
        params_teste2 = {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': '1.0'
        }
        
        resultado_teste2 = trader._request('POST', '/api/v3/order/test', params_teste2, signed=True)
        
        if resultado_teste2.get('error'):
            print(f"❌ Erro com 1.0 ADA: {resultado_teste2}")
        else:
            print(f"✅ Teste com 1.0 ADA OK: {resultado_teste2}")
            
            confirmacao = input("Executar trade real com 1.0 ADA? (SIM/não): ")
            if confirmacao == 'SIM':
                params_real = {
                    'symbol': 'ADAUSDT',
                    'side': 'BUY',
                    'type': 'MARKET',
                    'quantity': '1.0'
                }
                
                resultado_real = trader._request('POST', '/api/v3/order', params_real, signed=True)
                
                if resultado_real.get('error'):
                    print(f"❌ Erro no trade real: {resultado_real}")
                else:
                    print("✅ TRADE EXECUTADO!")
                    print(f"Order ID: {resultado_real.get('orderId')}")
                    print(f"Executado: {resultado_real.get('executedQty')} ADA")
                    print(f"Preço médio: ${float(resultado_real.get('fills', [{}])[0].get('price', 0)):.4f}")
                    
                    # Verificar saldo
                    novo_saldo = trader.get_saldo_usdt()
                    print(f"Novo saldo USDT: ${novo_saldo:.2f}")
    else:
        print(f"✅ Teste OK: {resultado_teste}")

if __name__ == "__main__":
    trade_com_quantity()