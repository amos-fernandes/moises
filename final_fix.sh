#!/bin/bash

echo "🎯 APLICAÇÃO FINAL - SEM target_accuracy"
echo "======================================="

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
echo "⏳ Aguardando 25 segundos..."
sleep 25

echo "🧪 Teste final..."
if curl -f -s http://localhost:8001/health; then
    echo ""
    echo "🎉 SUCESSO! API funcionando!"
    IP=$(curl -s ifconfig.me 2>/dev/null)
    echo "🧠 API: http://$IP:8001"
    echo "📊 Dashboard: http://$IP:8501"
else
    echo "❌ Logs do erro:"
    docker compose logs --tail=5 neural
fi