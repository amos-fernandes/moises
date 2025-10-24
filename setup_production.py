#!/usr/bin/env python3
"""
Script de Configuração e Deploy - ATCoin Real Trading System
Configura e testa o sistema antes do deploy para VPS
"""

import os
import sys
import asyncio
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

def print_banner():
    print("=" * 60)
    print("🚀 ATCOIN REAL TRADING SYSTEM - SETUP & DEPLOY")
    print("=" * 60)
    print("📈 Estratégia: Equilibrada_Pro (+1.24% vs -78% RNN)")
    print("💰 Exchange: Binance (Real Trading)")
    print("🔄 Conversão: BRL → USD automática")
    print("=" * 60)

def check_environment():
    """Verifica se o ambiente está configurado corretamente"""
    print("\n🔍 VERIFICANDO AMBIENTE...")
    
    # Verifica .env
    required_vars = [
        'BINANCE_API_KEY', 
        'BINANCE_SECRET_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Variáveis ausentes no .env: {', '.join(missing_vars)}")
        return False
    
    print("✅ Variáveis de ambiente configuradas")
    
    # Verifica arquivos essenciais
    required_files = [
        'app_real_trading.py',
        'src/trading/binance_real_trading.py',
        'src/trading/production_system.py',
        'Dockerfile',
        'docker-compose.yml'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Arquivos ausentes: {', '.join(missing_files)}")
        return False
    
    print("✅ Arquivos essenciais presentes")
    return True

def install_requirements():
    """Instala dependências Python"""
    print("\n📦 INSTALANDO DEPENDÊNCIAS...")
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ], check=True, capture_output=True)
        print("✅ Dependências instaladas")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao instalar dependências: {e}")
        return False

async def test_binance_connection():
    """Testa conexão com Binance"""
    print("\n🔗 TESTANDO CONEXÃO BINANCE...")
    
    try:
        # Importa sistema de trading
        sys.path.insert(0, str(Path.cwd()))
        from src.trading.binance_real_trading import BinanceRealTrading
        
        # Cria instância
        trading_system = BinanceRealTrading()
        
        # Testa conexão
        success = await trading_system.initialize()
        
        if success:
            print("✅ Conexão com Binance estabelecida")
            print(f"🔧 Modo: {'TESTNET' if trading_system.testnet else 'REAL'}")
            
            # Fecha conexão
            if trading_system.exchange:
                await trading_system.exchange.close()
            
            return True
        else:
            print("❌ Falha na conexão com Binance")
            return False
            
    except Exception as e:
        print(f"❌ Erro no teste de conexão: {e}")
        return False

async def test_strategy():
    """Testa estratégia Equilibrada_Pro"""
    print("\n🎯 TESTANDO ESTRATÉGIA EQUILIBRADA_PRO...")
    
    try:
        from src.trading.production_system import ProductionTradingSystem
        
        # Cria sistema
        strategy = ProductionTradingSystem()
        
        # Testa com dados sintéticos
        import pandas as pd
        import numpy as np
        
        # Gera dados de teste
        periods = 100
        dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='h')
        price = 2500
        
        data = []
        for _ in range(periods):
            change = np.random.normal(0, 0.02)
            price *= (1 + change)
            
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 5000)
            
            data.append([price, high, low, price, volume])
        
        df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)
        
        # Testa indicadores
        df_with_indicators = strategy.calculate_indicators(df)
        
        # Testa sinal
        signal, confidence, reason = strategy.generate_signal(df_with_indicators, -1)
        
        print(f"✅ Estratégia testada")
        print(f"🎯 Sinal gerado: {signal} (confiança: {confidence:.2f})")
        print(f"📝 Razão: {reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste da estratégia: {e}")
        return False

def create_production_env():
    """Cria arquivo .env para produção"""
    print("\n⚙️ CRIANDO CONFIGURAÇÃO DE PRODUÇÃO...")
    
    production_env = f"""# === PRODUÇÃO - ATCOIN REAL TRADING ===
# ATENÇÃO: CONFIGURAÇÃO PARA DINHEIRO REAL!

# === BINANCE CREDENTIALS ===
BINANCE_API_KEY={os.getenv('BINANCE_API_KEY', '')}
BINANCE_SECRET_KEY={os.getenv('BINANCE_SECRET_KEY', '')}

# === TRADING CONFIGURATION ===
TRADING_MODE=REAL
BINANCE_TESTNET=false
INITIAL_BALANCE_BRL=1000.00
MAX_POSITION_SIZE=0.15
STOP_LOSS_PERCENT=0.02
TAKE_PROFIT_PERCENT=0.06

# === SERVIDOR ===
HOST=0.0.0.0
PORT=8000
WORKERS=1
LOG_LEVEL=INFO

# === SEGURANÇA ===
SECRET_KEY=atcoin_equilibrada_pro_secret_key_production_2024
CORS_ORIGINS=*

# === AIBANK INTEGRATION ===
AIBANK_API_KEY=atcoin_production_key_2024
AIBANK_CALLBACK_URL=https://aibank-api.com/api/rnn_investment_result_callback
CALLBACK_SHARED_SECRET=super_secret_production_key_equilibrada_pro_2024

# === APIs EXTERNAS ===
FINNHUB_API_KEY={os.getenv('FINNHUB_API_KEY', '')}
TWELVE_DATA_API_KEY={os.getenv('TWELVE_DATA_API_KEY', '')}
ALPHA_VANTAGE_API_KEY={os.getenv('ALPHA_VANTAGE_API_KEY', '')}
"""
    
    # Salva arquivo de produção
    with open('.env.production', 'w') as f:
        f.write(production_env)
    
    print("✅ Arquivo .env.production criado")
    print("🔧 Configure as URLs do AIBank antes do deploy")

def create_deploy_script():
    """Cria script de deploy para VPS"""
    print("\n📜 CRIANDO SCRIPT DE DEPLOY...")
    
    deploy_script = """#!/bin/bash
# Deploy Script para VPS Hostinger
# ATCoin Real Trading System

set -e

echo "🚀 Iniciando deploy ATCoin Real Trading System..."

# 1. Atualizar sistema
echo "📦 Atualizando sistema..."
sudo apt-get update
sudo apt-get install -y docker.io docker-compose curl

# 2. Verificar Docker
echo "🐳 Verificando Docker..."
sudo systemctl start docker
sudo systemctl enable docker

# 3. Clonar/atualizar repositório
if [ -d "atcoin-trading" ]; then
    echo "🔄 Atualizando repositório..."
    cd atcoin-trading
    git pull origin main
else
    echo "📥 Clonando repositório..."
    git clone <SEU_REPOSITORIO_GIT> atcoin-trading
    cd atcoin-trading
fi

# 4. Configurar ambiente
echo "⚙️ Configurando ambiente..."
cp .env.production .env

# 5. Build da aplicação
echo "🔨 Construindo aplicação..."
sudo docker-compose build

# 6. Parar serviços antigos
echo "🛑 Parando serviços antigos..."
sudo docker-compose down || true

# 7. Iniciar serviços
echo "🚀 Iniciando serviços..."
sudo docker-compose up -d

# 8. Verificar saúde
echo "🔍 Verificando saúde do sistema..."
sleep 30
curl -f http://localhost:8000/health || echo "⚠️ Sistema pode estar iniciando..."

echo "✅ Deploy concluído!"
echo "🌐 Acesse: http://SEU_IP_VPS:8000"
echo "📊 Health Check: http://SEU_IP_VPS:8000/health"
echo "💰 Saldo Binance: http://SEU_IP_VPS:8000/api/binance/balance"
"""
    
    with open('deploy.sh', 'w') as f:
        f.write(deploy_script)
    
    # Torna executável
    os.chmod('deploy.sh', 0o755)
    
    print("✅ Script deploy.sh criado")
    print("🔧 Edite o script com seu repositório Git")

def print_next_steps():
    """Mostra próximos passos"""
    print("\n" + "=" * 60)
    print("🎯 PRÓXIMOS PASSOS PARA DEPLOY")
    print("=" * 60)
    
    steps = [
        "1. 📋 Copie os arquivos para seu VPS:",
        "   scp -r . usuario@seu-vps:/home/usuario/atcoin-trading/",
        "",
        "2. 🔧 Configure no VPS:",
        "   - Edite .env.production com URLs reais do AIBank",
        "   - Configure seu repositório Git no deploy.sh",
        "",
        "3. 🚀 Execute o deploy:",
        "   chmod +x deploy.sh",
        "   ./deploy.sh",
        "",
        "4. 🔍 Monitore o sistema:",
        "   docker-compose logs -f atcoin-trading",
        "",
        "5. 🌐 URLs importantes:",
        "   - API: http://SEU-IP:8000/api/invest/real",
        "   - Health: http://SEU-IP:8000/health",
        "   - Saldo: http://SEU-IP:8000/api/binance/balance",
        "",
        "6. ⚠️  ATENÇÃO: SISTEMA COM DINHEIRO REAL!",
        "   - Teste primeiro com valores baixos",
        "   - Monitore os logs constantemente",
        "   - Configure alertas de segurança"
    ]
    
    for step in steps:
        print(step)
    
    print("=" * 60)

async def main():
    """Função principal"""
    print_banner()
    
    # Verifica ambiente
    if not check_environment():
        print("\n❌ Ambiente não configurado corretamente")
        return False
    
    # Instala dependências
    if not install_requirements():
        print("\n❌ Falha na instalação de dependências")
        return False
    
    # Testa conexão Binance
    if not await test_binance_connection():
        print("\n❌ Falha na conexão com Binance")
        return False
    
    # Testa estratégia
    if not await test_strategy():
        print("\n❌ Falha no teste da estratégia")
        return False
    
    # Cria arquivos de produção
    create_production_env()
    create_deploy_script()
    
    print("\n✅ SETUP CONCLUÍDO COM SUCESSO!")
    print("🎯 Sistema pronto para deploy na VPS")
    
    print_next_steps()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)