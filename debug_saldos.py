#!/usr/bin/env python3
"""
Debug do Sistema - Verificar por que saldos estão zerados
"""

import json
from moises_estrategias_avancadas import TradingAvancado

def debug_saldos():
    print("=== DEBUG DOS SALDOS ===")
    
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    for nome, dados in config.items():
        print(f"\n[{nome.upper()}] Debugando...")
        
        try:
            trader = TradingAvancado(
                api_key=dados['api_key'],
                api_secret=dados['api_secret'],
                conta_nome=nome
            )
            
            # Testar requisição direta
            print("  Fazendo requisição de conta...")
            account_data = trader._request('GET', '/api/v3/account', {}, signed=True)
            
            if account_data.get('error'):
                print(f"  ❌ Erro na API: {account_data}")
            else:
                print("  ✅ Requisição OK")
                
                # Verificar balances
                balances = account_data.get('balances', [])
                print(f"  Total de assets: {len(balances)}")
                
                # Procurar USDT
                usdt_balance = None
                for balance in balances:
                    if balance['asset'] == 'USDT':
                        usdt_balance = balance
                        break
                
                if usdt_balance:
                    print(f"  USDT encontrado:")
                    print(f"    Free: {usdt_balance['free']}")
                    print(f"    Locked: {usdt_balance['locked']}")
                    print(f"    Total: {float(usdt_balance['free']) + float(usdt_balance['locked'])}")
                else:
                    print("  ❌ USDT não encontrado nos balances!")
                    # Mostrar primeiros 5 assets
                    print("  Primeiros assets encontrados:")
                    for i, balance in enumerate(balances[:5]):
                        if float(balance['free']) > 0 or float(balance['locked']) > 0:
                            print(f"    {balance['asset']}: {balance['free']} (free) + {balance['locked']} (locked)")
            
            # Testar função get_saldo_usdt
            print("\n  Testando get_saldo_usdt()...")
            saldo = trader.get_saldo_usdt()
            print(f"  Resultado: ${saldo:.2f}")
            
        except Exception as e:
            print(f"  ❌ Erro: {e}")

if __name__ == "__main__":
    debug_saldos()