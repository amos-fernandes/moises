<#
PowerShell script to create a virtual environment, pre-install heavy numeric/ML wheels,
and install the rest of the requirements with --prefer-binary to avoid long source builds.

Usage examples (PowerShell):
    # Use default python in PATH
    .\scripts\setup_env.ps1

    # Use a specific Python executable
    .\scripts\setup_env.ps1 -PythonPath "C:\\Python311\\python.exe"

The script creates a .venv folder in the repository root.
#>
param(
    [string] $PythonPath = "python"
)

$ErrorActionPreference = 'Stop'

Write-Host "Using Python: $PythonPath"

# Create venv
& $PythonPath -m venv .venv
Write-Host "Created .venv"

# Activate the venv for the remainder of the script
$activateScript = Join-Path -Path (Resolve-Path .venv).Path -ChildPath "Scripts\Activate.ps1"
Write-Host "Activating .venv..."
& $activateScript

# Upgrade pip and install wheel
Write-Host "Upgrading pip and installing wheel and setuptools..."
python -m pip install --upgrade pip setuptools wheel

# Pre-install heavy/compiled packages first to pull wheels when available
$preinstalls = @(
    'numpy',
    'pandas',
    'scikit-learn',
    'tensorflow',
    'scipy'
)

Write-Host "Pre-installing heavy packages (this may still pick wheels or build if wheels aren't available)..."
foreach ($pkg in $preinstalls) {
    try {
        Write-Host "Installing $pkg --prefer-binary ..."
        python -m pip install --prefer-binary $pkg
    } catch {
        Write-Warning "Failed to pre-install $pkg: $($_.Exception.Message)"
    }
}

# Finally install the project requirements preferring binaries
Write-Host "Installing project requirements with --prefer-binary (falls back to sdist if necessary)..."
python -m pip install --prefer-binary -r .\requirements.txt

Write-Host "Environment setup complete. Activate with: .\\.venv\\Scripts\\Activate.ps1"
