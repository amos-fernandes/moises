#!/bin/bash

# Script para resolver conflitos Git no VPS e atualizar sistema neural

echo "🔧 Resolvendo conflitos Git e atualizando sistema neural..."
echo "============================================================"

# Navegar para diretório do projeto
cd ~/moises || { echo "❌ Diretório moises não encontrado!"; exit 1; }

# 1. Fazer backup dos arquivos não rastreados
echo "💾 Fazendo backup de arquivos locais..."
BACKUP_DIR="backup_vps_$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR

# Backup arquivos que causam conflito
if [ -f "app_neural_trading.py" ]; then
    cp app_neural_trading.py $BACKUP_DIR/
    echo "✅ Backup: app_neural_trading.py"
fi

if [ -f "neural_monitor_dashboard.py" ]; then
    cp neural_monitor_dashboard.py $BACKUP_DIR/
    echo "✅ Backup: neural_monitor_dashboard.py"
fi

if [ -d "src/ml" ]; then
    mkdir -p $BACKUP_DIR/src/ml
    cp -r src/ml/* $BACKUP_DIR/src/ml/ 2>/dev/null || true
    echo "✅ Backup: src/ml/"
fi

# 2. Fazer stash das alterações (se houver arquivos rastreados modificados)
echo "📦 Salvando alterações locais..."
git stash push -m "VPS backup before neural system update" -u 2>/dev/null || true

# 3. Fazer pull das atualizações
echo "📥 Baixando atualizações do repositório..."
git pull origin main

# 4. Verificar se arquivos neurais foram baixados
echo "✅ Verificando arquivos do sistema neural..."
files=(
    "app_neural_trading.py"
    "neural_monitor_dashboard.py" 
    "src/ml/neural_learning_agent.py"
    "src/ml/continuous_training.py"
    "update_neural_vps.sh"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - OK"
    else
        echo "❌ $file - FALTANDO!"
    fi
done

# 5. Tornar scripts executáveis
chmod +x *.sh 2>/dev/null || true

# 6. Verificar se temos Docker
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker não encontrado! Execute primeiro:"
    echo "   ./fix_docker_conflicts.sh"
    echo "   ./deploy_neural_vps.sh"
    exit 1
fi

# 7. Preparar ambiente neural
echo "🧠 Preparando ambiente para sistema neural..."

# Criar estrutura de diretórios
mkdir -p {logs,data,models,backups}

# 8. Instalar dependências Python (se pip estiver disponível)
if command -v pip3 &> /dev/null; then
    echo "📦 Instalando dependências Python..."
    pip3 install --user pandas numpy scikit-learn tensorflow plotly streamlit requests schedule pandas_ta 2>/dev/null || true
fi

# 9. Executar script de atualização neural (se existir)
if [ -f "update_neural_vps.sh" ]; then
    echo "🚀 Executando atualização do sistema neural..."
    chmod +x update_neural_vps.sh
    ./update_neural_vps.sh
else
    echo "⚠️ Script update_neural_vps.sh não encontrado"
    echo "📋 Arquivos disponíveis:"
    ls -la *.py *.sh 2>/dev/null || echo "Nenhum script encontrado"
fi

echo ""
echo "============================================================"
echo "✅ Resolução de conflitos concluída!"
echo "============================================================"
echo ""
echo "📋 Próximos passos:"
echo "1. Se Docker não estiver instalado: ./fix_docker_conflicts.sh"
echo "2. Para deploy completo: ./deploy_neural_vps.sh"  
echo "3. Para iniciar sistema: docker-compose up -d"
echo "4. Para monitorar: ./monitor_neural_trading.sh"
echo ""
echo "🌐 URLs após inicialização:"
echo "   Neural API: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8001"
echo "   Dashboard:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8501"
echo ""
echo "📁 Backup salvo em: $BACKUP_DIR"
echo "============================================================"