#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Day Trading Simples - Sem Problemas de Timestamp
Volta ao básico: Trading simples e eficaz
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from binance.client import Client
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SimpleDayTrader:
    def __init__(self):
        self.client = None
        self.saldo_inicial = 0
        self.time_offset = 0
        self.setup_client()
    
    def setup_client(self):
        """Setup do cliente Binance com sincronização"""
        try:
            with open('config/contas.json', 'r', encoding='utf-8') as f:
                contas = json.load(f)
            
            conta = contas['CONTA_3']  # Amos
            
            self.client = Client(
                api_key=conta['api_key'],
                api_secret=conta['api_secret'],
                testnet=False
            )
            
            # Sincronizar tempo inicial
            self.sync_time()
            
            logger.info("Cliente Binance configurado com sincronização")
            
        except Exception as e:
            logger.error(f"Erro configurando cliente: {e}")
            raise
    
    def sync_time(self):
        """Sincroniza tempo com servidor Binance"""
        try:
            server_time = self.client.get_server_time()
            local_time = int(time.time() * 1000)
            self.time_offset = server_time['serverTime'] - local_time
            logger.info(f"Tempo sincronizado - Offset: {self.time_offset}ms")
        except Exception as e:
            logger.warning(f"Erro sincronizando tempo: {e}")
    
    def safe_api_call(self, func, max_retries=3, *args, **kwargs):
        """Executa chamada API com retry automático para problemas de timestamp"""
        for attempt in range(max_retries):
            try:
                # Sincronizar tempo antes da chamada
                if attempt > 0:
                    self.sync_time()
                    time.sleep(1)  # Aguardar estabilização
                
                return func(*args, **kwargs)
                
            except Exception as e:
                if "Timestamp" in str(e) or "recvWindow" in str(e):
                    if attempt < max_retries - 1:
                        logger.warning(f"Erro timestamp (tentativa {attempt + 1}), ressincronizando...")
                        continue
                raise e
        
        return None
    
    def get_balance(self):
        """Obtém saldo simplificado"""
        try:
            account = self.safe_api_call(self.client.get_account)
            if not account:
                return 0, 0, []
            
            usdt = 0
            crypto_value = 0
            positions = []
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if balance['asset'] == 'USDT' and total > 0:
                    usdt = total
                elif total > 0.001:
                    try:
                        symbol = f"{balance['asset']}USDT"
                        ticker = self.safe_api_call(self.client.get_symbol_ticker, symbol=symbol)
                        if not ticker:
                            continue
                        price = float(ticker['price'])
                        value = total * price
                        
                        if value > 0.50:  # Só valores > $0.50
                            crypto_value += value
                            positions.append({
                                'asset': balance['asset'],
                                'amount': total,
                                'value': value,
                                'price': price
                            })
                    except:
                        pass
            
            # Log resumido
            logger.info(f"USDT: ${usdt:.2f}")
            for pos in positions:
                logger.info(f"{pos['asset']}: {pos['amount']:.6f} = ${pos['value']:.2f}")
            logger.info(f"TOTAL: ${usdt + crypto_value:.2f}")
            
            return usdt, crypto_value, positions
            
        except Exception as e:
            logger.error(f"Erro obtendo saldo: {e}")
            return 0, 0, []
    
    def get_simple_analysis(self, symbol):
        """Análise técnica super simples"""
        try:
            # Obter dados recentes
            klines = self.safe_api_call(
                self.client.get_klines,
                symbol=symbol,
                interval='5m',
                limit=50
            )
            
            if not klines or len(klines) < 20:
                return 0, "Dados insuficientes"
            
            # Extrair preços
            prices = [float(k[4]) for k in klines]  # Close prices
            volumes = [float(k[5]) for k in klines]  # Volumes
            
            current_price = prices[-1]
            
            # RSI simples (últimos 14 períodos)
            gains = []
            losses = []
            
            for i in range(1, min(15, len(prices))):
                change = prices[i] - prices[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = sum(gains) / len(gains) if gains else 0
            avg_loss = sum(losses) / len(losses) if losses else 0.001
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Médias simples
            sma_10 = sum(prices[-10:]) / 10
            sma_20 = sum(prices[-20:]) / 20
            
            # Score baseado em regras simples
            score = 0
            reasons = []
            
            # RSI
            if rsi < 25:
                score += 40
                reasons.append("RSI muito baixo")
            elif rsi < 35:
                score += 25
                reasons.append("RSI baixo") 
            elif rsi > 75:
                score += 35
                reasons.append("RSI muito alto")
            elif rsi > 65:
                score += 20
                reasons.append("RSI alto")
            
            # Tendência
            if current_price > sma_10:
                score += 10
                reasons.append("Acima SMA10")
            
            if current_price > sma_20:
                score += 10
                reasons.append("Acima SMA20")
            
            if sma_10 > sma_20:
                score += 5
                reasons.append("Tendencia alta")
            
            # Volume (último vs média)
            avg_volume = sum(volumes[-10:]) / 10
            if volumes[-1] > avg_volume * 1.5:
                score += 10
                reasons.append("Volume alto")
            
            reason_text = ", ".join(reasons[:3]) if reasons else "Neutro"
            
            logger.info(f"{symbol}: Score={score}, RSI={rsi:.1f} - {reason_text}")
            
            return score, reason_text
            
        except Exception as e:
            logger.error(f"Erro analisando {symbol}: {e}")
            return 0, "Erro na análise"
    
    def execute_buy(self, symbol, usdt_amount):
        """Compra simples"""
        try:
            # Preço atual
            ticker = self.safe_api_call(self.client.get_symbol_ticker, symbol=symbol)
            if not ticker:
                return False, None
            price = float(ticker['price'])
            
            # Quantidade
            quantity = usdt_amount / price
            
            # Info do símbolo para precisão
            info = self.safe_api_call(self.client.get_symbol_info, symbol)
            step_size = None
            
            for f in info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = f['stepSize']
                    break
            
            if step_size:
                precision = len(step_size.rstrip('0').split('.')[-1])
                quantity = round(quantity, precision)
            
            # Executar
            order = self.safe_api_call(
                self.client.order_market_buy,
                symbol=symbol,
                quantity=quantity
            )
            
            logger.info(f"✅ COMPRA: {quantity} {symbol.replace('USDT','')} = ${usdt_amount:.2f}")
            return True, order
            
        except Exception as e:
            logger.error(f"Erro comprando {symbol}: {e}")
            return False, None
    
    def execute_sell(self, asset, amount):
        """Venda simples"""
        try:
            symbol = f"{asset}USDT"
            
            # Info do símbolo
            info = self.safe_api_call(self.client.get_symbol_info, symbol)
            step_size = None
            
            for f in info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = f['stepSize']
                    break
            
            if step_size:
                precision = len(step_size.rstrip('0').split('.')[-1])
                quantity = round(amount, precision)
            else:
                quantity = amount
            
            # Executar
            order = self.safe_api_call(
                self.client.order_market_sell,
                symbol=symbol,
                quantity=quantity
            )
            
            logger.info(f"✅ VENDA: {quantity} {asset}")
            return True, order
            
        except Exception as e:
            logger.error(f"Erro vendendo {asset}: {e}")
            return False, None
    
    def trading_cycle(self, cycle_num):
        """Ciclo de trading"""
        logger.info(f"=== CICLO {cycle_num} ===")
        
        try:
            # Obter posições atuais
            usdt, crypto_value, positions = self.get_balance()
            
            if usdt == 0 and crypto_value == 0:
                logger.warning("Sem saldo disponível")
                return
            
            # 1. VERIFICAR VENDAS
            for pos in positions:
                symbol = f"{pos['asset']}USDT"
                score, reason = self.get_simple_analysis(symbol)
                
                # Vender se score alto (sobrecompra)
                if score >= 80:
                    logger.info(f"🚀 VENDENDO {pos['asset']} - Score: {score}")
                    success, order = self.execute_sell(pos['asset'], pos['amount'])
                    if success:
                        time.sleep(2)
            
            # 2. BUSCAR COMPRAS
            if usdt >= 6:  # Mínimo $6
                symbols = ['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT', 'AVAXUSDT']
                
                best_symbol = None
                best_score = 0
                
                for symbol in symbols:
                    score, reason = self.get_simple_analysis(symbol)
                    
                    # Buscar oportunidade: Score alto + condições de compra
                    if score >= 60 and score > best_score:
                        # Verificar se RSI não está muito alto
                        if "RSI muito alto" not in reason and "RSI alto" not in reason:
                            best_symbol = symbol
                            best_score = score
                
                # Executar melhor compra
                if best_symbol and best_score >= 60:
                    investment = min(usdt * 0.4, 10.0)  # 40% do USDT ou $10
                    logger.info(f"🎯 COMPRANDO {best_symbol} - Score: {best_score}")
                    
                    success, order = self.execute_buy(best_symbol, investment)
                    if success:
                        time.sleep(2)
                else:
                    logger.info("ℹ️ Aguardando oportunidade de compra")
            
            # Status final
            final_usdt, final_crypto, _ = self.get_balance()
            logger.info(f"💰 Patrimônio: ${final_usdt + final_crypto:.2f}")
            
        except Exception as e:
            logger.error(f"Erro no ciclo: {e}")
    
    def run(self, cycles=10):
        """Executar sistema"""
        logger.info("🚀 SISTEMA DAY TRADING SIMPLES")
        logger.info("📈 Estratégia: Análise Técnica Básica")
        logger.info("=" * 40)
        
        # Patrimônio inicial
        initial_usdt, initial_crypto, _ = self.get_balance()
        self.saldo_inicial = max(initial_usdt + initial_crypto, 1)
        
        logger.info(f"💰 Patrimônio inicial: ${self.saldo_inicial:.2f}")
        logger.info("🎯 Iniciando operações...")
        
        try:
            for cycle in range(1, cycles + 1):
                self.trading_cycle(cycle)
                
                if cycle < cycles:
                    logger.info("⏰ Próximo ciclo em 5 minutos...")
                    time.sleep(300)  # 5 minutos
        
        except KeyboardInterrupt:
            logger.info("🛑 Sistema interrompido")
        
        except Exception as e:
            logger.error(f"Erro no sistema: {e}")
        
        finally:
            # Relatório final
            try:
                final_usdt, final_crypto, positions = self.get_balance()
                final_total = final_usdt + final_crypto
                
                logger.info("=" * 40)
                logger.info("📊 RELATÓRIO FINAL")
                logger.info(f"💰 Inicial: ${self.saldo_inicial:.2f}")
                logger.info(f"💰 Final: ${final_total:.2f}")
                logger.info(f"📈 Variação: ${final_total - self.saldo_inicial:+.2f}")
                
                if self.saldo_inicial > 0:
                    perf = ((final_total / self.saldo_inicial - 1) * 100)
                    logger.info(f"🎯 Performance: {perf:+.2f}%")
                
                if positions:
                    logger.info("🏦 Posições finais:")
                    for pos in positions:
                        logger.info(f"   {pos['asset']}: ${pos['value']:.2f}")
                
            except Exception as e:
                logger.error(f"Erro no relatório: {e}")

def main():
    try:
        trader = SimpleDayTrader()
        trader.run(cycles=10)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()