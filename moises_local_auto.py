#!/usr/bin/env python3
# moises_local_auto.py
# MOISES Trading Real - Execução Automatizada Local

import os
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

BASE_URL = "https://api.binance.com"

class MoisesAutomatizado:
    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must be provided")
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 5000
        self.server_time_offset = 0
        self.trades_executed = 0
        self.initial_balance = 0
        self.current_balance = 0

    def _request(self, method, path, params, signed: bool):
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = int(time.time() * 1000) + int(self.server_time_offset)
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        try:
            if method == 'GET':
                r = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': True, 'detail': str(e)}

    def sync_time(self):
        """Sincroniza o offset entre o servidor Binance e o relógio local"""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            return True
        except Exception as e:
            print(f"❌ Erro na sincronização: {e}")
            return False

    def get_account(self):
        return self._request('GET', '/api/v3/account', {}, signed=True)

    def place_market_buy(self, symbol: str, quote_qty: float):
        params = {
            'symbol': symbol, 
            'side': 'BUY', 
            'type': 'MARKET', 
            'quoteOrderQty': str(quote_qty)
        }
        return self._request('POST', '/api/v3/order', params, signed=True)

    def get_symbol_price(self, symbol: str):
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5)
            return float(r.json()['price'])
        except:
            return 0

    def run_automated_session(self):
        print("🎂💰 MOISES TRADING REAL - SESSÃO AUTOMATIZADA 💰🎂")
        print("=" * 60)
        
        # 1. Sincronizar tempo
        print("⏰ Sincronizando horário com Binance...")
        if not self.sync_time():
            return
        print(f"✅ Offset sincronizado: {self.server_time_offset}ms")

        # 2. Obter saldo
        print("\n💰 Obtendo saldo da conta...")
        account = self.get_account()
        if account.get('error'):
            print(f"❌ Erro na conta: {account}")
            return

        # Encontrar saldo USDT
        usdt_balance = 0
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                usdt_balance = float(balance['free'])
                break

        self.initial_balance = usdt_balance
        self.current_balance = usdt_balance
        
        print(f"💵 Saldo USDT disponível: ${usdt_balance:.2f}")
        
        if usdt_balance < 5:
            print("⚠️ Saldo insuficiente para trading (mínimo $5)")
            return

        # 3. Configuração do trading
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        trade_amount = max(5.0, usdt_balance * 0.5)  # 50% do saldo, mínimo $5
        max_trades = 1  # Um trade apenas para teste
        
        print(f"\n🎯 Configuração da sessão:")
        print(f"   💰 Valor por trade: ${trade_amount:.2f} USDT")
        print(f"   🎯 Máximo de trades: {max_trades}")
        print(f"   📊 Pares: {', '.join(symbols)}")
        print(f"   ✅ AUTORIZADO para operações reais")

        # 4. Executar trades automatizados
        for i in range(max_trades):
            try:
                symbol = symbols[i % len(symbols)]
                current_price = self.get_symbol_price(symbol)
                
                if current_price == 0:
                    print(f"❌ Erro ao obter preço do {symbol}")
                    continue

                print(f"\n🚀 TRADE #{i+1} - {symbol}")
                print(f"   💰 Preço atual: ${current_price:,.2f}")
                print(f"   💵 Investindo: ${trade_amount:.2f} USDT")
                
                # Executar ordem
                result = self.place_market_buy(symbol, trade_amount)
                
                if result.get('error'):
                    print(f"   ❌ Erro na ordem: {result}")
                    continue
                
                # Processar resultado
                executed_qty = float(result.get('executedQty', 0))
                spent_usdt = float(result.get('cummulativeQuoteQty', 0))
                
                print(f"   ✅ ORDEM EXECUTADA!")
                print(f"   📊 Quantidade: {executed_qty:.8f} {symbol[:3]}")
                print(f"   💸 Gasto real: ${spent_usdt:.2f} USDT")
                print(f"   🆔 Order ID: {result.get('orderId')}")
                
                self.trades_executed += 1
                self.current_balance -= spent_usdt
                
                # Pausa entre trades
                if i < max_trades - 1:
                    print("   ⏳ Aguardando 10 segundos...")
                    time.sleep(10)
                    
            except Exception as e:
                print(f"   ❌ Erro no trade: {e}")
                continue

        # 5. Relatório final
        self.generate_report()

    def generate_report(self):
        """Gera relatório final da sessão"""
        total_spent = self.initial_balance - self.current_balance
        
        print(f"\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL - MOISES AUTOMATIZADO")
        print("=" * 60)
        print(f"🎯 Trades executados: {self.trades_executed}/3")
        print(f"💰 Saldo inicial: ${self.initial_balance:.2f} USDT")
        print(f"💸 Total investido: ${total_spent:.2f} USDT")
        print(f"💵 Saldo restante: ${self.current_balance:.2f} USDT")
        print(f"📈 Posições abertas em criptomoedas")
        print(f"⏰ Sessão: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)
        print("🎂 MOISES operando com fundos reais - SUCESSO! 🎂")
        print("💝 Próximo: configurar % para crianças necessitadas")

def load_env_file(path='.env'):
    """Carrega variáveis do arquivo .env"""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, 'r', encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith('#'):
                continue
            if '=' not in ln:
                continue
            k, v = ln.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

def main():
    # Carregar credenciais
    env = load_env_file('.env')
    api_key = os.getenv('BINANCE_API_KEY') or env.get('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET') or env.get('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print('❌ Configure BINANCE_API_KEY e BINANCE_API_SECRET')
        return

    try:
        moises = MoisesAutomatizado(api_key, api_secret)
        moises.run_automated_session()
    except KeyboardInterrupt:
        print("\n⏹️ Sessão interrompida pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro na execução: {e}")

if __name__ == '__main__':
    main()