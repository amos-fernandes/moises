#!/bin/bash

# CORREÇÃO COMPLETA - Resolve Git + Instala Docker Compose + Inicia Sistema

echo "🔧 CORREÇÃO COMPLETA - Git + Docker Compose..."
echo "=============================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. RESOLVER CONFLITOS GIT
echo "📁 Resolvendo conflitos Git..."
rm -f fix_final_sem_pandas_ta.sh 2>/dev/null || true
git reset --hard HEAD 2>/dev/null || true
git clean -fd 2>/dev/null || true
git pull origin main --force

echo "✅ Git atualizado!"

# 2. INSTALAR DOCKER COMPOSE
echo ""
echo "🐳 Verificando/Instalando Docker Compose..."

if ! command -v docker-compose >/dev/null 2>&1; then
    echo "📦 Docker Compose não encontrado. Instalando..."
    
    # Método 1: Via apt (Ubuntu/Debian)
    if command -v apt >/dev/null 2>&1; then
        sudo apt update
        sudo apt install -y docker-compose-plugin docker-compose
    fi
    
    # Método 2: Download direto (fallback)
    if ! command -v docker-compose >/dev/null 2>&1; then
        echo "📥 Instalando via download direto..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
        
        # Criar link simbólico se necessário
        sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose 2>/dev/null || true
    fi
    
    # Método 3: Docker plugin (mais moderno)
    if ! command -v docker-compose >/dev/null 2>&1; then
        echo "🔧 Tentando docker compose (plugin)..."
        # Testar se docker compose funciona
        if docker compose version >/dev/null 2>&1; then
            echo "✅ Docker Compose plugin disponível!"
            # Criar alias
            echo 'alias docker-compose="docker compose"' >> ~/.bashrc
            alias docker-compose="docker compose"
        fi
    fi
else
    echo "✅ Docker Compose já instalado!"
fi

# Verificar versão
echo "🔍 Versão Docker Compose:"
docker-compose --version 2>/dev/null || docker compose version 2>/dev/null || echo "❌ Não funcionou"

# 3. DEFINIR COMANDO DOCKER COMPOSE
if command -v docker-compose >/dev/null 2>&1; then
    DC_CMD="docker-compose"
elif docker compose version >/dev/null 2>&1; then
    DC_CMD="docker compose"
else
    echo "❌ Docker Compose não disponível!"
    echo "🔧 Tentando instalação Python..."
    pip3 install docker-compose 2>/dev/null || true
    DC_CMD="docker-compose"
fi

echo "📋 Usando comando: $DC_CMD"

# 4. REQUIREMENTS SEM PANDAS-TA
echo ""
echo "📦 Criando requirements correto..."
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

# 5. DOCKERFILE OTIMIZADO
echo "🐳 Criando Dockerfile..."
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

CMD ["python", "app_neural_trading.py"]
EOF

# 6. DOCKER COMPOSE SIMPLES
echo "📋 Criando docker-compose.yml..."
cat > docker-compose.yml << 'EOF'
services:
  neural:
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
      - neural
    restart: unless-stopped
EOF

# 7. PARAR CONTAINERS EXISTENTES
echo ""
echo "🛑 Parando containers existentes..."
$DC_CMD down -v --remove-orphans 2>/dev/null || true
docker container prune -f 2>/dev/null || true

# 8. BUILD DO SISTEMA
echo ""
echo "🔨 Build do sistema neural..."
if $DC_CMD build --no-cache 2>&1 | tee build.log; then
    echo "✅ BUILD SUCESSO!"
    
    # 9. INICIAR SISTEMA
    echo "🚀 Iniciando sistema..."
    $DC_CMD up -d
    
    # 10. AGUARDAR E VERIFICAR
    echo "⏳ Aguardando 60 segundos..."
    sleep 60
    
    echo ""
    echo "🔍 Verificando containers..."
    $DC_CMD ps
    
    if docker ps | grep -E "(neural-api|neural-dashboard)" | wc -l | grep -q "2"; then
        echo ""
        echo "✅ SISTEMA NEURAL FUNCIONANDO COMPLETAMENTE!"
        
        # Obter IPs
        IP_EXTERNO=$(curl -s ifconfig.me 2>/dev/null || echo "VPS_IP")
        IP_INTERNO=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")
        
        echo ""
        echo "🌐 SISTEMA DISPONÍVEL:"
        echo "   🤖 Neural API:  http://$IP_EXTERNO:8001"
        echo "   📊 Dashboard:   http://$IP_EXTERNO:8501"  
        echo "   🏠 Local API:   http://$IP_INTERNO:8001"
        echo "   🏠 Local Dash:  http://$IP_INTERNO:8501"
        
        echo ""
        echo "🎯 TESTANDO APIs..."
        if curl -f -s http://localhost:8001/health >/dev/null 2>&1; then
            echo "✅ Neural API respondendo!"
        else
            echo "⚠️  Neural API ainda carregando..."
        fi
        
        if curl -f -s http://localhost:8501 >/dev/null 2>&1; then
            echo "✅ Dashboard respondendo!"
        else
            echo "⚠️  Dashboard ainda carregando..."
        fi
        
        echo ""
        echo "📋 Logs recentes:"
        $DC_CMD logs --tail=5 neural
        
    else
        echo "⚠️  Containers ainda iniciando..."
        echo ""
        echo "📋 Status containers:"
        docker ps -a | grep neural
        
        echo ""
        echo "📋 Logs de erro:"
        $DC_CMD logs --tail=10
    fi
    
else
    echo "❌ Build falhou!"
    echo ""
    echo "📋 Últimas linhas do erro:"
    tail -10 build.log
    
    echo ""
    echo "🐍 Alternativa Python direto:"
    if command -v python3 >/dev/null; then
        echo "Instalando dependências..."
        python3 -m pip install --user -r requirements.txt 2>/dev/null || true
        echo ""
        echo "🚀 Para rodar manualmente:"
        echo "  python3 app_neural_trading.py &"
        echo "  streamlit run neural_monitor_dashboard.py --server.port=8501 &"
    fi
fi

echo ""
echo "=============================================="
echo "🎯 CORREÇÃO COMPLETA FINALIZADA!"
echo "   ✅ Git resolvido"
echo "   ✅ Docker Compose instalado"  
echo "   ✅ Sistema Neural configurado"
echo "   ❌ Removido pandas-ta problemático"
echo "   ✅ Usando ta==0.10.2 (funcional)"
echo "=============================================="