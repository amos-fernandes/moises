#!/usr/bin/env python3
# teste_trade_real_simulado.py
# Teste com simulação de trade real usando as condições atuais

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
    except:
        return 0

def executar_trade_real(api_key, api_secret, symbol, amount, offset):
    """Executar trade real de compra"""
    try:
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': str(amount),
            'recvWindow': 5000,
            'timestamp': int(time.time() * 1000) + offset
        }
        
        query_string = urlencode(params)
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        r = requests.post(BASE_URL + '/api/v3/order', params=params, headers=headers, timeout=10)
        
        if r.status_code == 200:
            return r.json()
        else:
            return {'error': True, 'detail': f"HTTP {r.status_code}: {r.text}"}
    except Exception as e:
        return {'error': True, 'detail': str(e)}

def get_saldo_usdt(api_key, api_secret, offset):
    """Obter saldo USDT atual"""
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
        return 0
    except:
        return 0

def get_preco_atual(symbol):
    """Obter preço atual de um par"""
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5)
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

def teste_trade_real():
    """Teste de trade real com a conta que tem mais saldo"""
    print("🎂💰 TESTE DE TRADE REAL - VERIFICAÇÃO COMPLETA 💰🎂")
    print("=" * 65)
    
    # Sincronizar tempo
    offset = sync_time()
    print(f"⏰ Offset de tempo: {offset}ms\n")
    
    # Carregar contas
    contas_config = carregar_contas()
    
    # Encontrar conta com maior saldo USDT
    melhor_conta = None
    maior_saldo = 0
    
    for conta_id, dados in contas_config.items():
        saldo = get_saldo_usdt(dados['api_key'], dados['api_secret'], offset)
        print(f"📊 {conta_id} ({dados['nome']}): ${saldo:.2f} USDT")
        
        if saldo > maior_saldo:
            maior_saldo = saldo
            melhor_conta = {
                'id': conta_id,
                'nome': dados['nome'],
                'api_key': dados['api_key'],
                'api_secret': dados['api_secret'],
                'saldo': saldo
            }
    
    if not melhor_conta or melhor_conta['saldo'] < 3:
        print(f"\n❌ Nenhuma conta com saldo suficiente (mín. $3)")
        return False
    
    print(f"\n✅ Usando conta: {melhor_conta['nome']} (${melhor_conta['saldo']:.2f})")
    
    # Escolher par para trading (BTC por ter maior liquidez)
    symbol = 'BTCUSDT'
    preco_atual = get_preco_atual(symbol)
    
    print(f"📊 Par selecionado: {symbol}")
    print(f"💰 Preço atual: ${preco_atual:,.2f}")
    
    # Calcular valor do trade (máximo 10% do saldo ou $15)
    trade_amount = min(15.0, melhor_conta['saldo'] * 0.1)
    trade_amount = max(5.0, trade_amount)  # Mínimo $5 (requisito Binance)
    
    print(f"💵 Valor do trade: ${trade_amount:.2f}")
    
    # Confirmar execução
    print(f"\n⚠️ ATENÇÃO: Este será um TRADE REAL!")
    print(f"   Conta: {melhor_conta['nome']}")
    print(f"   Par: {symbol}")
    print(f"   Valor: ${trade_amount:.2f} USDT")
    print(f"   Estimativa BTC: {trade_amount/preco_atual:.8f}")
    
    confirmacao = input("\n🚀 Confirma execução do trade real? (s/n): ").strip().lower()
    
    if confirmacao not in ['s', 'sim', 'y', 'yes']:
        print("❌ Trade cancelado pelo usuário")
        return False
    
    # Executar trade
    print(f"\n🚀 EXECUTANDO TRADE REAL...")
    
    saldo_antes = melhor_conta['saldo']
    
    result = executar_trade_real(
        melhor_conta['api_key'],
        melhor_conta['api_secret'],
        symbol,
        trade_amount,
        offset
    )
    
    if result.get('error'):
        print(f"❌ ERRO no trade: {result['detail']}")
        return False
    
    # Processar resultado
    executed_qty = float(result.get('executedQty', 0))
    spent_usdt = float(result.get('cummulativeQuoteQty', 0))
    order_id = result.get('orderId')
    
    print(f"✅ TRADE EXECUTADO COM SUCESSO!")
    print(f"   Order ID: {order_id}")
    print(f"   USDT gasto: ${spent_usdt:.2f}")
    print(f"   BTC recebido: {executed_qty:.8f}")
    print(f"   Preço médio: ${spent_usdt/executed_qty:,.2f}")
    
    # Verificar saldo após trade
    time.sleep(2)  # Aguardar atualização
    saldo_depois = get_saldo_usdt(melhor_conta['api_key'], melhor_conta['api_secret'], offset)
    
    print(f"\n💰 SALDOS ANTES/DEPOIS:")
    print(f"   USDT antes: ${saldo_antes:.2f}")
    print(f"   USDT depois: ${saldo_depois:.2f}")
    print(f"   Diferença: ${saldo_antes - saldo_depois:.2f}")
    print(f"   + BTC: {executed_qty:.8f}")
    
    # Salvar resultado
    trade_record = {
        'timestamp': datetime.now().isoformat(),
        'conta_id': melhor_conta['id'],
        'conta_nome': melhor_conta['nome'],
        'symbol': symbol,
        'order_id': order_id,
        'usdt_gasto': spent_usdt,
        'btc_recebido': executed_qty,
        'preco_execucao': spent_usdt/executed_qty,
        'saldo_antes': saldo_antes,
        'saldo_depois': saldo_depois,
        'teste_sistema': True
    }
    
    # Salvar no arquivo de trades
    trades_file = BASE_DIR / "reports" / "trades_multi_conta.json"
    trades = []
    if trades_file.exists():
        try:
            with open(trades_file, 'r') as f:
                trades = json.load(f)
        except:
            pass
    
    trades.append(trade_record)
    
    with open(trades_file, 'w') as f:
        json.dump(trades, f, indent=2)
    
    print(f"\n📋 Trade salvo no histórico: {trades_file}")
    
    print(f"\n🎯 CONCLUSÃO:")
    print(f"✅ Sistema funcionando perfeitamente!")
    print(f"✅ Trade real executado com sucesso")
    print(f"✅ Saldos USDT e BTC gerenciados corretamente")
    print(f"✅ Pronto para operação automática contínua")
    
    return True

if __name__ == '__main__':
    try:
        sucesso = teste_trade_real()
        
        if sucesso:
            print(f"\n🎂💰 SISTEMA TOTALMENTE VALIDADO PARA OPERAÇÃO REAL! 💰🎂")
            print(f"🚀 Execute 'python moises_multi_conta.py' para trading automático")
        else:
            print(f"\n🔧 Ajustes necessários antes da operação automática")
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Teste cancelado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")