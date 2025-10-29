"""
SISTEMA DAY TRADING - VERSAO DEFINITIVA
Solucao completa para timestamp + compatibilidade Windows
Autorizado para CONTA_3 (Amos) - $1.00 disponivel
"""

import json
import time
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests
import os
import sys

# Configuracao de logging compativel com Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_definitivo.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TimestampManager:
    """Gerenciador de timestamp para Binance"""
    
    def __init__(self):
        self.offset = 0
        self.last_sync = 0
    
    def get_server_time(self):
        """Obtem tempo do servidor Binance"""
        try:
            response = requests.get('https://api.binance.com/api/v3/time', timeout=5)
            if response.status_code == 200:
                return response.json()['serverTime']
        except:
            pass
        return None
    
    def sync(self):
        """Sincroniza com servidor"""
        try:
            server_time = self.get_server_time()
            if server_time:
                local_time = int(time.time() * 1000)
                self.offset = server_time - local_time
                self.last_sync = time.time()
                logger.info(f"Sync OK - Offset: {self.offset}ms")
                return True
        except Exception as e:
            logger.error(f"Erro sync: {e}")
        return False
    
    def should_resync(self):
        """Verifica se precisa ressincronizar"""
        return (time.time() - self.last_sync) > 30
    
    def get_timestamp(self):
        """Timestamp corrigido"""
        if self.should_resync():
            self.sync()
        return int(time.time() * 1000) + self.offset

class BinanceClientRobust:
    """Cliente Binance ultra-robusto"""
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timestamp_manager = TimestampManager()
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Inicializa cliente"""
        try:
            # Sincronizar primeiro
            if not self.timestamp_manager.sync():
                logger.error("Falha sync inicial")
                return False
            
            # Aguardar estabilizar
            time.sleep(2)
            
            # Criar cliente
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=False
            )
            
            logger.info("Cliente inicializado")
            return True
            
        except Exception as e:
            logger.error(f"Erro init cliente: {e}")
            return False
    
    def _execute_safe(self, func, *args, **kwargs):
        """Executa funcao com protecao total"""
        max_attempts = 8
        
        for attempt in range(max_attempts):
            try:
                # Aguardar progressivamente
                if attempt > 0:
                    wait = min(2 ** attempt, 15)
                    logger.info(f"Aguardando {wait}s (tentativa {attempt + 1})")
                    time.sleep(wait)
                    
                    # Ressincronizar
                    self.timestamp_manager.sync()
                    time.sleep(1)
                
                # Executar
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Sucesso tentativa {attempt + 1}")
                
                return result
                
            except BinanceAPIException as e:
                if e.code in [-1021, -1022]:
                    logger.warning(f"Erro {e.code} tentativa {attempt + 1}")
                    if attempt < max_attempts - 1:
                        continue
                raise e
            except Exception as e:
                if "timestamp" in str(e).lower():
                    if attempt < max_attempts - 1:
                        continue
                raise e
        
        raise Exception(f"Falha apos {max_attempts} tentativas")
    
    def get_account(self):
        return self._execute_safe(self.client.get_account)
    
    def get_symbol_ticker(self, symbol):
        return self._execute_safe(self.client.get_symbol_ticker, symbol=symbol)
    
    def get_klines(self, symbol, interval, limit=50):
        return self._execute_safe(self.client.get_klines, symbol=symbol, interval=interval, limit=limit)
    
    def order_market_buy(self, symbol, quoteOrderQty):
        return self._execute_safe(self.client.order_market_buy, symbol=symbol, quoteOrderQty=quoteOrderQty)
    
    def order_market_sell(self, symbol, quantity):
        return self._execute_safe(self.client.order_market_sell, symbol=symbol, quantity=quantity)

class TradingSystem:
    """Sistema de Trading Definitivo"""
    
    def __init__(self):
        self.client = None
        self.balance = 1.0
        self.positions = {}
        self._setup()
    
    def _setup(self):
        """Setup inicial"""
        try:
            # Carregar credenciais
            with open('config/contas.json', 'r') as f:
                contas = json.load(f)
            
            conta = contas['CONTA_3']
            
            # Criar cliente
            self.client = BinanceClientRobust(
                api_key=conta['api_key'],
                api_secret=conta['api_secret']
            )
            
            logger.info("Sistema configurado")
            
        except Exception as e:
            logger.error(f"Erro setup: {e}")
            sys.exit(1)
    
    def calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        try:
            prices = pd.Series(prices)
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
        except:
            return 50
    
    def get_indicators(self, symbol):
        """Obtem indicadores"""
        try:
            klines = self.client.get_klines(symbol=symbol, interval='5m', limit=30)
            
            closes = [float(k[4]) for k in klines]
            
            current_price = closes[-1]
            rsi = self.calculate_rsi(closes)
            sma_20 = np.mean(closes[-20:]) if len(closes) >= 20 else current_price
            
            return {
                'price': current_price,
                'rsi': rsi,
                'sma_20': sma_20
            }
            
        except Exception as e:
            logger.error(f"Erro indicadores {symbol}: {e}")
            return None
    
    def analyze_signal(self, symbol):
        """Analisa sinais"""
        try:
            indicators = self.get_indicators(symbol)
            if not indicators:
                return 'HOLD', 0
            
            price = indicators['price']
            rsi = indicators['rsi']
            sma_20 = indicators['sma_20']
            
            # Sinal COMPRA
            if rsi < 30 and price < sma_20:
                confidence = (30 - rsi) * 2
                logger.info(f"COMPRA {symbol}: RSI={rsi:.1f}, Price={price:.6f}")
                return 'BUY', confidence
            
            # Sinal VENDA  
            elif rsi > 70 and price > sma_20:
                confidence = (rsi - 70) * 2
                logger.info(f"VENDA {symbol}: RSI={rsi:.1f}, Price={price:.6f}")
                return 'SELL', confidence
            
            return 'HOLD', 0
            
        except Exception as e:
            logger.error(f"Erro analise {symbol}: {e}")
            return 'HOLD', 0
    
    def execute_buy(self, symbol, amount):
        """Executa compra"""
        try:
            logger.info(f"Comprando {symbol} - ${amount:.2f}")
            
            order = self.client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=amount
            )
            
            qty = float(order['executedQty'])
            price = float(order['fills'][0]['price'])
            
            self.positions[symbol] = {
                'qty': qty,
                'price': price,
                'time': time.time()
            }
            
            logger.info(f"Compra OK: {qty:.6f} {symbol} @ ${price:.6f}")
            return True
            
        except Exception as e:
            logger.error(f"Erro compra {symbol}: {e}")
            return False
    
    def execute_sell(self, symbol):
        """Executa venda"""
        try:
            if symbol not in self.positions:
                return False
            
            qty = self.positions[symbol]['qty']
            buy_price = self.positions[symbol]['price']
            
            logger.info(f"Vendendo {symbol} - {qty:.6f}")
            
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=qty
            )
            
            sell_price = float(order['fills'][0]['price'])
            pnl = ((sell_price - buy_price) / buy_price) * 100
            
            logger.info(f"Venda OK: {qty:.6f} {symbol} @ ${sell_price:.6f}")
            logger.info(f"PnL: {pnl:+.2f}%")
            
            del self.positions[symbol]
            return True
            
        except Exception as e:
            logger.error(f"Erro venda {symbol}: {e}")
            return False
    
    def get_balance(self):
        """Obtem saldo"""
        try:
            account = self.client.get_account()
            
            total = 0
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                
                if free > 0:
                    if asset == 'USDT':
                        total += free
                    else:
                        try:
                            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
                            price = float(ticker['price'])
                            total += free * price
                        except:
                            pass
            
            self.balance = total
            return total
            
        except Exception as e:
            logger.error(f"Erro saldo: {e}")
            return self.balance
    
    def trading_cycle(self, cycle):
        """Ciclo de trading"""
        logger.info(f"=== CICLO {cycle} ===")
        
        try:
            # Obter saldo
            balance = self.get_balance()
            logger.info(f"Saldo: ${balance:.2f}")
            
            # Simbolos para analisar
            symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT']
            
            # Verificar vendas
            for symbol in list(self.positions.keys()):
                signal, confidence = self.analyze_signal(symbol)
                if signal == 'SELL' and confidence > 20:
                    self.execute_sell(symbol)
            
            # Procurar compras
            if balance > 0.5:
                best_symbol = None
                best_confidence = 0
                
                for symbol in symbols:
                    signal, confidence = self.analyze_signal(symbol)
                    
                    if signal == 'BUY' and confidence > best_confidence and confidence > 25:
                        best_symbol = symbol
                        best_confidence = confidence
                
                if best_symbol:
                    amount = min(balance * 0.8, 0.9)
                    self.execute_buy(best_symbol, amount)
            
        except Exception as e:
            logger.error(f"Erro ciclo {cycle}: {e}")
    
    def run(self, cycles=10):
        """Executa sistema"""
        logger.info("=== SISTEMA DAY TRADING DEFINITIVO ===")
        logger.info("Estrategia: RSI + SMA")
        logger.info("Conta: CONTA_3 (Amos)")
        logger.info("=" * 50)
        
        # Saldo inicial
        initial_balance = self.get_balance()
        logger.info(f"Saldo inicial: ${initial_balance:.2f}")
        logger.info("Iniciando operacoes...")
        logger.info("=" * 50)
        
        for cycle in range(1, cycles + 1):
            try:
                self.trading_cycle(cycle)
                
                if cycle < cycles:
                    logger.info("Aguardando proximo ciclo (5min)...")
                    time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Sistema interrompido")
                break
            except Exception as e:
                logger.error(f"Erro fatal ciclo {cycle}: {e}")
                time.sleep(60)
        
        # Relatorio final
        final_balance = self.get_balance()
        pnl = ((final_balance - initial_balance) / initial_balance) * 100
        
        logger.info("=" * 50)
        logger.info("RELATORIO FINAL")
        logger.info(f"Saldo inicial: ${initial_balance:.2f}")
        logger.info(f"Saldo final: ${final_balance:.2f}")
        logger.info(f"Resultado: {pnl:+.2f}%")
        logger.info("=" * 50)

def main():
    """Funcao principal"""
    try:
        logger.info("Inicializando sistema...")
        system = TradingSystem()
        system.run(cycles=8)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()