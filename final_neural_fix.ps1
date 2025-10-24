# FINAL FIX - Resolvendo neural_agent None
Write-Host "🔧 FINAL FIX - Resolvendo neural_agent None" -ForegroundColor Yellow

# Para e remove containers
Write-Host "📦 Parando containers..." -ForegroundColor Blue
docker stop neural-trading-api neural-dashboard neural-redis 2>$null
docker rm neural-trading-api neural-dashboard neural-redis 2>$null

# Remove imagem antiga para forçar rebuild
Write-Host "🗑️ Removendo imagem antiga..." -ForegroundColor Blue
docker rmi moises-neural-trading 2>$null

# Rebuild com as correções
Write-Host "🔨 Rebuilding com correções neural_agent..." -ForegroundColor Green
docker build -t moises-neural-trading .

# Inicia containers
Write-Host "🚀 Iniciando containers corrigidos..." -ForegroundColor Green

docker run -d --name neural-redis -p 6379:6379 redis:alpine

docker run -d --name neural-trading-api `
  -p 8001:8001 `
  -v "${PWD}:/app" `
  -e PYTHONPATH=/app `
  --link neural-redis:redis `
  moises-neural-trading `
  python app_neural_trading.py

docker run -d --name neural-dashboard `
  -p 8501:8501 `
  -v "${PWD}:/app" `
  -e PYTHONPATH=/app `
  --link neural-redis:redis `
  --link neural-trading-api:api `
  moises-neural-trading `
  streamlit run dashboard/main.py --server.port=8501 --server.address=0.0.0.0

Write-Host "⏳ Aguardando containers iniciarem..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "🔍 Testando API corrigida..." -ForegroundColor Blue

# Testa health check
Write-Host "Health Check:" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Erro no health check: $($_.Exception.Message)" -ForegroundColor Red
}

# Testa neural status
Write-Host "`nNeural Status:" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/neural/status" -Method Get
    $response | ConvertTo-Json -Depth 5
} catch {
    Write-Host "Erro no neural status: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n✅ CORREÇÃO APLICADA!" -ForegroundColor Green
Write-Host "🌐 API: http://localhost:8001" -ForegroundColor Cyan
Write-Host "📊 Dashboard: http://localhost:8501" -ForegroundColor Cyan

# Mostra logs se houver erro
Write-Host "`n📋 Logs da API:" -ForegroundColor Blue
docker logs neural-trading-api --tail 20