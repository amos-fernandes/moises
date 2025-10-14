# diagnose.py
import os
import sys
import json
import time
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
import requests
import httpx

# ===========================================
# SCRIPT DE DIAGNÓSTICO PARA ATCoin Neural Agents
# Executa verificações críticas e gera relatório
# ===========================================

# Configuração
API_URL = "http://127.0.0.1:7860"
INVEST_ENDPOINT = f"{API_URL}/api/invest"
HEALTH_ENDPOINT = f"{API_URL}/health"
AIBANK_API_KEY = "At0R6ebAME5rvFAFv2vfdniyamxdjIN3ouw9NcVU0jBuejrMRlpt2070wKwNGOil"  # Deve ser igual ao do HF
TIMEOUT = 10

# Estrutura de relatório
report = {
    "timestamp": datetime.utcnow().isoformat(),
    "checks": [],
    "overall_status": "unknown"
}

def add_check(name: str, status: str, details: str):
    """Adiciona um item ao relatório"""
    report["checks"].append({
        "name": name,
        "status": status,
        "details": details,
        "timestamp": datetime.utcnow().isoformat()
    })
    print(f"[{status.upper()}] {name}: {details}")

def check_local_files():
    """Verifica arquivos locais críticos"""
    paths = {
        "app.py": "app.py",
        "requirements.txt": "requirements.txt",
        "Procfile": "Procfile",
        "templates/dashboard.html": "templates/dashboard.html",
        "static/css/style.css": "static/css/style.css",
        "src/model/model.h5": "src/model/model.h5",
        "src/model/vec_normalize_stats.pkl": "src/model/vec_normalize_stats.pkl",
        "src/model/other_indicators_scaler.joblib": "src/model/other_indicators_scaler_sup.joblib",
        "src/model/other_indicators_scaler.joblib": "src/model/other_indicators_scaler.joblib",
        "src/model/price_volume_atr_norm_scaler_sup.joblib": "src/model/price_volume_atr_norm_scaler_sup.joblib",
        "src/model/price_volume_atr_norm_scaler.joblib": "src/model/price_volume_atr_norm_scaler.joblib",
        "src/model/rnn_predictor.py": "src/model/rnn_predictor.py"
    }
    for name, path in paths.items():
        file_path = Path(path)
        if file_path.exists():
            add_check(f"Arquivo: {name}", "success", f"Encontrado")
        else:
            add_check(f"Arquivo: {name}", "error", f"NÃO encontrado em {path}")

def check_environment_vars():
    """Verifica variáveis de ambiente críticas"""
    vars_to_check = [
        "AIBANK_API_KEY",
        "CCXT_API_KEY",
        "CCXT_API_SECRET",
        "CALLBACK_SHARED_SECRET",
        "AIBANK_CALLBACK_URL"
    ]
    for var in vars_to_check:
        value = os.environ.get(var)
        if value:
            status = "success" if var != "CCXT_API_KEY" else "warning"  # Não expõe chaves reais
            add_check(f"ENV: {var}", status, "Configurada")
        else:
            if "CCXT" in var:
                add_check(f"ENV: {var}", "info", "Opcional para simulação")
            else:
                add_check(f"ENV: {var}", "warning", "Não configurada (pode causar falha)")

def check_python_dependencies():
    """Verifica se as dependências estão instaladas"""
    required = ["fastapi", "uvicorn", "jinja2", "ccxt", "pandas", "numpy", "httpx"]
    missing = []
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)
    if missing:
        add_check("Dependências Python", "error", f"Faltando: {', '.join(missing)}")
    else:
        add_check("Dependências Python", "success", "Todas instaladas")

async def check_api_health():
    """Testa o endpoint de saúde"""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(HEALTH_ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            model_loaded = data.get("model_loaded", False)
            status_msg = "Modelo carregado" if model_loaded else "Modelo NÃO carregado"
            add_check("API: /health", "success", f"Retorno 200. {status_msg}")
        else:
            add_check("API: /health", "error", f"Retorno {response.status_code}")
    except Exception as e:
        add_check("API: /health", "error", f"Falha na conexão: {str(e)}")

async def check_api_invest():
    """Testa o endpoint /api/invest"""
    payload = {
        "client_id": "diagnose-123",
        "amount": 10.0,
        "aibank_transaction_token": "tok_diag_abc123"
    }
    headers = {
        "Authorization": f"Bearer {AIBANK_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(INVEST_ENDPOINT, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "pending":
                add_check("API: /api/invest", "success", f"Requisição aceita. ID: {data.get('rnn_transaction_id')}")
            else:
                add_check("API: /api/invest", "warning", f"Retorno inesperado: {data}")
        elif response.status_code == 403:
            add_check("API: /api/invest", "error", "403 Forbidden - Chave API incorreta ou não autorizada")
        elif response.status_code == 404:
            add_check("API: /api/invest", "error", "404 Not Found - Verifique a URL do endpoint")
        else:
            add_check("API: /api/invest", "error", f"{response.status_code} - {response.text}")
    except Exception as e:
        add_check("API: /api/invest", "error", f"Falha ao conectar: {str(e)}")

def check_hf_space_status():
    """Verifica se o Space está online (via API do HF)"""
    #space_api = "http://127.0.0.1:7860/"  https://amos-fernandes-nina-cry.hf.space
    space_api = "https://huggingface.co/api/spaces/amos-fernandes/nina-cry"
    try:
        response = requests.get(space_api, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("runtime", {}).get("stage") == "RUNNING":
                add_check("HF Space Status", "success", "RUNNING")
            else:
                add_check("HF Space Status", "warning", f"Status: {data.get('runtime', {}).get('stage')}")
        else:
            add_check("HF Space Status", "error", f"API do HF retornou {response.status_code}")
    except Exception as e:
        add_check("HF Space Status", "error", f"Falha ao verificar status: {str(e)}")

# ============
# EXECUÇÃO
# ============

async def run_diagnostics():
    print("🔍 Iniciando diagnóstico do ATCoin Neural Agents...\n")

    # Etapa 1: Verificações locais
    add_check("Sistema", "info", f"Plataforma: {sys.platform}")
    check_local_files()
    check_environment_vars()
    check_python_dependencies()

    # Etapa 2: Verificações remotas
    print("\n🌐 Testando conexão com o Hugging Face Space...\n")
    await check_api_health()
    await check_api_invest()
    check_hf_space_status()

    # Etapa 3: Resumo
    errors = sum(1 for c in report["checks"] if c["status"] == "error")
    warnings = sum(1 for c in report["checks"] if c["status"] in ["warning", "info"])
    successes = sum(1 for c in report["checks"] if c["status"] == "success")

    print("\n" + "="*60)
    if errors == 0:
        report["overall_status"] = "healthy"
        print("✅ STATUS FINAL: SAUDÁVEL")
        print("🎉 Tudo está configurado corretamente!")
    elif errors > 0:
        report["overall_status"] = "critical"
        print("❌ STATUS FINAL: CRÍTICO")
        print("🚨 Corrija os erros acima para o sistema funcionar.")
    else:
        report["overall_status"] = "warning"
        print("⚠️  STATUS FINAL: AVISO")
        print("🔧 Alguns itens precisam de atenção.")

    print(f"Erros: {errors} | Avisos: {warnings} | Sucessos: {successes}")
    print("="*60)

    # Salvar relatório
    with open("diagnosis_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n📄 Relatório salvo em: diagnosis_report.json")

if __name__ == "__main__":
    asyncio.run(run_diagnostics())