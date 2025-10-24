#!/bin/bash

echo "🔧 CORREÇÃO DEFINITIVA MANUAL - Linha por linha"
echo "============================================="

cd ~/moises

# Verificar exatamente o que está na linha 109
echo "🔍 Conteúdo atual da linha 109:"
sed -n '109p' app_neural_trading.py

# Se ainda tem o erro, corrigir manualmente
if grep -q "start_continuous_learning" app_neural_trading.py; then
    echo "⚠️ AINDA COM ERRO! Corrigindo manualmente..."
    
    # Backup do arquivo
    cp app_neural_trading.py app_neural_trading.py.backup
    
    # Substituir TODAS as ocorrências
    sed -i 's/start_continuous_learning/start_continuous_training/g' app_neural_trading.py
    
    echo "✅ Correção manual aplicada!"
    echo "Nova linha 109:"
    sed -n '109p' app_neural_trading.py
    
    # Verificar se ainda tem alguma ocorrência
    if grep -q "start_continuous_learning" app_neural_trading.py; then
        echo "❌ AINDA TEM ERRO! Editando linha diretamente..."
        
        # Editar linha específica
        sed -i '109s/.*/            self.learning_system.start_continuous_training()/' app_neural_trading.py
        
        echo "Linha 109 após edição direta:"
        sed -n '109p' app_neural_trading.py
    fi
    
else
    echo "✅ Linha já está correta!"
fi

# Verificar se há outras ocorrências problemáticas
echo ""
echo "🔍 Verificando todas as ocorrências no arquivo:"
grep -n "start_continuous" app_neural_trading.py || echo "Nenhuma ocorrência encontrada"

# Parar e restart do container
echo ""
echo "🔄 Restart do container..."
docker compose stop neural-trading
sleep 5
docker compose start neural-trading

# Aguardar inicialização
echo "⏳ Aguardando 30 segundos para inicialização..."
sleep 30

# Teste direto
echo "🧪 TESTE DIRETO..."
for i in {1..5}; do
    echo "Tentativa $i/5..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo ""
        echo "🎉 FINALMENTE FUNCIONOU!"
        echo "======================="
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo "🧠 API Neural: http://$IP:8001"
        echo "📊 Dashboard: http://$IP:8501"
        
        echo ""
        echo "✅ Health Check Response:"
        curl -s http://localhost:8001/health | jq . 2>/dev/null || curl -s http://localhost:8001/health
        
        echo ""
        echo "🎯 Sistema Metrics:"
        curl -s http://localhost:8001/metrics | head -200
        
        echo ""
        echo "🚀 SUCESSO TOTAL! Sistema operacional!"
        echo "📈 De -78% para sistema funcional - OBJETIVO ALCANÇADO!"
        exit 0
        
    else
        echo "❌ Tentativa $i falhou"
        if [ $i -eq 5 ]; then
            echo ""
            echo "📋 Diagnóstico final:"
            echo "Container status:"
            docker compose ps neural-trading
            echo ""
            echo "Últimos logs:"
            docker compose logs neural-trading --tail=10
            echo ""
            echo "Conteúdo da linha problemática:"
            sed -n '109p' app_neural_trading.py
        else
            sleep 10
        fi
    fi
done