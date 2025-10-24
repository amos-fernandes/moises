#!/bin/bash

echo "🔧 FORÇANDO ATUALIZAÇÃO + CORREÇÃO DEFINITIVA"
echo "============================================="

cd ~/moises

# Remove arquivos que estão conflitando
echo "🧹 Removendo arquivos conflitantes..."
rm -f apply_fix.sh detailed_diagnosis.sh fix_neural_api.sh fix_neural_corrected.sh

# Force pull
echo "📥 Forçando git pull..."
git fetch origin
git reset --hard origin/main

echo "🔍 Verificando se correção foi aplicada:"
echo "Linha 25:"
sed -n '25p' app_neural_trading.py
echo "Linha 88:"
sed -n '88p' app_neural_trading.py

# Se ainda não foi aplicada, aplicar manualmente
if grep -q "EquilibradaProStrategy" app_neural_trading.py; then
    echo "⚠️ Correção não aplicada. Aplicando manualmente..."
    
    # Corrigir linha 25
    sed -i 's/from src.trading.production_system import EquilibradaProStrategy/from src.trading.production_system import ProductionTradingSystem/' app_neural_trading.py
    
    # Corrigir linha 88
    sed -i 's/self.equilibrada_pro = EquilibradaProStrategy()/self.equilibrada_pro = ProductionTradingSystem()/' app_neural_trading.py
    
    echo "✅ Correção aplicada manualmente!"
    echo "Nova linha 25:"
    sed -n '25p' app_neural_trading.py
    echo "Nova linha 88:"
    sed -n '88p' app_neural_trading.py
fi

# Rebuild e restart
echo "🔨 Rebuilding container..."
docker compose build neural-trading --no-cache
docker compose up -d neural-trading

echo "⏳ Aguardando 30 segundos..."
sleep 30

# Teste final
echo "🧪 TESTE FINAL..."
for i in {1..5}; do
    echo "Tentativa $i/5..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo ""
        echo "🎉 SUCESSO TOTAL!"
        echo "=================="
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
        
        echo ""
        echo "🔗 Testando endpoints:"
        echo "1️⃣ Health Check:"
        curl -s http://localhost:8001/health
        
        echo ""
        echo "2️⃣ Metrics:"
        curl -s http://localhost:8001/metrics | head -200
        
        echo ""
        echo "✅ SISTEMA 100% OPERACIONAL!"
        exit 0
    else
        echo "❌ Falhou"
        if [ $i -eq 5 ]; then
            echo ""
            echo "📋 Logs finais:"
            docker compose logs neural-trading --tail=15
        else
            sleep 15
        fi
    fi
done