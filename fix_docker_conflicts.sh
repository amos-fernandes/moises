#!/bin/bash

# Script para resolver conflitos de Docker/Containerd no Ubuntu
# Use este script no seu VPS antes do deploy principal

echo "=========================================="
echo "  RESOLVENDO CONFLITOS DOCKER/CONTAINERD"
echo "=========================================="

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. PARAR SERVIÇOS DOCKER
log_info "Parando todos os serviços Docker..."
sudo systemctl stop docker.service || true
sudo systemctl stop docker.socket || true
sudo systemctl stop containerd.service || true

# 2. REMOVER INSTALAÇÕES CONFLITANTES
log_info "Removendo instalações conflitantes..."
sudo apt-get remove -y \
    docker \
    docker-engine \
    docker.io \
    containerd \
    containerd.io \
    runc \
    docker-ce \
    docker-ce-cli || true

sudo apt-get purge -y \
    docker \
    docker-engine \
    docker.io \
    containerd \
    containerd.io \
    runc \
    docker-ce \
    docker-ce-cli || true

# 3. LIMPAR RESÍDUOS
log_info "Limpando resíduos..."
sudo apt-get autoremove -y
sudo apt-get autoclean

# Remover repositórios Docker antigos
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -rf /etc/apt/keyrings/docker*
sudo rm -rf /usr/share/keyrings/docker*

# 4. LIMPAR CONFIGURAÇÕES
log_info "Limpando configurações antigas..."
sudo rm -rf /var/lib/docker
sudo rm -rf /var/lib/containerd
sudo rm -rf /etc/docker

# 5. ATUALIZAR SISTEMA
log_info "Atualizando sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

# 6. INSTALAR PRÉ-REQUISITOS
log_info "Instalando pré-requisitos..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 7. CONFIGURAR REPOSITÓRIO DOCKER OFICIAL
log_info "Configurando repositório Docker oficial..."

# Criar diretório para chaves
sudo mkdir -p /etc/apt/keyrings

# Baixar chave GPG do Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Adicionar repositório
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 8. ATUALIZAR LISTA DE PACOTES
log_info "Atualizando lista de pacotes..."
sudo apt-get update -y

# 9. INSTALAR DOCKER ENGINE
log_info "Instalando Docker Engine..."
sudo apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# 10. INSTALAR DOCKER COMPOSE STANDALONE
log_info "Instalando Docker Compose standalone..."
DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/')
sudo curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 11. CONFIGURAR SERVIÇOS
log_info "Configurando serviços Docker..."
sudo systemctl enable docker.service
sudo systemctl enable containerd.service
sudo systemctl start docker.service
sudo systemctl start containerd.service

# 12. CONFIGURAR USUÁRIO
log_info "Adicionando usuário ao grupo docker..."
sudo usermod -aG docker $USER

# 13. CONFIGURAR DAEMON DOCKER
log_info "Configurando daemon Docker..."
sudo mkdir -p /etc/docker

sudo tee /etc/docker/daemon.json > /dev/null <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "100m",
        "max-file": "3"
    },
    "storage-driver": "overlay2",
    "exec-opts": ["native.cgroupdriver=systemd"],
    "live-restore": true
}
EOF

# 14. REINICIAR SERVIÇOS
log_info "Reiniciando serviços..."
sudo systemctl daemon-reload
sudo systemctl restart docker.service

# 15. TESTAR INSTALAÇÃO
log_info "Testando instalação..."

# Aguardar serviços iniciarem
sleep 5

# Testar Docker
if sudo docker --version; then
    log_info "✅ Docker instalado com sucesso!"
    sudo docker --version
else
    log_error "❌ Falha na instalação do Docker"
    exit 1
fi

# Testar Docker Compose
if docker-compose --version; then
    log_info "✅ Docker Compose instalado com sucesso!"
    docker-compose --version
else
    log_error "❌ Falha na instalação do Docker Compose"
    exit 1
fi

# Testar execução
if sudo docker run --rm hello-world > /dev/null 2>&1; then
    log_info "✅ Docker funcional!"
else
    log_warn "⚠️  Docker pode precisar de logout/login para funcionar sem sudo"
fi

echo ""
echo "=========================================="
log_info "DOCKER INSTALADO COM SUCESSO!"
echo "=========================================="
echo ""
log_warn "IMPORTANTE: Faça logout e login novamente para usar Docker sem sudo"
log_info "Ou execute: newgrp docker"
echo ""
log_info "Próximos passos:"
echo "1. Logout/login ou execute: newgrp docker"  
echo "2. Execute: ./deploy_neural_vps.sh"
echo "3. Configure credenciais no .env"
echo "4. Inicie o sistema: docker-compose up -d"
echo ""
echo "=========================================="