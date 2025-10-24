#!/bin/bash

# TESTE RÁPIDO - apenas verificar se está funcionando

cd ~/moises

echo "🧪 TESTE DIRETO DOS ENDPOINTS"
echo "============================="

echo "📊 Containers ativos:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "🔍 Testando API Neural (porta 8001)..."
if curl -s -w "\nStatus: %{http_code}\n" http://localhost:8001/health; then
    echo ""
    echo "✅ API Neural respondendo!"
else
    echo "❌ API Neural não responde"
    echo ""
    echo "📋 Logs do neural-trading-api:"
    docker compose logs --tail=15 neural-trading-api
fi

echo ""
echo "🔍 Testando Dashboard (porta 8501)..."
if curl -s -o /dev/null -w "Status: %{http_code}\n" http://localhost:8501; then
    echo "✅ Dashboard respondendo!"
else
    echo "❌ Dashboard não responde"
fi

echo ""
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo "🌐 URLs para acesso:"
echo "  API Neural: http://$IP:8001"
echo "  Dashboard: http://$IP:8501"