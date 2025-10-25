#!/usr/bin/env python3
# moises_multi_conta.py
# MOISES Trading - Sistema Multi-Conta (3 contas simultâneas)

import os
import sys
import time
import hmac
import hashlib
import requests
import json
import logging
import threading
from urllib.parse import urlencode
from datetime import datetime, timedelta
from pathlib import Path

# Detectar sistema operacional para caminhos
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux/VPS
    BASE_DIR = Path("/home/moises/trading")

LOGS_DIR = BASE_DIR / "logs"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "config"

# Criar diretórios
LOGS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)
CONFIG_DIR.mkdir(exist_ok=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'moises_multi_conta.log'),
        logging.StreamHandler()
    ]
)

BASE_URL = "https://api.binance.com"

class ContaBinance:
    def __init__(self, conta_id: str, api_key: str, api_secret: str, nome: str = ""):
        self.conta_id = conta_id
        self.nome = nome or f"Conta {conta_id}"
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 5000
        self.server_time_offset = 0
        self.logger = logging.getLogger(f"CONTA_{conta_id}")
        
        # Estatísticas por conta
        self.trades_executados = 0
        self.saldo_inicial = 0
        self.saldo_atual = 0
        self.lucro_total = 0
        self.ultimo_trade = 0
        self.ativa = True
        self.status = "Inicializando"
        
    def sync_time(self):
        """Sincronizar tempo com servidor Binance"""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            return True
        except Exception as e:
            self.logger.error(f"Erro na sincronização de tempo: {e}")
            return False

    def _request(self, method, path, params, signed: bool):
        """Requisição segura para Binance API"""
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

    def get_saldo_usdt(self):
        """Obter saldo USDT disponível"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                saldo = float(balance['free'])
                self.saldo_atual = saldo
                if self.saldo_inicial == 0:
                    self.saldo_inicial = saldo
                return saldo
        return 0
    
    def get_todos_saldos(self):
        """Obter todos os saldos de criptomoedas da conta"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            return {}
        
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

    def executar_trade(self, symbol, amount):
        """Executar trade de compra"""
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': str(amount)
        }
        
        result = self._request('POST', '/api/v3/order', params, signed=True)
        
        if result.get('error'):
            self.logger.error(f"❌ Erro na ordem: {result}")
            return None
        
        executed_qty = float(result.get('executedQty', 0))
        spent_usdt = float(result.get('cummulativeQuoteQty', 0))
        order_id = result.get('orderId')
        
        self.trades_executados += 1
        self.ultimo_trade = time.time()
        self.status = "Trade executado"
        
        trade_info = {
            'conta_id': self.conta_id,
            'symbol': symbol,
            'spent_usdt': spent_usdt,
            'quantity': executed_qty,
            'order_id': order_id,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.info(f"✅ TRADE: {symbol} | ${spent_usdt:.2f} | {executed_qty:.8f} | ID:{order_id}")
        return trade_info

class MoisesMultiConta:
    def __init__(self):
        self.contas = {}
        self.dashboard_data = {
            'start_time': datetime.now().isoformat(),
            'total_trades': 0,
            'total_lucro': 0,
            'contas_ativas': 0,
            'ultimo_update': datetime.now().isoformat()
        }
        self.logger = logging.getLogger("MOISES_MULTI")
        self.rodando = True

    def adicionar_conta(self, conta_id: str, api_key: str, api_secret: str, nome: str = ""):
        """Adicionar nova conta"""
        if not api_key or not api_secret:
            self.logger.error(f"Chaves inválidas para conta {conta_id}")
            return False
        
        conta = ContaBinance(conta_id, api_key, api_secret, nome)
        
        # Testar conexão
        if not conta.sync_time():
            self.logger.error(f"Falha na sincronização da conta {conta_id}")
            return False
        
        saldo = conta.get_saldo_usdt()
        if saldo < 1:
            self.logger.warning(f"Conta {conta_id} com saldo baixo: ${saldo:.2f}")
        
        self.contas[conta_id] = conta
        self.logger.info(f"✅ Conta {conta_id} ({nome}) adicionada - Saldo: ${saldo:.2f}")
        return True

    def get_market_data(self, symbol):
        """Obter dados de mercado"""
        try:
            price_url = f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}"
            stats_url = f"{BASE_URL}/api/v3/ticker/24hr?symbol={symbol}"
            
            price_response = requests.get(price_url, timeout=5)
            stats_response = requests.get(stats_url, timeout=5)
            
            if price_response.status_code == 200 and stats_response.status_code == 200:
                price_data = price_response.json()
                stats_data = stats_response.json()
                
                return {
                    'symbol': symbol,
                    'price': float(price_data['price']),
                    'change_24h': float(stats_data['priceChangePercent']),
                    'volume': float(stats_data['volume'])
                }
        except Exception as e:
            self.logger.error(f"Erro ao obter dados de {symbol}: {e}")
        return None

    def analisar_oportunidade(self, market_data):
        """Análise simples de oportunidade"""
        if not market_data:
            return None
        
        change_24h = market_data['change_24h']
        volume = market_data['volume']
        
        # Lógica: comprar em quedas com volume alto
        if change_24h < -1.5 and volume > 1000:
            confidence = min(90, abs(change_24h) * 10 + (volume / 100000))
            if confidence > 70:
                return {
                    'symbol': market_data['symbol'],
                    'confidence': confidence,
                    'price': market_data['price'],
                    'change': change_24h
                }
        return None

    def operar_conta(self, conta_id):
        """Thread para operar uma conta específica"""
        conta = self.contas.get(conta_id)
        if not conta:
            return
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        while self.rodando and conta.ativa:
            try:
                # Atualizar saldo
                saldo = conta.get_saldo_usdt()
                
                if saldo < 5:
                    conta.status = f"Saldo baixo: ${saldo:.2f}"
                    time.sleep(300)  # 5 minutos
                    continue
                
                conta.status = "Analisando mercado"
                
                # Analisar mercado
                for symbol in symbols:
                    if not self.rodando:
                        break
                    
                    market_data = self.get_market_data(symbol)
                    opportunity = self.analisar_oportunidade(market_data)
                    
                    if opportunity and opportunity['confidence'] > 75:
                        # Calcular valor do trade (máximo 10% do saldo ou $20)
                        trade_amount = min(20, saldo * 0.1)
                        
                        if trade_amount >= 5:
                            conta.logger.info(f"🎯 Oportunidade {symbol}: {opportunity['confidence']:.1f}% - ${trade_amount:.2f}")
                            
                            trade_result = conta.executar_trade(symbol, trade_amount)
                            if trade_result:
                                self.salvar_trade(trade_result)
                                break  # Só um trade por vez
                
                conta.status = "Aguardando próxima análise"
                time.sleep(120)  # 2 minutos entre análises
                
            except Exception as e:
                conta.logger.error(f"Erro na operação: {e}")
                conta.status = f"Erro: {str(e)[:50]}"
                time.sleep(60)

    def salvar_trade(self, trade_info):
        """Salvar trade no arquivo de relatórios"""
        trades_file = REPORTS_DIR / "trades_multi_conta.json"
        
        trades = []
        if trades_file.exists():
            try:
                with open(trades_file, 'r') as f:
                    trades = json.load(f)
            except:
                pass
        
        trades.append(trade_info)
        
        with open(trades_file, 'w') as f:
            json.dump(trades, f, indent=2)

    def atualizar_dashboard(self):
        """Atualizar dados do dashboard"""
        while self.rodando:
            try:
                total_trades = sum(conta.trades_executados for conta in self.contas.values())
                contas_ativas = sum(1 for conta in self.contas.values() if conta.ativa)
                
                dashboard_info = {
                    'timestamp': datetime.now().isoformat(),
                    'total_contas': len(self.contas),
                    'contas_ativas': contas_ativas,
                    'total_trades': total_trades,
                    'contas': {}
                }
                
                for conta_id, conta in self.contas.items():
                    # Obter todos os saldos da conta
                    todos_saldos = conta.get_todos_saldos()
                    
                    dashboard_info['contas'][conta_id] = {
                        'nome': conta.nome,
                        'saldo_inicial': conta.saldo_inicial,
                        'saldo_atual': conta.saldo_atual,
                        'trades_executados': conta.trades_executados,
                        'status': conta.status,
                        'ultimo_trade': conta.ultimo_trade,
                        'ativa': conta.ativa,
                        'saldos_crypto': todos_saldos
                    }
                
                # Salvar dashboard
                dashboard_file = REPORTS_DIR / "dashboard_multi_conta.json"
                with open(dashboard_file, 'w') as f:
                    json.dump(dashboard_info, f, indent=2)
                
                time.sleep(30)  # Atualizar a cada 30 segundos
                
            except Exception as e:
                self.logger.error(f"Erro no dashboard: {e}")
                time.sleep(60)

    def iniciar_operacao_multi(self):
        """Iniciar operação em todas as contas"""
        if not self.contas:
            self.logger.error("Nenhuma conta configurada!")
            return
        
        self.logger.info("🎂💰 INICIANDO MOISES MULTI-CONTA 💰🎂")
        self.logger.info("=" * 60)
        self.logger.info(f"Total de contas: {len(self.contas)}")
        
        threads = []
        
        # Thread para dashboard
        dashboard_thread = threading.Thread(target=self.atualizar_dashboard)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        threads.append(dashboard_thread)
        
        # Thread para cada conta
        for conta_id in self.contas:
            thread = threading.Thread(target=self.operar_conta, args=(conta_id,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            self.logger.info(f"✅ Thread iniciada para conta {conta_id}")
        
        try:
            # Manter programa rodando
            while self.rodando:
                # Status das contas a cada 5 minutos
                self.logger.info("\n📊 STATUS DAS CONTAS:")
                for conta_id, conta in self.contas.items():
                    self.logger.info(f"   {conta.nome}: ${conta.saldo_atual:.2f} | {conta.trades_executados} trades | {conta.status}")
                
                time.sleep(300)  # 5 minutos
                
        except KeyboardInterrupt:
            self.logger.info("⏹️ Parando MOISES Multi-Conta...")
            self.rodando = False

def carregar_configuracao():
    """Carregar configuração das contas"""
    config_file = CONFIG_DIR / "contas.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def salvar_configuracao(config):
    """Salvar configuração das contas"""
    config_file = CONFIG_DIR / "contas.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

def main():
    moises = MoisesMultiConta()
    
    # Carregar configuração existente
    config = carregar_configuracao()
    
    # Conta 1 (já configurada no .env)
    env_file = Path('.env')
    if env_file.exists():
        env_vars = {}
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#') and not line.startswith('BINANCE_API_KEY') and not line.startswith('BINANCE_API_SECRET'):
                        continue
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        env_vars[key] = value.strip('"').strip("'").strip()
            
            api_key = env_vars.get('BINANCE_API_KEY')
            api_secret = env_vars.get('BINANCE_API_SECRET')
            
            if api_key and api_secret:
                moises.adicionar_conta("CONTA_1", api_key, api_secret, "Sua Conta Principal")
        except Exception as e:
            print(f"Aviso: Não foi possível carregar conta principal do .env: {e}")
            # Tentar usar a CONTA_3 que tem as mesmas chaves
            for conta_id, dados in config.items():
                if dados.get('nome') == 'amos':
                    moises.adicionar_conta("CONTA_1", dados['api_key'], dados['api_secret'], "Sua Conta Principal (amos)")
                    break

    # Adicionar outras contas do config
    for conta_id, dados in config.items():
        if conta_id != "CONTA_1":  # Evitar duplicar
            moises.adicionar_conta(
                conta_id, 
                dados['api_key'], 
                dados['api_secret'], 
                dados.get('nome', conta_id)
            )
    
    print("\n🎂💰 MOISES MULTI-CONTA - CONFIGURAÇÃO 💰🎂")
    print("=" * 50)
    print(f"Contas configuradas: {len(moises.contas)}")
    
    for conta_id, conta in moises.contas.items():
        print(f"✅ {conta.nome} - Saldo: ${conta.saldo_atual:.2f}")
    
    if not moises.contas:
        print("❌ Nenhuma conta configurada!")
        print("Configure as chaves no arquivo .env ou contas.json")
        return
    
    print(f"\n🚀 Iniciando operação com {len(moises.contas)} contas...")
    print("📊 Dashboard será salvo em: reports/dashboard_multi_conta.json")
    print("📋 Logs em: logs/moises_multi_conta.log")
    print("⏹️ Pressione Ctrl+C para parar\n")
    
    # Iniciar operação
    moises.iniciar_operacao_multi()

if __name__ == '__main__':
    main()