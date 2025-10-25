# MOISES VPS Deployment Guide

## 🚀 Deploy Automático

### Pré-requisitos
- VPS Ubuntu/Debian 20.04+ 
- Acesso root (sudo)
- Git instalado

### 1. Fazer Deploy

```bash
# Clonar repositório na VPS
git clone https://github.com/amos-fernandes/moises.git
cd moises

# Executar deploy automático
sudo chmod +x deploy/deploy_vps.sh
sudo ./deploy/deploy_vps.sh
```

### 2. Configurar Chaves API

```bash
# Editar arquivo de ambiente do usuário moises
sudo -u moises nano /home/moises/.bashrc

# Adicionar no final do arquivo:
export BINANCE_API_KEY='WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc'
export BINANCE_API_SECRET='sua_secret_key_aqui'

# Recarregar ambiente
sudo -u moises bash -c 'source ~/.bashrc'
```

### 3. Iniciar Serviço

```bash
# Iniciar MOISES como serviço
systemctl start moises
systemctl status moises

# Ver logs em tempo real
journalctl -u moises -f
```

### 4. Comandos Úteis

```bash
# Status do serviço
systemctl status moises

# Parar serviço  
systemctl stop moises

# Reiniciar serviço
systemctl restart moises

# Ver logs
journalctl -u moises -n 100

# Logs em tempo real
journalctl -u moises -f

# Atualizar código
cd /home/moises/trading
sudo -u moises git pull origin main
systemctl restart moises
```

## 🔧 Estrutura na VPS

```
/home/moises/trading/
├── trading_real_vps.py     # Cliente principal
├── requirements.txt        # Dependências
├── logs/                   # Logs da aplicação  
├── reports/               # Relatórios
├── data/                  # Dados
├── backups/              # Backups
└── .venv/                # Ambiente virtual
```

## 🛡️ Segurança

- Usuário dedicado `moises` (não-root)
- Chaves API em variáveis de ambiente
- Firewall básico configurado
- Logs centralizados via systemd
- Restart automático em caso de falha

## 📊 Monitoramento

```bash
# CPU e memória
htop

# Espaço em disco
df -h

# Status geral do sistema
systemctl --failed

# Logs específicos do MOISES
tail -f /home/moises/trading/logs/*.log
```

## 🎯 Próximos Passos

1. ✅ Deploy automático concluído
2. ⚙️ Configurar chaves API 
3. 🚀 Iniciar serviço
4. 📊 Monitorar logs
5. 💰 MOISES operando com fundos reais!