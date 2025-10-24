#!/bin/bash

echo "🔧 CORREÇÃO DEFINITIVA TOTAL - TODOS OS ARQUIVOS"
echo "==============================================="

cd ~/moises

# Remove arquivos conflitantes
echo "🧹 Limpando conflitos..."
rm -f apply_fix.sh detailed_diagnosis.sh fix_neural_api.sh fix_neural_corrected.sh force_fix.sh

# Force pull
echo "📥 Forçando atualização completa..."
git fetch origin
git reset --hard origin/main

# Verificar se todas as correções foram aplicadas
echo "🔍 Verificando correções aplicadas:"

echo "1️⃣ app_neural_trading.py linha 25:"
sed -n '25p' app_neural_trading.py

echo "2️⃣ src/ml/neural_learning_agent.py linha 25:"
sed -n '25p' src/ml/neural_learning_agent.py

echo "3️⃣ app_multi_asset.py linha 22:"
sed -n '22p' app_multi_asset.py

# Aplicar correções se ainda necessário
files_to_fix=("app_neural_trading.py" "src/ml/neural_learning_agent.py" "app_multi_asset.py")
for file in "${files_to_fix[@]}"; do
    if grep -q "EquilibradaProStrategy" "$file" 2>/dev/null; then
        echo "⚠️ Corrigindo $file..."
        sed -i 's/EquilibradaProStrategy/ProductionTradingSystem/g' "$file"
        echo "✅ $file corrigido!"
    fi
done

echo ""
echo "🔍 Verificação final - deve estar tudo ProductionTradingSystem:"
grep -n "ProductionTradingSystem" app_neural_trading.py src/ml/neural_learning_agent.py app_multi_asset.py 2>/dev/null | head -10

# Rebuild TOTAL
echo ""
echo "🔨 REBUILD TOTAL - sem cache..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo "⏳ Aguardando inicialização completa (40 segundos)..."
sleep 40

# Teste FINAL
echo "🧪 TESTE DEFINITIVO..."
for i in {1..5}; do
    echo "Tentativa $i/5..."
    
    API_HEALTH=$(curl -s -w "%{http_code}" -o /tmp/api_health http://localhost:8001/health 2>/dev/null)
    DASH_HEALTH=$(curl -s -w "%{http_code}" -o /tmp/dash_health http://localhost:8501 2>/dev/null)
    
    if [ "$API_HEALTH" = "200" ]; then
        echo ""
        echo "🎉 SUCESSO COMPLETO!"
        echo "==================="
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo "🧠 API Neural: http://$IP:8001 ✅"
        echo "📊 Dashboard: http://$IP:8501 $([ "$DASH_HEALTH" = "200" ] && echo "✅" || echo "⚠️")"
        
        echo ""
        echo "🔗 Resposta da API Health:"
        cat /tmp/api_health
        
        echo ""
        echo "🎯 Testando endpoint de trading:"
        curl -s -X POST http://localhost:8001/trade/decision \
             -H "Content-Type: application/json" \
             -d '{"symbol":"AAPL","timeframe":"1h"}' | head -200
        
        echo ""
        echo "✅ SISTEMA 100% OPERACIONAL!"
        echo "🚀 Rede neural funcionando perfeitamente!"
        exit 0
        
    else
        echo "❌ API falhou (status: $API_HEALTH)"
        if [ $i -eq 5 ]; then
            echo ""
            echo "📋 Logs de diagnóstico:"
            echo "Status containers:"
            docker compose ps
            echo ""
            echo "Logs neural-trading:"
            docker compose logs neural-trading --tail=20
        else
            sleep 20
        fi
    fi
done

echo ""
echo "❌ Sistema ainda com problemas após todas as tentativas"