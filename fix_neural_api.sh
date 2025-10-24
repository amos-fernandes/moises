#!/bin/bash

echo "🔧 CORREÇÃO: Container neural-trading-api crashando"
echo "=============================================="

cd ~/moises

echo "🔍 Verificando logs detalhados..."
docker compose logs neural-trading-api --tail=50

echo ""
echo "🔍 Verificando se container está buildando corretamente..."
docker compose ps neural-trading-api

echo ""
echo "🛠️ Tentativa 1: Restart do container"
docker compose restart neural-trading-api

echo "⏳ Aguardando 10 segundos..."
sleep 10

echo "📊 Status após restart:"
docker compose ps neural-trading-api

echo ""
echo "🧪 Testando conectividade:"
if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "✅ FUNCIONOU! API respondendo"
else
    echo "❌ Ainda com problema"
    
    echo ""
    echo "🔍 Logs após restart:"
    docker compose logs neural-trading-api --tail=20
    
    echo ""
    echo "🛠️ Tentativa 2: Rebuild específico do neural-trading"
    docker compose build neural-trading --no-cache
    docker compose up -d neural-trading
    
    echo "⏳ Aguardando mais 15 segundos..."
    sleep 15
    
    echo "📊 Status final:"
    docker compose ps neural-trading-api
    
    echo "🧪 Teste final:"
    curl -s -w "Status: %{http_code}\n" http://localhost:8001/health || echo "Não conseguiu conectar"
fi

echo ""
echo "📋 Se ainda não funcionar, execute:"
echo "docker compose exec neural-trading-api bash"
echo "python3 app_neural_trading.py"