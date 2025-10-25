#!/usr/bin/env python3
# verificar_todos_saldos.py
# Verificar todos os saldos de todas as contas após trades

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
BASE_URL = "https://api.binance.com"

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

def get_todos_saldos(api_key, api_secret, offset=0):
    """Obter todos os saldos de uma conta"""
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
            saldos = {}
            
            for balance in account.get('balances', []):
                free_balance = float(balance['free'])
                locked_balance = float(balance['locked'])
                total_balance = free_balance + locked_balance
                
                if total_balance > 0:
                    saldos[balance['asset']] = {
                        'free': free_balance,
                        'locked': locked_balance,
                        'total': total_balance
                    }
            
            return saldos
        else:
            print(f"Erro HTTP {r.status_code}: {r.text}")
            return {}
    except Exception as e:
        print(f"Erro ao obter saldos: {e}")
        return {}

def get_preco_atual(symbol):
    """Obter preço atual de um par"""
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}USDT", timeout=5)
        if r.status_code == 200:
            return float(r.json()['price'])
    except:
        pass
    return 0

def carregar_contas():
    """Carregar contas do config"""
    config_file = CONFIG_DIR / "contas.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def verificar_todas_contas():
    """Verificar saldos completos de todas as contas"""
    print("🎂💰 VERIFICAÇÃO COMPLETA DE SALDOS - TODAS AS CONTAS 💰🎂")
    print("=" * 70)
    
    # Sincronizar tempo
    offset = sync_time()
    print(f"⏰ Offset de tempo: {offset}ms\n")
    
    # Carregar contas
    contas_config = carregar_contas()
    
    dashboard_data = {
        'timestamp': datetime.now().isoformat(),
        'total_contas': len(contas_config),
        'contas_ativas': 0,
        'total_trades': 0,
        'contas': {}
    }
    
    valor_total_portfolio = 0
    
    for conta_id, dados in contas_config.items():
        print(f"📊 {conta_id} - {dados['nome']}:")
        print("-" * 50)
        
        saldos = get_todos_saldos(dados['api_key'], dados['api_secret'], offset)
        
        if saldos:
            saldo_usdt = saldos.get('USDT', {}).get('total', 0)
            valor_conta = saldo_usdt
            
            print(f"💵 USDT: {saldo_usdt:.8f}")
            
            # Verificar outras criptomoedas
            cryptos_encontradas = []
            for asset, saldo_info in saldos.items():
                if asset != 'USDT' and saldo_info['total'] > 0:
                    preco = get_preco_atual(asset)
                    valor_usd = saldo_info['total'] * preco if preco > 0 else 0
                    valor_conta += valor_usd
                    
                    print(f"🪙 {asset}: {saldo_info['total']:.8f} (≈${valor_usd:.2f})")
                    cryptos_encontradas.append({
                        'asset': asset,
                        'quantidade': saldo_info['total'],
                        'valor_usd': valor_usd,
                        'preco': preco
                    })
            
            valor_total_portfolio += valor_conta
            
            print(f"💰 Valor total da conta: ${valor_conta:.2f}")
            
            # Salvar no dashboard
            dashboard_data['contas'][conta_id] = {
                'nome': dados['nome'],
                'saldo_inicial': saldo_usdt,
                'saldo_atual': saldo_usdt,
                'trades_executados': 0,
                'status': f"{len(cryptos_encontradas)} posições ativas",
                'ultimo_trade': 0,
                'ativa': True,
                'saldos_crypto': saldos,
                'valor_total_usd': valor_conta,
                'cryptos': cryptos_encontradas
            }
            
            dashboard_data['contas_ativas'] += 1
            
        else:
            print("❌ Não foi possível obter saldos")
            dashboard_data['contas'][conta_id] = {
                'nome': dados['nome'],
                'saldo_inicial': 0,
                'saldo_atual': 0,
                'trades_executados': 0,
                'status': 'Erro na conexão',
                'ultimo_trade': 0,
                'ativa': False,
                'saldos_crypto': {},
                'valor_total_usd': 0,
                'cryptos': []
            }
        
        print()
    
    print("=" * 70)
    print(f"💎 VALOR TOTAL DO PORTFOLIO: ${valor_total_portfolio:.2f}")
    print("=" * 70)
    
    # Salvar dashboard atualizado
    dashboard_file = REPORTS_DIR / "dashboard_multi_conta.json"
    with open(dashboard_file, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    print(f"✅ Dashboard atualizado: {dashboard_file}")
    print("🌐 Acesse: http://localhost:8001")
    
    return dashboard_data

if __name__ == '__main__':
    try:
        verificar_todas_contas()
    except KeyboardInterrupt:
        print("\n⏹️ Verificação interrompida")
    except Exception as e:
        print(f"❌ Erro: {e}")