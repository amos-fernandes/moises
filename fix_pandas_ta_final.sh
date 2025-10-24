#!/bin/bash

# Correção definitiva do problema pandas-ta no VPS

echo "🔧 Aplicando correção definitiva pandas-ta..."
echo "=============================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. Parar tudo
echo "🛑 Parando containers..."
docker-compose down
docker container prune -f

# 2. Atualizar repositório
echo "📥 Atualizando código..."
git stash push -m "backup before pandas-ta fix"
git pull origin main

# 3. Substituir requirements.txt problemático
echo "🔄 Corrigindo requirements.txt..."

cat > requirements.txt << 'EOF'
fastapi==0.119.0
uvicorn[standard]==0.30.6
pandas==2.1.4
numpy==1.26.4
scikit-learn==1.3.2
tensorflow==2.15.0
plotly==5.18.0
streamlit==1.29.0
requests==2.31.0
schedule==1.2.0
pandas_ta==0.3.14b0
ccxt==4.1.64
python-multipart==0.0.6
pydantic==2.5.2
redis==5.0.1
python-dotenv==1.0.0
aiofiles==23.2.1
websockets==12.0
yfinance==0.2.28
ta==0.10.2
matplotlib==3.7.1
seaborn==0.13.0
joblib==1.3.2
EOF

# 4. Criar Dockerfile corrigido
echo "🐳 Criando Dockerfile corrigido..."

cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Configurar timezone
RUN ln -snf /usr/share/zoneinfo/UTC /etc/localtime && echo UTC > /etc/timezone

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd --create-home --shell /bin/bash neural

WORKDIR /app

# Copiar requirements corrigido
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar aplicação
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs data models && \
    chown -R neural:neural /app

# Mudar para usuário não-root  
USER neural

# Expor porta
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/api/neural/status || exit 1

# Comando de inicialização
CMD ["python", "app_neural_trading.py"]
EOF

# 5. Criar docker-compose.yml simplificado
echo "📦 Criando docker-compose.yml..."

cat > docker-compose.yml << 'EOF'
services:
  neural-trading:
    build: .
    container_name: neural-trading-api
    ports:
      - "8001:8001"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./models:/app/models
    environment:
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    networks:
      - neural-net

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
    networks:
      - neural-net

  redis:
    image: redis:7-alpine
    container_name: neural-redis
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - neural-net

networks:
  neural-net:
    driver: bridge
EOF

# 6. Limpar cache Docker completamente
echo "🧹 Limpando cache Docker..."
docker system prune -af
docker builder prune -af
docker volume prune -f

# 7. Build com no-cache
echo "🔨 Build do zero..."
docker-compose build --no-cache --pull

# 8. Verificar se build funcionou
if [ $? -eq 0 ]; then
    echo "✅ Build bem-sucedido!"
    
    # 9. Iniciar sistema
    echo "🚀 Iniciando sistema..."
    docker-compose up -d
    
    # 10. Aguardar inicialização
    echo "⏳ Aguardando 60 segundos..."
    sleep 60
    
    # 11. Testar API
    echo "🔍 Testando sistema..."
    if curl -f -s http://localhost:8001/api/neural/status > /dev/null; then
        echo "✅ Sistema funcionando!"
        
        # Mostrar status
        echo ""
        echo "📊 Status do sistema:"
        docker-compose ps
        
        echo ""
        echo "🌐 URLs disponíveis:"
        IP=$(curl -s ifconfig.me 2>/dev/null || echo "SEU_IP")
        echo "   Neural API: http://$IP:8001"
        echo "   Dashboard:  http://$IP:8501"
        
    else
        echo "⚠️ Sistema ainda inicializando ou com problemas"
        echo "📋 Logs:"
        docker-compose logs --tail=20
    fi
    
else
    echo "❌ Build falhou. Tentando instalação Python direta..."
    
    # Alternativa: instalação Python direta
    if command -v python3 >/dev/null; then
        echo "🐍 Instalando dependências Python..."
        pip3 install --user -r requirements.txt
        
        echo "🚀 Iniciando modo Python direto..."
        echo "Execute manualmente:"
        echo "  python3 app_neural_trading.py &"
        echo "  streamlit run neural_monitor_dashboard.py --server.port=8501 &"
    fi
fi

echo ""
echo "=============================================="
echo "✅ Correção pandas-ta concluída!"
echo "=============================================="