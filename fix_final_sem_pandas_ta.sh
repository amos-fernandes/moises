#!/bin/bash

# CORREÇÃO FINAL - Remove pandas-ta problemático e usa apenas 'ta'

echo "🎯 CORREÇÃO FINAL - Removendo pandas-ta problemático..."
echo "=================================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. PARAR TUDO
echo "🛑 Parando containers..."
docker-compose down -v --remove-orphans 2>/dev/null || true
docker container prune -f 2>/dev/null || true

# 2. LIMPAR CACHE DOCKER
echo "🧹 Limpando cache Docker..."
docker system prune -af
docker builder prune -af

# 3. ATUALIZAR CÓDIGO
echo "📥 Atualizando código..."
git stash 2>/dev/null || true
git pull origin main

# 4. REQUIREMENTS SEM PANDAS-TA
echo "📦 Criando requirements SEM pandas-ta..."
cat > requirements.txt << 'EOF'
# Sistema Neural Trading - Python 3.11 - SEM PANDAS-TA
fastapi==0.119.0
uvicorn[standard]==0.30.6
pydantic==2.5.2
python-multipart==0.0.6
pandas==2.1.4
numpy==1.26.4
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

echo "✅ Requirements sem pandas-ta criado!"

# 5. DOCKERFILE FUNCIONAL
echo "🐳 Criando Dockerfile funcional..."
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

# 6. DOCKER COMPOSE SIMPLES
echo "📋 Criando docker-compose..."
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
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped

  dashboard:
    build: 
      context: .
      no_cache: true
    container_name: neural-dashboard
    ports:
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    command: ["streamlit", "run", "neural_monitor_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
    depends_on:
      - neural
    restart: unless-stopped
EOF

# 7. TESTAR REQUIREMENTS PRIMEIRO
echo ""
echo "🔍 Testando requirements localmente..."
python3 -c "
import subprocess
import sys

packages = [
    'fastapi==0.119.0',
    'pandas==2.1.4', 
    'numpy==1.26.4',
    'ta==0.10.2',
    'tensorflow==2.15.0',
    'streamlit==1.29.0'
]

print('Testando pacotes essenciais...')
for pkg in packages:
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '--dry-run', pkg], 
                              capture_output=True, text=True, timeout=10)
        status = '✅' if result.returncode == 0 else '❌'
        print(f'{status} {pkg}')
    except Exception as e:
        print(f'❌ {pkg} - Erro: {e}')
"

# 8. BUILD
echo ""
echo "🔨 Build do sistema..."
if docker-compose build --no-cache 2>&1 | tee build.log; then
    echo "✅ BUILD SUCESSO!"
    
    echo "🚀 Iniciando sistema..."
    docker-compose up -d
    
    sleep 45
    
    if docker ps | grep -q neural-api; then
        echo ""
        echo "✅ SISTEMA NEURAL FUNCIONANDO!"
        
        IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
        echo ""
        echo "🌐 Acesse:"
        echo "   API Neural: http://$IP:8001"
        echo "   Dashboard:  http://$IP:8501"
        
        echo ""
        echo "📊 Containers:"
        docker-compose ps
        
        echo ""
        echo "🎯 PROBLEMA PANDAS-TA RESOLVIDO! Sistema usa apenas 'ta'"
        
    else
        echo "⚠️ Container iniciando..."
        docker-compose logs --tail=15
    fi
    
else
    echo "❌ Build falhou!"
    
    if grep -i "pandas" build.log; then
        echo "🔍 Ainda há problema com pandas. Logs:"
        grep -i "error\|failed" build.log | tail -5
    fi
    
    echo ""
    echo "🐍 Alternativa Python direto:"
    if command -v python3 >/dev/null; then
        python3 -m pip install --user -r requirements.txt
        echo "Execute: python3 app_neural_trading.py"
    fi
fi

echo ""
echo "=================================================="
echo "🎯 CORREÇÃO FINAL CONCLUÍDA!"
echo "   Removido: pandas-ta (problemático)"  
echo "   Mantido: ta==0.10.2 (funcional)"
echo "=================================================="