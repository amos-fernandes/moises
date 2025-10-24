# 🚀 COMANDOS CORRETOS PARA VPS - Diretório /moises

## ✅ COMANDOS PARA EXECUTAR NO VPS

```bash
# 1. Navegar para diretório correto
cd ~/moises

# 2. Resolver conflitos Git (se necessário)
git stash push -m "VPS backup" -u
git pull origin main

# 3. Executar atualização
chmod +x update_moises_vps.sh
./update_moises_vps.sh
```

## 📋 COMANDOS INDIVIDUAIS (SE PREFERIR)

```bash
# Ir para diretório
cd ~/moises

# Verificar arquivos
ls -la app_neural_trading.py neural_monitor_dashboard.py src/ml/

# Dar permissão aos scripts
chmod +x *.sh

# Iniciar sistema (com Docker)
docker-compose up -d

# OU iniciar sistema (Python direto)
python3 app_neural_trading.py &
streamlit run neural_monitor_dashboard.py --server.port=8501 &

# Verificar status
curl http://localhost:8001/api/neural/status
```

## 🔍 VERIFICAÇÕES

```bash
# Status dos containers
docker-compose ps

# Logs do sistema
docker-compose logs -f

# Teste da API
curl http://localhost:8001/api/neural/status | python3 -m json.tool

# Verificar se portas estão abertas
netstat -tlnp | grep -E ':(8001|8501)'
```

## 🌐 URLs APÓS INICIALIZAÇÃO

- **Neural API**: `http://SEU_IP:8001`
- **Dashboard**: `http://SEU_IP:8501`
- **Health Check**: `http://SEU_IP:8001/api/neural/status`

## 🚨 SE HOUVER PROBLEMAS

```bash
# Reinstalar dependências
pip3 install --user --upgrade pandas numpy tensorflow streamlit requests

# Resolver problemas Docker
./fix_docker_conflicts.sh

# Deploy completo
./deploy_neural_vps.sh

# Verificar logs de erro
journalctl -u docker.service | tail -20
```

## ✅ RESULTADO ESPERADO

Após executar os comandos, você deve ter:

- 🧠 Sistema Neural rodando na porta 8001
- 📊 Dashboard Streamlit na porta 8501  
- 🎯 Meta de 60% assertividade ativa
- 🔄 Aprendizado contínuo funcionando
- 📈 Monitoramento em tempo real