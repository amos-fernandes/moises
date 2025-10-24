# 🚀 Guia de Deploy VPS - Sistema Neural Trading

## ❌ Problema Identificado

O erro que você está enfrentando é um conflito comum entre diferentes versões do `containerd`:

```
containerd.io : Conflicts: containerd
E: Error, pkgProblemResolver::Resolve generated breaks, this may be caused by held packages.
```

## ✅ Solução Completa

### 1. **Resolver Conflitos Docker** (Execute no VPS)

```bash
# Copie e execute o script de correção
wget -O fix_docker_conflicts.sh https://raw.githubusercontent.com/SEU_REPO/fix_docker_conflicts.sh
chmod +x fix_docker_conflicts.sh
./fix_docker_conflicts.sh
```

Ou execute manualmente:

```bash
# Parar serviços
sudo systemctl stop docker.service docker.socket containerd.service || true

# Remover versões conflitantes
sudo apt-get remove -y docker docker-engine docker.io containerd containerd.io runc
sudo apt-get purge -y docker docker-engine docker.io containerd containerd.io runc
sudo apt-get autoremove -y

# Limpar repositórios
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -rf /etc/apt/keyrings/docker*

# Instalar Docker oficial
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 2. **Copiar Sistema Neural** (Do seu PC para VPS)

```bash
# No seu PC Windows (PowerShell)
scp -r d:\dev\moises\*.py usuario@SEU_IP:~/neural-trading/
scp -r d:\dev\moises\src usuario@SEU_IP:~/neural-trading/
scp d:\dev\moises\deploy_neural_vps.sh usuario@SEU_IP:~/
```

### 3. **Executar Deploy Neural** (No VPS)

```bash
# No VPS
chmod +x ~/deploy_neural_vps.sh
./deploy_neural_vps.sh
```

### 4. **Configurar Credenciais** (No VPS)

```bash
cd ~/neural-trading
nano .env
```

Configure:
```env
# === BINANCE CREDENTIALS ===
BINANCE_API_KEY=sua_api_key_real
BINANCE_SECRET_KEY=sua_secret_key_real

# === ALPHA VANTAGE (para dados US) ===
ALPHA_VANTAGE_API_KEY=0BZTLZG8FP5KZHFV

# === NEURAL SYSTEM ===
TARGET_ACCURACY=0.60
CONFIDENCE_THRESHOLD=0.65
US_MARKET_PRIORITY=true
```

### 5. **Iniciar Sistema** (No VPS)

```bash
cd ~/neural-trading

# Fazer build
docker-compose build

# Iniciar serviços
docker-compose up -d

# Monitorar logs
docker-compose logs -f
```

## 📊 Verificação do Sistema

### Status do Sistema
```bash
# Script de monitoramento
~/monitor_neural_trading.sh

# OU manualmente
curl http://localhost:8001/api/neural/status
curl http://localhost:8001/api/neural/performance
```

### URLs Disponíveis
- **Neural API**: `http://SEU_IP:8001`
- **Dashboard**: `http://SEU_IP:8501` 
- **Health Check**: `http://SEU_IP:8001/api/neural/status`

## 🔧 Comandos Úteis

### Gerenciamento Docker
```bash
# Ver containers
docker-compose ps

# Logs em tempo real
docker-compose logs -f neural-trading

# Reiniciar sistema
docker-compose restart

# Parar sistema
docker-compose down

# Rebuild após mudanças
docker-compose build --no-cache
docker-compose up -d
```

### Monitoramento Neural
```bash
# Status do aprendizado
curl -s http://localhost:8001/api/neural/status | python3 -m json.tool

# Performance atual
curl -s http://localhost:8001/api/neural/performance | python3 -m json.tool

# Predição teste
curl -X POST http://localhost:8001/api/neural/predict \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL", "use_neural": true}'
```

### Controle do Sistema Neural
```bash
# Iniciar aprendizado
curl -X POST "http://localhost:8001/api/neural/control?action=start"

# Parar aprendizado
curl -X POST "http://localhost:8001/api/neural/control?action=stop"

# Salvar modelo
curl -X POST "http://localhost:8001/api/neural/control?action=save"
```

## 🎯 Fluxo Completo de Deploy

```bash
# 1. No VPS - Resolver conflitos Docker
./fix_docker_conflicts.sh

# 2. Fazer logout/login ou
newgrp docker

# 3. Executar deploy neural
./deploy_neural_vps.sh

# 4. Copiar arquivos do sistema (do PC)
scp -r sistema_neural/* usuario@ip:~/neural-trading/

# 5. Configurar .env
nano ~/neural-trading/.env

# 6. Iniciar sistema
cd ~/neural-trading
docker-compose up -d

# 7. Verificar funcionamento
~/monitor_neural_trading.sh
```

## 🚨 Troubleshooting

### Se Docker não funcionar:
```bash
# Verificar status
sudo systemctl status docker
sudo systemctl status containerd

# Reiniciar serviços
sudo systemctl restart docker
sudo systemctl restart containerd

# Verificar logs
sudo journalctl -u docker.service
```

### Se a API não responder:
```bash
# Verificar logs
docker-compose logs neural-trading

# Verificar se porta está livre
sudo netstat -tlnp | grep :8001

# Reiniciar container
docker-compose restart neural-trading
```

### Se o aprendizado não funcionar:
```bash
# Verificar logs neural
docker-compose logs neural-trading | grep -i "neural\|learning"

# Verificar memória
docker stats neural-trading-api

# Verificar configuração
curl http://localhost:8001/api/neural/status
```

## ✅ Sistema Pronto!

Após seguir esses passos, você terá:

- ✅ **Sistema Neural Funcionando** - API na porta 8001
- ✅ **Dashboard Interativo** - Streamlit na porta 8501  
- ✅ **Aprendizado Contínuo** - IA melhorando 24/7
- ✅ **Integração Binance** - Operações reais configuradas
- ✅ **Foco Mercado US** - Meta 60%+ assertividade
- ✅ **Monitoramento** - Scripts automáticos de acompanhamento

**O sistema está pronto para atingir a meta de 60%+ assertividade com aprendizado neural contínuo!** 🧠🚀