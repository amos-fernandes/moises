#!/bin/bash

echo "🔧 FINAL FIX - Resolvendo neural_agent None"

# Para e remove containers
echo "📦 Parando containers..."
docker stop neural-trading-api neural-dashboard neural-redis 2>/dev/null || true
docker rm neural-trading-api neural-dashboard neural-redis 2>/dev/null || true

# Remove imagem antiga para forçar rebuild
echo "🗑️ Removendo imagem antiga..."
docker rmi moises-neural-trading 2>/dev/null || true

# Rebuild com as correções
echo "🔨 Rebuilding com correções neural_agent..."
docker build -t moises-neural-trading .

# Inicia containers
echo "🚀 Iniciando containers corrigidos..."
docker run -d --name neural-redis -p 6379:6379 redis:alpine

docker run -d --name neural-trading-api \
  -p 8001:8001 \
  -v $(pwd):/app \
  -e PYTHONPATH=/app \
  --link neural-redis:redis \
  moises-neural-trading \
  python app_neural_trading.py

docker run -d --name neural-dashboard \
  -p 8501:8501 \
  -v $(pwd):/app \
  -e PYTHONPATH=/app \
  --link neural-redis:redis \
  --link neural-trading-api:api \
  moises-neural-trading \
  streamlit run dashboard/main.py --server.port=8501 --server.address=0.0.0.0

echo "⏳ Aguardando containers iniciarem..."
sleep 15

echo "🔍 Testando API corrigida..."

# Testa health check
echo "Health Check:"
curl -s http://localhost:8001/health | python -m json.tool

# Testa neural status
echo -e "\nNeural Status:"
curl -s http://localhost:8001/api/neural/status | python -m json.tool

echo -e "\n✅ CORREÇÃO APLICADA!"
echo "🌐 API: http://localhost:8001"
echo "📊 Dashboard: http://localhost:8501"

# Mostra logs se houver erro
echo -e "\n📋 Logs da API:"
docker logs neural-trading-api --tail 20