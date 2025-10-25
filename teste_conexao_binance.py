#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 TESTE DE CONEXÃO REAL - BINANCE API
====================================
Testando conexão com suas API keys reais
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
import sys
from datetime import datetime

def test_binance_connection():
    """Testa conexão com Binance"""
    try:
        from binance.client import Client
        from binance.exceptions import BinanceAPIException
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("🎂🔗 TESTE DE CONEXÃO REAL - MOISES 🔗🎂")
        print("=" * 50)
        print("🎯 Testando API keys para começar a ajudar crianças")
        print("=" * 50)
        
        # Carregar API keys
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            print("❌ API Keys não encontradas no .env")
            return False
        
        print(f"🔑 API Key: {api_key[:20]}...")
        print(f"🔐 Secret: {api_secret[:20]}...")
        
        print("\n🔍 TESTANDO CONEXÃO...")
        
        # Testar mainnet (produção)
        print("\n💎 Testando MAINNET (produção real)...")
        try:
            client = Client(api_key, api_secret, testnet=False)
            status = client.get_system_status()
            print(f"✅ Mainnet conectado: {status}")
            
            account = client.get_account()
            print(f"✅ Tipo de conta: {account['accountType']}")
            print(f"✅ Permissões: {', '.join(account['permissions'])}")
            
            # Mostrar saldos reais
            balances = [b for b in account['balances'] 
                       if float(b['free']) > 0 or float(b['locked']) > 0]
            
            print(f"\n💰 SALDOS REAIS:")
            total_value_usdt = 0
            
            for balance in balances:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    print(f"  {asset}: {total:.8f} (Livre: {free:.8f})")
                    
                    if asset == 'USDT':
                        total_value_usdt += total
            
            print(f"\n💰 VALOR TOTAL: ${total_value_usdt:.2f} USDT")
            print(f"💱 Em reais: R$ {total_value_usdt * 5.5:.2f}")
            
            # Testar permissões
            if 'SPOT' in account['permissions']:
                print("\n✅ Permissão SPOT ativa - Pode fazer trades!")
            else:
                print("\n❌ Permissão SPOT não ativa")
            
            print("\n" + "="*50)
            print("🎉 CONEXÃO REAL ESTABELECIDA! 🎉")
            print("💝 MOISES pode ajudar crianças DE VERDADE!")
            print("=" * 50)
            
            return True
            
        except BinanceAPIException as e:
            print(f"❌ Erro da API: {e}")
            return False
            
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return False

    except ImportError as e:
        print(f"❌ Erro de importação: {e}")
        return False

def main():
    """Função principal"""
    success = test_binance_connection()
    
    if success:
        print("\n🎂 PRÓXIMOS PASSOS:")
        print("1. 🚀 Execute: python dashboard_lucros_moises.py")
        print("2. 📊 Acesse: http://localhost:8000")
        print("3. 💝 Veja os lucros ajudando crianças!")
        print("\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
    else:
        print("\n🔧 Verifique as API keys e tente novamente")

if __name__ == "__main__":
    main()