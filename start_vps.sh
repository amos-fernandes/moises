#!/bin/bash
# Script de inicialização para VPS - MOISES Trading Real
# Autorizado para operações com fundos reais

echo "🎂💰 INICIANDO MOISES TRADING REAL - VPS 💰🎂"
echo "================================================"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 não encontrado. Instalando..."
    sudo apt update
    sudo apt install -y python3 python3-pip python3-venv
fi

# Criar virtual environment se não existir
if [ ! -d ".venv" ]; then
    echo "📦 Criando ambiente virtual..."
    python3 -m venv .venv
fi

# Ativar ambiente virtual
source .venv/bin/activate

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Criar diretórios necessários
mkdir -p logs reports data backups

# Configurar timezone
export TZ='America/Sao_Paulo'

# Verificar se variáveis de ambiente estão configuradas
if [ -z "$BINANCE_API_KEY" ] || [ -z "$BINANCE_API_SECRET" ]; then
    echo "⚠️ AVISO: Configure BINANCE_API_KEY e BINANCE_API_SECRET nas variáveis de ambiente"
    echo "Exemplo: export BINANCE_API_KEY='sua_key'"
    echo "         export BINANCE_API_SECRET='seu_secret'"
fi

# Iniciar trading real
echo "🚀 Iniciando MOISES Trading Real..."
echo "✅ Autorizado para operações reais"
echo "💰 Modo: PRODUÇÃO"
echo "📊 Cliente: trading_real_vps.py"

python3 trading_real_vps.py