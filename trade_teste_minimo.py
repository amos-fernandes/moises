#!/usr/bin/env python3
"""
Trade de Teste Mínimo - $5 ADAUSDT
"""

import json
from moises_estrategias_avancadas import TradingAvancado

def trade_teste_minimo():
    print("=== TRADE TESTE MÍNIMO $5 ===")
    
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    dados_paulo = list(config.values())[0]
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="TESTE_MINIMO"
    )
    
    saldo = trader.get_saldo_usdt()
    print(f"Saldo: ${saldo:.2f}")
    
    # Trade mínimo de $5
    oportunidade = {
        'estrategia': 'teste_minimo',
        'confidence': 85,
        'entry_price': 0.6762,
        'stop_loss': 0.6562,
        'take_profit': 0.7100
    }
    
    # Forçar tamanho mínimo
    print("Executando trade de $5...")
    
    try:
        # Tentar requisição manual mais simples
        params = {
            'symbol': 'ADAUSDT',
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': '5.00'  # Exato $5
        }
        
        print(f"Parâmetros: {params}")
        
        resultado = trader._request('POST', '/api/v3/order', params, signed=True)
        print(f"Resultado: {resultado}")
        
        if resultado.get('error'):
            print(f"❌ Erro: {resultado}")
        else:
            print("✅ Trade executado!")
            print(f"Order ID: {resultado.get('orderId')}")
            print(f"Executado: {resultado.get('executedQty')} ADA")
            
            # Verificar saldo após
            novo_saldo = trader.get_saldo_usdt()
            print(f"Novo saldo: ${novo_saldo:.2f}")
            
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    confirmacao = input("Executar trade teste de $5? (SIM/não): ")
    if confirmacao == 'SIM':
        trade_teste_minimo()
    else:
        print("Teste cancelado")