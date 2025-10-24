#!/bin/bash

# Script automatizado de deploy para VPS Hostinger
# ATCoin Real Trading System - Versão corrigida

set -e

echo "=============================================="
echo "  ATCOIN NEURAL TRADING - AUTO DEPLOY VPS"
echo "=============================================="
echo "Sistema: Neural Learning + Expert Strategies"
echo "Meta: 60%+ Assertividade"
echo "Exchange: Binance (Operações Reais)"
echo "=============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Verifica se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Não execute este script como root!"
   exit 1
fi

# 1. ATUALIZAR SISTEMA
log_info "Atualizando sistema..."
sudo apt-get update -y

# 2. RESOLVER CONFLITOS DE CONTAINERD
log_info "Resolvendo conflitos de containerd..."
# Remove versões conflitantes
sudo apt-get remove -y containerd containerd.io docker docker-engine docker.io runc || true
sudo apt-get autoremove -y
sudo apt-get autoclean

# Limpa repositórios Docker antigos
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -f /etc/apt/keyrings/docker.gpg

# 3. INSTALAR DEPENDÊNCIAS BÁSICAS
log_info "Instalando dependências básicas..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    wget \
    git \
    htop \
    nano \
    ufw \
    ntp \
    python3 \
    python3-pip \
    unzip

# 4. CONFIGURAR REPOSITÓRIO DOCKER OFICIAL
log_info "Configurando repositório Docker oficial..."
# Adiciona chave GPG oficial do Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Adiciona repositório Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Atualiza lista de pacotes
sudo apt-get update -y

# 5. INSTALAR DOCKER ENGINE
log_info "Instalando Docker Engine..."
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Instala docker-compose standalone
log_info "Instalando Docker Compose..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
sudo curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 6. CONFIGURAR DOCKER
log_info "Configurando Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Criar configuração do Docker daemon
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "storage-driver": "overlay2"
}
EOF

sudo systemctl restart docker

# 7. INSTALAR PYTHON DEPENDENCIES
log_info "Instalando dependências Python..."
pip3 install --user --upgrade pip
pip3 install --user pandas numpy scikit-learn tensorflow plotly streamlit requests schedule pandas_ta

# 8. SINCRONIZAR HORÁRIO (importante para Binance)
log_info "Sincronizando horário..."
sudo systemctl start ntp
sudo systemctl enable ntp
sudo ntpdate -s time.nist.gov || log_warn "Falha na sincronização de horário"

# Configura timezone para UTC (melhor para trading)
sudo timedatectl set-timezone UTC
log_info "Timezone configurado para UTC"

# 9. CONFIGURAR FIREWALL
log_info "Configurando firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8001/tcp  # Neural Trading API
sudo ufw allow 8501/tcp  # Streamlit Dashboard
sudo ufw allow 8000/tcp  # Legacy API
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# 10. CRIAR ESTRUTURA DE DIRETÓRIOS
log_info "Criando estrutura de diretórios..."
mkdir -p ~/neural-trading/{logs,data,backups,models}
cd ~/neural-trading

# 11. CRIAR ARQUIVO .env PARA SISTEMA NEURAL
log_info "Criando configuração neural..."
cat > .env << 'EOF'
# === NEURAL TRADING SYSTEM ===
SYSTEM_MODE=NEURAL_PRODUCTION
TARGET_ACCURACY=0.60
LEARNING_ENABLED=true

# === BINANCE CREDENTIALS ===
BINANCE_API_KEY=SUA_BINANCE_API_KEY_AQUI
BINANCE_SECRET_KEY=SUA_BINANCE_SECRET_KEY_AQUI

# === TRADING CONFIGURATION ===
TRADING_MODE=REAL
BINANCE_TESTNET=false
INITIAL_BALANCE_BRL=1000.00
MAX_POSITION_SIZE=0.15
STOP_LOSS_PERCENT=0.02
TAKE_PROFIT_PERCENT=0.06
CONFIDENCE_THRESHOLD=0.65

# === NEURAL LEARNING ===
TRAINING_INTERVAL_MINUTES=30
EVALUATION_INTERVAL_MINUTES=120
MEMORY_SIZE=10000
BATCH_SIZE=32
LEARNING_RATE=0.001

# === US MARKET FOCUS ===
US_MARKET_PRIORITY=true
ALPHA_VANTAGE_API_KEY=SUA_ALPHA_VANTAGE_API_KEY
FINNHUB_API_KEY=SUA_FINNHUB_API_KEY
TWELVE_DATA_API_KEY=SUA_TWELVE_DATA_API_KEY

# === SERVIDOR ===
HOST=0.0.0.0
PORT=8001
STREAMLIT_PORT=8501
WORKERS=1
LOG_LEVEL=INFO

# === SEGURANÇA ===
SECRET_KEY=neural_trading_secret_key_production_2024
CORS_ORIGINS=*

# === MONITORAMENTO ===
ENABLE_DASHBOARD=true
AUTO_SAVE_MODEL=true
PERFORMANCE_ALERTS=true
EOF

# 12. CRIAR DOCKER-COMPOSE PARA SISTEMA NEURAL
log_info "Criando Docker Compose para sistema neural..."
cat > docker-compose.yml << 'EOF'
version: '3.8'

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
      - ./.env:/app/.env
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/neural/status"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - neural-net

  dashboard:
    build: 
      context: .
      dockerfile: Dockerfile.dashboard
    container_name: neural-dashboard
    ports:
      - "8501:8501"
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
      - ./.env:/app/.env
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
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - neural-net

networks:
  neural-net:
    driver: bridge

volumes:
  redis_data:
EOF

# 13. CRIAR DOCKERFILE PARA SISTEMA NEURAL
log_info "Criando Dockerfile..."
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create necessary directories
RUN mkdir -p logs data models

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8001/api/neural/status || exit 1

# Run application
CMD ["python", "app_neural_trading.py"]
EOF

# 14. CRIAR DOCKERFILE PARA DASHBOARD
cat > Dockerfile.dashboard << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8501

# Run dashboard
CMD ["streamlit", "run", "neural_monitor_dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
EOF

# 15. CRIAR REQUIREMENTS.TXT
log_info "Criando requirements.txt..."
cat > requirements.txt << 'EOF'
fastapi==0.104.1
uvicorn[standard]==0.24.0
pandas==2.1.4
numpy==1.25.2
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
EOL
EOF

# 16. AGUARDAR RECONEXÃO DOCKER (devido ao usermod)
log_warn "Recarregando configurações do Docker..."
newgrp docker << 'EOF'
# Testa se Docker está funcionando
if docker --version > /dev/null 2>&1; then
    echo "Docker configurado com sucesso!"
else
    echo "Erro na configuração do Docker"
    exit 1
fi
EOF

# 17. CRIAR SCRIPT DE MONITORAMENTO NEURAL
log_info "Criando script de monitoramento neural..."
cat > ~/monitor_neural_trading.sh << 'EOF'
#!/bin/bash
# Monitor Neural Trading System

echo "=== NEURAL TRADING SYSTEM STATUS ==="
echo "Data: $(date)"
echo ""

echo "=== CONTAINERS STATUS ==="
cd ~/neural-trading
docker-compose ps
echo ""

echo "=== NEURAL SYSTEM HEALTH ==="
echo "API Status:"
curl -s http://localhost:8001/api/neural/status | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(f'System Ready: {data.get(\"system_ready\", False)}')
    print(f'Learning Active: {data.get(\"learning_status\", {}).get(\"learning_active\", False)}')
    print(f'Current Accuracy: {data.get(\"learning_status\", {}).get(\"current_accuracy\", 0):.2%}')
except:
    print('API não respondendo')
"
echo ""

echo "=== PERFORMANCE METRICS ==="
curl -s http://localhost:8001/api/neural/performance | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    current_perf = data.get('current_performance', {})
    print(f'Model Accuracy: {current_perf.get(\"accuracy\", 0):.2%}')
    print(f'Total Experiences: {current_perf.get(\"total_experiences\", 0)}')
    print(f'Training Sessions: {data.get(\"learning_evolution\", {}).get(\"training_sessions\", 0)}')
except:
    print('Performance data não disponível')
"
echo ""

echo "=== RESOURCE USAGE ==="
docker stats --no-stream neural-trading-api neural-dashboard neural-redis || echo "Containers não encontrados"
echo ""

echo "=== ÚLTIMOS LOGS ==="
docker-compose logs --tail=10 neural-trading
EOF

chmod +x ~/monitor_neural_trading.sh

# 18. CONFIGURAR BACKUP AUTOMÁTICO
log_info "Configurando backup automático..."
# Backup de logs e modelos
(crontab -l 2>/dev/null; cat << 'EOF'
# Neural Trading System Backups
0 2 * * * cd ~/neural-trading && docker-compose logs --since=24h > backups/logs_$(date +\%Y\%m\%d).log
0 6 * * * cd ~/neural-trading && cp -r models/ backups/models_$(date +\%Y\%m\%d)/ 2>/dev/null || true
0 0 * * 0 cd ~/neural-trading && find backups/ -type f -mtime +7 -delete
EOF
) | crontab -

# 19. MOSTRAR INSTRUÇÕES FINAIS
echo ""
echo "=============================================="
log_info "SISTEMA NEURAL PREPARADO PARA DEPLOY!"
echo "=============================================="
echo ""
echo "PRÓXIMOS PASSOS:"
echo ""
echo "1. 📁 COPIAR ARQUIVOS DO PROJETO:"
echo "   scp -r /local/path/neural-system/* usuario@$HOSTNAME:~/neural-trading/"
echo ""
echo "2. ⚙️  CONFIGURAR CREDENCIAIS:"
echo "   nano ~/neural-trading/.env"
echo "   - Configure BINANCE_API_KEY"
echo "   - Configure BINANCE_SECRET_KEY"  
echo "   - Configure ALPHA_VANTAGE_API_KEY"
echo ""
echo "3. 🚀 INICIAR SISTEMA:"
echo "   cd ~/neural-trading"
echo "   docker-compose up -d"
echo ""
echo "4. 📊 MONITORAR SISTEMA:"
echo "   ~/monitor_neural_trading.sh"
echo ""
echo "URLs após deploy:"
echo "  Neural API:    http://$(curl -s ifconfig.me):8001"
echo "  Dashboard:     http://$(curl -s ifconfig.me):8501" 
echo "  Health Check:  http://$(curl -s ifconfig.me):8001/api/neural/status"
echo ""
echo "=============================================="
log_warn "LEMBRE-SE:"
echo "  • Configure as credenciais antes de iniciar"
echo "  • Sistema focado na bolsa americana (60%+ assertividade)"
echo "  • Aprendizado neural contínuo ativo"  
echo "  • Monitore constantemente o desempenho"
echo "=============================================="

log_info "Preparação VPS concluída! Agora copie os arquivos e configure as credenciais."