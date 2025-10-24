#!/bin/bash

# Script de correção rápida para problemas Docker no VPS
# Resolve problema do pandas-ta e configurações Docker

echo "🔧 Corrigindo problemas Docker - Sistema Neural..."
echo "=================================================="

cd ~/moises || { echo "❌ Diretório moises não encontrado!"; exit 1; }

# 1. Parar containers que possam estar rodando
echo "🛑 Parando containers existentes..."
docker-compose down 2>/dev/null || true

# 2. Baixar arquivos corrigidos
echo "📥 Baixando correções..."
curl -O https://raw.githubusercontent.com/amos-fernandes/moises/main/requirements_fixed.txt
curl -O https://raw.githubusercontent.com/amos-fernandes/moises/main/docker-compose_fixed.yml
curl -O https://raw.githubusercontent.com/amos-fernandes/moises/main/Dockerfile.neural
curl -O https://raw.githubusercontent.com/amos-fernandes/moises/main/Dockerfile.dashboard

# 3. Substituir arquivos problemáticos
echo "🔄 Aplicando correções..."
cp requirements_fixed.txt requirements.txt
cp docker-compose_fixed.yml docker-compose.yml

# 4. Limpar cache Docker
echo "🧹 Limpando cache Docker..."
docker system prune -f
docker builder prune -f

# 5. Build com cache limpo
echo "🔨 Fazendo build com correções..."
docker-compose build --no-cache

# 6. Iniciar sistema
echo "🚀 Iniciando sistema corrigido..."
docker-compose up -d

# 7. Aguardar inicialização
echo "⏳ Aguardando inicialização (45 segundos)..."
sleep 45

# 8. Verificar status
echo "🔍 Verificando status..."
if curl -f -s http://localhost:8001/api/neural/status > /dev/null; then
    echo "✅ Sistema Neural funcionando!"
    
    echo ""
    echo "📊 Status atual:"
    curl -s http://localhost:8001/api/neural/status | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    ready = data.get('system_ready', False)
    learning = data.get('learning_status', {}).get('learning_active', False)
    print(f'Sistema Pronto: {ready}')
    print(f'Aprendizado Ativo: {learning}')
except:
    print('Sistema inicializando...')
" 2>/dev/null || echo "Sistema inicializando..."

else
    echo "⚠️ Sistema ainda inicializando..."
    echo "📋 Status dos containers:"
    docker-compose ps
    
    echo ""
    echo "📋 Logs recentes:"
    docker-compose logs --tail=20 neural-trading
fi

echo ""
echo "=================================================="
echo "✅ Correções aplicadas!"
echo "=================================================="
echo ""
echo "🌐 URLs disponíveis:"
echo "   Neural API: http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8001"
echo "   Dashboard:  http://$(curl -s ifconfig.me 2>/dev/null || echo 'SEU_IP'):8501"
echo ""
echo "📋 Comandos úteis:"
echo "   Status: docker-compose ps"
echo "   Logs: docker-compose logs -f neural-trading"
echo "   Restart: docker-compose restart"
echo "   Test API: curl http://localhost:8001/api/neural/status"
echo "=================================================="