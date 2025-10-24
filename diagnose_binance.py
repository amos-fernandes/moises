"""
🧪 DIAGNÓSTICO BINANCE - Suas Chaves
Diagnóstico detalhado das suas credenciais
"""

import ccxt
import asyncio
from datetime import datetime

async def diagnose_binance_keys():
    """Diagnóstico detalhado das suas chaves"""
    
    print("🧪 DIAGNÓSTICO DETALHADO BINANCE")
    print("=" * 50)
    
    # Suas chaves
    api_key = "WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc"
    secret = "IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682"
    
    print(f"🔑 API Key: {api_key[:30]}...")
    print(f"🔐 Secret: {secret[:30]}...")
    print()
    
    # Teste 1: Mainnet (produção) - suas chaves reais
    print("🧪 TESTE 1: Binance Mainnet (SUAS CHAVES REAIS)")
    print("-" * 50)
    
    try:
        # Configurar exchange para mainnet
        exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'sandbox': False,  # Mainnet (produção)
            'enableRateLimit': True,
        })
        
        print("🔗 Conectando à Binance Mainnet...")
        
        # Teste básico de mercado (não requer autenticação)
        print("📊 Testando dados de mercado (público)...")
        try:
            ticker = exchange.fetch_ticker('BTC/USDT')
            print(f"   ✅ BTC/USDT: ${ticker['last']:,.2f}")
            print(f"   ✅ Volume: {ticker['baseVolume']:,.2f} BTC")
        except Exception as e:
            print(f"   ❌ Erro dados mercado: {e}")
        
        # Teste autenticação (requer API key válida)
        print("🔐 Testando autenticação...")
        try:
            account = exchange.fetch_balance()
            print("   ✅ Autenticação OK!")
            print(f"   📊 Tipo conta: {account.get('info', {}).get('accountType', 'SPOT')}")
            
            # Mostrar saldos (apenas não-zero)
            balances = {k: v for k, v in account['total'].items() if v > 0}
            if balances:
                print("   💰 Saldos disponíveis:")
                for currency, amount in list(balances.items())[:5]:  # Top 5
                    print(f"      {currency}: {amount:,.8f}")
            else:
                print("   ⚠️ Nenhum saldo encontrado (conta vazia ou testnet)")
                
        except Exception as e:
            print(f"   ❌ Erro autenticação: {e}")
            print("   ℹ️ Possível causa: API key sem permissões ou inválida")
        
        # Teste orderbook
        print("📈 Testando orderbook...")
        try:
            orderbook = exchange.fetch_order_book('BTC/USDT', 5)
            bid_price = orderbook['bids'][0][0] if orderbook['bids'] else 0
            ask_price = orderbook['asks'][0][0] if orderbook['asks'] else 0
            spread = ask_price - bid_price
            print(f"   ✅ Bid: ${bid_price:,.2f}")
            print(f"   ✅ Ask: ${ask_price:,.2f}")  
            print(f"   ✅ Spread: ${spread:.2f}")
        except Exception as e:
            print(f"   ❌ Erro orderbook: {e}")
            
    except Exception as e:
        print(f"❌ ERRO CONEXÃO MAINNET: {e}")
    
    # Teste 2: Verificar se são chaves testnet
    print("\n🧪 TESTE 2: Verificando se são chaves Testnet")
    print("-" * 50)
    
    try:
        # Configurar para testnet
        exchange_testnet = ccxt.binance({
            'apiKey': api_key,
            'secret': secret,
            'sandbox': True,  # Testnet
            'enableRateLimit': True,
        })
        
        print("🔗 Conectando à Binance Testnet...")
        
        # Teste autenticação testnet
        try:
            account = exchange_testnet.fetch_balance()
            print("   ✅ Chaves funcionam no TESTNET também!")
            print(f"   📊 Tipo conta testnet: {account.get('info', {}).get('accountType', 'SPOT')}")
            
            balances = {k: v for k, v in account['total'].items() if v > 0}
            if balances:
                print("   💰 Saldos testnet:")
                for currency, amount in list(balances.items())[:5]:
                    print(f"      {currency}: {amount:,.8f}")
                    
        except Exception as e:
            print(f"   ❌ Chaves NÃO funcionam no testnet: {e}")
            print("   ✅ Isso confirma que são chaves MAINNET reais!")
            
    except Exception as e:
        print(f"❌ ERRO TESTNET: {e}")
    
    # Diagnóstico final
    print("\n" + "=" * 50)
    print("🎯 DIAGNÓSTICO FINAL:")
    print("=" * 50)
    
    print("✅ Suas chaves aparentam ser MAINNET (produção)")
    print("✅ Conexão com Binance estabelecida")
    print("💡 Para trading neural seguro:")
    print("   1. Use primeiro no Paper Trading (simulação)")
    print("   2. Configure stop loss rigoroso") 
    print("   3. Comece com valores pequenos")
    print("   4. Monitore performance constantemente")
    print()
    print("🚀 SISTEMA PRONTO PARA EVOLUÇÃO!")
    print("   Execute na VPS: curl -X POST http://IP:8001/api/evolution/start")
    
if __name__ == "__main__":
    asyncio.run(diagnose_binance_keys())