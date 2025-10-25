#!/bin/bash
# deploy_vps.sh - Script automatizado de deployment para VPS
# MOISES Trading Real - Deployment completo

set -e  # Exit on error

echo "🚀 MOISES VPS DEPLOYMENT - SETUP COMPLETO"
echo "========================================="

# Variáveis
USER="moises"
APP_DIR="/home/$USER/trading"
SERVICE_NAME="moises"

# Verificar se está rodando como root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Execute como root: sudo ./deploy_vps.sh"
    exit 1
fi

# 1. Criar usuário se não existir
if ! id "$USER" &>/dev/null; then
    echo "👤 Criando usuário $USER..."
    useradd -m -s /bin/bash "$USER"
    usermod -aG sudo "$USER"
fi

# 2. Instalar dependências do sistema
echo "📦 Instalando dependências do sistema..."
apt update
apt install -y python3 python3-pip python3-venv git curl htop

# 3. Configurar diretório da aplicação
echo "📁 Configurando diretório da aplicação..."
mkdir -p "$APP_DIR"
chown -R "$USER:$USER" "$APP_DIR"

# 4. Clonar repositório (se necessário)
if [ ! -d "$APP_DIR/.git" ]; then
    echo "📥 Clonando repositório..."
    sudo -u "$USER" git clone https://github.com/amos-fernandes/moises.git "$APP_DIR"
else
    echo "🔄 Atualizando repositório..."
    cd "$APP_DIR"
    sudo -u "$USER" git pull origin main
fi

# 5. Configurar ambiente Python
echo "🐍 Configurando ambiente Python..."
cd "$APP_DIR"
sudo -u "$USER" python3 -m venv .venv
sudo -u "$USER" .venv/bin/pip install -r requirements.txt

# 6. Criar diretórios necessários
echo "📂 Criando estrutura de diretórios..."
sudo -u "$USER" mkdir -p "$APP_DIR"/{logs,reports,data,backups}

# 7. Configurar service do systemd
echo "⚙️ Configurando serviço systemd..."
cp "$APP_DIR/deploy/moises.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

# 8. Configurar variáveis de ambiente
echo "🔐 Configuração das chaves da API..."
ENV_FILE="/home/$USER/.bashrc"
echo "# MOISES Trading - Binance API" >> "$ENV_FILE"
echo "# Configure suas chaves aqui:" >> "$ENV_FILE"
echo "# export BINANCE_API_KEY='sua_chave_aqui'" >> "$ENV_FILE"
echo "# export BINANCE_API_SECRET='seu_secret_aqui'" >> "$ENV_FILE"

# 9. Configurar firewall básico
echo "🔥 Configurando firewall..."
ufw --force enable
ufw allow ssh
ufw allow 22

# 10. Configurar logs
echo "📋 Configurando logs..."
mkdir -p /var/log/moises
chown "$USER:$USER" /var/log/moises

echo ""
echo "✅ DEPLOYMENT CONCLUÍDO!"
echo "========================"
echo ""
echo "🔧 PRÓXIMOS PASSOS MANUAIS:"
echo "1. Configure as chaves da API:"
echo "   sudo -u $USER nano /home/$USER/.bashrc"
echo "   Adicione:"
echo "   export BINANCE_API_KEY='sua_chave'"
echo "   export BINANCE_API_SECRET='seu_secret'"
echo ""
echo "2. Recarregue o ambiente:"
echo "   sudo -u $USER bash -c 'source ~/.bashrc'"
echo ""
echo "3. Teste o serviço:"
echo "   systemctl start $SERVICE_NAME"
echo "   systemctl status $SERVICE_NAME"
echo ""
echo "4. Ver logs:"
echo "   journalctl -u $SERVICE_NAME -f"
echo ""
echo "5. Parar/reiniciar serviço:"
echo "   systemctl stop $SERVICE_NAME"
echo "   systemctl restart $SERVICE_NAME"
echo ""
echo "🎂💰 MOISES está pronto para rodar na VPS! 💰🎂"