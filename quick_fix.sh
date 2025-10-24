#!/bin/bash

# Script rápido para aplicar TODAS as correções e testar

echo "🎯 APLICANDO CORREÇÕES FINAIS NA VPS"
echo "===================================="

cd ~/moises

# Pull das correções
echo "📥 Baixando correções..."
git pull origin main

# Parar e limpar tudo
echo "🧹 Limpando containers..."
docker compose down
docker system prune -f

# Rebuild completo
echo "🔨 Rebuild TOTAL..."
docker compose build --no-cache

# Iniciar
echo "🚀 Iniciando..."
docker compose up -d

# Aguardar menos tempo
echo "⏳ Aguardando 20 segundos..."
sleep 20

# Teste rápido
echo "🧪 Teste rápido..."
if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
    echo "✅ SUCCESS! API funcionando!"
    
    IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    echo ""
    echo "🎉 SISTEMA FUNCIONANDO!"
    echo "🧠 API Neural: http://$IP:8001"
    echo "📊 Dashboard: http://$IP:8501"
    
else
    echo "❌ Ainda com problema. Logs:"
    docker compose logs --tail=10 neural
fi