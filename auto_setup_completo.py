#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 SETUP AUTOMATIZADO - BINANCE API KEYS
======================================
Configuração automática para MOISES começar a ajudar crianças
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
from pathlib import Path
from datetime import datetime

def create_production_env():
    """Cria arquivo .env para produção"""
    env_content = f'''# 🔐 CONFIGURAÇÃO BINANCE - MOISES TRADING
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
'''
    
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
    
    import json
    config_file = config_dir / "moises_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuração salva: {config_file}")
    return config_file

def create_validation_script():
    """Cria script de validação da produção"""
    validation_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 VALIDAÇÃO DE PRODUÇÃO - MOISES
===============================
Verifica se tudo está pronto para ajudar crianças
"""

import os
import json
from pathlib import Path
from datetime import datetime

def validate_environment():
    """Valida configuração do ambiente"""
    print("🔍 VALIDANDO AMBIENTE DE PRODUÇÃO...")
    print("=" * 40)
    
    issues = []
    
    # 1. Verificar arquivo .env
    env_file = Path("d:/dev/moises/.env")
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        if 'SUA_API_KEY_AQUI' in content:
            issues.append("❌ API Keys ainda não foram configuradas")
        else:
            print("✅ Arquivo .env configurado")
    else:
        issues.append("❌ Arquivo .env não encontrado")
    
    # 2. Verificar estrutura de diretórios
    required_dirs = [
        "d:/dev/moises/config",
        "d:/dev/moises/logs", 
        "d:/dev/moises/reports"
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            print(f"✅ Diretório existe: {dir_path}")
        else:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            print(f"✅ Diretório criado: {dir_path}")
    
    # 3. Verificar arquivos principais
    required_files = [
        "moises_trading_real.py",
        "setup_binance_api.py", 
        "src/social/humanitarian_system.py"
    ]
    
    for file_name in required_files:
        file_path = Path(f"d:/dev/moises/{file_name}")
        if file_path.exists():
            print(f"✅ Arquivo existe: {file_name}")
        else:
            issues.append(f"❌ Arquivo ausente: {file_name}")
    
    # 4. Validar dependências
    try:
        import binance
        print("✅ python-binance instalado")
    except ImportError:
        issues.append("❌ python-binance não instalado")
    
    try:
        import dotenv
        print("✅ python-dotenv instalado")
    except ImportError:
        issues.append("❌ python-dotenv não instalado")
    
    # 5. Status do sistema
    print("\\n📊 STATUS DO SISTEMA:")
    print("=" * 25)
    print("🎂 MOISES Aniversário: 24/10/2025")
    print("🚀 Fase atual: BEBÊ")
    print("💰 Capital inicial: $18.18 USDT")
    print("🎯 Precisão neural: 95%")
    print("💝 Missão: Ajudar crianças necessitadas")
    print("📈 Meta diária: 2 trades, 1% lucro cada")
    print("👶 Alocação humanitária: 20% dos lucros")
    
    # Relatório final
    print("\\n" + "="*50)
    if not issues:
        print("🎉 SISTEMA PRONTO PARA PRODUÇÃO! 🎉")
        print("💝 MOISES pode começar a ajudar crianças!")
        print("🚀 Execute: python moises_trading_real.py")
    else:
        print("⚠️ PENDÊNCIAS ENCONTRADAS:")
        for issue in issues:
            print(f"  {issue}")
        print("\\n🔧 Configure as pendências e execute novamente")
    
    print("="*50)

if __name__ == "__main__":
    validate_environment()
'''
    
    validation_file = Path("d:/dev/moises/validate_production.py")
    validation_file.write_text(validation_content, encoding='utf-8')
    print(f"✅ Script de validação criado: {validation_file}")
    return validation_file

def create_startup_script():
    """Cria script de inicialização"""
    startup_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 INICIALIZAÇÃO MOISES - MODO PRODUÇÃO
=====================================
Script para iniciar MOISES e começar a ajudar crianças
"""

import os
import sys
from pathlib import Path

def startup_moises():
    """Inicializa MOISES para produção"""
    print("🎂🚀 INICIALIZANDO MOISES - ANIVERSÁRIO 2025 🚀🎂")
    print("=" * 55)
    print("💝 MISSÃO: Transformar trading em ajuda para crianças")
    print("🎯 OBJETIVO: R$ 100 → Milhões para famílias necessitadas") 
    print("=" * 55)
    
    # Verificar se está configurado
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Arquivo .env não encontrado!")
        print("🔧 Execute primeiro: python setup_binance_api.py")
        return False
    
    # Verificar API keys
    content = env_file.read_text(encoding='utf-8')
    if 'SUA_API_KEY_AQUI' in content:
        print("⚠️ API KEYS AINDA NÃO CONFIGURADAS!")
        print("\\n📋 PARA CONFIGURAR:")
        print("1. Acesse: https://www.binance.com/en/my/settings/api-management")
        print("2. Crie API Key com permissões de trading")
        print("3. Edite o arquivo .env com suas keys reais")
        print("4. Execute novamente este script")
        return False
    
    print("✅ Configuração encontrada!")
    print("🚀 Iniciando sistema de trading...")
    
    # Executar MOISES
    try:
        os.system("python moises_trading_real.py")
    except Exception as e:
        print(f"❌ Erro ao iniciar: {e}")
        return False
    
    return True

if __name__ == "__main__":
    startup_moises()
'''
    
    startup_file = Path("d:/dev/moises/start_moises.py")
    startup_file.write_text(startup_content, encoding='utf-8')
    print(f"✅ Script de inicialização criado: {startup_file}")
    return startup_file

def main():
    """Configuração completa automática"""
    print("🎂💝 CONFIGURAÇÃO AUTOMÁTICA - MOISES PARA CRIANÇAS 💝🎂")
    print("=" * 60)
    print("🎯 Preparando tudo para começar a ajudar crianças necessitadas")
    print("=" * 60)
    
    # 1. Criar estrutura
    print("\\n📁 CRIANDO ESTRUTURA...")
    create_config_structure()
    
    # 2. Criar arquivo .env
    print("\\n🔐 CONFIGURANDO AMBIENTE...")
    create_production_env()
    
    # 3. Criar validação
    print("\\n🔍 CRIANDO VALIDAÇÃO...")
    create_validation_script()
    
    # 4. Criar inicialização
    print("\\n🚀 CRIANDO INICIALIZAÇÃO...")
    create_startup_script()
    
    # 5. Criar diretórios necessários
    print("\\n📂 CRIANDO DIRETÓRIOS...")
    for dir_name in ["logs", "reports", "backups"]:
        dir_path = Path(f"d:/dev/moises/{dir_name}")
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Diretório: {dir_name}")
    
    print("\\n" + "="*60)
    print("🎉 CONFIGURAÇÃO COMPLETA! 🎉")
    print("💝 MOISES está pronto para ajudar crianças!")
    print("=" * 60)
    print("\\n📋 PRÓXIMOS PASSOS:")
    print("1. 🔐 Configure suas API Keys da Binance no arquivo .env")
    print("2. 🔍 Execute: python validate_production.py")
    print("3. 🚀 Execute: python start_moises.py")
    print("4. 💝 Comece a transformar vidas!")
    print("\\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")

if __name__ == "__main__":
    main()
'''
    
    auto_setup_file = Path("d:/dev/moises/auto_setup.py")
    auto_setup_file.write_text(auto_setup_content, encoding='utf-8')
    return auto_setup_file

# Executar configuração completa
auto_setup_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 SETUP AUTOMATIZADO - BINANCE API KEYS
======================================
Configuração automática para MOISES começar a ajudar crianças
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
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
    
    import json
    config_file = config_dir / "moises_config.json"
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Configuração salva: {config_file}")
    return config_file

def main():
    """Configuração completa automática"""
    print("🎂💝 CONFIGURAÇÃO AUTOMÁTICA - MOISES PARA CRIANÇAS 💝🎂")
    print("=" * 60)
    print("🎯 Preparando tudo para começar a ajudar crianças necessitadas")
    print("=" * 60)
    
    # 1. Criar estrutura
    print("\\n📁 CRIANDO ESTRUTURA...")
    create_config_structure()
    
    # 2. Criar arquivo .env
    print("\\n🔐 CONFIGURANDO AMBIENTE...")
    create_production_env()
    
    # 3. Criar diretórios necessários
    print("\\n📂 CRIANDO DIRETÓRIOS...")
    for dir_name in ["logs", "reports", "backups"]:
        dir_path = Path(f"d:/dev/moises/{dir_name}")
        dir_path.mkdir(exist_ok=True)
        print(f"✅ Diretório: {dir_name}")
    
    print("\\n" + "="*60)
    print("🎉 CONFIGURAÇÃO COMPLETA! 🎉")
    print("💝 MOISES está pronto para ajudar crianças!")
    print("=" * 60)
    print("\\n📋 PRÓXIMOS PASSOS:")
    print("1. 🔐 Configure suas API Keys da Binance no arquivo .env")
    print("2. 🔍 Valide a configuração")
    print("3. 🚀 Inicie o trading para ajudar crianças!")
    print("\\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")

if __name__ == "__main__":
    main()
'''