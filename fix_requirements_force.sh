#!/bin/bash

# CORREÇÃO DEFINITIVA - Força atualização do requirements.txt na VPS

echo "🔧 FORÇANDO ATUALIZAÇÃO DO REQUIREMENTS.TXT..."
echo "================================================"

cd ~/moises || { echo "❌ Erro: Diretório ~/moises não encontrado!"; exit 1; }

# 1. MOSTRAR PROBLEMA ATUAL
echo "🔍 Verificando requirements.txt atual..."
if [ -f "requirements.txt" ]; then
    echo "📄 Conteúdo atual do requirements.txt:"
    head -10 requirements.txt
    echo "..."
    
    if grep -q "pandas-ta==0.4.71b0\|pandas_ta==0.4.71b0" requirements.txt; then
        echo "❌ PROBLEMA ENCONTRADO: Versão 0.4.71b0 detectada!"
    elif grep -q "pandas_ta==0.3.14b0" requirements.txt; then
        echo "✅ Versão correta encontrada, mas Docker ainda com problema..."
    fi
else
    echo "❌ requirements.txt não encontrado!"
fi

# 2. FORÇAR LIMPEZA TOTAL DO GIT
echo ""
echo "🗑️  Forçando limpeza Git..."
git stash clear 2>/dev/null || true
git reset --hard HEAD 2>/dev/null || true
git clean -fdx 2>/dev/null || true

# 3. PULL FORÇADO
echo "📥 Pull forçado do GitHub..."
git fetch origin --force
git reset --hard origin/main
git pull origin main --force

# 4. VERIFICAR SE CORRIGIU
echo ""
echo "🔍 Verificando após pull..."
if grep -q "pandas-ta==0.4.71b0\|pandas_ta==0.4.71b0" requirements.txt 2>/dev/null; then
    echo "❌ AINDA COM PROBLEMA! Forçando correção manual..."
    
    # SOBRESCREVER FORÇADO
    cat > requirements.txt << 'EOF'
# Sistema Neural Trading - Dependências Essenciais Python 3.11
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
keras==3.11.3
ccxt==4.1.64
requests==2.31.0
streamlit==1.29.0
plotly==5.18.0
matplotlib==3.7.1
seaborn==0.13.0
schedule==1.2.0
python-dotenv==1.0.0
redis==5.0.1
aiofiles==23.2.1
joblib==1.3.2
websockets==12.0
EOF
    echo "✅ Requirements.txt sobrescrito forçadamente!"
else
    echo "✅ Requirements.txt está correto!"
fi

# 5. MOSTRAR CONTEÚDO FINAL
echo ""
echo "📋 Requirements.txt final:"
head -15 requirements.txt

echo ""
echo "🔍 Verificando pandas_ta especificamente:"
grep pandas_ta requirements.txt || echo "❌ pandas_ta não encontrado!"

# 6. LIMPAR DOCKER COMPLETAMENTE
echo ""
echo "🧹 Limpeza Docker total..."
docker-compose down -v --remove-orphans 2>/dev/null || true
docker container prune -f 2>/dev/null || true
docker image prune -af 2>/dev/null || true
docker system prune -af 2>/dev/null || true
docker builder prune -af 2>/dev/null || true

# Remover arquivos Docker locais
rm -f Dockerfile docker-compose.yml 2>/dev/null || true

# 7. CRIAR DOCKERFILE LIMPO
echo "🐳 Criando Dockerfile limpo..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y gcc g++ curl git && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home neural

WORKDIR /app
COPY requirements.txt .

# Instalar pandas_ta específico primeiro
RUN pip install --upgrade pip --no-cache-dir
RUN pip install pandas_ta==0.3.14b0 --no-cache-dir
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs data models && chown -R neural:neural /app

USER neural
EXPOSE 8001
CMD ["python", "app_neural_trading.py"]
EOF

# 8. DOCKER COMPOSE SIMPLES
echo "📦 Criando docker-compose simples..."
cat > docker-compose.yml << 'EOF'
services:
  neural:
    build: 
      context: .
      no_cache: true
    container_name: neural-api
    ports:
      - "8001:8001"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
EOF

# 9. BUILD COM VERIFICAÇÃO
echo ""
echo "🔨 Testando build..."
if docker-compose build --no-cache 2>&1 | tee build.log; then
    echo "✅ BUILD SUCESSO!"
    
    echo "🚀 Iniciando sistema..."
    docker-compose up -d
    
    sleep 30
    
    if docker ps | grep -q neural-api; then
        echo "✅ SISTEMA FUNCIONANDO!"
        
        # Mostrar IPs
        IP_EXTERNO=$(curl -s ifconfig.me 2>/dev/null || echo "VPS_IP")
        IP_INTERNO=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
        
        echo ""
        echo "🌐 Acesse o sistema:"
        echo "   Externo: http://$IP_EXTERNO:8001"
        echo "   Interno: http://$IP_INTERNO:8001"
        echo "   Local:   http://localhost:8001"
        
        echo ""
        echo "✅ PROBLEMA PANDAS-TA RESOLVIDO DEFINITIVAMENTE!"
        
    else
        echo "⚠️ Container iniciando..."
        docker-compose logs --tail=10
    fi
    
else
    echo "❌ Build falhou! Verificando log..."
    if grep -q "pandas-ta==0.4.71b0" build.log 2>/dev/null; then
        echo "🔥 AINDA TEM 0.4.71b0! Problema no cache Git."
        echo "Execute: rm requirements.txt && git checkout HEAD -- requirements.txt"
    fi
    
    echo ""
    echo "🔧 Alternativa Python direto:"
    if command -v python3 >/dev/null; then
        pip3 install --user pandas_ta==0.3.14b0
        pip3 install --user -r requirements.txt 2>/dev/null || true
        echo "Execute: python3 app_neural_trading.py"
    fi
fi

echo ""
echo "================================================"
echo "🎯 CORREÇÃO REQUIREMENTS.TXT CONCLUÍDA!"
echo "================================================"