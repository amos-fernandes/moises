#!/bin/bash

# Script de atualização rápida do sistema neural no VPS
# Execute no VPS após copiar arquivos

echo "🧠 Atualizando Sistema Neural Trading..."
echo "======================================"

# Navegar para diretório
cd ~/neural-trading || { echo "❌ Diretório neural-trading não encontrado!"; exit 1; }

# Parar sistema atual
echo "🛑 Parando sistema atual..."
docker-compose down

# Backup de modelos salvos (se existirem)
if [ -d "models" ]; then
    echo "💾 Fazendo backup de modelos..."
    cp -r models/ backups/models_backup_$(date +%Y%m%d_%H%M%S)/ 2>/dev/null || true
fi

# Rebuild containers com cache limpo
echo "🔨 Rebuilding containers..."
docker-compose build --no-cache

# Instalar/atualizar dependências Python se necessário
echo "📦 Atualizando dependências..."
pip3 install --user --upgrade -r requirements.txt 2>/dev/null || true

# Verificar arquivos essenciais
echo "✅ Verificando arquivos essenciais..."
files=("app_neural_trading.py" "neural_monitor_dashboard.py" "src/ml/neural_learning_agent.py" "src/ml/continuous_training.py")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - OK"
    else
        echo "❌ $file - FALTANDO!"
    fi
done

# Atualizar permissões
chmod +x *.sh 2>/dev/null || true

# Iniciar sistema
echo "🚀 Iniciando sistema atualizado..."
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
    print('Dados não disponíveis')
" 2>/dev/null || echo "Sistema iniciando..."

else
    echo "⚠️ Sistema ainda inicializando..."
    echo "📋 Logs recentes:"
    docker-compose logs --tail=10 neural-trading
fi

echo ""
echo "======================================"
echo "✅ Atualização concluída!"
echo ""
echo "🌐 URLs disponíveis:"
echo "   Neural API: http://$(curl -s ifconfig.me):8001"
echo "   Dashboard:  http://$(curl -s ifconfig.me):8501"
echo ""
echo "📋 Comandos úteis:"
echo "   Logs: docker-compose logs -f"
echo "   Status: ~/monitor_neural_trading.sh"
echo "   Restart: docker-compose restart"
echo "======================================"