#!/usr/bin/env python3
# teste_contas_rapido.py
# Teste rápido das contas e geração de dados para o dashboard

import os
import json
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from pathlib import Path
from datetime import datetime

# Detectar sistema
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"
REPORTS_DIR.mkdir(exist_ok=True)

BASE_URL = "https://api.binance.com"

def carregar_env():
    """Carregar variáveis do .env"""
    env_file = Path('.env')
    env_vars = {}
    if env_file.exists():
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value.strip('"').strip("'")
        except Exception as e:
            print(f"Erro ao carregar .env: {e}")
    return env_vars

def carregar_contas():
    """Carregar contas do config"""
    config_file = CONFIG_DIR / "contas.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar contas: {e}")
    return {}

def sync_time():
    """Sincronizar tempo com Binance"""
    try:
        r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
        r.raise_for_status()
        data = r.json()
        server_time = int(data['serverTime'])
        local_time = int(time.time() * 1000)
        offset = server_time - local_time
        return offset
    except Exception as e:
        print(f"Erro na sincronização: {e}")
        return 0

def get_saldo_usdt(api_key, api_secret, offset=0):
    """Obter saldo USDT de uma conta"""
    try:
        params = {
            'recvWindow': 5000,
            'timestamp': int(time.time() * 1000) + offset
        }
        query_string = urlencode(params)
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        r = requests.get(BASE_URL + '/api/v3/account', params=params, headers=headers, timeout=10)
        
        if r.status_code == 200:
            account = r.json()
            for balance in account.get('balances', []):
                if balance['asset'] == 'USDT':
                    return float(balance['free'])
        else:
            print(f"Erro HTTP {r.status_code}: {r.text}")
            return 0
    except Exception as e:
        print(f"Erro ao obter saldo: {e}")
        return 0

def gerar_dashboard_inicial():
    """Gerar dados iniciais para o dashboard"""
    print("🎂💰 TESTANDO CONTAS E GERANDO DASHBOARD 💰🎂")
    print("=" * 60)
    
    # Sincronizar tempo
    offset = sync_time()
    print(f"⏰ Offset de tempo: {offset}ms")
    
    # Carregar contas
    env_vars = carregar_env()
    contas_config = carregar_contas()
    
    dashboard_data = {
        'timestamp': datetime.now().isoformat(),
        'total_contas': 0,
        'contas_ativas': 0,
        'total_trades': 0,
        'contas': {}
    }
    
    # Testar conta principal (.env)
    api_key = env_vars.get('BINANCE_API_KEY')
    api_secret = env_vars.get('BINANCE_API_SECRET')
    
    if api_key and api_secret:
        print("\n📊 CONTA_1 (Sua Conta Principal):")
        saldo = get_saldo_usdt(api_key, api_secret, offset)
        print(f"   💰 Saldo USDT: ${saldo:.2f}")
        
        dashboard_data['contas']['CONTA_1'] = {
            'nome': 'Sua Conta Principal',
            'saldo_inicial': saldo,
            'saldo_atual': saldo,
            'trades_executados': 0,
            'status': 'Ativo - Pronto para operar',
            'ultimo_trade': 0,
            'ativa': True
        }
        dashboard_data['total_contas'] += 1
        dashboard_data['contas_ativas'] += 1
    
    # Testar contas adicionais
    for conta_id, dados in contas_config.items():
        print(f"\n📊 {conta_id} ({dados['nome']}):")
        saldo = get_saldo_usdt(dados['api_key'], dados['api_secret'], offset)
        print(f"   💰 Saldo USDT: ${saldo:.2f}")
        
        dashboard_data['contas'][conta_id] = {
            'nome': dados['nome'],
            'saldo_inicial': saldo,
            'saldo_atual': saldo,
            'trades_executados': 0,
            'status': 'Ativo - Pronto para operar',
            'ultimo_trade': 0,
            'ativa': saldo > 0
        }
        dashboard_data['total_contas'] += 1
        if saldo > 0:
            dashboard_data['contas_ativas'] += 1
    
    # Salvar dados do dashboard
    dashboard_file = REPORTS_DIR / "dashboard_multi_conta.json"
    with open(dashboard_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"\n✅ Dashboard gerado com sucesso!")
    print(f"📁 Arquivo: {dashboard_file}")
    print(f"📊 Total de contas: {dashboard_data['total_contas']}")
    print(f"🟢 Contas ativas: {dashboard_data['contas_ativas']}")
    
    # Criar arquivo de trades vazio se não existir
    trades_file = REPORTS_DIR / "trades_multi_conta.json"
    if not trades_file.exists():
        with open(trades_file, 'w') as f:
            json.dump([], f)
        print(f"📋 Arquivo de trades criado: {trades_file}")
    
    print(f"\n🌐 Dashboard disponível em: http://localhost:8001")
    print("🔄 Execute 'python dashboard_multi_conta.py' se não estiver rodando")
    
    return dashboard_data

if __name__ == '__main__':
    try:
        dados = gerar_dashboard_inicial()
        
        print("\n" + "=" * 60)
        print("🎯 RESUMO DAS CONTAS:")
        for conta_id, conta in dados['contas'].items():
            status = "✅" if conta['ativa'] else "❌"
            print(f"   {status} {conta['nome']}: ${conta['saldo_atual']:.2f}")
        
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido")
    except Exception as e:
        print(f"❌ Erro no teste: {e}")