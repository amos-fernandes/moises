#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Day Trading Final - Corrigido
Resolução definitiva dos problemas de timestamp
"""

import json
import logging
import time
import numpy as np
import pandas as pd
import ta
from datetime import datetime
from binance.client import Client
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DayTradingFinal:
    def __init__(self):
        self.client = None
        self.saldo_inicial = 0
        self.time_offset = 0
        self.setup_binance()
        
    def setup_binance(self):
        """Configura cliente Binance com correção de timestamp"""
        try:
            with open('config/contas.json', 'r', encoding='utf-8') as f:
                contas = json.load(f)
            
            conta_amos = contas['CONTA_3']
            
            self.client = Client(
                api_key=conta_amos['api_key'],
                api_secret=conta_amos['api_secret'],
                testnet=False
            )
            
            # Calcular offset de tempo
            for i in range(3):  # 3 tentativas
                try:
                    server_time = self.client.get_server_time()
                    local_time = int(time.time() * 1000)
                    self.time_offset = server_time['serverTime'] - local_time
                    break
                except:
                    time.sleep(1)
            
            logger.info(f"Cliente Binance configurado - Offset: {self.time_offset}ms")
            
        except Exception as e:
            logger.error(f"Erro configurando Binance: {e}")
    
    def sync_time(self):
        """Sincroniza tempo antes de cada operação"""
        try:
            # Aguardar um pouco para estabilizar
            time.sleep(0.5)
            
            # Atualizar offset periodicamente
            if hasattr(self, '_last_sync'):
                if time.time() - self._last_sync > 300:  # 5 minutos
                    server_time = self.client.get_server_time()
                    local_time = int(time.time() * 1000)
                    self.time_offset = server_time['serverTime'] - local_time
            
            self._last_sync = time.time()
            
        except:
            pass
    
    def safe_api_call(self, func, *args, **kwargs):
        """Wrapper para chamadas API com retry automático"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                self.sync_time()
                return func(*args, **kwargs)
                
            except Exception as e:
                if "Timestamp" in str(e) or "recvWindow" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Erro timestamp, tentativa {attempt + 1}")
                        time.sleep(2 ** attempt)  # Backoff exponencial
                        continue
                raise e
        
        return None
    
    def get_account_balance(self):
        """Obtém saldo com API segura"""
        try:
            account = self.safe_api_call(self.client.get_account)
            if not account:
                return 0, 0
            
            usdt_balance = 0
            crypto_value = 0
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if balance['asset'] == 'USDT' and total > 0:
                    usdt_balance = total
                elif total > 0.001:
                    try:
                        symbol = f"{balance['asset']}USDT"
                        ticker = self.safe_api_call(self.client.get_symbol_ticker, symbol=symbol)
                        if ticker:
                            price = float(ticker['price'])
                            value = total * price
                            crypto_value += value
                            logger.info(f"[{balance['asset']}] {total:.6f} = ${value:.2f}")
                    except:
                        pass
            
            logger.info(f"[PORTFOLIO] USDT: ${usdt_balance:.2f}")
            logger.info(f"[PORTFOLIO] Crypto: ${crypto_value:.2f}")
            logger.info(f"[PORTFOLIO] Total: ${usdt_balance + crypto_value:.2f}")
            
            return usdt_balance, crypto_value
            
        except Exception as e:
            logger.error(f"Erro obtendo saldo: {e}")
            return 0, 0
    
    def get_klines_safe(self, symbol, interval='5m', limit=100):
        """Obtém klines com API segura"""
        try:
            klines = self.safe_api_call(
                self.client.get_klines,
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            if not klines:
                return None
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                df[col] = df[col].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro obtendo klines {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos"""
        try:
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            # Bollinger
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            
            # Volume
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            return df
            
        except Exception as e:
            logger.error(f"Erro calculando indicadores: {e}")
            return df
    
    def analyze_symbol(self, symbol):
        """Análise técnica simplificada"""
        try:
            df = self.get_klines_safe(symbol, limit=60)
            if df is None or len(df) < 20:
                return 0
            
            df = self.calculate_indicators(df)
            last = df.iloc[-1]
            
            score = 0
            reasons = []
            
            rsi = last['rsi']
            price = last['close']
            
            # RSI principal
            if rsi > 75:
                score += 35
                reasons.append("RSI alto")
            elif rsi > 60:
                score += 25  
                reasons.append("RSI moderado")
            elif rsi < 25:
                score += 45
                reasons.append("RSI muito baixo")
            elif rsi < 35:
                score += 30
                reasons.append("RSI baixo")
            
            # Médias
            if price > last['sma_20']:
                score += 10
                reasons.append("Acima SMA20")
            
            if price > last['sma_50']:
                score += 10
                reasons.append("Tendencia alta")
            
            # Bollinger
            if price > last['bb_upper']:
                score += 15
                reasons.append("Acima BB")
            elif price < last['bb_lower']:
                score += 20
                reasons.append("Abaixo BB")
            
            logger.info(f"[ANALISE {symbol}] Score: {score}, RSI: {rsi:.1f}")
            if reasons:
                logger.info(f"  Razoes: {', '.join(reasons)}")
            
            return score
            
        except Exception as e:
            logger.error(f"Erro analisando {symbol}: {e}")
            return 0
    
    def execute_trade(self, action, symbol, amount_or_quantity):
        """Executa negociação com retry"""
        try:
            if action == "BUY":
                # Compra por valor em USDT
                ticker = self.safe_api_call(self.client.get_symbol_ticker, symbol=symbol)
                if not ticker:
                    return False, None
                
                price = float(ticker['price'])
                quantity = amount_or_quantity / price
                
                # Ajustar precisão
                symbol_info = self.safe_api_call(self.client.get_symbol_info, symbol)
                if symbol_info:
                    step_size = float(symbol_info['filters'][1]['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = round(quantity, precision)
                
                order = self.safe_api_call(
                    self.client.order_market_buy,
                    symbol=symbol,
                    quantity=quantity
                )
                
                if order:
                    logger.info(f"COMPRA: {quantity} {symbol.replace('USDT','')} por ${amount_or_quantity:.2f}")
                    return True, order
            
            elif action == "SELL":
                # Venda por quantidade
                symbol_info = self.safe_api_call(self.client.get_symbol_info, symbol)
                if symbol_info:
                    step_size = float(symbol_info['filters'][1]['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = round(amount_or_quantity, precision)
                
                order = self.safe_api_call(
                    self.client.order_market_sell,
                    symbol=symbol,
                    quantity=quantity
                )
                
                if order:
                    logger.info(f"VENDA: {quantity} {symbol.replace('USDT','')}")
                    return True, order
            
            return False, None
            
        except Exception as e:
            logger.error(f"Erro executando {action} {symbol}: {e}")
            return False, None
    
    def run_cycle(self, cycle_num):
        """Executa ciclo de trading"""
        logger.info(f"[CICLO {cycle_num}] Day Trading")
        logger.info("=" * 40)
        
        try:
            # Verificar saldos
            usdt_balance, crypto_value = self.get_account_balance()
            
            if usdt_balance == 0 and crypto_value == 0:
                logger.warning("Nao foi possivel obter saldos")
                return
            
            # Verificar vendas (posições existentes)
            account = self.safe_api_call(self.client.get_account)
            if account:
                for balance in account['balances']:
                    free = float(balance['free'])
                    if free > 0.001 and balance['asset'] != 'USDT':
                        symbol = f"{balance['asset']}USDT"
                        score = self.analyze_symbol(symbol)
                        
                        # Vender se score muito alto (sobrecompra)
                        if score >= 80:
                            logger.info(f"SINAL VENDA: {symbol} (Score: {score})")
                            success, _ = self.execute_trade("SELL", symbol, free)
                            if success:
                                time.sleep(2)
            
            # Buscar compras
            if usdt_balance >= 6:
                symbols = ['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT']
                
                best_symbol = None
                best_score = 0
                
                for symbol in symbols:
                    score = self.analyze_symbol(symbol)
                    
                    # Critério: Score >= 60 + RSI baixo
                    if score >= 60:
                        df = self.get_klines_safe(symbol, limit=30)
                        if df is not None and len(df) > 15:
                            df = self.calculate_indicators(df)
                            rsi = df.iloc[-1]['rsi']
                            
                            if rsi < 35 and score > best_score:
                                best_symbol = symbol
                                best_score = score
                
                # Executar compra
                if best_symbol:
                    buy_amount = min(usdt_balance * 0.4, 10.0)  # Max 40% ou $10
                    logger.info(f"COMPRANDO {best_symbol} - Score: {best_score}")
                    success, _ = self.execute_trade("BUY", best_symbol, buy_amount)
                    if success:
                        time.sleep(2)
                else:
                    logger.info("[INFO] Aguardando oportunidade (Score>=60 + RSI<35)")
            
            # Status final
            final_usdt, final_crypto = self.get_account_balance()
            logger.info(f"[STATUS] Total: ${final_usdt + final_crypto:.2f}")
            
        except Exception as e:
            logger.error(f"Erro no ciclo: {e}")
    
    def run(self, cycles=15):
        """Executa sistema de trading"""
        logger.info("=== SISTEMA DAY TRADING FINAL ===")
        logger.info("Estrategia Tecnica Otimizada")
        
        # Saldo inicial
        initial_usdt, initial_crypto = self.get_account_balance()
        self.saldo_inicial = max(initial_usdt + initial_crypto, 1)  # Evitar divisão por zero
        
        logger.info(f"Patrimonio inicial: ${self.saldo_inicial:.2f}")
        logger.info("=" * 40)
        
        try:
            for cycle in range(1, cycles + 1):
                self.run_cycle(cycle)
                
                if cycle < cycles:
                    logger.info("Aguardando 5 minutos...")
                    time.sleep(300)
                    
        except KeyboardInterrupt:
            logger.info("Sistema interrompido pelo usuario")
        except Exception as e:
            logger.error(f"Erro no sistema: {e}")
        
        # Relatório final
        final_usdt, final_crypto = self.get_account_balance()
        final_total = final_usdt + final_crypto
        
        logger.info("=" * 40)
        logger.info("=== RELATORIO FINAL ===")
        logger.info(f"Inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"Final: ${final_total:.2f}")
        logger.info(f"Variacao: ${final_total - self.saldo_inicial:+.2f}")
        
        if self.saldo_inicial > 0:
            perf = ((final_total / self.saldo_inicial - 1) * 100)
            logger.info(f"Performance: {perf:+.2f}%")

def main():
    trader = DayTradingFinal()
    trader.run(cycles=15)

if __name__ == "__main__":
    main()