param(
    [Parameter(Mandatory=$true)][string]$AssetKey,
    [Parameter(Mandatory=$true)][string]$Ticker,
    [int]$Timesteps = 5000000,
    [string]$ModelDir = "src\model\5m_runs",
    [string]$PythonExe
)

# Simple helper to run a full training for a single asset by temporarily providing a scripts.config override
# Usage: .\run_single_5m_asset.ps1 -AssetKey 'crypto_eth' -Ticker 'ETH-USD' -Timesteps 5000000

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $PythonExe) {
    # default to the repo venv Python if present
    $possible = Join-Path $scriptRoot "..\.venv\Scripts\python.exe"
    if (Test-Path $possible) { $PythonExe = (Resolve-Path $possible).Path } else { $PythonExe = "python" }
}

# Create temporary override package
$tmpRoot = Join-Path $scriptRoot "tmp_scripts_override_$AssetKey"
Remove-Item -Recurse -Force $tmpRoot -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path (Join-Path $tmpRoot "scripts") | Out-Null

$configContent = @"
# Auto-generated override config for single-asset runs
MULTI_ASSET_SYMBOLS = {
    '$AssetKey': '$Ticker'
}
# Optionally other configs you want to override for the run
MODEL_SAVE_DIR = r'$ModelDir\$AssetKey'
"@

Set-Content -Path (Join-Path $tmpRoot "scripts\config.py") -Value $configContent -Encoding UTF8
Set-Content -Path (Join-Path $tmpRoot "scripts\__init__.py") -Value "# override package" -Encoding UTF8

# Ensure model dir exists
$fullModelDir = Join-Path $scriptRoot "..\$ModelDir\$AssetKey"
New-Item -ItemType Directory -Force -Path $fullModelDir | Out-Null

# Run training with environment overrides
Write-Host "Starting 5M run for $AssetKey -> $Ticker with $Timesteps timesteps. Using Python: $PythonExe"
$env:PPO_TOTAL_TIMESTEPS = [string]$Timesteps
# Ensure SMOKE_TIMESTEPS is not set so the script runs the full configured timesteps
if ($env:SMOKE_TIMESTEPS) { Remove-Item Env:\SMOKE_TIMESTEPS }

# Prepend tmp override dir on PYTHONPATH so `import scripts.config` picks this override
$oldPy = $env:PYTHONPATH
$env:PYTHONPATH = (Convert-Path $tmpRoot)

# Execute the train script and capture stdout/stderr to a per-run log file so we can inspect "Starting PPO.learn"
$timestamp = (Get-Date).ToString('yyyyMMddTHHmmss')
$logFile = Join-Path $fullModelDir ("train_{0}_{1}.log" -f $AssetKey, $timestamp)
Write-Host "Logging training stdout/stderr to: $logFile"

$pythonScript = (Join-Path $scriptRoot "..\agents\train_rl_portfolio_agent.py")
try {
    $proc = Start-Process -FilePath $PythonExe -ArgumentList @($pythonScript) -NoNewWindow -Wait -PassThru -RedirectStandardOutput $logFile -RedirectStandardError $logFile
    $exitCode = $proc.ExitCode
} catch {
    # If Start-Process with redirection fails (old PS versions), fall back to inline execution with redirection
    Write-Host "Start-Process failed or not supported, falling back to inline execution with redirection"
    & $PythonExe $pythonScript > $logFile 2>&1
    $exitCode = $LASTEXITCODE
}

# Restore PYTHONPATH and cleanup
$env:PYTHONPATH = $oldPy
try { Remove-Item -Recurse -Force $tmpRoot -ErrorAction SilentlyContinue } catch { }

if ($exitCode -eq 0) { Write-Host "Run finished (exit 0). Model saved under: $fullModelDir" } else { Write-Host "Run exited with code: $exitCode" }
exit $exitCode
