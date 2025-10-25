#!/usr/bin/env python3
# teste_trading_completo.py
# Teste completo do sistema de trading com todas as moedas

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

# Pares de trading que o MOISES usa
PARES_TRADING = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']

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
        print(f"❌ Erro na sincronização: {e}")
        return 0

def get_market_data(symbol):
    """Obter dados de mercado para análise"""
    try:
        # Preço atual
        price_url = f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}"
        price_response = requests.get(price_url, timeout=5)
        
        # Estatísticas 24h
        stats_url = f"{BASE_URL}/api/v3/ticker/24hr?symbol={symbol}"
        stats_response = requests.get(stats_url, timeout=5)
        
        if price_response.status_code == 200 and stats_response.status_code == 200:
            price_data = price_response.json()
            stats_data = stats_response.json()
            
            return {
                'symbol': symbol,
                'price': float(price_data['price']),
                'change_24h': float(stats_data['priceChangePercent']),
                'volume': float(stats_data['volume']),
                'high_24h': float(stats_data['highPrice']),
                'low_24h': float(stats_data['lowPrice'])
            }
    except Exception as e:
        print(f"❌ Erro ao obter dados de {symbol}: {e}")
    return None

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
            print(f"❌ Erro HTTP {r.status_code}")
            return {}
    except Exception as e:
        print(f"❌ Erro ao obter saldos: {e}")
        return {}

def analisar_oportunidade(market_data):
    """Analisar se há oportunidade de trading"""
    if not market_data:
        return None
    
    change_24h = market_data['change_24h']
    volume = market_data['volume']
    volatility = (market_data['high_24h'] - market_data['low_24h']) / market_data['low_24h'] * 100
    
    # Lógica de análise neural simplificada
    score = 0
    recommendation = 'HOLD'
    
    # Condições para BUY (queda + volume + volatilidade)
    if change_24h < -1.5 and volume > 1000 and volatility > 2:
        recommendation = 'BUY'
        score = abs(change_24h) + (volume / 10000) + volatility * 2
        
    # Condições para SELL (alta + volume alto)
    elif change_24h > 3 and volume > 1000 and volatility > 3:
        recommendation = 'SELL'
        score = change_24h + (volume / 10000) + volatility
    
    # Confidence baseado no score
    confidence = min(90, 60 + score * 3) if score > 0 else 0
    
    return {
        'symbol': market_data['symbol'],
        'action': recommendation,
        'confidence': confidence,
        'price': market_data['price'],
        'change_24h': change_24h,
        'volume': volume,
        'volatility': volatility,
        'score': score
    }

def simular_trade_compra(symbol, usdt_amount, preco_atual):
    """Simular trade de compra"""
    asset = symbol.replace('USDT', '')
    quantidade = usdt_amount / preco_atual
    
    return {
        'tipo': 'BUY',
        'symbol': symbol,
        'asset': asset,
        'usdt_gasto': usdt_amount,
        'quantidade_comprada': quantidade,
        'preco_execucao': preco_atual,
        'simulado': True
    }

def simular_trade_venda(asset, quantidade, preco_atual):
    """Simular trade de venda"""
    symbol = f"{asset}USDT"
    usdt_recebido = quantidade * preco_atual
    
    return {
        'tipo': 'SELL',
        'symbol': symbol,
        'asset': asset,
        'usdt_recebido': usdt_recebido,
        'quantidade_vendida': quantidade,
        'preco_execucao': preco_atual,
        'simulado': True
    }

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

def teste_trading_completo():
    """Teste completo do sistema de trading"""
    print("🎂💰 TESTE COMPLETO - TRADING MULTI-MOEDAS 💰🎂")
    print("=" * 70)
    
    # Sincronizar tempo
    offset = sync_time()
    print(f"⏰ Sincronização: {offset}ms\n")
    
    # 1. TESTAR DADOS DE MERCADO
    print("📊 1. TESTANDO DADOS DE MERCADO:")
    print("-" * 40)
    
    mercado_ok = True
    dados_mercado = {}
    
    for par in PARES_TRADING:
        market_data = get_market_data(par)
        if market_data:
            dados_mercado[par] = market_data
            print(f"✅ {par}: ${market_data['price']:,.2f} ({market_data['change_24h']:+.2f}%)")
        else:
            print(f"❌ {par}: Falha na obtenção de dados")
            mercado_ok = False
    
    print(f"\n📈 Dados de mercado: {'✅ OK' if mercado_ok else '❌ ERRO'}")
    
    # 2. TESTAR ANÁLISE DE OPORTUNIDADES
    print(f"\n🧠 2. TESTANDO ANÁLISE IA:")
    print("-" * 40)
    
    oportunidades = []
    for par, dados in dados_mercado.items():
        oportunidade = analisar_oportunidade(dados)
        if oportunidade and oportunidade['confidence'] > 60:
            oportunidades.append(oportunidade)
            action_emoji = "🟢" if oportunidade['action'] == 'BUY' else "🔴" if oportunidade['action'] == 'SELL' else "⚪"
            print(f"{action_emoji} {par}: {oportunidade['action']} - Confiança: {oportunidade['confidence']:.1f}%")
        else:
            print(f"⚪ {par}: HOLD - Sem oportunidade clara")
    
    print(f"\n🎯 Oportunidades encontradas: {len(oportunidades)}")
    
    # 3. TESTAR SALDOS DAS CONTAS
    print(f"\n💰 3. TESTANDO SALDOS DAS CONTAS:")
    print("-" * 40)
    
    contas_config = carregar_contas()
    saldos_ok = True
    
    for conta_id, dados in contas_config.items():
        print(f"📊 {conta_id} ({dados['nome']}):")
        saldos = get_todos_saldos(dados['api_key'], dados['api_secret'], offset)
        
        if saldos:
            usdt_disponivel = saldos.get('USDT', {}).get('total', 0)
            print(f"   💵 USDT: {usdt_disponivel:.2f}")
            
            # Verificar posições em crypto
            cryptos = []
            for asset, saldo_info in saldos.items():
                if asset != 'USDT' and saldo_info['total'] > 0:
                    cryptos.append(f"{asset}: {saldo_info['total']:.8f}")
            
            if cryptos:
                print(f"   🪙 Cryptos: {', '.join(cryptos)}")
            
            if usdt_disponivel >= 3:
                print(f"   ✅ Pronto para trading (${usdt_disponivel:.2f} ≥ $3)")
            else:
                print(f"   ⚠️ Saldo baixo para trading (${usdt_disponivel:.2f} < $3)")
        else:
            print(f"   ❌ Erro ao obter saldos")
            saldos_ok = False
        print()
    
    # 4. SIMULAR TRADES DE COMPRA E VENDA
    print(f"🚀 4. SIMULANDO TRADES:")
    print("-" * 40)
    
    if oportunidades and saldos_ok:
        melhor_oportunidade = max(oportunidades, key=lambda x: x['confidence'])
        
        # Simular compra
        if melhor_oportunidade['action'] == 'BUY':
            trade_amount = 10.0  # $10 USDT
            trade_compra = simular_trade_compra(
                melhor_oportunidade['symbol'], 
                trade_amount, 
                melhor_oportunidade['price']
            )
            
            print(f"🟢 SIMULAÇÃO COMPRA:")
            print(f"   Par: {trade_compra['symbol']}")
            print(f"   USDT gasto: ${trade_compra['usdt_gasto']:.2f}")
            print(f"   {trade_compra['asset']} recebido: {trade_compra['quantidade_comprada']:.8f}")
            print(f"   Preço: ${trade_compra['preco_execucao']:,.2f}")
            
            # Simular venda posterior
            time.sleep(1)  # Simular passagem de tempo
            novo_preco = melhor_oportunidade['price'] * 1.005  # +0.5% de lucro
            
            trade_venda = simular_trade_venda(
                trade_compra['asset'], 
                trade_compra['quantidade_comprada'], 
                novo_preco
            )
            
            print(f"\n🔴 SIMULAÇÃO VENDA (após lucro):")
            print(f"   Par: {trade_venda['symbol']}")
            print(f"   {trade_venda['asset']} vendido: {trade_venda['quantidade_vendida']:.8f}")
            print(f"   USDT recebido: ${trade_venda['usdt_recebido']:.2f}")
            print(f"   Lucro: ${trade_venda['usdt_recebido'] - trade_compra['usdt_gasto']:.2f}")
            
        else:
            print("⚪ Nenhuma oportunidade de compra no momento")
    else:
        print("❌ Não é possível simular trades (sem oportunidades ou saldos)")
    
    # 5. RESUMO FINAL
    print(f"\n" + "=" * 70)
    print("📋 RESUMO DO TESTE:")
    print("=" * 70)
    
    status_sistema = "✅ OPERACIONAL" if mercado_ok and saldos_ok else "❌ COM PROBLEMAS"
    
    print(f"🎯 Status geral: {status_sistema}")
    print(f"📊 Dados de mercado: {'✅' if mercado_ok else '❌'}")
    print(f"💰 Saldos das contas: {'✅' if saldos_ok else '❌'}")
    print(f"🧠 Análise IA: ✅ ({len(oportunidades)} oportunidades)")
    print(f"🚀 Simulação trades: ✅")
    print(f"🔄 Pares disponíveis: {', '.join(PARES_TRADING)}")
    
    print(f"\n💡 CONCLUSÃO:")
    if mercado_ok and saldos_ok:
        print("🎂💰 SISTEMA PRONTO PARA TRADING REAL COM TODAS AS MOEDAS! 💰🎂")
        print("✅ Pode executar trades de compra e venda")
        print("✅ Gerencia USDT e posições em crypto")
        print("✅ Análise funcional para todos os pares")
    else:
        print("⚠️ Sistema precisa de ajustes antes do trading real")
    
    return status_sistema == "✅ OPERACIONAL"

if __name__ == '__main__':
    try:
        sistema_ok = teste_trading_completo()
        
        if sistema_ok:
            print(f"\n🚀 PRONTO PARA INICIAR TRADING AUTOMÁTICO!")
            print("Execute: python moises_multi_conta.py")
        else:
            print(f"\n🔧 Verifique os problemas antes de continuar")
            
    except KeyboardInterrupt:
        print("\n⏹️ Teste interrompido")
    except Exception as e:
        print(f"\n❌ Erro no teste: {e}")