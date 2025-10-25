#!/usr/bin/env python3
# trading_real_vps.py
# Cliente Binance minimal para VPS com sincronização de hora e execução real (com confirmação)

import os
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime

BASE_URL = "https://api.binance.com"

class MinimalBinanceClient:
    def __init__(self, api_key: str, api_secret: str, recv_window: int = 5000):
        if not api_key or not api_secret:
            raise ValueError("API key and secret must be provided")
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = recv_window
        self.server_time_offset = 0  # ms

    def _get(self, path, params=None, signed=False):
        return self._request('GET', path, params or {}, signed)

    def _post(self, path, params=None, signed=False):
        return self._request('POST', path, params or {}, signed)

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
        except requests.exceptions.HTTPError as e:
            # try to parse error
            try:
                err = r.json()
            except Exception:
                err = {'msg': str(e)}
            return {'error': True, 'http_status': r.status_code if 'r' in locals() else None, 'detail': err}
        except Exception as e:
            return {'error': True, 'detail': str(e)}

    def sync_time(self):
        """Sincroniza o offset entre o servidor Binance e o relógio local (em ms)."""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            return {'server_time': server_time, 'local_time': local_time, 'offset_ms': self.server_time_offset}
        except Exception as e:
            return {'error': True, 'detail': str(e)}

    def account(self):
        return self._get('/api/v3/account', signed=True)

    def place_market_buy_quote(self, symbol: str, quote_order_qty: float):
        """Faz uma ordem MARKET BUY usando `quoteOrderQty` para gastar X USDT (quote asset).
        Ex: quote_order_qty=10 (gasta 10 USDT para comprar BTC).
        """
        params = {'symbol': symbol, 'side': 'BUY', 'type': 'MARKET', 'quoteOrderQty': str(quote_order_qty)}
        return self._post('/api/v3/order', params=params, signed=True)

    def place_market_sell(self, symbol: str, quantity: float):
        params = {'symbol': symbol, 'side': 'SELL', 'type': 'MARKET', 'quantity': str(quantity)}
        return self._post('/api/v3/order', params=params, signed=True)


def load_env_file(path='.env'):
    """Carrega pares KEY=VALUE de um arquivo .env simples (não exporta para OS).
    Preferível setar as variáveis no ambiente da VPS.
    """
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


def human_money(x):
    try:
        return f"${float(x):,.2f}"
    except Exception:
        return str(x)


def main():
    # Carregar credenciais preferencialmente das variáveis de ambiente
    env = load_env_file('.env')
    api_key = os.getenv('BINANCE_API_KEY') or env.get('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET') or env.get('BINANCE_API_SECRET')

    if not api_key or not api_secret:
        print('ERRO: Configure BINANCE_API_KEY e BINANCE_API_SECRET no ambiente ou em .env')
        return

    client = MinimalBinanceClient(api_key, api_secret)

    print('1) Sincronizando hora com Binance...')
    sync = client.sync_time()
    if sync.get('error'):
        print('Falha ao sincronizar hora:', sync)
        return
    print('Offset (ms):', sync['offset_ms'])

    print('\n2) Solicitando informações da conta...')
    acc = client.account()
    if acc.get('error'):
        print('Erro na requisição de conta:', acc)
        # Se for timestamp error, tentar reaplicar sync e refazer
        detail = acc.get('detail')
        if isinstance(detail, dict) and detail.get('code') == -1021:
            print('Erro -1021 detectado, reverificando tempo e tentando novamente...')
            client.sync_time()
            acc = client.account()
            print('Tentativa nova:', acc if 'error' in acc else 'Conta obtida com sucesso')
        else:
            return

    # Mostrar saldo USDT
    balances = acc.get('balances', [])
    usdt_bal = 0.0
    for b in balances:
        if b.get('asset') == 'USDT':
            usdt_bal = float(b.get('free', 0)) + float(b.get('locked', 0))
            break
    print('Saldo USDT disponível:', human_money(usdt_bal))

    # Confirmação do usuário para ações reais
    print('\nATENÇÃO: você autorizou operações reais. Este script fará ORDENS de mercado reais na sua conta.')
    ans = input('Confirmar execução REAL agora? (s/n): ').strip().lower()
    if ans not in ('s', 'sim', 'y', 'yes'):
        print('Execução cancelada pelo usuário (modo seguro).')
        return

    # Exemplo de operação: gastar 10 USDT comprando BTCUSDT via quoteOrderQty
    symbol = input('Par a negociar (ex: BTCUSDT) [padrão BTCUSDT]: ').strip().upper() or 'BTCUSDT'
    amount_str = input('Valor em USDT a gastar (quoteOrderQty) [padrão 10]: ').strip() or '10'
    try:
        amount = float(amount_str)
    except Exception:
        print('Valor inválido')
        return

    print(f'Enviando ordem MARKET BUY {symbol} usando quoteOrderQty={amount} USDT...')
    res = client.place_market_buy_quote(symbol, amount)
    if res.get('error'):
        print('Erro ao criar ordem:', res)
        # tratar timestamp novamente
        detail = res.get('detail')
        if isinstance(detail, dict) and detail.get('code') == -1021:
            print('Erro -1021 detectado ao enviar ordem, sincronizando tempo e tentando novamente...')
            client.sync_time()
            res = client.place_market_buy_quote(symbol, amount)
            print('Resultado da nova tentativa:', res)
        return

    print('Ordem enviada com sucesso!')
    print(res)


if __name__ == '__main__':
    main()
