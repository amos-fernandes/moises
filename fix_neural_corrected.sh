#!/bin/bash

echo "🔧 CORREÇÃO: Container neural-trading crashando"
echo "============================================="

cd ~/moises

echo "🔍 Verificando logs detalhados..."
docker compose logs neural-trading --tail=50

echo ""
echo "🔍 Verificando se container está buildando corretamente..."
docker compose ps neural-trading

echo ""
echo "🛠️ Tentativa 1: Restart do container"
docker compose restart neural-trading

echo "⏳ Aguardando 15 segundos..."
sleep 15

echo "📊 Status após restart:"
docker compose ps neural-trading

echo ""
echo "🧪 Testando conectividade:"
if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "✅ FUNCIONOU! API respondendo"
    
    IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo ""
    echo "🎉 SUCESSO! Sistema operacional:"
    echo "🧠 API Neural: http://$IP:8001"
    echo "📊 Dashboard: http://$IP:8501"
    
else
    echo "❌ Ainda com problema"
    
    echo ""
    echo "🔍 Logs após restart (últimas 30 linhas):"
    docker compose logs neural-trading --tail=30
    
    echo ""
    echo "🛠️ Tentativa 2: Parar, rebuild e restart"
    docker compose stop neural-trading
    docker compose build neural-trading --no-cache
    docker compose up -d neural-trading
    
    echo "⏳ Aguardando mais 20 segundos..."
    sleep 20
    
    echo "📊 Status final:"
    docker compose ps neural-trading
    
    echo "🧪 Teste final:"
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ FUNCIONOU após rebuild!"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo ""
        echo "🎉 SUCESSO! Sistema operacional:"
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
    else
        echo "❌ Ainda com problema após rebuild"
        echo ""
        echo "📋 Logs finais:"
        docker compose logs neural-trading --tail=20
        
        echo ""
        echo "🔧 Diagnóstico manual necessário:"
        echo "docker compose exec neural-trading bash"
        echo "python3 app_neural_trading.py"
    fi
fi

echo ""
echo "📊 Status de todos os containers:"
docker compose ps