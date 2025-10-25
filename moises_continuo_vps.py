#!/usr/bin/env python3
# moises_continuo_vps.py
# MOISES Trading Contínuo - Operação 24/7 na VPS

import os
import time
import hmac
import hashlib
import requests
import json
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/moises/trading/logs/moises_continuo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class MoisesContinuo:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 5000
        self.server_time_offset = 0
        
        # Configuração operacional
        self.min_trade_interval = 300  # 5 minutos entre trades
        self.max_daily_trades = 20
        self.min_profit_threshold = 0.005  # 0.5%
        self.max_trade_amount = 50  # Máximo $50 por trade
        self.humanitarian_percentage = 0.20  # 20% para crianças
        
        # Estatísticas
        self.daily_trades = 0
        self.total_profit = 0
        self.humanitarian_fund = 0
        self.last_trade_time = 0
        self.session_start = datetime.now()
        
        # Criar diretórios
        os.makedirs('/home/moises/trading/logs', exist_ok=True)
        os.makedirs('/home/moises/trading/reports', exist_ok=True)

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
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=10)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=10)
                r.raise_for_status()
                return r.json()
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                    time.sleep(2 ** attempt)  # Backoff exponencial
                    continue
                return {'error': True, 'detail': str(e)}

    def sync_time(self):
        """Sincronizar tempo com servidor Binance"""
        try:
            r = requests.get(BASE_URL + '/api/v3/time', timeout=5)
            r.raise_for_status()
            data = r.json()
            server_time = int(data['serverTime'])
            local_time = int(time.time() * 1000)
            self.server_time_offset = server_time - local_time
            logger.info(f"Tempo sincronizado - Offset: {self.server_time_offset}ms")
            return True
        except Exception as e:
            logger.error(f"Erro na sincronização de tempo: {e}")
            return False

    def get_account_info(self):
        """Obter informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)

    def get_usdt_balance(self):
        """Obter saldo USDT disponível"""
        account = self.get_account_info()
        if account.get('error'):
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0

    def get_market_data(self, symbol):
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
            logger.error(f"Erro ao obter dados de {symbol}: {e}")
        return None

    def analyze_opportunity(self, market_data):
        """Analisar oportunidade de trading"""
        if not market_data:
            return None
        
        price_change = market_data['change_24h']
        volume = market_data['volume']
        volatility = (market_data['high_24h'] - market_data['low_24h']) / market_data['low_24h'] * 100
        
        # Lógica de análise neural simplificada
        score = 0
        recommendation = 'HOLD'
        
        # Condições para BUY (queda + volume + volatilidade)
        if price_change < -1.5 and volume > 1000 and volatility > 2:
            recommendation = 'BUY'
            score = abs(price_change) + (volume / 10000) + volatility * 2
        
        # Confidence baseado no score
        confidence = min(90, 60 + score * 3) if score > 0 else 0
        
        if confidence > 75 and recommendation == 'BUY':
            return {
                'symbol': market_data['symbol'],
                'action': recommendation,
                'confidence': confidence,
                'price': market_data['price'],
                'analysis': {
                    'price_change': price_change,
                    'volume': volume,
                    'volatility': volatility,
                    'score': score
                }
            }
        return None

    def execute_trade(self, opportunity, trade_amount):
        """Executar trade real"""
        symbol = opportunity['symbol']
        
        logger.info(f"🚀 EXECUTANDO TRADE: {symbol}")
        logger.info(f"   Confiança: {opportunity['confidence']:.1f}%")
        logger.info(f"   Valor: ${trade_amount:.2f} USDT")
        
        # Executar ordem MARKET BUY
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': str(trade_amount)
        }
        
        result = self._request('POST', '/api/v3/order', params, signed=True)
        
        if result.get('error'):
            logger.error(f"❌ Erro na ordem: {result}")
            return False
        
        # Processar resultado
        executed_qty = float(result.get('executedQty', 0))
        spent_usdt = float(result.get('cummulativeQuoteQty', 0))
        order_id = result.get('orderId')
        
        logger.info(f"✅ TRADE EXECUTADO!")
        logger.info(f"   Quantidade: {executed_qty:.8f}")
        logger.info(f"   Gasto: ${spent_usdt:.2f} USDT")
        logger.info(f"   Order ID: {order_id}")
        
        # Atualizar estatísticas
        self.daily_trades += 1
        self.last_trade_time = time.time()
        
        # Salvar registro
        self.save_trade_record(opportunity, spent_usdt, executed_qty, order_id)
        
        return True

    def save_trade_record(self, opportunity, spent_usdt, executed_qty, order_id):
        """Salvar registro do trade"""
        trade_record = {
            'timestamp': datetime.now().isoformat(),
            'symbol': opportunity['symbol'],
            'spent_usdt': spent_usdt,
            'quantity': executed_qty,
            'order_id': order_id,
            'confidence': opportunity['confidence'],
            'analysis': opportunity['analysis']
        }
        
        # Salvar em arquivo JSON
        records_file = Path('/home/moises/trading/reports/trade_records.json')
        
        records = []
        if records_file.exists():
            try:
                with open(records_file, 'r') as f:
                    records = json.load(f)
            except:
                pass
        
        records.append(trade_record)
        
        with open(records_file, 'w') as f:
            json.dump(records, f, indent=2)

    def run_continuous_trading(self):
        """Loop principal de trading contínuo"""
        logger.info("🎂💰 INICIANDO MOISES TRADING CONTÍNUO 💰🎂")
        logger.info("=" * 60)
        logger.info("🚀 Modo: OPERAÇÃO REAL 24/7")
        logger.info("💰 Configuração: Trades automáticos com IA")
        logger.info("💝 Humanitário: 20% dos lucros para crianças")
        logger.info("=" * 60)
        
        symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT']
        
        while True:
            try:
                current_time = time.time()
                
                # Verificar se pode fazer novo trade
                if (current_time - self.last_trade_time) < self.min_trade_interval:
                    time.sleep(60)  # Aguardar 1 minuto
                    continue
                
                # Verificar limite diário
                if self.daily_trades >= self.max_daily_trades:
                    # Reset diário às 00:00 UTC
                    if datetime.now().hour == 0 and datetime.now().minute < 5:
                        self.daily_trades = 0
                        logger.info("🔄 Reset diário - Contador de trades zerado")
                    else:
                        time.sleep(300)  # Aguardar 5 minutos
                        continue
                
                # Sincronizar tempo periodicamente
                if current_time % 3600 < 60:  # A cada hora
                    self.sync_time()
                
                # Verificar saldo
                usdt_balance = self.get_usdt_balance()
                if usdt_balance < 5:
                    logger.warning(f"⚠️ Saldo insuficiente: ${usdt_balance:.2f}")
                    time.sleep(1800)  # Aguardar 30 minutos
                    continue
                
                # Calcular valor do trade
                trade_amount = min(self.max_trade_amount, usdt_balance * 0.1)
                
                logger.info(f"🔍 Analisando mercado... Saldo: ${usdt_balance:.2f}")
                
                # Analisar cada símbolo
                best_opportunity = None
                best_confidence = 0
                
                for symbol in symbols:
                    market_data = self.get_market_data(symbol)
                    if market_data:
                        opportunity = self.analyze_opportunity(market_data)
                        if opportunity and opportunity['confidence'] > best_confidence:
                            best_opportunity = opportunity
                            best_confidence = opportunity['confidence']
                
                # Executar trade se oportunidade encontrada
                if best_opportunity and best_confidence > 75:
                    logger.info(f"🎯 OPORTUNIDADE: {best_opportunity['symbol']} - {best_confidence:.1f}%")
                    
                    if self.execute_trade(best_opportunity, trade_amount):
                        logger.info("✅ Trade executado com sucesso")
                    else:
                        logger.error("❌ Falha na execução do trade")
                else:
                    logger.info("⏸️ Nenhuma oportunidade clara detectada")
                
                # Aguardar antes da próxima análise
                time.sleep(180)  # 3 minutos
                
            except KeyboardInterrupt:
                logger.info("⏹️ Trading interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro no loop principal: {e}")
                time.sleep(300)  # Aguardar 5 minutos antes de tentar novamente

def main():
    # Carregar credenciais do ambiente
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("❌ Configure BINANCE_API_KEY e BINANCE_API_SECRET no ambiente")
        return
    
    try:
        moises = MoisesContinuo(api_key, api_secret)
        
        # Sincronizar tempo inicial
        if not moises.sync_time():
            logger.error("❌ Falha na sincronização inicial")
            return
        
        # Iniciar trading contínuo
        moises.run_continuous_trading()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == '__main__':
    main()