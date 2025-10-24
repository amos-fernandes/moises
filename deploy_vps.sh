#!/bin/bash

# Script automatizado de deploy para VPS Hostinger
# ATCoin Real Trading System

set -e

echo "=============================================="
echo "  ATCOIN REAL TRADING - AUTO DEPLOY VPS"
echo "=============================================="
echo "Estratégia: Equilibrada_Pro (+1.24% vs -78%)"
echo "Exchange: Binance (Operações Reais)"
echo "=============================================="

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Verifica se está rodando como root
if [[ $EUID -eq 0 ]]; then
   log_error "Não execute este script como root!"
   exit 1
fi

# 1. ATUALIZAR SISTEMA
log_info "Atualizando sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 2. INSTALAR DEPENDÊNCIAS
log_info "Instalando dependências..."
sudo apt-get install -y \
    docker.io \
    docker-compose \
    curl \
    wget \
    git \
    htop \
    nano \
    ufw \
    ntp

# 3. CONFIGURAR DOCKER
log_info "Configurando Docker..."
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# 4. SINCRONIZAR HORÁRIO (importante para Binance)
log_info "Sincronizando horário..."
sudo systemctl start ntp
sudo systemctl enable ntp
sudo ntpdate -s time.nist.gov || log_warn "Falha na sincronização de horário"

# 5. CONFIGURAR FIREWALL
log_info "Configurando firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8000/tcp  # ATCoin API
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw --force enable

# 6. CRIAR ESTRUTURA DE DIRETÓRIOS
log_info "Criando estrutura de diretórios..."
mkdir -p ~/atcoin-trading/{logs,data,backups}
cd ~/atcoin-trading

# 7. VERIFICAR SE PROJETO EXISTE
if [ ! -f "app_real_trading.py" ]; then
    log_warn "Arquivos do projeto não encontrados!"
    log_info "Por favor, copie os arquivos do projeto para este diretório:"
    log_info "scp -r /caminho/local/projeto/* usuario@$HOSTNAME:~/atcoin-trading/"
    exit 1
fi

# 8. VERIFICAR ARQUIVO .env
if [ ! -f ".env" ]; then
    log_error "Arquivo .env não encontrado!"
    log_info "Criando template .env..."
    
    cat > .env << EOF
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

# === SERVIDOR ===
HOST=0.0.0.0
PORT=8000
WORKERS=1
LOG_LEVEL=INFO

# === SEGURANÇA ===
SECRET_KEY=atcoin_equilibrada_pro_secret_key_production_2024
CORS_ORIGINS=*

# === AIBANK INTEGRATION ===
AIBANK_API_KEY=atcoin_production_key_2024
AIBANK_CALLBACK_URL=https://aibank-api.com/api/rnn_investment_result_callback
CALLBACK_SHARED_SECRET=super_secret_production_key_equilibrada_pro_2024
EOF
    
    log_error "Configure o arquivo .env com suas credenciais reais!"
    log_info "Execute: nano .env"
    exit 1
fi

# 9. VERIFICAR CREDENCIAIS BINANCE
log_info "Verificando credenciais Binance..."
if grep -q "SUA_BINANCE_API_KEY_AQUI" .env; then
    log_error "Credenciais Binance não configuradas no .env!"
    log_info "Execute: nano .env"
    exit 1
fi

# 10. BUILD DA APLICAÇÃO
log_info "Fazendo build da aplicação Docker..."
if ! docker-compose build; then
    log_error "Falha no build da aplicação!"
    exit 1
fi

# 11. PARAR SERVIÇOS ANTIGOS
log_info "Parando serviços antigos..."
docker-compose down || true

# 12. INICIAR SERVIÇOS
log_info "Iniciando serviços ATCoin..."
docker-compose up -d

# 13. AGUARDAR INICIALIZAÇÃO
log_info "Aguardando inicialização (30 segundos)..."
sleep 30

# 14. VERIFICAR SAÚDE DO SISTEMA
log_info "Verificando saúde do sistema..."
if curl -f -s http://localhost:8000/health > /dev/null; then
    log_info "Sistema iniciado com sucesso!"
else
    log_warn "Sistema pode estar ainda inicializando..."
fi

# 15. MOSTRAR STATUS
log_info "Status dos containers:"
docker-compose ps

# 16. MOSTRAR LOGS RECENTES
log_info "Logs recentes:"
docker-compose logs --tail=20 atcoin-trading

# 17. CONFIGURAR MONITORAMENTO
log_info "Configurando monitoramento..."

# Cria script de monitoramento
cat > ~/monitor_atcoin.sh << 'EOF'
#!/bin/bash
# Monitor ATCoin Real Trading System

echo "=== ATCOIN SYSTEM STATUS ==="
echo "Data: $(date)"
echo ""

echo "=== CONTAINERS STATUS ==="
cd ~/atcoin-trading
docker-compose ps
echo ""

echo "=== SYSTEM HEALTH ==="
curl -s http://localhost:8000/health | python3 -m json.tool || echo "API não respondendo"
echo ""

echo "=== RESOURCE USAGE ==="
docker stats --no-stream atcoin-real-trading || echo "Container não encontrado"
echo ""

echo "=== ÚLTIMOS LOGS ==="
docker-compose logs --tail=10 atcoin-trading
EOF

chmod +x ~/monitor_atcoin.sh

# 18. CONFIGURAR CRONTAB PARA BACKUP
log_info "Configurando backup automático..."
(crontab -l 2>/dev/null; echo "0 2 * * * cd ~/atcoin-trading && docker-compose logs --since=24h > backups/logs_\$(date +\%Y\%m\%d).log") | crontab -

# 19. RESUMO FINAL
echo ""
echo "=============================================="
log_info "DEPLOY CONCLUÍDO COM SUCESSO!"
echo "=============================================="
echo ""
echo "URLs importantes:"
echo "  API Principal: http://$(curl -s ifconfig.me):8000/api/invest/real"
echo "  Health Check:  http://$(curl -s ifconfig.me):8000/health"
echo "  Dashboard:     http://$(curl -s ifconfig.me):8000/"
echo ""
echo "Comandos úteis:"
echo "  Monitorar:     ~/monitor_atcoin.sh"
echo "  Logs:          cd ~/atcoin-trading && docker-compose logs -f"
echo "  Reiniciar:     cd ~/atcoin-trading && docker-compose restart"
echo "  Parar:         cd ~/atcoin-trading && docker-compose down"
echo ""
log_warn "ATENÇÃO: Sistema configurado para OPERAÇÕES REAIS!"
log_warn "Monitore constantemente e teste com valores baixos!"
echo ""
echo "=============================================="

# 20. TESTE FINAL OPCIONAL
read -p "Deseja executar teste de conexão Binance? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Testando conexão Binance..."
    curl -s "http://localhost:8000/api/binance/balance" | python3 -m json.tool || log_warn "Teste falhou - verifique credenciais"
fi

log_info "Deploy finalizado! Sistema ATCoin Real Trading ativo."

# Sugestão de próximos passos
echo ""
echo "Próximos passos sugeridos:"
echo "1. Execute: ~/monitor_atcoin.sh"
echo "2. Verifique: curl http://localhost:8000/health"
echo "3. Configure SSL/HTTPS se necessário"
echo "4. Configure alertas de monitoramento"
echo "5. Faça um teste com valor baixo (R$ 50-100)"