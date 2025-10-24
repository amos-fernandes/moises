#!/bin/bash

echo "🔍 DIAGNÓSTICO COMPLETO + CORREÇÃO FORÇADA"
echo "=========================================="

cd ~/moises

echo "📍 Diretório atual:"
pwd

echo ""
echo "📋 Status do Git:"
git status

echo ""
echo "📥 Git pull FORÇADO:"
git fetch origin
git reset --hard origin/main

echo ""
echo "🔍 Verificando arquivo app_neural_trading.py:"
echo "Linha 95 (deve estar SEM target_accuracy):"
sed -n '95p' app_neural_trading.py

echo ""
echo "🔍 Verificando continuous_training.py:"
echo "Deve ser versão mínima com 20 linhas:"
wc -l src/ml/continuous_training.py
head -10 src/ml/continuous_training.py

echo ""
echo "🧹 Limpeza TOTAL Docker:"
docker compose down
docker system prune -af
docker volume prune -f

echo ""
echo "🔨 Build COMPLETO (sem cache):"
docker compose build --no-cache --pull

echo ""
echo "🚀 Iniciando containers:"
docker compose up -d

echo ""
echo "⏳ Aguardando 30 segundos..."
sleep 30

echo ""
echo "🧪 TESTE FINAL:"
for i in {1..3}; do
    echo "Tentativa $i..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo "✅ SUCESSO! API funcionando!"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo ""
        echo "🎉 SISTEMA TOTALMENTE FUNCIONANDO!"
        echo "=================================="
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
        echo ""
        echo "🔗 Endpoints testados:"
        echo "  ✅ GET /health"
        curl -s http://localhost:8001/health | head -100
        echo ""
        
        exit 0
    else
        echo "❌ Tentativa $i falhou"
        if [ $i -eq 3 ]; then
            echo ""
            echo "📋 LOGS COMPLETOS DO ERRO:"
            docker compose logs --tail=50 neural
            
            echo ""
            echo "📊 STATUS CONTAINERS:"
            docker ps -a
        else
            sleep 15
        fi
    fi
done

echo ""
echo "🔧 Se ainda não funcionar, execute manualmente:"
echo "git show HEAD:app_neural_trading.py | grep -n target_accuracy"
echo "docker compose exec neural cat /app/app_neural_trading.py | grep -n target_accuracy"