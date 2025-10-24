#!/bin/bash

# CORREÇÃO DEFINITIVA - Limpa tudo e reconstroi do zero

echo "🧹 LIMPEZA TOTAL DO SISTEMA..."
echo "=============================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. PARAR E LIMPAR TUDO
echo "🛑 Parando e removendo tudo..."
docker-compose down -v
docker container prune -f
docker image prune -af
docker system prune -af
docker builder prune -af

# 2. ATUALIZAR CÓDIGO
echo "📥 Atualizando código..."
git stash
git pull origin main

# 3. USAR REQUIREMENTS MINIMAL
echo "📦 Usando requirements limpo..."
if [ -f "requirements_minimal.txt" ]; then
    cp requirements_minimal.txt requirements.txt
    echo "✅ Requirements atualizado"
else
    echo "⚠️  Criando requirements mínimo..."
    cat > requirements.txt << 'EOF'
# Sistema Neural Trading - Dependências Essenciais
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
EOF
fi

# 4. DOCKERFILE LIMPO
echo "🐳 Criando Dockerfile otimizado..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    gcc g++ curl git \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home neural
WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data models && chown -R neural:neural /app

USER neural
EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "app_neural_trading.py"]
EOF

# 5. DOCKER-COMPOSE SIMPLES
echo "📋 Criando docker-compose otimizado..."
cat > docker-compose.yml << 'EOF'
services:
  neural-trading:
    build: .
    container_name: neural-api
    ports:
      - "8001:8001"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped

  dashboard:
    build: .
    container_name: neural-dashboard  
    ports:
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    command: ["streamlit", "run", "neural_monitor_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
    depends_on:
      - neural-trading
    restart: unless-stopped
EOF

# 6. BUILD DO ZERO
echo "🔨 Build do zero (pode demorar)..."
docker-compose build --no-cache --pull

if [ $? -eq 0 ]; then
    echo "✅ Build sucesso!"
    
    echo "🚀 Iniciando sistema..."
    docker-compose up -d
    
    echo "⏳ Aguardando 60s..."
    sleep 60
    
    if curl -f -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "✅ SISTEMA FUNCIONANDO!"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || echo "$(hostname -I | awk '{print $1}')")
        echo ""
        echo "🌐 Acesse:"
        echo "   Neural API: http://$IP:8001"
        echo "   Dashboard:  http://$IP:8501"
        
        echo ""
        echo "📊 Status:"
        docker-compose ps
        
    else
        echo "⚠️  Sistema ainda carregando..."
        echo "📋 Logs:"
        docker-compose logs --tail=20
    fi
else
    echo "❌ Build falhou! Tentando Python direto..."
    
    if command -v python3 >/dev/null; then
        echo "🐍 Instalando Python direto..."
        python3 -m pip install --user -r requirements.txt
        
        echo "🚀 Execute manualmente:"
        echo "  python3 app_neural_trading.py &"
        echo "  streamlit run neural_monitor_dashboard.py &"
    fi
fi

echo ""
echo "=============================================="
echo "🎯 CORREÇÃO COMPLETA!"
echo "=============================================="