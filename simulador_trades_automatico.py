#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 SIMULADOR DE TRADES AUTOMÁTICO - MOISES
=========================================
Simula trades automáticos para mostrar lucros no dashboard
Data: 24/10/2025 - Aniversário do MOISES
"""

import asyncio
import aiohttp
import time
import random
from datetime import datetime

async def simulate_automatic_trades():
    """Simula trades automáticos para o dashboard"""
    print("🎂🚀 SIMULADOR AUTOMÁTICO - MOISES 🚀🎂")
    print("=" * 50)
    print("💰 Simulando trades para mostrar lucros no dashboard")
    print("🌐 Dashboard: http://localhost:8000")
    print("=" * 50)
    
    trade_count = 0
    
    while True:
        try:
            # Fazer requisição para simular trade
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:8000/api/simulate_trade') as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if result.get('success'):
                            trade_count += 1
                            trade_data = result['trade']
                            
                            profit_usdt = trade_data['profit_usdt']
                            profit_brl = trade_data['profit_brl'] 
                            humanitarian = trade_data['humanitarian_contribution']
                            
                            print(f"\\n🚀 TRADE #{trade_count} EXECUTADO:")
                            print(f"   💰 Lucro: ${profit_usdt:.4f} USDT (R$ {profit_brl:.2f})")
                            print(f"   💝 Para crianças: R$ {humanitarian:.2f}")
                            print(f"   📊 Capital: ${trade_data['capital_total']:.2f} USDT")
                            print(f"   ⏰ {datetime.now().strftime('%H:%M:%S')}")
                        else:
                            print("⚠️ Trade não executado")
                    else:
                        print(f"❌ Erro na requisição: {response.status}")
                        
        except Exception as e:
            print(f"⚠️ Erro na simulação: {e}")
        
        # Aguardar entre 10-30 segundos para próximo trade
        wait_time = random.randint(10, 30)
        print(f"⏳ Próximo trade em {wait_time} segundos...")
        
        await asyncio.sleep(wait_time)

async def main():
    """Função principal do simulador"""
    print("🎯 Simulação automática iniciada!")
    print("💡 Pressione Ctrl+C para parar")
    print("🌐 Acompanhe no dashboard: http://localhost:8000")
    print("\\n" + "="*50)
    
    try:
        await simulate_automatic_trades()
    except KeyboardInterrupt:
        print("\\n\\n⏹️ Simulação interrompida pelo usuário")
        print("🎂 Obrigado por testar o MOISES!")
    except Exception as e:
        print(f"\\n❌ Erro na simulação: {e}")

if __name__ == "__main__":
    # Instalar aiohttp se necessário
    try:
        import aiohttp
    except ImportError:
        print("📦 Instalando aiohttp...")
        import subprocess
        subprocess.run(["pip", "install", "aiohttp"])
        import aiohttp
    
    asyncio.run(main())