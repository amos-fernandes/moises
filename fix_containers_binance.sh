#!/bin/bash

# 🔧 FIX CONTAINERS + TESTE BINANCE REAL
# Corrige conflitos e configura conexão com Binance para testes reais

echo "🔧 CORREÇÃO CONTAINERS + CONFIGURAÇÃO BINANCE REAL"
echo "=========================================================="

# 1. Parar e remover containers completamente
echo "🛑 Removendo containers conflituosos..."
docker stop neural-trading-api neural-dashboard neural-redis 2>/dev/null || true
docker rm neural-trading-api neural-dashboard neural-redis 2>/dev/null || true

# 2. Verificar se ainda há containers rodando
echo "📋 Verificando containers restantes..."
docker ps --filter "name=neural-" --format "table {{.Names}}\t{{.Status}}"

# 3. Reiniciar containers corretamente
echo "🚀 Reiniciando containers limpos..."

# Redis primeiro
echo "   📊 Iniciando Redis..."
docker run -d --name neural-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:alpine

sleep 3

# API Neural com todas as correções
echo "   🧠 Iniciando Neural API com Sistema de Evolução..."
docker run -d --name neural-trading-api \
  -p 8001:8001 \
  --link neural-redis:redis \
  --restart unless-stopped \
  --health-cmd="curl -f http://localhost:8001/health || exit 1" \
  --health-interval=30s \
  --health-timeout=10s \
  --health-retries=3 \
  -e REDIS_URL=redis://redis:6379 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/models:/app/models \
  moises-neural-trading

sleep 5

# Dashboard
echo "   📈 Iniciando Dashboard..."
docker run -d --name neural-dashboard \
  -p 8501:8501 \
  --link neural-trading-api:api \
  --restart unless-stopped \
  -e API_URL=http://api:8001 \
  moises-neural-trading streamlit run dashboard.py --server.port=8501

echo "⏳ Aguardando inicialização (30 segundos)..."
sleep 30

# 4. Testar endpoints básicos
echo ""
echo "🧪 TESTANDO ENDPOINTS CORRIGIDOS:"
echo "================================"

echo "📊 Health Check:"
curl -s http://localhost:8001/health || echo "❌ Health Check falhou"

echo -e "\n🧠 Neural Status:"
curl -s http://localhost:8001/api/neural/status || echo "❌ Neural Status falhou"

echo -e "\n🎯 Evolution Status (NOVO):"
curl -s http://localhost:8001/api/evolution/status || echo "⚠️ Evolution endpoint não disponível ainda"

echo ""
echo "=========================================================="
echo "🎯 PRÓXIMA ETAPA: CONFIGURAÇÃO BINANCE TESTNET"
echo ""
echo "Para testar com Binance REAL mas sem risco:"
echo ""
echo "1. 🔑 Configure suas chaves da Binance TESTNET:"
echo "   • Acesse: https://testnet.binance.vision/"
echo "   • Crie API Key e Secret"
echo "   • Use para testes seguros"
echo ""
echo "2. 🧪 Execute teste real:"
echo "   curl -X POST http://localhost:8001/api/trading/test-binance \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"api_key\":\"SUA_TESTNET_KEY\", \"secret\":\"SUA_TESTNET_SECRET\"}'"
echo ""
echo "3. 🚀 Ative evolução para 85%:"
echo "   curl -X POST http://localhost:8001/api/evolution/start"
echo ""
echo "✅ Containers corrigidos e prontos para testes!"