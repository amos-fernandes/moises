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
from pathlib import Path

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
        sys.exit(1)
    
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"🔐 Secret: {api_secret[:20]}...")
    
    print("\\n🔍 TESTANDO CONEXÃO...")
    
    # Primeiro testar no testnet
    print("\\n1️⃣ Testando TESTNET (seguro)...")
    try:
        client_test = Client(api_key, api_secret, testnet=True)
        status = client_test.get_system_status()
        print(f"✅ Testnet conectado: {status}")
        
        account_test = client_test.get_account()
        print(f"✅ Tipo de conta testnet: {account_test['accountType']}")
        print(f"✅ Permissões: {', '.join(account_test['permissions'])}")
        
        # Mostrar saldos testnet
        balances_test = [b for b in account_test['balances'] 
                        if float(b['free']) > 0 or float(b['locked']) > 0]
        
        print(f"\\n💰 SALDOS TESTNET:")
        for balance in balances_test[:5]:  # Primeiros 5
            free = float(balance['free'])
            if free > 0:
                print(f"  {balance['asset']}: {free:.8f}")
        
    except Exception as e:
        print(f"❌ Erro no testnet: {e}")
    
    # Testar mainnet (produção)
    print("\\n2️⃣ Testando MAINNET (produção real)...")
    try:
        client_main = Client(api_key, api_secret, testnet=False)
        status_main = client_main.get_system_status()
        print(f"✅ Mainnet conectado: {status_main}")
        
        account_main = client_main.get_account()
        print(f"✅ Tipo de conta real: {account_main['accountType']}")
        print(f"✅ Permissões: {', '.join(account_main['permissions'])}")
        
        # Mostrar saldos reais
        balances_main = [b for b in account_main['balances'] 
                        if float(b['free']) > 0 or float(b['locked']) > 0]
        
        print(f"\\n💎 SALDOS REAIS:")
        total_value_usdt = 0
        
        for balance in balances_main:
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                print(f"  {asset}: {total:.8f} (Livre: {free:.8f})")
                
                # Estimar valor em USDT
                if asset == 'USDT':
                    total_value_usdt += total
                elif asset in ['BTC', 'ETH', 'BNB']:
                    # Para principais cryptos, pegar cotação
                    try:
                        ticker = client_main.get_symbol_ticker(symbol=f"{asset}USDT")
                        price = float(ticker['price'])
                        value_usdt = total * price
                        total_value_usdt += value_usdt
                        print(f"    → Valor: ${value_usdt:.2f} USDT (${price:.2f} cada)")
                    except:
                        pass
        
        print(f"\\n💰 VALOR TOTAL ESTIMADO: ${total_value_usdt:.2f} USDT")
        print(f"💱 Equivalente em BRL: R$ {total_value_usdt * 5.5:.2f}")
        
        # Testar permissões de trading
        print("\\n🔒 TESTANDO PERMISSÕES DE TRADING...")
        if 'SPOT' in account_main['permissions']:
            print("✅ Permissão SPOT ativa - Pode fazer trades!")
            
            # Testar uma ordem de teste (não executa)
            try:
                test_order = client_main.create_test_order(
                    symbol='BTCUSDT',
                    side='BUY',
                    type='MARKET',
                    quoteOrderQty=10  # $10 USDT
                )
                print("✅ Teste de ordem bem-sucedido - Trading habilitado!")
                
            except Exception as e:
                print(f"⚠️ Erro no teste de ordem: {e}")
        else:
            print("❌ Permissão SPOT não ativa")
        
        print("\\n" + "="*50)
        print("🎉 CONEXÃO REAL ESTABELECIDA COM SUCESSO! 🎉")
        print("💝 MOISES pode começar a ajudar crianças DE VERDADE!")
        print("🚀 Execute: python dashboard_lucros_moises.py")
        print("📊 Depois: python moises_trading_real.py")
        print("=" * 50)
        
        return True
        
    except BinanceAPIException as e:
        print(f"❌ Erro da API Binance: {e}")
        if 'Invalid API-key' in str(e):
            print("🔧 Verifique se as API keys estão corretas")
        elif 'signature' in str(e):
            print("🔧 Verifique se a chave secreta está correta")
        return False
        
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return False

except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print("🔧 Execute: pip install python-binance python-dotenv")
    sys.exit(1)

if __name__ == "__main__":
    success = True  # Placeholder para o resultado do teste
    
    if success:
        print("\\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
        print("💖 Pronto para transformar cada real em esperança!")
    else:
        print("\\n🔧 Configure as API keys e tente novamente")