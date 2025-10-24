#!/bin/bash

echo "🔍 DIAGNÓSTICO DETALHADO - Identificar erro específico"
echo "================================================="

cd ~/moises

echo "📊 Status atual dos containers:"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"

echo ""
echo "🔍 Testando conectividade:"

# Teste 1: API Neural
echo "1️⃣ Testando API Neural (8001)..."
API_STATUS=$(curl -s -w "%{http_code}" -o /tmp/api_response http://localhost:8001/health 2>/dev/null)
if [ "$API_STATUS" = "200" ]; then
    echo "✅ API Neural: OK (200)"
    echo "📄 Resposta:" 
    cat /tmp/api_response | head -200
else
    echo "❌ API Neural: Status $API_STATUS"
    echo ""
    echo "📋 Logs COMPLETOS do neural-trading-api:"
    docker compose logs neural-trading-api 2>/dev/null || docker logs neural-trading-api 2>/dev/null
fi

echo ""
echo "2️⃣ Testando Dashboard (8501)..."
DASH_STATUS=$(curl -s -w "%{http_code}" -o /tmp/dash_response http://localhost:8501 2>/dev/null)
if [ "$DASH_STATUS" = "200" ]; then
    echo "✅ Dashboard: OK (200)"
else
    echo "❌ Dashboard: Status $DASH_STATUS"
    echo ""
    echo "📋 Logs do neural-dashboard:"
    docker compose logs neural-dashboard 2>/dev/null || docker logs neural-dashboard 2>/dev/null
fi

echo ""
echo "3️⃣ Verificando arquivos críticos:"

echo "📄 app_neural_trading.py linha 95:"
sed -n '95p' app_neural_trading.py

echo ""
echo "📄 continuous_training.py (primeiras linhas):"
head -5 src/ml/continuous_training.py

echo ""
echo "📄 docker-compose.yml (serviços):"
grep -A 2 -B 2 "services\|neural-trading-api\|neural-dashboard" docker-compose.yml

echo ""
echo "4️⃣ Verificando portas em uso:"
netstat -tlnp 2>/dev/null | grep -E ":8001|:8501" || ss -tlnp | grep -E ":8001|:8501"

echo ""
echo "5️⃣ Recursos do sistema:"
echo "Memória:"
free -h
echo "CPU:"
top -bn1 | grep "Cpu(s)" | head -1

echo ""
echo "🔧 Se algum container não estiver rodando:"
echo "  docker compose restart neural-trading-api"
echo "  docker compose restart neural-dashboard"

echo ""
echo "🔧 Para logs em tempo real:"
echo "  docker compose logs -f neural-trading-api"
echo "  docker compose logs -f neural-dashboard"

# Obter IP para URLs
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "🌐 URLs para teste externo:"
echo "  API: http://$IP:8001/health"
echo "  Dashboard: http://$IP:8501"