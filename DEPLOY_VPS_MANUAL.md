# MANUAL DE DEPLOY PARA VPS HOSTINGER
# ATCoin Real Trading System

## PREPARAÇÃO LOCAL

### 1. Verificar arquivos essenciais:
- ✅ app_real_trading.py (app principal)
- ✅ src/trading/binance_real_trading_clean.py (sistema limpo)
- ✅ src/trading/production_system.py (estratégia)
- ✅ Dockerfile (container)
- ✅ docker-compose.yml (orquestração)
- ✅ .env (credenciais)

### 2. Configurações importantes no .env:
```env
# BINANCE (suas credenciais já configuradas)
BINANCE_API_KEY=WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc
BINANCE_SECRET_KEY=IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682

# PRODUÇÃO
TRADING_MODE=REAL
BINANCE_TESTNET=false
INITIAL_BALANCE_BRL=1000.00
HOST=0.0.0.0
PORT=8000
```

## DEPLOY NA VPS HOSTINGER

### 1. Conectar na VPS:
```bash
ssh seu_usuario@seu_ip_vps
```

### 2. Instalar dependências:
```bash
sudo apt update
sudo apt install -y docker.io docker-compose git curl
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

### 3. Fazer logout e login novamente para ativar grupo docker

### 4. Clonar/copiar projeto:
```bash
# Opção A: Se tiver git
git clone https://github.com/seu-usuario/atcoin-trading.git
cd atcoin-trading

# Opção B: Copiar via SCP (do seu PC)
scp -r d:/dev/moises/ usuario@ip-vps:/home/usuario/atcoin-trading/
```

### 5. Configurar ambiente:
```bash
cd atcoin-trading

# Editar .env para produção
nano .env

# Adicionar suas configurações específicas da VPS
# Exemplo: URLs do AIBank, domínios, etc.
```

### 6. Build e start:
```bash
# Build da aplicação
docker-compose build

# Iniciar serviços
docker-compose up -d

# Verificar logs
docker-compose logs -f atcoin-trading
```

### 7. Verificar funcionamento:
```bash
# Health check
curl http://localhost:8000/health

# Saldo Binance
curl http://localhost:8000/api/binance/balance

# Se tudo OK, acesse externamente:
curl http://SEU_IP_VPS:8000/health
```

## CONFIGURAÇÃO DE FIREWALL

### Liberar portas necessárias:
```bash
sudo ufw allow 22    # SSH
sudo ufw allow 8000  # ATCoin API
sudo ufw allow 80    # HTTP (se usar nginx)
sudo ufw enable
```

## MONITORAMENTO

### 1. Ver logs em tempo real:
```bash
docker-compose logs -f atcoin-trading
```

### 2. Status dos containers:
```bash
docker-compose ps
```

### 3. Reiniciar se necessário:
```bash
docker-compose restart atcoin-trading
```

### 4. Ver uso de recursos:
```bash
docker stats atcoin-trading
```

## TESTES DE PRODUÇÃO

### 1. Teste de conexão:
```bash
curl -X GET http://SEU_IP:8000/health
```

### 2. Teste de saldo Binance:
```bash
curl -X GET http://SEU_IP:8000/api/binance/balance
```

### 3. Teste de investimento (CUIDADO - DINHEIRO REAL):
```bash
curl -X POST http://SEU_IP:8000/api/invest/real \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer atcoin_production_key_2024" \
  -d '{
    "client_id": "test_client",
    "amount_brl": 100.0,
    "aibank_transaction_token": "test_token"
  }'
```

## BACKUP E SEGURANÇA

### 1. Backup dos logs:
```bash
docker cp atcoin-real-trading:/app/logs ./backup/logs/
```

### 2. Backup do banco de dados (se usar):
```bash
docker-compose exec redis redis-cli BGSAVE
```

### 3. Configurar SSL (recomendado):
- Use certbot para Let's Encrypt
- Configure nginx como proxy reverso

## URLS IMPORTANTES APÓS DEPLOY

- **API Principal**: http://SEU_IP_VPS:8000/api/invest/real
- **Health Check**: http://SEU_IP_VPS:8000/health
- **Saldo Binance**: http://SEU_IP_VPS:8000/api/binance/balance
- **Dashboard**: http://SEU_IP_VPS:8000/
- **Transações**: http://SEU_IP_VPS:8000/api/transactions/recent

## TROUBLESHOOTING

### Problema: Container não inicia
```bash
docker-compose logs atcoin-trading
# Verifique erros de importação ou configuração
```

### Problema: Erro de conexão Binance
```bash
# Verificar credenciais no .env
# Verificar se IP da VPS está liberado na Binance
# Verificar se horário do servidor está correto
```

### Problema: Erro de timestamp Binance
```bash
# Sincronizar horário do servidor
sudo ntpdate -s time.nist.gov
```

### Problema: Porta bloqueada
```bash
# Verificar firewall
sudo ufw status
sudo ufw allow 8000
```

## CONFIGURAÇÕES ESPECÍFICAS HOSTINGER

### No cPanel (se aplicável):
1. Verificar se Docker está habilitado
2. Configurar DNS se necessário
3. Verificar limites de recursos
4. Configurar SSL/TLS

### Recursos recomendados:
- RAM: Mínimo 1GB
- CPU: Mínimo 1 core
- Storage: Mínimo 10GB SSD
- Bandwidth: Ilimitado

## ATENÇÃO - SEGURANÇA

⚠️ **SISTEMA COM DINHEIRO REAL!**

1. **Sempre teste com valores baixos primeiro**
2. **Monitore os logs constantemente**
3. **Configure alertas de segurança**
4. **Mantenha backups regulares**
5. **Não exponha credenciais**
6. **Use HTTPS em produção**

## SUPORTE

Em caso de problemas:
1. Verificar logs: `docker-compose logs -f`
2. Verificar saúde: `curl http://localhost:8000/health`
3. Reiniciar sistema: `docker-compose restart`
4. Verificar recursos: `docker stats`