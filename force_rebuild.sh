#!/bin/bash

# SOLUÇÃO FORÇADA - Remove TUDO e reconstrói

echo "💥 DESTRUINDO TUDO E RECONSTRUINDO..."
echo "=============================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. PARAR TUDO
echo "🛑 Parando todos os containers..."
docker stop $(docker ps -aq) 2>/dev/null || true
docker rm $(docker ps -aq) 2>/dev/null || true

# 2. REMOVER IMAGENS E CACHE
echo "🧹 Removendo TODAS as imagens e cache..."
docker rmi $(docker images -aq) --force 2>/dev/null || true
docker system prune -af --volumes
docker builder prune -af

# 3. LIMPAR DIRETÓRIO
echo "📁 Limpando diretório..."
rm -rf .dockerignore
rm -rf docker-compose.yml
rm -rf Dockerfile

# 4. BACKUP E ATUALIZAR
echo "💾 Fazendo backup e atualizando..."
git stash push -m "backup antes da correção forçada"
git reset --hard HEAD
git pull origin main --force

# 5. VERIFICAR SE REQUIREMENTS ESTÁ CORRETO
echo "🔍 Verificando requirements.txt..."
if grep -q "pandas-ta==0.4.71b0" requirements.txt; then
    echo "❌ Requirements ainda tem versão antiga! Corrigindo..."
    
    cat > requirements.txt << 'EOF'
fastapi==0.119.0
uvicorn[standard]==0.30.6
pydantic==2.5.2
python-multipart==0.0.6
pandas==2.1.4
numpy==1.26.4
pandas_ta==0.3.14b0
ta==0.10.2
yfinance==0.2.28
tensorflow==2.15.0
scikit-learn==1.3.2
ccxt==4.1.64
requests==2.31.0
streamlit==1.29.0
plotly==5.18.0
matplotlib==3.7.1
schedule==1.2.0
python-dotenv==1.0.0
redis==5.0.1
joblib==1.3.2
websockets==12.0
EOF
else
    echo "✅ Requirements correto"
fi

# 6. CRIAR DOCKERFILE FORÇADO
echo "🐳 Criando Dockerfile do zero..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Sistema
RUN apt-get update && apt-get install -y gcc g++ curl git && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home neural

# App
WORKDIR /app
COPY requirements.txt .

# Instalar sem cache FORÇADO
RUN pip install --upgrade pip --no-cache-dir
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data models && chown -R neural:neural /app

USER neural
EXPOSE 8001

CMD ["python", "app_neural_trading.py"]
EOF

# 7. DOCKER COMPOSE SIMPLES
echo "📦 Criando docker-compose do zero..."
cat > docker-compose.yml << 'EOF'
services:
  neural:
    build: 
      context: .
      no_cache: true
    container_name: neural-system
    ports:
      - "8001:8001"
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
EOF

# 8. BUILD FORÇADO SEM CACHE
echo "🔨 BUILD FORÇADO (sem cache)..."
DOCKER_BUILDKIT=1 docker-compose build --no-cache --pull --force-rm

if [ $? -eq 0 ]; then
    echo "✅ BUILD SUCESSO!"
    
    echo "🚀 Iniciando..."
    docker-compose up -d
    
    sleep 30
    
    if docker ps | grep -q neural-system; then
        echo "✅ SISTEMA FUNCIONANDO!"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo ""
        echo "🌐 Acesse: http://$IP:8001"
        echo "🎯 Dashboard: http://$IP:8501"
        
        echo ""
        echo "📊 Containers ativos:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
    else
        echo "⚠️ Sistema iniciando..."
        docker-compose logs
    fi
    
else
    echo "❌ BUILD FALHOU!"
    echo ""
    echo "🔧 Tentativa Python direto:"
    
    if command -v python3 >/dev/null; then
        echo "Instalando dependências Python..."
        python3 -m pip install --user --upgrade pip
        python3 -m pip install --user -r requirements.txt
        
        echo ""
        echo "🚀 Para rodar manualmente:"
        echo "  python3 app_neural_trading.py"
    fi
fi

echo ""
echo "=============================================="
echo "💥 RECONSTRUÇÃO FORÇADA COMPLETA!"
echo "=============================================="