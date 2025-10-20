# Start a detached PowerShell that runs the all-assets 5M sequential runner with CPU-only env
param(
    [int]$Timesteps = 5000000
)

$py = "D:/dev/moises/.venv/Scripts/python.exe"
$runner = Join-Path $PSScriptRoot "run_all_assets_5m.ps1"

$env:CUDA_VISIBLE_DEVICES = ''
$env:CUDA_DEVICE_ORDER = 'PCI_BUS_ID'
$env:TF_CPP_MIN_LOG_LEVEL = '2'
$env:OMP_NUM_THREADS = 4
$env:MKL_NUM_THREADS = 4
$env:PPO_TOTAL_TIMESTEPS = $Timesteps
# Ensure SMOKE_TIMESTEPS is unset for full runs
if (Test-Path Env:\SMOKE_TIMESTEPS) { Remove-Item Env:\SMOKE_TIMESTEPS }

Write-Host "Launching detached PowerShell to run full $Timesteps timesteps sequentially on CPU..."
$cmd = "& { $env:CUDA_VISIBLE_DEVICES=''; $env:CUDA_DEVICE_ORDER='PCI_BUS_ID'; $env:TF_CPP_MIN_LOG_LEVEL='2'; $env:OMP_NUM_THREADS=4; $env:MKL_NUM_THREADS=4; $env:PPO_TOTAL_TIMESTEPS=$Timesteps; & `"$runner`" }"
Start-Process -FilePath 'powershell' -ArgumentList '-NoProfile','-NoExit','-Command',$cmd -WindowStyle Normal
Write-Host "Start-Process invoked. Check the new window for progress or use scripts/monitor_5m_runs.py to monitor artifacts."