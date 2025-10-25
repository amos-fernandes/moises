# 🚀 CONFIGURAÇÃO PÓS-DEPLOY - OPERAÇÃO CONTÍNUA

## COMANDOS PARA EXECUTAR NA VPS

### 1. Atualizar código para versão contínua
```bash
cd /home/moises/trading
sudo -u moises git pull origin main
```

### 2. Atualizar serviço systemd
```bash
# Copiar novo service file
cp /home/moises/trading/deploy/moises.service /etc/systemd/system/
systemctl daemon-reload
```

### 3. Configurar chaves (OBRIGATÓRIO!)
```bash
# Editar arquivo de ambiente
sudo -u moises nano /home/moises/.bashrc

# Adicionar no final:
export BINANCE_API_KEY='WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc'
export BINANCE_API_SECRET='SUA_SECRET_KEY_AQUI'

# IMPORTANTE: Substitua SUA_SECRET_KEY_AQUI pela sua chave secret real!
```

### 4. Recarregar ambiente e iniciar
```bash
# Recarregar variáveis
sudo -u moises bash -c 'source ~/.bashrc'

# Reiniciar serviço
systemctl restart moises
systemctl enable moises

# Verificar status
systemctl status moises
```

### 5. Configurar monitoramento
```bash
# Tornar script executável
chmod +x /home/moises/trading/deploy/monitor_moises.sh

# Criar alias para fácil acesso
echo "alias monitor='sudo /home/moises/trading/deploy/monitor_moises.sh'" >> ~/.bashrc
source ~/.bashrc

# Agora você pode usar apenas: monitor
```

## 📊 COMANDOS DE MONITORAMENTO

### Logs em tempo real
```bash
journalctl -u moises -f
```

### Status detalhado
```bash
systemctl status moises -l
```

### Painel de monitoramento
```bash
/home/moises/trading/deploy/monitor_moises.sh
# ou simplesmente: monitor (se configurou o alias)
```

### Ver relatórios de trades
```bash
cat /home/moises/trading/reports/trade_records.json | jq '.'
```

### Logs de aplicação
```bash
tail -f /home/moises/trading/logs/moises_continuo.log
```

## 🔧 OPERAÇÕES DE MANUTENÇÃO

### Parar sistema temporariamente
```bash
systemctl stop moises
```

### Reiniciar sistema
```bash
systemctl restart moises
```

### Atualizar código
```bash
cd /home/moises/trading
sudo -u moises git pull origin main
systemctl restart moises
```

### Backup de dados
```bash
# Criar backup dos reports e logs
tar -czf moises_backup_$(date +%Y%m%d).tar.gz /home/moises/trading/{logs,reports}
```

## ⚙️ CONFIGURAÇÕES AVANÇADAS

### Ajustar frequência de trades
Editar `/home/moises/trading/moises_continuo_vps.py`:
- `min_trade_interval = 300` (segundos entre trades)
- `max_daily_trades = 20` (máximo por dia)
- `max_trade_amount = 50` (máximo por trade em USDT)

### Configurar alertas (opcional)
```bash
# Instalar mailutils para alertas por email
apt install mailutils -y

# Configurar cron para alertas
crontab -e

# Adicionar linha para verificar se serviço está rodando a cada 5min:
*/5 * * * * systemctl is-active --quiet moises || echo "MOISES parou!" | mail -s "ALERTA MOISES" seu@email.com
```

## 🎯 VERIFICAÇÕES FINAIS

### Checklist pós-deploy:
- [ ] ✅ Código atualizado (git pull)
- [ ] ✅ Chaves API configuradas no ambiente
- [ ] ✅ Serviço systemd atualizado
- [ ] ✅ MOISES rodando (systemctl status moises)
- [ ] ✅ Logs funcionando (journalctl -u moises -f)
- [ ] ✅ Monitoramento configurado
- [ ] ✅ Primeiro trade executado com sucesso

### Como verificar se está tudo funcionando:
```bash
# 1. Status do serviço deve mostrar "active (running)"
systemctl status moises

# 2. Logs devem mostrar sincronização e análises
journalctl -u moises -n 20

# 3. Arquivo de log deve estar sendo atualizado
ls -la /home/moises/trading/logs/moises_continuo.log

# 4. Verificar se está fazendo análises de mercado
grep "Analisando mercado" /home/moises/trading/logs/moises_continuo.log
```

## 🎂💰 MOISES OPERACIONAL 24/7! 💰🎂

Uma vez configurado, o MOISES vai:
- ✅ Operar 24 horas por dia, 7 dias por semana
- ✅ Analisar mercado a cada 3 minutos
- ✅ Executar trades reais quando encontrar oportunidades
- ✅ Manter logs detalhados de todas as operações
- ✅ Reiniciar automaticamente em caso de falha
- ✅ Respeitar limites de risco configurados