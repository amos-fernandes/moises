#!/usr/bin/env python3
"""
Executar Trade Real de Recuperação - ADAUSDT
Baseado no sinal RSI oversold detectado
"""

import json
from moises_estrategias_avancadas import TradingAvancado

def executar_trade_recovery_adausdt():
    print("=== TRADE DE RECUPERAÇÃO ADAUSDT ===")
    print("RSI detectado: 27.4 (oversold - sinal de compra)")
    
    # Carregar config Paulo (CONTA_2)
    with open('config/contas.json', 'r') as f:
        config = json.load(f)
    
    dados_paulo = list(config.values())[0]  # Primeira conta (Paulo)
    
    trader = TradingAvancado(
        api_key=dados_paulo['api_key'],
        api_secret=dados_paulo['api_secret'],
        conta_nome="PAULO_RECOVERY"
    )
    
    # Verificar saldo
    saldo_inicial = trader.get_saldo_usdt()
    print(f"Saldo inicial Paulo: ${saldo_inicial:.2f}")
    
    if saldo_inicial < 5:
        print("❌ Saldo insuficiente para trade")
        return
    
    # Obter dados atuais do ADAUSDT
    candles = trader.get_candles_rapidos('ADAUSDT', '5m', 20)
    if not candles:
        print("❌ Erro ao obter dados do ADAUSDT")
        return
    
    preco_atual = candles[-1]['close']
    prices = [c['close'] for c in candles]
    rsi = trader.calcular_rsi_rapido(prices)
    
    print(f"Preço atual ADAUSDT: ${preco_atual:.4f}")
    print(f"RSI atual: {rsi:.2f}")
    
    # Criar oportunidade manual para RSI oversold
    if rsi < 35:  # Confirmar oversold
        oportunidade = {
            'estrategia': 'rsi_oversold_recovery',
            'confidence': min(95, 70 + (35 - rsi) * 2),  # Mais oversold = mais confiança
            'entry_price': preco_atual,
            'stop_loss': preco_atual * 0.97,  # 3% stop loss
            'take_profit': preco_atual * 1.05  # 5% take profit
        }
        
        print(f"Oportunidade criada:")
        print(f"  Confiança: {oportunidade['confidence']:.1f}%")
        print(f"  Entrada: ${oportunidade['entry_price']:.4f}")
        print(f"  Stop Loss: ${oportunidade['stop_loss']:.4f} (-3%)")
        print(f"  Take Profit: ${oportunidade['take_profit']:.4f} (+5%)")
        
        # Calcular tamanho
        tamanho = trader.calcular_tamanho_agressivo(
            saldo_inicial,
            oportunidade['confidence'],
            oportunidade['entry_price'],
            oportunidade['stop_loss']
        )
        
        print(f"Tamanho calculado: ${tamanho:.2f} ({(tamanho/saldo_inicial)*100:.1f}% do saldo)")
        
        # Confirmar execução
        print(f"\n{'='*50}")
        print(f"CONFIRMAR TRADE DE RECUPERAÇÃO")
        print(f"{'='*50}")
        print(f"Símbolo: ADAUSDT")
        print(f"Valor: ${tamanho:.2f}")
        print(f"Estratégia: RSI Oversold Recovery")
        print(f"Risco: 3% (Stop Loss)")
        print(f"Objetivo: 5% (Take Profit)")
        print(f"{'='*50}")
        
        confirmacao = input("Executar trade real? (digite 'SIM'): ")
        
        if confirmacao == 'SIM':
            print("🚀 EXECUTANDO TRADE REAL...")
            
            resultado = trader.executar_trade_inteligente(oportunidade, 'ADAUSDT')
            
            if resultado:
                print("✅ TRADE EXECUTADO COM SUCESSO!")
                print(f"Order ID: {resultado.get('order_id')}")
                print(f"Valor investido: ${resultado.get('usdt_investido', 0):.2f}")
                print(f"Quantidade: {resultado.get('quantidade', 0):.6f} ADA")
                
                # Verificar saldo após trade
                saldo_final = trader.get_saldo_usdt()
                print(f"Saldo após trade: ${saldo_final:.2f}")
                
                return resultado
            else:
                print("❌ Erro na execução do trade")
                return None
        else:
            print("Trade cancelado pelo usuário")
            return None
    else:
        print(f"❌ RSI não oversold o suficiente: {rsi:.2f} (precisa < 35)")
        return None

if __name__ == "__main__":
    executar_trade_recovery_adausdt()