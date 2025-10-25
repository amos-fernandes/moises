#!/usr/bin/env python3
# dashboard_multi_conta.py
# Dashboard web para monitorar múltiplas contas MOISES

import json
import asyncio
import time
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Detectar sistema
import os
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

REPORTS_DIR = BASE_DIR / "reports"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Criar diretórios
REPORTS_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

app = FastAPI(title="MOISES Multi-Conta Dashboard")

# Configurar templates e arquivos estáticos
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Armazenar conexões WebSocket
websocket_connections = []

def get_dashboard_data():
    """Obter dados das contas"""
    dashboard_file = REPORTS_DIR / "dashboard_multi_conta.json"
    
    if dashboard_file.exists():
        try:
            with open(dashboard_file, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"Erro ao ler dashboard: {e}")
    
    # Dados padrão se arquivo não existir
    return {
        'timestamp': datetime.now().isoformat(),
        'total_contas': 0,
        'contas_ativas': 0,
        'total_trades': 0,
        'contas': {}
    }

def get_trades_data():
    """Obter dados dos trades"""
    trades_file = REPORTS_DIR / "trades_multi_conta.json"
    
    if trades_file.exists():
        try:
            with open(trades_file, 'r') as f:
                trades = json.load(f)
            return trades[-50:]  # Últimos 50 trades
        except:
            pass
    return []

@app.get("/")
async def dashboard(request: Request):
    """Página principal do dashboard"""
    return templates.TemplateResponse("dashboard_multi.html", {"request": request})

@app.get("/api/dashboard")
async def api_dashboard():
    """API para dados do dashboard"""
    dashboard_data = get_dashboard_data()
    trades_data = get_trades_data()
    
    # Calcular estatísticas
    total_saldo_inicial = sum(conta.get('saldo_inicial', 0) for conta in dashboard_data.get('contas', {}).values())
    total_saldo_atual = sum(conta.get('saldo_atual', 0) for conta in dashboard_data.get('contas', {}).values())
    crescimento_total = ((total_saldo_atual - total_saldo_inicial) / total_saldo_inicial * 100) if total_saldo_inicial > 0 else 0
    
    return {
        'dashboard': dashboard_data,
        'trades': trades_data,
        'resumo': {
            'total_saldo_inicial': total_saldo_inicial,
            'total_saldo_atual': total_saldo_atual,
            'crescimento_percentual': crescimento_total,
            'total_trades_executados': len(trades_data)
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para atualizações em tempo real"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Aguardar dados do cliente (ping)
            await websocket.receive_text()
            
            # Enviar dados atualizados
            data = await api_dashboard()
            await websocket.send_json(data)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)

async def broadcast_updates():
    """Broadcast de atualizações para todos os clientes conectados"""
    while True:
        if websocket_connections:
            try:
                data = await api_dashboard()
                
                # Enviar para todos os clientes conectados
                disconnected = []
                for websocket in websocket_connections:
                    try:
                        await websocket.send_json(data)
                    except:
                        disconnected.append(websocket)
                
                # Remover conexões desconectadas
                for ws in disconnected:
                    websocket_connections.remove(ws)
                    
            except Exception as e:
                print(f"Broadcast error: {e}")
        
        await asyncio.sleep(10)  # Atualizar a cada 10 segundos

# Iniciar broadcast em background
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(broadcast_updates())

if __name__ == "__main__":
    print("🎂💰 DASHBOARD MULTI-CONTA MOISES 💰🎂")
    print("=" * 50)
    print("📊 Dashboard: http://localhost:8001")
    print("📂 Dados: reports/dashboard_multi_conta.json")
    print("🔄 Atualizações em tempo real via WebSocket")
    print("=" * 50)
    
    uvicorn.run(app, host="127.0.0.1", port=8001)