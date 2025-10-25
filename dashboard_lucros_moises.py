#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 DASHBOARD MOISES - LUCROS EM TEMPO REAL
=========================================
Dashboard web para acompanhar lucros e impacto humanitário
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
import sys
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from pydantic import BaseModel

# Importações condicionais
try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException
    BINANCE_AVAILABLE = True
except ImportError:
    BINANCE_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

# Modelos de dados
class TradeResult(BaseModel):
    timestamp: str
    symbol: str
    side: str
    quantity: float
    price: float
    profit_usdt: float
    profit_brl: float
    humanitarian_contribution: float
    capital_total: float
    success: bool

class DashboardStats(BaseModel):
    capital_inicial: float
    capital_atual: float
    lucro_total_usdt: float
    lucro_total_brl: float
    trades_hoje: int
    trades_total: int
    precisao_neural: int
    fundo_humanitario_brl: float
    familias_ajudadas: int
    crescimento_percent: float

# Sistema principal
class MoisesLiveDashboard:
    def __init__(self):
        self.app = FastAPI(title="MOISES Dashboard", description="Lucros em Tempo Real")
        self.setup_routes()
        
        # Estado do sistema
        self.capital_inicial = 18.18
        self.capital_atual = 18.18
        self.trades_executados = []
        self.stats = DashboardStats(
            capital_inicial=18.18,
            capital_atual=18.18,
            lucro_total_usdt=0.0,
            lucro_total_brl=0.0,
            trades_hoje=0,
            trades_total=0,
            precisao_neural=95,
            fundo_humanitario_brl=0.0,
            familias_ajudadas=0,
            crescimento_percent=0.0
        )
        
        # Conexões WebSocket
        self.websocket_connections = []
        
        # Cliente Binance
        self.initialize_binance()
        
    def initialize_binance(self):
        """Inicializa conexão com Binance"""
        try:
            api_key = os.getenv('BINANCE_API_KEY')
            api_secret = os.getenv('BINANCE_API_SECRET')
            
            if not api_key or not api_secret or api_key == 'SUA_API_KEY_AQUI':
                print("⚠️ API Keys não configuradas - usando modo demo")
                self.client = None
                return False
            
            # Primeiro testar no testnet
            self.client = Client(api_key, api_secret, testnet=True)
            
            # Testar conexão
            account = self.client.get_account()
            print(f"✅ Conectado à Binance Testnet")
            print(f"📊 Tipo da conta: {account['accountType']}")
            
            # Atualizar capital atual
            self.update_real_balance()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Erro na conexão Binance: {e}")
            print("🎭 Continuando em modo demonstração")
            self.client = None
            return False
    
    def update_real_balance(self):
        """Atualiza saldo real da conta"""
        if not self.client:
            return
            
        try:
            account = self.client.get_account()
            balances = {balance['asset']: float(balance['free']) 
                       for balance in account['balances'] 
                       if float(balance['free']) > 0}
            
            usdt_balance = balances.get('USDT', 0)
            if usdt_balance > 0:
                self.capital_atual = usdt_balance
                self.stats.capital_atual = usdt_balance
                
        except Exception as e:
            print(f"Erro ao atualizar saldo: {e}")
    
    def setup_routes(self):
        """Configura rotas da API"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            return self.get_dashboard_html()
        
        @self.app.get("/api/stats")
        async def get_stats():
            """Retorna estatísticas atuais"""
            self.calculate_current_stats()
            return self.stats.dict()
        
        @self.app.get("/api/trades")
        async def get_trades():
            """Retorna histórico de trades"""
            return {"trades": self.trades_executados[-50:]}  # Últimos 50 trades
        
        @self.app.websocket("/ws/live")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para dados em tempo real"""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Enviar stats atualizadas a cada 5 segundos
                    self.calculate_current_stats()
                    await websocket.send_json({
                        "type": "stats_update",
                        "data": self.stats.dict()
                    })
                    await asyncio.sleep(5)
                    
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
        
        @self.app.post("/api/simulate_trade")
        async def simulate_trade():
            """Simula um trade para demonstração"""
            trade = self.simulate_demo_trade()
            if trade:
                # Broadcast para todos os websockets conectados
                await self.broadcast_trade_update(trade)
                return {"success": True, "trade": trade.dict()}
            return {"success": False, "message": "Erro na simulação"}
    
    def calculate_current_stats(self):
        """Calcula estatísticas atuais"""
        if self.trades_executados:
            lucro_total_usdt = sum(t.get('profit_usdt', 0) for t in self.trades_executados)
            lucro_total_brl = lucro_total_usdt * 5.5  # Conversão USD->BRL
            fundo_humanitario = lucro_total_brl * 0.20
            
            self.stats.lucro_total_usdt = lucro_total_usdt
            self.stats.lucro_total_brl = lucro_total_brl
            self.stats.trades_total = len(self.trades_executados)
            self.stats.fundo_humanitario_brl = fundo_humanitario
            self.stats.familias_ajudadas = int(fundo_humanitario / 500)
            self.stats.crescimento_percent = ((self.capital_atual - self.capital_inicial) / self.capital_inicial) * 100
        
        # Contar trades de hoje
        today = datetime.now().strftime('%Y-%m-%d')
        self.stats.trades_hoje = len([t for t in self.trades_executados 
                                    if t.get('timestamp', '').startswith(today)])
    
    def simulate_demo_trade(self) -> Optional[TradeResult]:
        """Simula um trade para demonstração do dashboard"""
        import random
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        symbol = random.choice(symbols)
        side = random.choice(['BUY', 'SELL'])
        
        # Preços base
        base_prices = {'BTCUSDT': 67000, 'ETHUSDT': 2600, 'BNBUSDT': 590}
        price = base_prices[symbol] * (1 + random.uniform(-0.01, 0.01))
        
        # Simular trade bem-sucedido (95% de chance)
        success = random.random() < 0.95
        
        if success:
            trade_amount = self.capital_atual * 0.1  # 10% do capital
            quantity = trade_amount / price
            profit_percent = random.uniform(0.008, 0.015)  # 0.8% a 1.5%
            profit_usdt = trade_amount * profit_percent
            
            # Atualizar capital
            reinvestment = profit_usdt * 0.80
            self.capital_atual += reinvestment
            self.stats.capital_atual = self.capital_atual
            
            trade = TradeResult(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                profit_usdt=profit_usdt,
                profit_brl=profit_usdt * 5.5,
                humanitarian_contribution=profit_usdt * 0.20 * 5.5,
                capital_total=self.capital_atual,
                success=True
            )
            
            # Adicionar ao histórico
            self.trades_executados.append(trade.dict())
            
            return trade
        
        return None
    
    async def broadcast_trade_update(self, trade: TradeResult):
        """Envia atualização de trade para todos os websockets"""
        message = {
            "type": "new_trade",
            "data": trade.dict()
        }
        
        disconnected = []
        for websocket in self.websocket_connections:
            try:
                await websocket.send_json(message)
            except:
                disconnected.append(websocket)
        
        # Remove conexões desconectadas
        for ws in disconnected:
            if ws in self.websocket_connections:
                self.websocket_connections.remove(ws)
    
    def get_dashboard_html(self) -> str:
        """Gera HTML do dashboard"""
        return f"""
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎂 MOISES Dashboard - Aniversário 2025</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255,255,255,0.15);
            padding: 25px;
            border-radius: 15px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
            transition: transform 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
        }}
        
        .stat-card h3 {{
            font-size: 1.1rem;
            opacity: 0.9;
            margin-bottom: 15px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2.2rem;
            font-weight: bold;
            text-align: center;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.3);
        }}
        
        .positive {{ color: #4ade80; }}
        .negative {{ color: #f87171; }}
        .neutral {{ color: #60a5fa; }}
        
        .trades-section {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            backdrop-filter: blur(10px);
        }}
        
        .trades-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        
        .trades-list {{
            max-height: 400px;
            overflow-y: auto;
        }}
        
        .trade-item {{
            background: rgba(255,255,255,0.1);
            margin-bottom: 10px;
            padding: 15px;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.3s ease;
        }}
        
        .trade-item:hover {{
            background: rgba(255,255,255,0.2);
        }}
        
        .trade-info {{
            flex: 1;
        }}
        
        .trade-profit {{
            font-weight: bold;
            font-size: 1.1rem;
        }}
        
        .live-indicator {{
            display: inline-block;
            width: 10px;
            height: 10px;
            background: #4ade80;
            border-radius: 50%;
            animation: pulse 2s infinite;
            margin-right: 10px;
        }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
        
        .simulate-btn {{
            background: linear-gradient(45deg, #f093fb 0%, #f5576c 100%);
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s ease;
        }}
        
        .simulate-btn:hover {{
            transform: scale(1.05);
        }}
        
        .mission-card {{
            background: linear-gradient(45deg, #43e97b 0%, #38f9d7 100%);
            color: #2d3748;
            padding: 20px;
            border-radius: 15px;
            margin-top: 20px;
            text-align: center;
        }}
        
        .mission-card h3 {{
            color: #2d3748;
            margin-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎂 MOISES Dashboard - Aniversário 2025 🎂</h1>
            <p><span class="live-indicator"></span>Sistema Neural Ativo • 95% Precisão • Ajudando Crianças</p>
        </div>
        
        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>💰 Capital Atual</h3>
                <div class="stat-value neutral" id="capital-atual">$0.00</div>
            </div>
            
            <div class="stat-card">
                <h3>📈 Lucro Total (USDT)</h3>
                <div class="stat-value positive" id="lucro-usdt">$0.00</div>
            </div>
            
            <div class="stat-card">
                <h3>🇧🇷 Lucro Total (BRL)</h3>
                <div class="stat-value positive" id="lucro-brl">R$ 0,00</div>
            </div>
            
            <div class="stat-card">
                <h3>📊 Crescimento</h3>
                <div class="stat-value positive" id="crescimento">+0.00%</div>
            </div>
            
            <div class="stat-card">
                <h3>🚀 Trades Hoje</h3>
                <div class="stat-value neutral" id="trades-hoje">0</div>
            </div>
            
            <div class="stat-card">
                <h3>🎯 Total de Trades</h3>
                <div class="stat-value neutral" id="trades-total">0</div>
            </div>
            
            <div class="stat-card">
                <h3>💝 Fundo Humanitário</h3>
                <div class="stat-value positive" id="fundo-humanitario">R$ 0,00</div>
            </div>
            
            <div class="stat-card">
                <h3>👨‍👩‍👧‍👦 Famílias Ajudadas</h3>
                <div class="stat-value positive" id="familias-ajudadas">0</div>
            </div>
        </div>
        
        <!-- Trades Section -->
        <div class="trades-section">
            <div class="trades-header">
                <h2>🚀 Trades em Tempo Real</h2>
                <button class="simulate-btn" onclick="simulateTrade()">
                    🎭 Simular Trade
                </button>
            </div>
            
            <div class="trades-list" id="trades-list">
                <div class="trade-item">
                    <div class="trade-info">
                        <div>Aguardando primeiro trade...</div>
                        <small>Sistema pronto para operar</small>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Mission Card -->
        <div class="mission-card">
            <h3>🎯 Missão MOISES</h3>
            <p>Transformar cada lucro em esperança para crianças necessitadas. 20% de cada ganho vai diretamente para famílias em situação de vulnerabilidade.</p>
        </div>
    </div>

    <script>
        let ws;
        let statsData = {{}};
        
        // Conectar WebSocket
        function connectWebSocket() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${{protocol}}//${{window.location.host}}/ws/live`);
            
            ws.onopen = function() {{
                console.log('✅ Conectado ao MOISES em tempo real');
            }};
            
            ws.onmessage = function(event) {{
                const message = JSON.parse(event.data);
                
                if (message.type === 'stats_update') {{
                    updateStats(message.data);
                }} else if (message.type === 'new_trade') {{
                    addTradeToList(message.data);
                    updateStats(statsData);
                }}
            }};
            
            ws.onclose = function() {{
                console.log('⚠️ Conexão perdida, reconectando...');
                setTimeout(connectWebSocket, 3000);
            }};
        }}
        
        // Atualizar estatísticas na tela
        function updateStats(data) {{
            statsData = data;
            
            document.getElementById('capital-atual').textContent = `$${{data.capital_atual.toFixed(2)}}`;
            document.getElementById('lucro-usdt').textContent = `$${{data.lucro_total_usdt.toFixed(4)}}`;
            document.getElementById('lucro-brl').textContent = `R$ ${{data.lucro_total_brl.toFixed(2)}}`;
            document.getElementById('crescimento').textContent = `+${{data.crescimento_percent.toFixed(2)}}%`;
            document.getElementById('trades-hoje').textContent = data.trades_hoje;
            document.getElementById('trades-total').textContent = data.trades_total;
            document.getElementById('fundo-humanitario').textContent = `R$ ${{data.fundo_humanitario_brl.toFixed(2)}}`;
            document.getElementById('familias-ajudadas').textContent = data.familias_ajudadas;
        }}
        
        // Adicionar trade à lista
        function addTradeToList(trade) {{
            const tradesList = document.getElementById('trades-list');
            const tradeItem = document.createElement('div');
            tradeItem.className = 'trade-item';
            
            const profitClass = trade.success ? 'positive' : 'negative';
            const profitSymbol = trade.success ? '+' : '-';
            
            tradeItem.innerHTML = `
                <div class="trade-info">
                    <div>${{trade.symbol}} • ${{trade.side}} • ${{new Date(trade.timestamp).toLocaleTimeString()}}</div>
                    <small>Quantidade: ${{trade.quantity.toFixed(6)}} • Preço: $${{trade.price.toFixed(2)}}</small>
                </div>
                <div>
                    <div class="trade-profit ${{profitClass}}">
                        ${{profitSymbol}}$${{Math.abs(trade.profit_usdt).toFixed(4)}} USDT
                    </div>
                    <small>💝 R$ ${{trade.humanitarian_contribution.toFixed(2)}}</small>
                </div>
            `;
            
            tradesList.insertBefore(tradeItem, tradesList.firstChild);
            
            // Manter apenas os últimos 10 trades na tela
            if (tradesList.children.length > 10) {{
                tradesList.removeChild(tradesList.lastChild);
            }}
        }}
        
        // Simular trade (para demonstração)
        async function simulateTrade() {{
            try {{
                const response = await fetch('/api/simulate_trade', {{
                    method: 'POST'
                }});
                const result = await response.json();
                
                if (result.success) {{
                    console.log('✅ Trade simulado com sucesso');
                }} else {{
                    console.log('❌ Erro na simulação:', result.message);
                }}
            }} catch (error) {{
                console.error('Erro ao simular trade:', error);
            }}
        }}
        
        // Inicializar
        connectWebSocket();
        
        // Carregar stats iniciais
        fetch('/api/stats')
            .then(response => response.json())
            .then(data => updateStats(data))
            .catch(error => console.error('Erro ao carregar stats:', error));
    </script>
</body>
</html>
        """

def main():
    """Inicializa o dashboard"""
    print("🎂📊 INICIANDO DASHBOARD MOISES - LUCROS EM TEMPO REAL 📊🎂")
    print("=" * 60)
    print("🎯 Missão: Mostrar cada lucro transformando vidas de crianças")
    print("💝 Cada trade = Uma família mais próxima da dignidade")
    print("=" * 60)
    
    dashboard = MoisesLiveDashboard()
    
    print("\\n🚀 Dashboard disponível em:")
    print("   📱 Local: http://localhost:8000")
    print("   🌐 Rede: http://0.0.0.0:8000")
    print("\\n💡 Recursos do Dashboard:")
    print("   • 📊 Estatísticas em tempo real")
    print("   • 💰 Lucros USDT e BRL")
    print("   • 🚀 Histórico de trades")
    print("   • 💝 Impacto humanitário")
    print("   • 🎭 Modo demonstração")
    print("\\n🎂 FELIZ ANIVERSÁRIO, MOISES! 🎂")
    
    # Iniciar servidor
    uvicorn.run(
        dashboard.app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    main()