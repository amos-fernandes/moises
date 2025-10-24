# Script para reconstruir container com arquivo corrigido

Write-Host "🔧 Reconstruindo container neural com arquivo corrigido..." -ForegroundColor Green

# Possíveis localizações do Docker
$dockerPaths = @(
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    "C:\Program Files (x86)\Docker\Docker\resources\bin\docker.exe",
    "$env:ProgramFiles\Docker\Docker\resources\bin\docker.exe",
    "${env:ProgramFiles(x86)}\Docker\Docker\resources\bin\docker.exe"
)

$dockerPath = $null
foreach ($path in $dockerPaths) {
    if (Test-Path $path) {
        $dockerPath = $path
        break
    }
}

if (-not $dockerPath) {
    # Tenta encontrar no PATH
    $dockerExe = Get-Command docker -ErrorAction SilentlyContinue
    if ($dockerExe) {
        $dockerPath = $dockerExe.Source
    }
}

if (-not $dockerPath) {
    Write-Host "❌ Docker não encontrado! Verifique se o Docker Desktop está instalado e no PATH." -ForegroundColor Red
    Write-Host "Locais verificados:" -ForegroundColor Yellow
    $dockerPaths | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
    exit 1
}

Write-Host "✅ Docker encontrado: $dockerPath" -ForegroundColor Green

# Comandos Docker
Write-Host "🛑 Parando containers..." -ForegroundColor Yellow
& $dockerPath "compose" "down"

Write-Host "🔨 Reconstruindo container neural (sem cache)..." -ForegroundColor Yellow
& $dockerPath "compose" "build" "neural" "--no-cache"

Write-Host "🚀 Iniciando containers..." -ForegroundColor Yellow
& $dockerPath "compose" "up" "-d"

# Aguarda inicialização
Write-Host "⏳ Aguardando 30 segundos para inicialização..." -ForegroundColor Cyan
Start-Sleep -Seconds 30

# Testa endpoints
Write-Host "🧪 Testando endpoints..." -ForegroundColor Green

$testResults = @()

# Teste 1: API Neural
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $testResults += "✅ API Neural (8001): OK"
    } else {
        $testResults += "⚠️ API Neural (8001): Status $($response.StatusCode)"
    }
} catch {
    $testResults += "❌ API Neural (8001): $($_.Exception.Message)"
}

# Teste 2: Dashboard
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8501" -Method GET -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        $testResults += "✅ Dashboard (8501): OK"
    } else {
        $testResults += "⚠️ Dashboard (8501): Status $($response.StatusCode)"
    }
} catch {
    $testResults += "❌ Dashboard (8501): $($_.Exception.Message)"
}

# Mostra resultados
Write-Host ""
Write-Host "🎯 RESULTADOS DOS TESTES:" -ForegroundColor Cyan
$testResults | ForEach-Object { Write-Host "  $_" }

# Status dos containers
Write-Host ""
Write-Host "📊 STATUS DOS CONTAINERS:" -ForegroundColor Cyan
& $dockerPath "ps" "--filter" "name=neural"

# Se API Neural estiver funcionando
if ($testResults -like "*API Neural*OK*") {
    Write-Host ""
    Write-Host "🎉 SUCESSO! Sistema Neural funcionando!" -ForegroundColor Green
    
    # Tenta descobrir IP externo
    try {
        $ip = (Invoke-WebRequest -Uri "http://ifconfig.me" -UseBasicParsing -TimeoutSec 5).Content.Trim()
        Write-Host "🌐 Acesso externo:" -ForegroundColor Yellow
        Write-Host "  API Neural: http://$ip:8001" -ForegroundColor White
        Write-Host "  Dashboard: http://$ip:8501" -ForegroundColor White
    } catch {
        Write-Host "🏠 Acesso local:" -ForegroundColor Yellow
        Write-Host "  API Neural: http://localhost:8001" -ForegroundColor White
        Write-Host "  Dashboard: http://localhost:8501" -ForegroundColor White
    }
} else {
    Write-Host ""
    Write-Host "⚠️ API Neural com problemas. Verificando logs..." -ForegroundColor Red
    & $dockerPath "compose" "logs" "--tail=20" "neural"
}

Write-Host ""
Write-Host "✅ Script concluído!" -ForegroundColor Green