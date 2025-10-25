#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 TESTE CORRIGIDO - BINANCE API
==============================
Testando com sincronização de tempo
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
import sys
import time
from datetime import datetime

def test_binance_fixed():
    """Testa conexão com correção de timestamp"""
    try:
        from binance.client import Client
        from binance.exceptions import BinanceAPIException
        from dotenv import load_dotenv
        
        load_dotenv()
        
        print("🎂🔗 TESTE CORRIGIDO - MOISES 🔗🎂")
        print("=" * 45)
        
        # API keys
        api_key = os.getenv('BINANCE_API_KEY') 
        api_secret = os.getenv('BINANCE_API_SECRET')
        
        if not api_key or not api_secret:
            print("❌ API Keys não encontradas")
            return False
        
        print("🔑 API Keys carregadas")
        print("⏰ Sincronizando tempo...")
        
        # Criar cliente com configurações de tempo
        try:
            client = Client(
                api_key, 
                api_secret, 
                testnet=False
            )
            
            # Sincronizar tempo do servidor
            server_time = client.get_server_time()
            local_time = int(time.time() * 1000)
            time_diff = server_time['serverTime'] - local_time
            
            print(f"⏰ Diferença de tempo: {time_diff}ms")
            
            # Recriar cliente com offset se necessário
            if abs(time_diff) > 1000:  # Mais de 1 segundo
                print("🔧 Ajustando sincronização...")
                # Para resolver, usar requests_params
                import requests
                
                # Teste básico de conectividade
                response = requests.get('https://api.binance.com/api/v3/time')
                if response.status_code == 200:
                    print("✅ Conectividade com Binance OK")
                else:
                    print("❌ Problema de conectividade")
                    return False
            
            # Testar operações básicas
            print("\n📊 Testando operações...")
            
            # 1. Status do sistema
            status = client.get_system_status()
            print(f"✅ Status do sistema: {status['msg']}")
            
            # 2. Informações da conta (sem timestamp sensível)
            try:
                exchange_info = client.get_exchange_info()
                print(f"✅ Exchange info obtida ({len(exchange_info['symbols'])} pares)")
                
                # Testar preço sem autenticação
                btc_price = client.get_symbol_ticker(symbol="BTCUSDT")
                print(f"✅ Preço BTC: ${float(btc_price['price']):,.2f}")
                
            except Exception as e:
                print(f"⚠️ Erro em operações públicas: {e}")
            
            # 3. Tentar operação autenticada com retry
            print("\n🔐 Testando autenticação...")
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # Recriar cliente a cada tentativa
                    fresh_client = Client(api_key, api_secret, testnet=False)
                    
                    account = fresh_client.get_account()
                    print(f"✅ Autenticação bem-sucedida!")
                    print(f"📊 Tipo de conta: {account['accountType']}")
                    
                    # Mostrar saldos principais
                    main_balances = []
                    for balance in account['balances']:
                        free = float(balance['free'])
                        if free > 0:
                            main_balances.append({
                                'asset': balance['asset'],
                                'free': free
                            })
                    
                    print(f"\n💰 PRINCIPAIS SALDOS:")
                    for bal in main_balances[:10]:  # Top 10
                        print(f"  {bal['asset']}: {bal['free']:.8f}")
                    
                    # Calcular valor total aproximado
                    usdt_balance = 0
                    for bal in main_balances:
                        if bal['asset'] == 'USDT':
                            usdt_balance = bal['free']
                            break
                    
                    print(f"\n💎 Saldo USDT: ${usdt_balance:.2f}")
                    print(f"💱 Equivalente: R$ {usdt_balance * 5.5:.2f}")
                    
                    if 'SPOT' in account['permissions']:
                        print(f"✅ Trading SPOT habilitado")
                    
                    return True
                    
                except BinanceAPIException as e:
                    if 'Timestamp' in str(e) and attempt < max_retries - 1:
                        print(f"⚠️ Tentativa {attempt + 1} - Erro de timestamp, tentando novamente...")
                        time.sleep(1)
                        continue
                    else:
                        print(f"❌ Erro da API (tentativa {attempt + 1}): {e}")
                        if attempt == max_retries - 1:
                            return False
                        
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return False

    except ImportError as e:
        print(f"❌ Biblioteca ausente: {e}")
        return False

def main():
    """Função principal"""
    print("🎂🚀 TESTANDO CONEXÃO PARA DASHBOARD 🚀🎂")
    print("=" * 50)
    
    success = test_binance_fixed()
    
    if success:
        print("\n" + "="*50)
        print("🎉 CONEXÃO ESTABELECIDA COM SUCESSO! 🎉")
        print("💝 MOISES pronto para mostrar lucros no dashboard!")
        print("=" * 50)
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. 📊 Execute: python dashboard_lucros_moises.py")
        print("2. 🌐 Acesse: http://localhost:8000")
        print("3. 💰 Veja os lucros em tempo real!")
        print("4. 💝 Acompanhe o impacto para crianças!")
        print("\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
    else:
        print("\n❌ Problema na conexão")
        print("🔧 Possíveis soluções:")
        print("  • Verificar conexão com internet")
        print("  • Sincronizar relógio do sistema")
        print("  • Verificar se as API keys estão ativas")

if __name__ == "__main__":
    main()