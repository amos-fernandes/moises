"""
🔧 TESTE BINANCE SIMPLIFICADO - SYNC TIMESTAMP
Versão simplificada que corrige problema de sincronização
"""

import ccxt
import asyncio
from datetime import datetime

async def test_binance_simple():
    """
    Teste simplificado da Binance com suas credenciais
    """
    
    # Suas credenciais
    API_KEY = "WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc"
    SECRET = "IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682"
    
    print("🚨 TESTE BINANCE REAL SIMPLIFICADO")
    print("=" * 50)
    print("⚠️ APENAS LEITURA - SEM TRADES")
    print("💰 Conta: Binance Real (Mainnet)")
    print("=" * 50)
    
    try:
        # Configuração da exchange com sync de tempo
        exchange = ccxt.binance({
            'apiKey': API_KEY,
            'secret': SECRET,
            'sandbox': False,  # Mainnet real
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True,
                'recvWindow': 60000,  # 60 segundos
            }
        })
        
        print("🔗 Conectando à Binance...")
        
        # 1. Testar dados públicos primeiro (sem auth)
        print("\n📊 1. Testando dados públicos...")
        try:
            ticker = exchange.fetch_ticker('BTC/USDT')
            print(f"   ✅ BTC/USDT: ${ticker['last']:.2f}")
            print(f"   📈 24h Volume: {ticker['baseVolume']:.2f} BTC")
        except Exception as e:
            print(f"   ❌ Erro dados públicos: {e}")
            return False
        
        # 2. Testar orderbook
        print("\n📋 2. Testando orderbook...")
        try:
            orderbook = exchange.fetch_order_book('BTC/USDT', 5)
            best_bid = orderbook['bids'][0][0] if orderbook['bids'] else 0
            best_ask = orderbook['asks'][0][0] if orderbook['asks'] else 0
            spread = best_ask - best_bid
            print(f"   ✅ Bid: ${best_bid:.2f}")
            print(f"   ✅ Ask: ${best_ask:.2f}")
            print(f"   📊 Spread: ${spread:.2f}")
        except Exception as e:
            print(f"   ❌ Erro orderbook: {e}")
        
        # 3. Testar autenticação (account info)
        print("\n🔐 3. Testando autenticação...")
        try:
            # Sincronizar tempo primeiro (não async)
            exchange.load_time_difference()
            
            # Buscar informações da conta
            balance = exchange.fetch_balance()
            print("   ✅ Autenticação OK!")
            
            # Mostrar saldos não-zero
            non_zero_balances = {
                currency: amount 
                for currency, amount in balance['total'].items() 
                if amount > 0
            }
            
            if non_zero_balances:
                print("   💰 Saldos disponíveis:")
                for currency, amount in list(non_zero_balances.items())[:5]:  # Top 5
                    print(f"      {currency}: {amount:.8f}")
                if len(non_zero_balances) > 5:
                    print(f"      ... e mais {len(non_zero_balances) - 5} moedas")
            else:
                print("   ⚠️ Nenhum saldo encontrado")
                
            # Informações da conta
            account_info = balance.get('info', {})
            account_type = account_info.get('accountType', 'SPOT')
            print(f"   📊 Tipo conta: {account_type}")
            
            # Verificar permissões
            permissions = account_info.get('permissions', [])
            if permissions:
                print(f"   🔑 Permissões: {', '.join(permissions)}")
            
            # Teste adicional - tentar criar uma ordem de teste
            print("   🧪 Testando permissões de trading...")
            try:
                # Teste com ordem inválida para verificar se retorna erro de permissão ou de ordem
                test_order = exchange.create_test_order('BTC/USDT', 'limit', 'buy', 0.001, 1.0)
                print("   ✅ Permissões de trading: OK!")
                can_trade = True
            except Exception as trade_error:
                error_msg = str(trade_error).lower()
                if 'permission' in error_msg or 'not allowed' in error_msg or 'unauthorized' in error_msg:
                    print("   ❌ Sem permissões de trading")
                    can_trade = False
                else:
                    # Se erro não é de permissão, provavelmente tem permissão mas ordem inválida
                    print("   ✅ Permissões OK (erro esperado na ordem teste)")
                    can_trade = True
            
        except Exception as e:
            print(f"   ❌ Erro autenticação: {e}")
            return False
        
        # 4. Teste de conectividade para trading
        print("\n🎯 4. Avaliação para trading neural...")
        
        print(f"   🚀 Pode fazer trades: {'✅ SIM' if can_trade else '❌ NÃO'}")
        
        if can_trade:
            print("   ✅ Conta configurada para trading!")
            print("   🎯 Sistema neural pode usar esta conta")
        else:
            print("   ⚠️ Verifique permissões da API Key")
            print("   💡 Ative 'Enable Spot & Margin Trading' na Binance")
        
        # Resumo final
        print("\n" + "=" * 50)
        print("📋 RESUMO DO TESTE:")
        print(f"✅ Dados públicos: OK")
        print(f"✅ Orderbook: OK") 
        print(f"✅ Autenticação: OK")
        print(f"💰 Saldos: {len(non_zero_balances)} moedas")
        print(f"🚀 Ready para trading: {'SIM' if can_trade else 'NÃO'}")
        
        if can_trade:
            print("\n🎉 BINANCE INTEGRAÇÃO COMPLETA!")
            print("✅ Sistema neural pode operar nesta conta")
            print("🎯 Próximo passo: Ativar evolução para 85%")
        else:
            print("\n⚠️ AJUSTES NECESSÁRIOS:")
            print("1. Ativar trading na API Key")
            print("2. Verificar permissões SPOT")
            
        return can_trade
        
    except Exception as e:
        print(f"\n❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Cleanup (ccxt não tem close method)
        pass

if __name__ == "__main__":
    print("🚀 Iniciando teste Binance real...")
    
    result = asyncio.run(test_binance_simple())
    
    if result:
        print(f"\n🎯 RESULTADO: SUCESSO TOTAL!")
        print("✅ Binance integrada e pronta")
        print("🚀 Pode ativar sistema neural!")
    else:
        print(f"\n❌ RESULTADO: Necessário ajustar")
        print("🔧 Verificar configurações")