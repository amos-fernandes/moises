#!/usr/bin/env python3
"""
Teste Manual de Estratégias - Verificar por que não há trades
"""

import json
from moises_estrategias_avancadas import TradingAvancado

def teste_estrategias_manual():
    print("=== TESTE MANUAL DE ESTRATÉGIAS ===")
    
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    # Testar com CONTA_2 (Paulo)
    dados_paulo = list(config.values())[0]
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="PAULO_TEST"
    )
    
    print(f"Saldo Paulo: ${trader.get_saldo_usdt():.2f}")
    
    # Testar análise de mercado
    print("\n=== ANÁLISE COMPLETA ===")
    mercado = trader.analisar_mercado_completo()
    
    if mercado:
        print("Oportunidades encontradas:")
        for symbol, oportunidade in mercado.items():
            if oportunidade and oportunidade.get('confidence', 0) > 80:
                print(f"  {symbol}: {oportunidade['confidence']:.1f}% - {oportunidade.get('estrategia', 'N/A')}")
                
                # Testar execução
                print(f"    Testando execução para {symbol}...")
                
                try:
                    # Calcular tamanho
                    saldo = trader.get_saldo_usdt()
                    tamanho = trader.calcular_tamanho_agressivo(
                        saldo,
                        oportunidade['confidence'],
                        oportunidade.get('entry_price', 50000),
                        oportunidade.get('stop_loss', 49000)
                    )
                    
                    print(f"    Tamanho calculado: ${tamanho:.2f}")
                    print(f"    Entry: ${oportunidade.get('entry_price', 0):.4f}")
                    print(f"    Stop Loss: ${oportunidade.get('stop_loss', 0):.4f}")
                    print(f"    Take Profit: ${oportunidade.get('take_profit', 0):.4f}")
                    
                    # IMPORTANTE: NÃO EXECUTAR TRADE REAL, APENAS SIMULAR
                    print(f"    [SIMULAÇÃO] Trade seria executado com ${tamanho:.2f}")
                    
                except Exception as e:
                    print(f"    Erro no cálculo: {e}")
    else:
        print("❌ Nenhuma oportunidade encontrada!")
        
    # Testar símbolos específicos
    print("\n=== TESTE SÍMBOLOS ESPECÍFICOS ===")
    simbolos_teste = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
    
    for symbol in simbolos_teste:
        print(f"\n[{symbol}]")
        try:
            # Obter candles
            candles = trader.get_candles_rapidos(symbol, '5m', 20)
            if candles:
                prices = [c['close'] for c in candles]
                
                # Calcular indicadores
                rsi = trader.calcular_rsi_rapido(prices)
                
                print(f"  Preço atual: ${candles[-1]['close']:.4f}")
                print(f"  RSI: {rsi:.2f}")
                print(f"  Volume: {candles[-1]['volume']:.0f}")
                
                # Lógica de decisão
                if rsi < 30:
                    print(f"  🟢 SINAL COMPRA: RSI oversold ({rsi:.1f})")
                elif rsi > 70:
                    print(f"  🔴 SINAL VENDA: RSI overbought ({rsi:.1f})")
                else:
                    print(f"  🟡 NEUTRO: RSI normal ({rsi:.1f})")
                    
            else:
                print(f"  ❌ Erro ao obter candles")
                
        except Exception as e:
            print(f"  ❌ Erro: {e}")

if __name__ == "__main__":
    teste_estrategias_manual()