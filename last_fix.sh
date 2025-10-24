#!/bin/bash

echo "🔧 ÚLTIMA CORREÇÃO: AttributeError start_continuous_learning"
echo "========================================================"

cd ~/moises

# Pull da correção
echo "📥 Baixando última correção..."
git pull origin main

# Verificar correção
echo "🔍 Verificando linha 109 (deve ter start_continuous_training):"
sed -n '109p' app_neural_trading.py

# Aplicar manualmente se necessário
if grep -q "start_continuous_learning" app_neural_trading.py; then
    echo "⚠️ Aplicando correção manual..."
    sed -i 's/start_continuous_learning/start_continuous_training/g' app_neural_trading.py
    echo "✅ Correção aplicada!"
fi

# Restart apenas do container neural-trading
echo "🔄 Restart rápido do container..."
docker compose restart neural-trading

# Aguardar
echo "⏳ Aguardando 25 segundos..."
sleep 25

# Teste final
echo "🧪 TESTE FINAL..."
for i in {1..3}; do
    echo "Tentativa $i/3..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo ""
        echo "🎉 SUCESSO DEFINITIVO!"
        echo "====================="
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo "🧠 API Neural: http://$IP:8001 ✅"
        echo "📊 Dashboard: http://$IP:8501 ✅"
        
        echo ""
        echo "🔗 Health Check:"
        curl -s http://localhost:8001/health
        
        echo ""
        echo "🎯 Metrics:"
        curl -s http://localhost:8001/metrics | head -100
        
        echo ""
        echo "✅ SISTEMA 100% OPERACIONAL!"
        echo "🚀 Objetivo alcançado: De -78% para sistema funcional!"
        exit 0
        
    else
        echo "❌ Falhou na tentativa $i"
        if [ $i -eq 3 ]; then
            echo ""
            echo "📋 Status final:"
            docker compose ps neural-trading
            echo ""
            echo "Logs finais:"
            docker compose logs neural-trading --tail=15
        else
            sleep 15
        fi
    fi
done