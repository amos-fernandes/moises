#!/bin/bash

echo "🎯 APLICAÇÃO FINAL - Nomes corretos dos serviços"
echo "=============================================="

cd ~/moises

# Git reset completo
echo "📥 Reset git completo..."
git fetch origin
git reset --hard origin/main

echo "🔍 Verificando correção:"
echo "Linha 95 (deve estar sem target_accuracy):"
sed -n '95p' app_neural_trading.py

# Docker rebuild
echo "🔨 Docker rebuild..."
docker compose down
docker compose build --no-cache
docker compose up -d

# Aguardar e testar
echo "⏳ Aguardando 30 segundos..."
sleep 30

echo "🧪 Teste final com nomes corretos..."

# Verifica qual serviço está rodando
echo "📊 Containers ativos:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🔍 Testando endpoints..."

# Teste API Neural (porta 8001)
if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "✅ API Neural (8001): FUNCIONANDO!"
    
    # Teste Dashboard (porta 8501)
    if curl -f -s http://localhost:8501 >/dev/null 2>&1; then
        echo "✅ Dashboard (8501): FUNCIONANDO!"
    else
        echo "⚠️ Dashboard (8501): Verificando..."
    fi
    
    IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo ""
    echo "🎉 SUCESSO TOTAL!"
    echo "==================="
    echo "🧠 API Neural: http://$IP:8001"
    echo "📊 Dashboard: http://$IP:8501"
    echo ""
    echo "🔗 Endpoints disponíveis:"
    echo "  GET  /health"
    echo "  GET  /metrics" 
    echo "  POST /trade/decision"
    echo ""
    
else
    echo "❌ API Neural (8001) com problema"
    
    echo ""
    echo "📋 Logs neural-trading-api:"
    docker compose logs --tail=10 neural-trading-api
    
    echo ""
    echo "📋 Logs neural-dashboard:"
    docker compose logs --tail=5 neural-dashboard
    
    echo ""
    echo "📊 Status de todos os containers:"
    docker ps -a
fi