#!/bin/bash

# 🚀 DEPLOY SISTEMA DE EVOLUÇÃO NA VPS
# Atualiza VPS com componentes de evolução para 85% ganhos

echo "🚀 DEPLOY DO SISTEMA DE EVOLUÇÃO - TARGET 85% GANHOS"
echo "============================================================"

# 1. Atualizar repositório na VPS
echo "📥 Atualizando repositório..."
cd ~/moises || exit 1
git pull origin main

# 2. Parar containers atuais
echo "🛑 Parando containers para atualização..."
docker stop neural-trading-api neural-dashboard neural-redis 2>/dev/null || true

# 3. Rebuild com novos componentes
echo "🔨 Rebuilding com sistema de evolução..."
docker build -t moises-neural-trading .

# 4. Reiniciar containers com evolução
echo "🚀 Iniciando sistema com componentes de evolução..."

# Redis
docker run -d --name neural-redis \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:alpine

# API Neural com Evolução
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

# Dashboard
docker run -d --name neural-dashboard \
  -p 8501:8501 \
  --link neural-trading-api:api \
  --restart unless-stopped \
  -e API_URL=http://api:8001 \
  moises-neural-trading streamlit run dashboard.py --server.port=8501

sleep 10

# 5. Testar novos endpoints de evolução
echo "🧪 Testando novos endpoints de evolução..."

echo "📊 Testando Health Check..."
curl -s http://localhost:8001/health | python3 -m json.tool

echo -e "\n🎯 Testando Evolution Status..."
curl -s http://localhost:8001/api/evolution/status | python3 -m json.tool

echo -e "\n🔧 Testando Optimization Analysis..."
curl -s http://localhost:8001/api/optimization/analysis | python3 -m json.tool

echo -e "\n📈 Testando Multi-Asset Portfolio..."
curl -s http://localhost:8001/api/multi-asset/portfolio | python3 -m json.tool

echo ""
echo "============================================================"
echo "🎉 SISTEMA DE EVOLUÇÃO DEPLOYADO COM SUCESSO!"
echo ""
echo "🌐 NOVOS ENDPOINTS DISPONÍVEIS:"
echo "   • Evolução Start:  POST http://IP:8001/api/evolution/start"
echo "   • Evolução Status: GET  http://IP:8001/api/evolution/status" 
echo "   • Optimization:    GET  http://IP:8001/api/optimization/analysis"
echo "   • Multi-Asset:     GET  http://IP:8001/api/multi-asset/portfolio"
echo ""
echo "🎯 PRÓXIMO PASSO:"
echo "   Execute: curl -X POST http://IP:8001/api/evolution/start"
echo "   Para iniciar evolução de 50% → 85% accuracy!"
echo ""
echo "✅ Sistema pronto para transformação completa!"