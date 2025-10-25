#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 SETUP SIMPLIFICADO DAS API KEYS - MOISES
==========================================
Configuração rápida para ativar o trading humanitário
"""

import os
from pathlib import Path
from datetime import datetime

def create_env_file():
    """Cria arquivo .env com configuração"""
    print("🔐 CONFIGURAÇÃO DAS API KEYS - MOISES")
    print("=" * 45)
    print("🎯 Missão: Ativar trading para ajudar as crianças!")
    print("💝 20% dos lucros vão direto para famílias necessitadas")
    print("=" * 45)
    
    print("\n📋 PASSO 1: Obtenha suas API keys da Binance")
    print("1. Acesse: https://www.binance.com/pt-BR/my/settings/api-management")
    print("2. Crie uma nova API Key")
    print("3. Ative: 'Enable Spot & Margin Trading'")
    print("4. Configure IP Whitelist (recomendado)")
    
    print("\n🔑 PASSO 2: Configure suas credenciais")
    print("(Cole suas keys da Binance aqui)")
    
    # Entrada das API keys
    api_key = input("\n🔑 BINANCE_API_KEY: ").strip()
    if not api_key:
        print("❌ API Key é obrigatória!")
        return False
    
    api_secret = input("🔐 BINANCE_API_SECRET: ").strip()
    if not api_secret:
        print("❌ API Secret é obrigatória!")
        return False
    
    print("\n🎯 PASSO 3: Escolha o modo de trading")
    print("1. TESTNET (Recomendado para começar)")
    print("2. LIVE (Trading real)")
    
    mode = input("Escolha (1 ou 2): ").strip()
    trading_mode = "testnet" if mode == "1" else "live"
    
    # Criar arquivo .env
    env_content = f'''# 🎂 MOISES TRADING - CONFIGURAÇÃO HUMANITÁRIA
# Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Missão: Ajudar crianças através do trading neural

BINANCE_API_KEY={api_key}
BINANCE_API_SECRET={api_secret}
TRADING_MODE={trading_mode}

# Configurações de Trading - Fase BEBÊ
MAX_DAILY_TRADES=2
PROFIT_TARGET=0.01
HUMANITARIAN_ALLOCATION=0.20

# Segurança
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENT=0.005
'''
    
    env_file = Path("d:/dev/moises/.env")
    env_file.write_text(env_content, encoding='utf-8')
    
    print(f"\n✅ Configuração salva em: {env_file}")
    print(f"🎯 Modo selecionado: {trading_mode.upper()}")
    print("💝 Sistema humanitário: ATIVO (20% para famílias)")
    
    return True

def create_quick_start_guide():
    """Cria guia de início rápido"""
    guide = '''
🚀 GUIA DE INÍCIO RÁPIDO - MOISES
================================

📋 PRÓXIMOS PASSOS:
1. ✅ API Keys configuradas
2. 🚀 Execute: python moises_trading_real.py
3. 💝 Escolha modo de operação
4. 📊 Acompanhe os relatórios

🎯 OBJETIVOS:
• 2 trades por dia (Fase BEBÊ)
• 1% lucro por trade
• 20% dos lucros para famílias necessitadas
• Crescimento de $18.18 → $47.12 USDT (3 meses)

💖 IMPACTO HUMANITÁRIO:
• Primeira família registrada em breve
• R$ 500/mês por família ajudada
• Milhares de crianças impactadas no futuro

🔥 MOISES está pronto para transformar vidas!
'''
    
    guide_file = Path("d:/dev/moises/GUIA_INICIO_RAPIDO.md")
    guide_file.write_text(guide, encoding='utf-8')
    print(f"📖 Guia salvo em: {guide_file}")

def main():
    print("🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
    print("💝 Vamos ativar o sistema para ajudar as crianças!")
    print()
    
    if create_env_file():
        create_quick_start_guide()
        
        print("\n" + "="*50)
        print("🎊 CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("🚀 MOISES está pronto para a missão humanitária!")
        print("💝 Cada trade = Uma criança mais próxima da esperança!")
        print("="*50)
        
        print("\n🎯 PRÓXIMO PASSO:")
        print("Execute: python moises_trading_real.py")
        
    else:
        print("\n❌ Configuração não concluída.")
        print("Tente novamente com API keys válidas.")

if __name__ == "__main__":
    main()