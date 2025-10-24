# Arquivo de sincronização rápida - Execute no Windows PowerShell

$VPS_IP = "SEU_IP_AQUI"
$VPS_USER = "SEU_USUARIO_AQUI"

Write-Host "🧠 Sincronizando Sistema Neural com VPS..." -ForegroundColor Green
Write-Host "=========================================="

# Verificar se está no diretório correto
if (!(Test-Path "app_neural_trading.py")) {
    Write-Host "❌ Execute no diretório do projeto (d:\dev\moises)" -ForegroundColor Red
    exit 1
}

# 1. Copiar arquivos principais
Write-Host "📤 Copiando arquivos principais..." -ForegroundColor Yellow
scp "app_neural_trading.py" "${VPS_USER}@${VPS_IP}:~/neural-trading/"
scp "neural_monitor_dashboard.py" "${VPS_USER}@${VPS_IP}:~/neural-trading/"

# 2. Copiar estrutura src/
Write-Host "📁 Copiando estrutura src/..." -ForegroundColor Yellow
scp -r "src" "${VPS_USER}@${VPS_IP}:~/neural-trading/"

# 3. Copiar configurações
Write-Host "⚙️ Copiando configurações..." -ForegroundColor Yellow
scp -r "new-rede-a" "${VPS_USER}@${VPS_IP}:~/neural-trading/"
scp "requirements.txt" "${VPS_USER}@${VPS_IP}:~/neural-trading/" 2>$null
scp "docker-compose.yml" "${VPS_USER}@${VPS_IP}:~/neural-trading/" 2>$null
scp "Dockerfile*" "${VPS_USER}@${VPS_IP}:~/neural-trading/" 2>$null

# 4. Copiar script de atualização
Write-Host "🔧 Copiando script de atualização..." -ForegroundColor Yellow
scp "update_neural_vps.sh" "${VPS_USER}@${VPS_IP}:~/"

# 5. Executar atualização no VPS
Write-Host "🚀 Executando atualização no VPS..." -ForegroundColor Green
ssh "${VPS_USER}@${VPS_IP}" "chmod +x ~/update_neural_vps.sh && ~/update_neural_vps.sh"

Write-Host ""
Write-Host "✅ Sincronização concluída!" -ForegroundColor Green
Write-Host "🌐 Acesse: http://${VPS_IP}:8001 (API) ou http://${VPS_IP}:8501 (Dashboard)"