param(
    [Parameter(Mandatory=$false)][string]$PythonExe
)

# Loop-runner to run 5M timesteps per asset sequentially using run_single_5m_asset.ps1
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PythonExe) {
    $possible = Join-Path $scriptRoot "..\.venv\Scripts\python.exe"
    if (Test-Path $possible) { $PythonExe = (Resolve-Path $possible).Path } else { $PythonExe = "python" }
}

# Load configured multi-asset symbols from scripts/config.py (project default)
try {
    Import-Module (Join-Path $scriptRoot "..\scripts\config.py") -ErrorAction Stop
} catch {
    # read file directly
}

# fallback: read symbols from new-rede-a config if scripts.config not present
$configPath = Join-Path $scriptRoot "..\scripts\config.py"
$symbols = @{
    'crypto_eth' = 'ETH-USD'
    'crypto_btc' = 'BTC-USD'
}
# Try to parse scripts/config.py for MULTI_ASSET_SYMBOLS if exists
if (Test-Path $configPath) {
    $content = Get-Content $configPath -Raw
    if ($content -match 'MULTI_ASSET_SYMBOLS\s*=\s*\{([\s\S]*?)\}') {
        $body = $Matches[1]
        $pairs = $body -split ",\s*'"
        # crude parse; fallback to default if anything fails
    }
}

# Use simplified list for now
$assetMap = @{
    'crypto_eth' = 'ETH-USD'
    'crypto_btc' = 'BTC-USD'
    'stock_aapl' = 'AAPL'
}

foreach ($k in $assetMap.Keys) {
    Write-Host "Starting run for $k -> $($assetMap[$k])"
    & (Join-Path $scriptRoot "run_single_5m_asset.ps1") -AssetKey $k -Ticker $assetMap[$k] -Timesteps 5000000 -PythonExe $PythonExe
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Run for $k failed with exit code $LASTEXITCODE. Stopping loop."
        break
    }
}

Write-Host "All sequential runs completed or loop stopped."