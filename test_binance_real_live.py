"""
🚨 TESTE BINANCE REAL - CONTA LIVE
⚠️ MÁXIMA SEGURANÇA - SÓ LEITURA DE DADOS
"""

import asyncio
import json
from datetime import datetime

async def test_binance_live_safe():
    """
    Teste SEGURO com conta Binance real
    ⚠️ APENAS LEITURA - NÃO FAZ TRADES
    """
    
    # Suas credenciais (modo LIVE)
    API_KEY = "WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc"
    SECRET = "IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682"
    
    print("🚨 TESTE BINANCE REAL - MODO SEGURO")
    print("=" * 60)
    print("⚠️  APENAS LEITURA DE DADOS - NÃO EXECUTA TRADES")
    print("💰 Conta: LIVE (não testnet)")
    print("🔒 Segurança: Máxima - só consultas")
    print("=" * 60)
    
    try:
        # Importar binance tester
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        
        from src.trading.binance_real_tester import binance_tester
        
        # TESTE MODO LIVE (use_testnet=False)
        print("🔗 Iniciando teste com conta REAL...")
        
        test_results = await binance_tester.test_binance_connection(
            api_key=API_KEY,
            secret=SECRET,
            use_testnet=False  # ⚠️ CONTA REAL
        )
        
        print("\n📊 RESULTADOS DO TESTE:")
        print("=" * 40)
        
        # Status geral
        connection_status = test_results.get("connection_status")
        print(f"🔗 Conexão: {connection_status}")
        
        if connection_status == "SUCCESS":
            print("✅ CONECTADO COM SUCESSO!")
            
            tests = test_results.get("tests", {})
            
            # Autenticação
            auth = tests.get("authentication", {})
            if auth.get("status") == "SUCCESS":
                print(f"✅ Autenticação: OK")
                print(f"   Account Type: {auth.get('account_type', 'N/A')}")
                permissions = auth.get('permissions', [])
                print(f"   Permissions: {', '.join(permissions) if permissions else 'N/A'}")
            else:
                print(f"❌ Autenticação: {auth.get('error', 'Falhou')}")
            
            # Market Data
            market = tests.get("market_data", {})
            if market.get("status") == "SUCCESS":
                print(f"✅ Market Data: OK")
                print(f"   BTC/USDT: ${market.get('price', 'N/A')}")
                print(f"   Volume: {market.get('volume', 'N/A')} BTC")
            else:
                print(f"❌ Market Data: {market.get('error', 'Falhou')}")
            
            # Orderbook
            orderbook = tests.get("orderbook", {})
            if orderbook.get("status") == "SUCCESS":
                print(f"✅ Orderbook: OK")
                print(f"   Bids: {orderbook.get('bids_count', 0)}")
                print(f"   Asks: {orderbook.get('asks_count', 0)}")
                print(f"   Spread: ${orderbook.get('spread', 0):.2f}")
            else:
                print(f"❌ Orderbook: {orderbook.get('error', 'Falhou')}")
            
            # Balance (conta real)
            balance = tests.get("balance", {})
            if balance.get("status") == "SUCCESS":
                print(f"✅ Saldo: Acessível")
                currencies = balance.get('currencies_available', [])
                print(f"   Moedas: {', '.join(currencies) if currencies else 'Nenhuma'}")
                print(f"   Total: {balance.get('balance_count', 0)} moedas")
            else:
                print(f"❌ Saldo: {balance.get('error', 'Inacessível')}")
                
        else:
            print(f"❌ FALHA NA CONEXÃO: {test_results.get('error', 'Erro desconhecido')}")
        
        # Resumo de segurança
        print("\n🔒 RESUMO DE SEGURANÇA:")
        print("=" * 40)
        
        summary = binance_tester.get_connection_summary()
        
        if summary.get("binance_connected"):
            print("✅ Conexão estabelecida com sucesso")
            print(f"📊 Score: {summary.get('connectivity_score', 0):.1%}")
            print(f"🎯 Ready for Neural: {summary.get('ready_for_neural_trading', False)}")
            
            print("\n🚀 PRÓXIMO PASSO:")
            print("   Se tudo OK, execute:")
            print("   curl -X POST http://SEU_IP:8001/api/evolution/start")
            print("   Para ativar evolução de 50% → 85% accuracy!")
        else:
            print("❌ Problemas na conexão - verificar configurações")
        
        print(f"\n⏰ Teste realizado: {datetime.now().strftime('%H:%M:%S')}")
        print("🔒 Nenhum trade foi executado - apenas leitura")
        
        return test_results
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    # Executar teste
    result = asyncio.run(test_binance_live_safe())
    
    if result and result.get("connection_status") == "SUCCESS":
        print("\n🎉 TESTE BINANCE REAL CONCLUÍDO COM SUCESSO!")
        print("✅ Sistema pronto para trading neural!")
    else:
        print("\n❌ Problemas no teste - verificar configuração")