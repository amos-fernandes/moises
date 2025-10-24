"""
🧪 TESTE LOCAL BINANCE - Suas Credenciais
Testa conectividade usando suas chaves reais
"""

import asyncio
import sys
import os

# Adicionar path do projeto
sys.path.append(os.path.dirname(__file__))

async def test_binance_local():
    """Testa suas credenciais Binance localmente"""
    
    print("🧪 TESTE LOCAL BINANCE - SUAS CREDENCIAIS")
    print("=" * 50)
    
    # Suas chaves
    api_key = "WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc"
    secret = "IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682"
    
    print(f"🔑 API Key: {api_key[:20]}...")
    print(f"🔐 Secret: {secret[:20]}...")
    print()
    
    try:
        # Importar tester
        from src.trading.binance_real_tester import BinanceRealTester
        
        tester = BinanceRealTester()
        
        # 1. Teste Testnet primeiro (mais seguro)
        print("🧪 TESTE 1: Binance Testnet (SEGURO)")
        print("-" * 40)
        
        testnet_results = await tester.test_binance_connection(
            api_key=api_key,
            secret=secret,
            use_testnet=True
        )
        
        print(f"📊 Status: {testnet_results.get('connection_status')}")
        
        if testnet_results.get('connection_status') == 'SUCCESS':
            print("✅ Testnet conectado com sucesso!")
            
            tests = testnet_results.get('tests', {})
            for test_name, result in tests.items():
                if result:
                    status_icon = "✅" if result.get('status') == 'SUCCESS' else "❌"
                    print(f"   {status_icon} {test_name}: {result.get('status')}")
        else:
            print(f"❌ Testnet falhou: {testnet_results.get('error', 'Erro desconhecido')}")
        
        print()
        
        # 2. Teste Mainnet (produção)
        print("🧪 TESTE 2: Binance Mainnet (PRODUÇÃO)")  
        print("-" * 40)
        
        mainnet_results = await tester.test_binance_connection(
            api_key=api_key,
            secret=secret,
            use_testnet=False
        )
        
        print(f"📊 Status: {mainnet_results.get('connection_status')}")
        
        if mainnet_results.get('connection_status') == 'SUCCESS':
            print("✅ Mainnet conectado com sucesso!")
            
            tests = mainnet_results.get('tests', {})
            for test_name, result in tests.items():
                if result:
                    status_icon = "✅" if result.get('status') == 'SUCCESS' else "❌"
                    print(f"   {status_icon} {test_name}: {result.get('status')}")
                    
            # Mostrar summary
            summary = tester.get_connection_summary()
            print(f"\n📈 Conectividade Score: {summary.get('connectivity_score', 0):.1%}")
            print(f"🚀 Pronto para Trading: {summary.get('ready_for_neural_trading', False)}")
            
        else:
            print(f"❌ Mainnet falhou: {mainnet_results.get('error', 'Erro desconhecido')}")
        
        # 3. Resultado final
        print("\n" + "=" * 50)
        summary = tester.get_connection_summary()
        
        if summary.get('ready_for_neural_trading'):
            print("🎉 SUAS CHAVES BINANCE FUNCIONAM PERFEITAMENTE!")
            print("✅ Sistema validado e pronto para trading neural")
            print("🎯 Pode ativar evolução para 85% com segurança!")
            print("\n🚀 PRÓXIMO PASSO:")
            print("   Execute na VPS: curl -X POST http://IP:8001/api/evolution/start")
            
        else:
            print("⚠️ Conectividade precisa de ajustes")
            print("Verifique permissões da API key na Binance")
            
    except Exception as e:
        print(f"❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_binance_local())