#!/bin/bash

# Script de atualização rápida do sistema neural no VPS
# Execute no VPS após copiar arquivos
# DIRETÓRIO CORRETO: ~/moises

echo "🧠 Atualizando Sistema Neural Trading..."
echo "======================================"

# Navegar para diretório correto
cd ~/moises || { echo "❌ Diretório moises não encontrado!"; exit 1; }

# Parar sistema atual (se estiver rodando)
echo "🛑 Parando sistema atual..."
docker-compose down 2>/dev/null || true

# Backup de modelos salvos (se existirem)
if [ -d "models" ]; then
    echo "💾 Fazendo backup de modelos..."
    mkdir -p backups
    cp -r models/ backups/models_backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
fi

# Verificar se Docker está instalado
if ! command -v docker &> /dev/null; then
    echo "⚠️ Docker não encontrado! Instalando dependências Python..."
    
    # Instalar/atualizar dependências Python
    if command -v pip3 &> /dev/null; then
        echo "📦 Instalando dependências Python..."
        pip3 install --user --upgrade pandas numpy scikit-learn tensorflow plotly streamlit requests schedule pandas_ta 2>/dev/null || true
    fi
    
    echo "ℹ️ Para usar Docker, execute primeiro:"
    echo "   ./fix_docker_conflicts.sh"
    echo "   ./deploy_neural_vps.sh"
else
    # Rebuild containers com cache limpo
    echo "🔨 Rebuilding containers..."
    docker-compose build --no-cache 2>/dev/null || echo "⚠️ docker-compose.yml não encontrado"
fi

# Verificar arquivos essenciais
echo "✅ Verificando arquivos essenciais..."
files=("app_neural_trading.py" "neural_monitor_dashboard.py" "src/ml/neural_learning_agent.py" "src/ml/continuous_training.py")
missing_files=0

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - OK"
    else
        echo "❌ $file - FALTANDO!"
        missing_files=$((missing_files + 1))
    fi
done

if [ $missing_files -gt 0 ]; then
    echo "⚠️ $missing_files arquivo(s) essencial(is) faltando!"
    echo "Execute primeiro: git pull origin main"
fi

# Atualizar permissões
chmod +x *.sh 2>/dev/null || true

# Criar estrutura de diretórios necessária
mkdir -p {logs,data,models,backups}

# Tentar iniciar sistema
if command -v docker &> /dev/null && [ -f "docker-compose.yml" ]; then
    echo "🚀 Iniciando sistema com Docker..."
    docker-compose up -d

    # Aguardar inicialização
    echo "⏳ Aguardando inicialização (30s)..."
    sleep 30

    # Verificar status
    echo "🔍 Verificando status do sistema..."
    if curl -f -s http://localhost:8001/api/neural/status > /dev/null; then
        echo "✅ Sistema Neural funcionando!"
        
        # Mostrar métricas rápidas
        echo ""
        echo "📊 Status Atual:"
        curl -s http://localhost:8001/api/neural/status | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    ready = data.get('system_ready', False)
    learning = data.get('learning_status', {}).get('learning_active', False)
    print(f'Sistema Pronto: {ready}')
    print(f'Aprendizado Ativo: {learning}')
except:
    print('Dados não disponíveis - sistema ainda inicializando')
" 2>/dev/null || echo "Sistema ainda inicializando..."

    else
        echo "⚠️ Sistema ainda inicializando ou com problemas..."
        echo "📋 Logs recentes:"
        docker-compose logs --tail=10 neural-trading 2>/dev/null || echo "Logs não disponíveis"
    fi

elif [ -f "app_neural_trading.py" ]; then
    echo "🐍 Iniciando sistema em modo Python direto..."
    echo "Para monitorar: python3 app_neural_trading.py"
    echo "Para dashboard: streamlit run neural_monitor_dashboard.py"
else
    echo "❌ Não foi possível iniciar o sistema"
    echo "Arquivos necessários não encontrados"
fi

echo ""
echo "======================================"
echo "✅ Atualização concluída!"
echo ""
echo "📁 Diretório de trabalho: ~/moises"
echo "🌐 URLs disponíveis (após inicialização):"
echo "   Neural API: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8001"
echo "   Dashboard:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8501"
echo ""
echo "📋 Comandos úteis:"
echo "   Logs: docker-compose logs -f (se usando Docker)"
echo "   Status: curl http://localhost:8001/api/neural/status"
echo "   Restart: docker-compose restart"
echo "   Monitor: python3 app_neural_trading.py"
echo "======================================"