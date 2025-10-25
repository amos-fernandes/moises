#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 SETUP AUTOMÁTICO COMPLETO - MOISES
===================================
Configuração automática para começar a ajudar crianças
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
import json
from pathlib import Path
from datetime import datetime

def create_production_env():
    """Cria arquivo .env para produção"""
    env_content = f"""# 🔐 CONFIGURAÇÃO BINANCE - MOISES TRADING
# Data de configuração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# MISSÃO: Ajudar crianças através de trading inteligente

# PARA ATIVAR: Substitua pelos seus dados reais da Binance
BINANCE_API_KEY=SUA_API_KEY_AQUI
BINANCE_API_SECRET=SUA_SECRET_KEY_AQUI

# Configurações de Trading - FASE BEBÊ
TRADING_MODE=testnet
MAX_DAILY_TRADES=2
PROFIT_TARGET=0.01
HUMANITARIAN_ALLOCATION=0.20

# Segurança
ENABLE_WHITELIST=true
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENT=0.005

# Status do Sistema
MOISES_PHASE=BEBE
MOISES_BIRTHDAY=2025-10-24
NEURAL_ACCURACY=95
MISSION_STATUS=ATIVO_PARA_CRIANCAS
"""
    
    env_file = Path("d:/dev/moises/.env")
    env_file.write_text(env_content, encoding='utf-8')
    print(f"✅ Arquivo .env criado: {env_file}")
    return env_file

def create_config_structure():
    """Cria estrutura de configuração"""
    config_dir = Path("d:/dev/moises/config")
    config_dir.mkdir(exist_ok=True)
    
    # Configuração inicial
    config = {
        "moises_info": {
            "birth_date": "2025-10-24",
            "current_phase": "BEBÊ", 
            "mission": "Ajudar crianças através de trading inteligente",
            "neural_accuracy": "95%",
            "humanitarian_allocation": "20%"
        },
        "trading_config": {
            "initial_capital_usdt": 18.18,
            "daily_trades_target": 2,
            "profit_per_trade": "1%", 
            "preferred_pairs": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            "trading_hours": "09:00-18:00 UTC"
        },
        "humanitarian_system": {
            "families_target": "Famílias necessitadas",
            "monthly_support": "R$ 500 por família",
            "allocation_percent": 20,
            "focus": "Crianças em situação de vulnerabilidade"
        }
    }
    
    config_file = config_dir / "moises_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuração salva: {config_file}")
    return config_file

def create_validation_script():
    """Cria script de validação"""
    validation_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 VALIDAÇÃO DE PRODUÇÃO - MOISES
===============================
"""

import os
from pathlib import Path

def validate_production():
    """Valida se está tudo pronto"""
    print("🔍 VALIDANDO PRODUÇÃO - MOISES")
    print("=" * 35)
    
    issues = []
    
    # Verificar .env
    env_file = Path("d:/dev/moises/.env")
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        if 'SUA_API_KEY_AQUI' in content:
            issues.append("❌ API Keys não configuradas")
        else:
            print("✅ API Keys configuradas")
    else:
        issues.append("❌ Arquivo .env ausente")
    
    # Verificar estrutura
    dirs = ["config", "logs", "reports"]
    for dir_name in dirs:
        dir_path = Path(f"d:/dev/moises/{dir_name}")
        if dir_path.exists():
            print(f"✅ Diretório {dir_name}")
        else:
            issues.append(f"❌ Diretório {dir_name} ausente")
    
    # Status final
    print("\\n" + "="*40)
    if not issues:
        print("🎉 PRODUÇÃO VALIDADA! 🎉")
        print("💝 MOISES pronto para ajudar crianças!")
    else:
        print("⚠️ PENDÊNCIAS:")
        for issue in issues:
            print(f"  {issue}")
    print("="*40)

if __name__ == "__main__":
    validate_production()
'''
    
    validation_file = Path("d:/dev/moises/validate_production.py")
    validation_file.write_text(validation_content, encoding='utf-8')
    print(f"✅ Validação criada: {validation_file}")
    return validation_file

def main():
    """Configuração completa"""
    print("🎂💝 SETUP AUTOMÁTICO - MOISES PARA CRIANÇAS 💝🎂")
    print("=" * 55)
    print("🎯 Preparando tudo para ajudar crianças necessitadas")
    print("=" * 55)
    
    # 1. Criar estrutura de config
    print("\n📁 CRIANDO ESTRUTURA...")
    create_config_structure()
    
    # 2. Criar .env
    print("\n🔐 CONFIGURANDO AMBIENTE...")  
    create_production_env()
    
    # 3. Criar validação
    print("\n🔍 CRIANDO VALIDAÇÃO...")
    create_validation_script()
    
    # 4. Criar diretórios
    print("\n📂 CRIANDO DIRETÓRIOS...")
    for dir_name in ["logs", "reports", "backups"]:
        dir_path = Path(f"d:/dev/moises/{dir_name}")
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Diretório: {dir_name}")
    
    print("\n" + "="*55)
    print("🎉 CONFIGURAÇÃO COMPLETA! 🎉") 
    print("💝 MOISES está pronto para ajudar crianças!")
    print("=" * 55)
    
    print("\n📋 PRÓXIMOS PASSOS:")
    print("1. 🔐 Edite o arquivo .env com suas API Keys da Binance")
    print("2. 🔍 Execute: python validate_production.py") 
    print("3. 🚀 Execute: python moises_trading_real.py")
    print("4. 💝 Transforme vidas!")
    
    print("\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
    print("💖 Cada trade = Uma criança mais próxima da dignidade!")

if __name__ == "__main__":
    main()