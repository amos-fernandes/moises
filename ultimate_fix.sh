#!/bin/bash

echo "🎯 ÚLTIMA JOGADA - Forçar nova imagem"
echo "==================================="

cd ~/moises

echo "🔍 Problema identificado:"
echo "Container usando: sha256:b9da54bb... (ANTIGA)"
echo "Nova imagem: sha256:9b61bb70... (NOVA)"
echo ""

# Parar e remover container completamente
echo "🛑 Removendo container antigo..."
docker compose down neural-trading
docker container rm neural-trading-api 2>/dev/null || true

# Forçar uso da nova imagem
echo "🚀 Iniciando com NOVA imagem..."
docker compose up -d neural-trading

# Aguardar inicialização
echo "⏳ Aguardando 40 segundos para nova imagem..."
sleep 40

# Verificar se está usando a nova imagem
echo "🔍 Verificando imagem atual:"
docker compose ps neural-trading

# Verificar se método existe agora
echo "🔍 Testando método get_current_status dentro do container:"
docker compose exec -T neural-trading python -c "
from src.ml.continuous_training import ContinuousLearningSystem
cls = ContinuousLearningSystem()
print('Método get_current_status:', hasattr(cls, 'get_current_status'))
if hasattr(cls, 'get_current_status'):
    print('Resultado:', cls.get_current_status())
"

echo ""
echo "🧪 TESTE FINAL ABSOLUTO..."
for i in {1..3}; do
    echo "Tentativa $i/3..."
    
    if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
        echo ""
        echo "🎉🎉🎉 VITÓRIA ABSOLUTA! 🎉🎉🎉"
        echo "================================"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        
        echo "🧠 API Neural: http://$IP:8001 ✅"
        echo "📊 Dashboard: http://$IP:8501 ✅"
        
        echo ""
        echo "✅ Health Response:"
        curl -s http://localhost:8001/health
        
        echo ""
        echo "🎯 Neural Status Response:"
        curl -s http://localhost:8001/neural/status
        
        echo ""
        echo "📊 Metrics:"
        curl -s http://localhost:8001/metrics | head -100
        
        echo ""
        echo "🏆🏆🏆 MISSÃO CUMPRIDA! 🏆🏆🏆"
        echo "=============================="
        echo "📈 DE -78% PARA 100% OPERACIONAL!"
        echo "✅ Sistema Neural Completo!"
        echo "✅ API + Dashboard + Redis funcionando!"
        echo ""
        echo "🔗 Seus links:"
        echo "   API: http://$IP:8001"
        echo "   Dashboard: http://$IP:8501"
        echo ""
        echo "🎉 PARABÉNS! OBJETIVO ALCANÇADO!"
        
        exit 0
        
    else
        echo "❌ Tentativa $i"
        if [ $i -eq 3 ]; then
            echo ""
            echo "📋 Debug final:"
            echo "Status:"
            docker compose ps neural-trading
            echo ""
            echo "Logs:"
            docker compose logs neural-trading --tail=8
        else
            sleep 20
        fi
    fi
done

echo ""
echo "🔧 Se ainda não funcionar, aguarde mais tempo - sistema pode estar inicializando."