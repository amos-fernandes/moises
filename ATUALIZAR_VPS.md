# 🚀 COMANDO PARA ATUALIZAR VPS AGORA

# ========================================
# MÉTODO 1: Git Pull (Mais Fácil)
# ========================================

# No VPS, execute:
cd ~/moises
git pull origin main
./update_neural_vps.sh

# ========================================
# MÉTODO 2: SCP Direto (Se preferir)  
# ========================================

# No Windows PowerShell, execute:
$IP = "SEU_IP_VPS"
$USER = "SEU_USUARIO"

# Copiar arquivos atualizados
scp app_neural_trading.py ${USER}@${IP}:~/moises/
scp neural_monitor_dashboard.py ${USER}@${IP}:~/moises/
scp -r src ${USER}@${IP}:~/moises/
scp -r new-rede-a ${USER}@${IP}:~/moises/
scp update_neural_vps.sh ${USER}@${IP}:~/

# Executar atualização no VPS
ssh ${USER}@${IP} "chmod +x ~/update_neural_vps.sh && ~/update_neural_vps.sh"

# ========================================
# VERIFICAÇÃO PÓS-ATUALIZAÇÃO
# ========================================

# Verificar se sistema está funcionando:
curl http://SEU_IP:8001/api/neural/status
curl http://SEU_IP:8001/api/neural/performance

# Acessar dashboard:
# http://SEU_IP:8501

# ========================================
# ARQUIVOS PRINCIPAIS ATUALIZADOS:
# ========================================
✅ app_neural_trading.py - Sistema neural principal
✅ neural_monitor_dashboard.py - Dashboard interativo  
✅ src/ml/neural_learning_agent.py - Agente Deep Q-Learning
✅ src/ml/continuous_training.py - Aprendizado contínuo
✅ src/trading/us_market_system.py - Foco mercado americano
✅ new-rede-a/config.py - Configurações otimizadas para 60% assertividade
✅ Scripts de deploy e monitoramento

# ========================================
# RESULTADO ESPERADO:
# ========================================
🧠 Sistema Neural rodando com aprendizado contínuo
🎯 Meta: 60%+ assertividade no mercado americano  
📊 Dashboard em tempo real
🔄 Treino automático a cada 30 minutos
🚀 Decisões adaptativas Expert + Neural