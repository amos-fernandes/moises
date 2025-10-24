#!/bin/bash

echo "🔧 APLICANDO CORREÇÃO DO ImportError"
echo "==================================="

cd ~/moises

# Pull da correção
echo "📥 Baixando correção..."
git pull origin main

echo "🔍 Verificando correção aplicada:"
echo "Linha 25 (deve ter ProductionTradingSystem):"
sed -n '25p' app_neural_trading.py
echo "Linha 88 (deve ter ProductionTradingSystem):"
sed -n '88p' app_neural_trading.py

# Parar e restart
echo "🔄 Reiniciando container..."
docker compose stop neural-trading
docker compose start neural-trading

# Aguardar
echo "⏳ Aguardando 20 segundos..."
sleep 20

# Testar
echo "🧪 Testando API..."
for i in {1..3}; do
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ SUCESSO! API funcionando na tentativa $i"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo ""
        echo "🎉 SISTEMA 100% OPERACIONAL!"
        echo "============================="
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
        echo ""
        echo "🔗 Testando endpoints:"
        
        echo "1️⃣ /health"
        curl -s http://localhost:8001/health | head -100
        
        echo ""
        echo "2️⃣ /metrics" 
        curl -s http://localhost:8001/metrics | head -100
        
        exit 0
    else
        echo "❌ Tentativa $i falhou"
        if [ $i -eq 3 ]; then
            echo ""
            echo "📋 Logs do erro:"
            docker compose logs neural-trading --tail=10
        else
            sleep 10
        fi
    fi
done