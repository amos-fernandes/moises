@echo off
REM Script de inicialização Windows VPS - MOISES Trading Real
REM Autorizado para operações com fundos reais

echo 🎂💰 INICIANDO MOISES TRADING REAL - VPS 💰🎂
echo ================================================

REM Verificar diretórios
if not exist "logs" mkdir logs
if not exist "reports" mkdir reports  
if not exist "data" mkdir data
if not exist "backups" mkdir backups

REM Instalar dependências
echo 📦 Verificando dependências...
pip install -r requirements.txt

REM Iniciar trading real
echo 🚀 Iniciando MOISES Trading Real...
echo ✅ Autorizado para operações reais
echo 💰 Modo: PRODUÇÃO

python trading_real_vps_moises.py

pause