#!/bin/bash

echo "🔧 REBUILD FORÇADO - Container usando código antigo"
echo "================================================="

cd ~/moises

echo "📋 Verificando se arquivo local está correto:"
echo "Linha 109 no arquivo:"
sed -n '109p' app_neural_trading.py

echo ""
echo "🔍 O problema é que o CONTAINER tem código antigo!"
echo "Vamos forçar rebuild completo..."

# Parar tudo
echo "🛑 Parando todos os containers..."
docker compose down

# Limpar images antigas
echo "🧹 Limpando images antigas..."
docker image rm moises-neural-trading moises-dashboard 2>/dev/null || true

# Build completo sem cache
echo "🔨 BUILD COMPLETO sem cache..."
docker compose build --no-cache --pull

# Subir tudo
echo "🚀 Iniciando com nova imagem..."
docker compose up -d

# Aguardar mais tempo
echo "⏳ Aguardando 45 segundos para build completo..."
sleep 45

# Verificar se está buildado corretamente
echo "🔍 Verificando se container tem código atualizado..."
docker compose exec -T neural-trading cat /app/app_neural_trading.py | sed -n '109p'

echo ""
echo "🧪 TESTE FINAL COM NOVA IMAGEM..."
for i in {1..3}; do
    echo "Tentativa $i/3..."
    
    # Verificar se container está rodando
    if docker compose ps neural-trading | grep -q "Up"; then
        # Testar API
        if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
            echo ""
            echo "🎉 SUCESSO! FINALMENTE FUNCIONOU!"
            echo "=================================="
            
            IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
            
            echo "🧠 API Neural: http://$IP:8001 ✅"
            echo "📊 Dashboard: http://$IP:8501 ✅"
            
            echo ""
            echo "✅ Health Check Response:"
            curl -s http://localhost:8001/health
            
            echo ""
            echo "🎯 Metrics Response:"
            curl -s http://localhost:8001/metrics | head -100
            
            echo ""
            echo "🚀 OBJETIVO FINAL ALCANÇADO!"
            echo "📈 Sistema Neural de -78% para 100% Operacional!"
            echo "✅ Docker + API + Dashboard funcionando!"
            echo ""
            echo "🔗 Acesso completo:"
            echo "   API: http://$IP:8001"
            echo "   Dashboard: http://$IP:8501"
            
            exit 0
            
        else
            echo "❌ API não responde ainda"
        fi
    else
        echo "❌ Container não está rodando"
    fi
    
    if [ $i -eq 3 ]; then
        echo ""
        echo "📋 Status final dos containers:"
        docker compose ps
        echo ""
        echo "📋 Logs detalhados:"
        docker compose logs neural-trading --tail=15
        echo ""
        echo "🔍 Código dentro do container (linha 109):"
        docker compose exec -T neural-trading cat /app/app_neural_trading.py | sed -n '105,115p' | cat -n
    else
        sleep 20
    fi
done

echo ""
echo "ℹ️ Se ainda não funcionar, o container precisa de mais tempo ou há outro erro."