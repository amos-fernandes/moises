#!/bin/bash

# Script para VPS - Atualizar e testar correção definitiva

echo "🚀 CORREÇÃO DEFINITIVA NA VPS"
echo "==============================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. PULL das correções
echo "📥 Baixando correções do GitHub..."
git pull origin main

# 2. VERIFICAR se arquivo está correto
echo "🔍 Verificando arquivo corrigido..."
if [ -f "src/ml/continuous_training.py" ]; then
    echo "✅ Arquivo existe"
    echo "📏 Tamanho: $(wc -c < src/ml/continuous_training.py) bytes"
    echo "📋 Primeiras linhas:"
    head -10 src/ml/continuous_training.py
else
    echo "❌ Arquivo não encontrado!"
    exit 1
fi

# 3. PARAR containers
echo "🛑 Parando containers..."
docker compose down

# 4. REBUILD sem cache
echo "🔨 Reconstruindo container neural..."
docker compose build neural --no-cache

# 5. INICIAR
echo "🚀 Iniciando containers..."
docker compose up -d

# 6. AGUARDAR
echo "⏳ Aguardando 30 segundos..."
sleep 30

# 7. TESTAR
echo "🧪 Testando endpoints..."

# Teste API Neural
for i in {1..5}; do
    echo "Tentativa $i/5..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ API Neural (8001): FUNCIONANDO!"
        
        # Teste Dashboard
        if curl -f -s http://localhost:8501 >/dev/null 2>&1; then
            echo "✅ Dashboard (8501): FUNCIONANDO!"
        else
            echo "⚠️ Dashboard (8501): Com problema"
        fi
        
        # Sucesso! Mostrar informações
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo ""
        echo "🎉 SUCESSO TOTAL!"
        echo "=================="
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
        echo ""
        echo "🔗 Endpoints disponíveis:"
        echo "  GET  /health          - Status da API"
        echo "  GET  /metrics         - Métricas do sistema"
        echo "  POST /trade/decision  - Decisão de trading"
        echo "  GET  /neural/status   - Status da rede neural"
        echo ""
        
        exit 0
    else
        echo "❌ API Neural falhou - Tentativa $i"
        if [ $i -lt 5 ]; then
            echo "⏳ Aguardando 15 segundos..."
            sleep 15
        fi
    fi
done

# Se chegou aqui, ainda há problema
echo ""
echo "❌ AINDA COM PROBLEMA"
echo "===================="
echo "📋 Logs do container:"
docker compose logs --tail=20 neural

echo ""
echo "📊 Status dos containers:"
docker ps | grep -E "(neural|dashboard)"

echo ""
echo "🔧 Comandos de diagnóstico:"
echo "  docker compose logs neural     # Ver logs completos"
echo "  docker compose exec neural bash # Entrar no container"
echo "  docker compose restart neural   # Reiniciar container"