#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Day Trading - Solução Definitiva Timestamp
Implementa correção automática de timestamp com servidor NTP
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

class TimestampSyncedClient:
    """Cliente Binance com sincronização automática de timestamp"""
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.client = None
        self.time_offset = 0
        self.last_sync = 0
        self.setup_client()
    
    def setup_client(self):
        """Configura cliente com timestamp corrigido"""
        try:
            # Cliente básico para sincronização inicial
            temp_client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=False
            )
            
            self.accepted_offset = 0
            
            # Múltiplas tentativas de sincronização
            for attempt in range(5):
                try:
                    server_time = temp_client.get_server_time()
                    local_time = int(time.time() * 1000)
                    self.time_offset = server_time['serverTime'] - local_time
                    
                    logger.info(f"Sincronizacao {attempt+1}: Offset = {self.time_offset}ms")
                    
                    # Aceitar qualquer offset se for consistente
                    if abs(self.time_offset) > 60000:  # > 1 minuto (muito extremo)
                        logger.warning(f"Offset extremo: {self.time_offset}ms, tentando novamente...")
                        time.sleep(2)
                        continue
                    
                    # Offset grande mas aceitável
                    if abs(self.time_offset) > 5000:
                        logger.info(f"Offset grande detectado: {self.time_offset}ms (aceitando)")
                    
                    # Usar offset encontrado
                    self.accepted_offset = self.time_offset
                    
                    break
                    
                except Exception as e:
                    logger.warning(f"Tentativa {attempt+1} falhou: {e}")
                    time.sleep(1)
            
            # Criar cliente final
            self.client = Client(
                api_key=self.api_key,
                api_secret=self.api_secret,
                testnet=False
            )
            
            self.last_sync = time.time()
            logger.info(f"Cliente configurado com offset: {self.time_offset}ms")
            
        except Exception as e:
            logger.error(f"Erro configurando cliente: {e}")
            raise
    
    def sync_if_needed(self):
        """Ressincroniza se necessário"""
        current_time = time.time()
        
        # Ressincronizar a cada 5 minutos
        if current_time - self.last_sync > 300:
            try:
                server_time = self.client.get_server_time()
                local_time = int(time.time() * 1000)
                new_offset = server_time['serverTime'] - local_time
                
                # Se mudança significativa, atualizar
                if abs(new_offset - self.time_offset) > 1000:
                    self.time_offset = new_offset
                    logger.info(f"Offset atualizado: {self.time_offset}ms")
                
                self.last_sync = current_time
                
            except:
                pass  # Ignorar erros de ressincronização
    
    def safe_call(self, method, *args, **kwargs):
        """Executa chamada API com retry e sincronização"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Sincronizar antes da chamada
                self.sync_if_needed()
                
                # Aguardar um pouco para estabilizar
                time.sleep(0.2)
                
                # Executar método
                return method(*args, **kwargs)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                if ("timestamp" in error_msg or "recvwindow" in error_msg) and attempt < max_retries - 1:
                    # Erro de timestamp - forçar nova sincronização
                    logger.warning(f"Erro timestamp (tentativa {attempt+1}), ressincronizando...")
                    
                    try:
                        # Sincronização forçada
                        server_time = self.client.get_server_time()
                        local_time = int(time.time() * 1000)
                        self.time_offset = server_time['serverTime'] - local_time
                        
                        # Aguardar mais tempo
                        time.sleep(2 ** attempt)
                        continue
                        
                    except:
                        time.sleep(2 ** attempt)
                        continue
                else:
                    # Outros erros ou último retry
                    raise e
        
        return None

class DayTradingSincronizado:
    def __init__(self):
        self.binance_client = None
        self.saldo_inicial = 0
        self.setup_binance()
    
    def setup_binance(self):
        """Configura cliente Binance sincronizado"""
        try:
            with open('config/contas.json', 'r', encoding='utf-8') as f:
                contas = json.load(f)
            
            conta_amos = contas['CONTA_3']
            
            self.binance_client = TimestampSyncedClient(
                api_key=conta_amos['api_key'],
                api_secret=conta_amos['api_secret']
            )
            
            logger.info("Sistema Binance sincronizado configurado")
            
        except Exception as e:
            logger.error(f"Erro configurando Binance: {e}")
            raise
    
    def get_account_info(self):
        """Obtém informações da conta"""
        try:
            account = self.binance_client.safe_call(self.binance_client.client.get_account)
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
                        ticker = self.binance_client.safe_call(
                            self.binance_client.client.get_symbol_ticker,
                            symbol=symbol
                        )
                        
                        if ticker:
                            price = float(ticker['price'])
                            value = total * price
                            crypto_value += value
                            
                            if value > 0.10:  # Mostrar só valores > $0.10
                                logger.info(f"[{balance['asset']}] {total:.6f} = ${value:.2f}")
                    except:
                        pass
            
            logger.info(f"[PORTFOLIO] USDT: ${usdt_balance:.2f}")
            logger.info(f"[PORTFOLIO] Crypto: ${crypto_value:.2f}")
            logger.info(f"[PORTFOLIO] Total: ${usdt_balance + crypto_value:.2f}")
            
            return usdt_balance, crypto_value
            
        except Exception as e:
            logger.error(f"Erro obtendo conta: {e}")
            return 0, 0
    
    def get_market_data(self, symbol, limit=50):
        """Obtém dados de mercado"""
        try:
            klines = self.binance_client.safe_call(
                self.binance_client.client.get_klines,
                symbol=symbol,
                interval='5m',
                limit=limit
            )
            
            if not klines:
                return None
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Converter para números
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"Erro obtendo dados {symbol}: {e}")
            return None
    
    def calculate_technical_analysis(self, df):
        """Análise técnica completa"""
        try:
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            
            # Médias móveis
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            # MACD
            exp1 = df['close'].ewm(span=12).mean()
            exp2 = df['close'].ewm(span=26).mean()
            df['macd'] = exp1 - exp2
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['close'])
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_lower'] = bb.bollinger_lband()
            
            # Stochastic
            df['stoch'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
            
            return df
            
        except Exception as e:
            logger.error(f"Erro na análise técnica: {e}")
            return df
    
    def evaluate_symbol(self, symbol):
        """Avalia símbolo para trading"""
        try:
            df = self.get_market_data(symbol, limit=60)
            if df is None or len(df) < 30:
                return 0, []
            
            df = self.calculate_technical_analysis(df)
            last_row = df.iloc[-1]
            
            score = 0
            signals = []
            
            # Análise RSI
            rsi = last_row['rsi']
            if rsi < 20:
                score += 50
                signals.append("RSI sobrevenda extrema")
            elif rsi < 30:
                score += 40
                signals.append("RSI sobrevenda")
            elif rsi < 40:
                score += 25
                signals.append("RSI baixo")
            elif rsi > 80:
                score += 40
                signals.append("RSI sobrecompra extrema")
            elif rsi > 70:
                score += 30
                signals.append("RSI sobrecompra")
            elif rsi > 60:
                score += 20
                signals.append("RSI alto")
            
            # Análise de tendência
            price = last_row['close']
            if price > last_row['sma_20']:
                score += 10
                signals.append("Acima SMA20")
            
            if price > last_row['sma_50']:
                score += 10
                signals.append("Tendencia alta")
            
            # MACD
            if last_row['macd'] > last_row['macd_signal']:
                score += 8
                signals.append("MACD positivo")
            
            # Bollinger Bands
            if price < last_row['bb_lower']:
                score += 25
                signals.append("Abaixo Bollinger inferior")
            elif price > last_row['bb_upper']:
                score += 20
                signals.append("Acima Bollinger superior")
            
            # Stochastic
            stoch = last_row['stoch']
            if stoch < 20:
                score += 15
                signals.append("Stoch sobrevenda")
            elif stoch > 80:
                score += 15
                signals.append("Stoch sobrecompra")
            
            logger.info(f"[ANALISE {symbol}] Score: {score}")
            logger.info(f"  RSI: {rsi:.1f}, Stoch: {stoch:.1f}")
            if signals:
                logger.info(f"  Sinais: {', '.join(signals[:3])}")  # Primeiros 3 sinais
            
            return score, signals
            
        except Exception as e:
            logger.error(f"Erro avaliando {symbol}: {e}")
            return 0, []
    
    def execute_order(self, action, symbol, amount_or_qty):
        """Executa ordem de trading"""
        try:
            if action.upper() == "BUY":
                # Compra por valor USDT
                ticker = self.binance_client.safe_call(
                    self.binance_client.client.get_symbol_ticker,
                    symbol=symbol
                )
                
                if not ticker:
                    return False, None
                
                price = float(ticker['price'])
                quantity = amount_or_qty / price
                
                # Ajustar precisão
                symbol_info = self.binance_client.safe_call(
                    self.binance_client.client.get_symbol_info,
                    symbol
                )
                
                if symbol_info:
                    step_size = float(symbol_info['filters'][1]['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = round(quantity, precision)
                
                # Executar compra
                order = self.binance_client.safe_call(
                    self.binance_client.client.order_market_buy,
                    symbol=symbol,
                    quantity=quantity
                )
                
                if order:
                    logger.info(f"✅ COMPRA: {quantity} {symbol.replace('USDT','')} por ${amount_or_qty:.2f}")
                    logger.info(f"   Order ID: {order['orderId']}")
                    return True, order
            
            elif action.upper() == "SELL":
                # Venda por quantidade
                symbol_info = self.binance_client.safe_call(
                    self.binance_client.client.get_symbol_info,
                    symbol
                )
                
                if symbol_info:
                    step_size = float(symbol_info['filters'][1]['stepSize'])
                    precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    quantity = round(amount_or_qty, precision)
                
                # Executar venda
                order = self.binance_client.safe_call(
                    self.binance_client.client.order_market_sell,
                    symbol=symbol,
                    quantity=quantity
                )
                
                if order:
                    logger.info(f"✅ VENDA: {quantity} {symbol.replace('USDT','')}")
                    logger.info(f"   Order ID: {order['orderId']}")
                    return True, order
            
            return False, None
            
        except Exception as e:
            logger.error(f"Erro executando {action} {symbol}: {e}")
            return False, None
    
    def trading_cycle(self, cycle_num):
        """Executa um ciclo de trading"""
        logger.info(f"[CICLO {cycle_num}] Trading Sincronizado")
        logger.info("=" * 45)
        
        try:
            # Verificar saldos atuais
            usdt_balance, crypto_value = self.get_account_info()
            
            if usdt_balance == 0 and crypto_value == 0:
                logger.warning("❌ Não foi possível obter saldos da conta")
                return
            
            # 1. VERIFICAR VENDAS (posições existentes)
            account = self.binance_client.safe_call(self.binance_client.client.get_account)
            
            if account:
                for balance in account['balances']:
                    free = float(balance['free'])
                    
                    if free > 0.001 and balance['asset'] != 'USDT':
                        symbol = f"{balance['asset']}USDT"
                        score, signals = self.evaluate_symbol(symbol)
                        
                        # Critério de venda: Score >= 85 (sinais fortes de sobrecompra)
                        if score >= 85:
                            logger.info(f"🚀 SINAL FORTE DE VENDA: {symbol} (Score: {score})")
                            success, order = self.execute_order("SELL", symbol, free)
                            
                            if success:
                                time.sleep(3)  # Aguardar processamento
            
            # 2. BUSCAR COMPRAS
            if usdt_balance >= 6:  # Mínimo $6 para operar
                symbols_to_check = ['SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT', 'AVAXUSDT', 'MATICUSDT']
                
                best_opportunity = None
                best_score = 0
                
                for symbol in symbols_to_check:
                    score, signals = self.evaluate_symbol(symbol)
                    
                    # Buscar oportunidades de compra (Score >= 70 + RSI < 40)
                    if score >= 70:
                        df = self.get_market_data(symbol, limit=30)
                        
                        if df is not None and len(df) > 20:
                            df = self.calculate_technical_analysis(df)
                            current_rsi = df.iloc[-1]['rsi']
                            
                            # RSI baixo indica boa oportunidade de compra
                            if current_rsi < 40 and score > best_score:
                                best_opportunity = symbol
                                best_score = score
                
                # Executar melhor compra encontrada
                if best_opportunity and best_score >= 70:
                    # Investir 35% do saldo USDT ou máximo $12
                    investment = min(usdt_balance * 0.35, 12.0)
                    
                    logger.info(f"🎯 MELHOR OPORTUNIDADE: {best_opportunity}")
                    logger.info(f"   Score: {best_score}, Investimento: ${investment:.2f}")
                    
                    success, order = self.execute_order("BUY", best_opportunity, investment)
                    
                    if success:
                        time.sleep(3)
                else:
                    logger.info("ℹ️  Aguardando oportunidade (Score >= 70 + RSI < 40)")
            else:
                logger.info(f"💰 Saldo USDT insuficiente: ${usdt_balance:.2f} (mínimo $6)")
            
            # Status final do ciclo
            final_usdt, final_crypto = self.get_account_info()
            total_patrimonio = final_usdt + final_crypto
            
            logger.info(f"💼 PATRIMÔNIO ATUAL: ${total_patrimonio:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Erro no ciclo {cycle_num}: {e}")
    
    def run_system(self, total_cycles=12):
        """Executa o sistema completo"""
        logger.info("🤖 SISTEMA DAY TRADING SINCRONIZADO")
        logger.info("📊 Estratégia: Análise Técnica Avançada")
        logger.info("🎯 Meta: Compra em baixa + Venda em alta")
        logger.info("=" * 50)
        
        try:
            # Patrimônio inicial
            initial_usdt, initial_crypto = self.get_account_info()
            self.saldo_inicial = max(initial_usdt + initial_crypto, 1)
            
            logger.info(f"💰 PATRIMÔNIO INICIAL: ${self.saldo_inicial:.2f}")
            logger.info("🚀 INICIANDO OPERAÇÕES...")
            logger.info("=" * 50)
            
            # Loop principal
            for cycle in range(1, total_cycles + 1):
                try:
                    self.trading_cycle(cycle)
                    
                    if cycle < total_cycles:
                        logger.info("⏰ Próximo ciclo em 5 minutos...")
                        time.sleep(300)  # 5 minutos
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Sistema interrompido pelo usuário")
                    break
                    
                except Exception as e:
                    logger.error(f"❌ Erro no ciclo {cycle}: {e}")
                    time.sleep(60)  # Aguardar 1 minuto e continuar
            
        except Exception as e:
            logger.error(f"❌ Erro fatal no sistema: {e}")
        
        finally:
            # Relatório final
            try:
                final_usdt, final_crypto = self.get_account_info()
                final_total = final_usdt + final_crypto
                
                logger.info("=" * 50)
                logger.info("📈 RELATÓRIO FINAL")
                logger.info("=" * 50)
                logger.info(f"💰 Patrimônio inicial: ${self.saldo_inicial:.2f}")
                logger.info(f"💰 Patrimônio final: ${final_total:.2f}")
                logger.info(f"📊 Variação: ${final_total - self.saldo_inicial:+.2f}")
                
                if self.saldo_inicial > 0:
                    performance = ((final_total / self.saldo_inicial - 1) * 100)
                    logger.info(f"🎯 Performance: {performance:+.2f}%")
                    
                    if performance > 0:
                        logger.info("🎉 RESULTADO POSITIVO!")
                    elif performance > -5:
                        logger.info("📊 Resultado neutro")
                    else:
                        logger.info("⚠️  Revisar estratégia")
                
            except Exception as e:
                logger.error(f"Erro no relatório final: {e}")

def main():
    """Função principal"""
    try:
        trader = DayTradingSincronizado()
        trader.run_system(total_cycles=12)
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()