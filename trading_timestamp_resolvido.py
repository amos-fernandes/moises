#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Day Trading - SOLUÇÃO DEFINITIVA TIMESTAMP
Implementa cliente Binance customizado que resolve problemas de timestamp
"""

import json
import logging
import time
import numpy as np
import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceClientFixed(Client):
    """Cliente Binance com retry automático para problemas de timestamp e assinatura"""
    
    def __init__(self, api_key, api_secret, testnet=False):
        super().__init__(api_key, api_secret, testnet=testnet)
        self.time_offset = 0
        self.last_sync = 0
        self._initial_sync()
    
    def _initial_sync(self):
        """Sincronização inicial com servidor"""
        try:
            server_time = super().get_server_time()
            local_time = int(time.time() * 1000)
            self.time_offset = server_time['serverTime'] - local_time
            self.last_sync = time.time()
            logger.info(f"Offset calculado: {self.time_offset}ms")
        except Exception as e:
            logger.warning(f"Erro na sincronização inicial: {e}")
    
    def _should_resync(self):
        """Verifica se precisa ressincronizar"""
        return (time.time() - self.last_sync) > 300  # A cada 5 minutos
    
    def _resync_if_needed(self):
        """Ressincroniza se necessário"""
        if self._should_resync():
            try:
                server_time = super().get_server_time()
                local_time = int(time.time() * 1000)
                new_offset = server_time['serverTime'] - local_time
                
                # Se mudança significativa, atualizar
                if abs(new_offset - self.time_offset) > 2000:  # > 2 segundos
                    self.time_offset = new_offset
                    logger.info(f"Offset atualizado: {self.time_offset}ms")
                
                self.last_sync = time.time()
            except:
                pass  # Ignorar erros de ressincronização
    
    def _safe_request(self, method, *args, **kwargs):
        """Executa requisição com retry automático"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Aguardar um pouco para estabilizar
                if attempt > 0:
                    time.sleep(min(2 ** attempt, 5))  # Backoff exponencial, máx 5s
                
                # Ressincronizar se necessário
                self._resync_if_needed()
                
                return method(*args, **kwargs)
                
            except BinanceAPIException as e:
                if e.code in [-1021, -1022]:  # Timestamp ou signature error
                    if attempt < max_retries - 1:
                        logger.warning(f"Erro API {e.code} (tentativa {attempt + 1}), aguardando...")
                        # Forçar nova sincronização
                        try:
                            server_time = super().get_server_time()
                            local_time = int(time.time() * 1000)
                            self.time_offset = server_time['serverTime'] - local_time
                            self.last_sync = time.time()
                        except:
                            pass
                        continue
                raise e
            except Exception as e:
                error_str = str(e).lower()
                if any(word in error_str for word in ['timestamp', 'signature', 'recvwindow']):
                    if attempt < max_retries - 1:
                        logger.warning(f"Erro de sincronização (tentativa {attempt + 1})")
                        continue
                raise e
        
        raise Exception(f"Falha após {max_retries} tentativas")
    
    # Override dos métodos principais
    def get_account(self, **kwargs):
        return self._safe_request(super().get_account, **kwargs)
    
    def get_symbol_ticker(self, **kwargs):
        return self._safe_request(super().get_symbol_ticker, **kwargs)
    
    def get_klines(self, **kwargs):
        return self._safe_request(super().get_klines, **kwargs)
    
    def get_symbol_info(self, symbol):
        return self._safe_request(super().get_symbol_info, symbol)
    
    def order_market_buy(self, **kwargs):
        return self._safe_request(super().order_market_buy, **kwargs)
    
    def order_market_sell(self, **kwargs):
        return self._safe_request(super().order_market_sell, **kwargs)

class DayTradingResolvido:
    def __init__(self):
        self.client = None
        self.saldo_inicial = 0
        self.setup_client()
    
    def setup_client(self):
        """Configura cliente com correção de timestamp"""
        try:
            with open('config/contas.json', 'r', encoding='utf-8') as f:
                contas = json.load(f)
            
            conta = contas['CONTA_3']  # Amos
            
            # Usar cliente customizado
            self.client = BinanceClientFixed(
                api_key=conta['api_key'],
                api_secret=conta['api_secret'],
                testnet=False
            )
            
            logger.info("✅ Cliente Binance com correção timestamp configurado")
            
        except Exception as e:
            logger.error(f"❌ Erro configurando cliente: {e}")
            raise
    
    def get_portfolio(self):
        """Obtém portfólio completo"""
        try:
            account = self.client.get_account()
            
            usdt_balance = 0
            crypto_positions = []
            total_crypto_value = 0
            
            for balance in account['balances']:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if balance['asset'] == 'USDT' and total > 0:
                    usdt_balance = total
                elif total > 0.001:  # Apenas ativos com valor significativo
                    try:
                        symbol = f"{balance['asset']}USDT"
                        ticker = self.client.get_symbol_ticker(symbol=symbol)
                        price = float(ticker['price'])
                        value_usd = total * price
                        
                        if value_usd > 0.50:  # Apenas valores > $0.50
                            crypto_positions.append({
                                'asset': balance['asset'],
                                'symbol': symbol,
                                'quantity': total,
                                'price': price,
                                'value': value_usd
                            })
                            total_crypto_value += value_usd
                    except:
                        continue  # Ignorar erros de símbolos inválidos
            
            # Log do portfólio
            logger.info("💰 PORTFÓLIO ATUAL:")
            logger.info(f"   USDT: ${usdt_balance:.2f}")
            
            for pos in crypto_positions:
                logger.info(f"   {pos['asset']}: {pos['quantity']:.6f} = ${pos['value']:.2f} (@${pos['price']:.6f})")
            
            total_portfolio = usdt_balance + total_crypto_value
            logger.info(f"   📊 TOTAL: ${total_portfolio:.2f}")
            
            return usdt_balance, crypto_positions, total_portfolio
            
        except Exception as e:
            logger.error(f"❌ Erro obtendo portfólio: {e}")
            return 0, [], 0
    
    def analyze_market(self, symbol, periods=50):
        """Análise de mercado simplificada mas eficaz"""
        try:
            # Obter dados históricos
            klines = self.client.get_klines(
                symbol=symbol,
                interval='5m',
                limit=periods
            )
            
            if len(klines) < 20:
                return 0, "Dados insuficientes", {}
            
            # Processar dados
            closes = [float(k[4]) for k in klines]
            volumes = [float(k[5]) for k in klines]
            highs = [float(k[2]) for k in klines]
            lows = [float(k[3]) for k in klines]
            
            current_price = closes[-1]
            
            # RSI Simplificado (14 períodos)
            def calculate_rsi(prices, period=14):
                gains = []
                losses = []
                
                for i in range(1, min(period + 1, len(prices))):
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
                return 100 - (100 / (1 + rs))
            
            rsi = calculate_rsi(closes)
            
            # Médias móveis
            sma_10 = sum(closes[-10:]) / 10
            sma_20 = sum(closes[-20:]) / 20
            
            # Análise de volume
            avg_volume = sum(volumes[-10:]) / 10
            volume_ratio = volumes[-1] / avg_volume
            
            # Sistema de pontuação
            score = 0
            signals = []
            
            # RSI Analysis
            if rsi <= 20:
                score += 50
                signals.append("RSI extremamente baixo")
            elif rsi <= 30:
                score += 35
                signals.append("RSI muito baixo")
            elif rsi <= 40:
                score += 20
                signals.append("RSI baixo")
            elif rsi >= 80:
                score += 45
                signals.append("RSI extremamente alto")
            elif rsi >= 70:
                score += 30
                signals.append("RSI muito alto")
            elif rsi >= 60:
                score += 15
                signals.append("RSI alto")
            
            # Trend Analysis
            if current_price > sma_10:
                score += 10
                signals.append("Acima SMA10")
            
            if current_price > sma_20:
                score += 10
                signals.append("Tendência alta")
            
            if sma_10 > sma_20:
                score += 5
                signals.append("SMA crescente")
            
            # Volume Analysis
            if volume_ratio > 2.0:
                score += 15
                signals.append("Volume muito alto")
            elif volume_ratio > 1.5:
                score += 10
                signals.append("Volume alto")
            
            # Price Movement
            price_change_1h = ((closes[-1] - closes[-12]) / closes[-12]) * 100 if len(closes) >= 12 else 0
            if abs(price_change_1h) > 3:
                score += 10
                signals.append(f"Movimento 1h: {price_change_1h:+.1f}%")
            
            # Dados técnicos
            technical_data = {
                'rsi': rsi,
                'price': current_price,
                'sma_10': sma_10,
                'sma_20': sma_20,
                'volume_ratio': volume_ratio,
                'price_change_1h': price_change_1h
            }
            
            reason = ", ".join(signals[:3]) if signals else "Neutro"
            
            logger.info(f"📊 {symbol}: Score={score}, RSI={rsi:.1f}")
            logger.info(f"   💡 {reason}")
            
            return score, reason, technical_data
            
        except Exception as e:
            logger.error(f"❌ Erro analisando {symbol}: {e}")
            return 0, "Erro na análise", {}
    
    def execute_trade(self, action, symbol, amount_or_quantity):
        """Executa negociação"""
        try:
            if action.upper() == "BUY":
                # Comprar por valor em USDT
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                current_price = float(ticker['price'])
                
                # Calcular quantidade
                quantity = amount_or_quantity / current_price
                
                # Ajustar precisão baseado no símbolo
                symbol_info = self.client.get_symbol_info(symbol)
                lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
                step_size = float(lot_size_filter['stepSize'])
                
                # Calcular casas decimais
                if step_size >= 1:
                    precision = 0
                else:
                    precision = len(str(step_size).split('.')[1].rstrip('0'))
                
                quantity = round(quantity, precision)
                
                # Executar compra
                order = self.client.order_market_buy(
                    symbol=symbol,
                    quantity=quantity
                )
                
                logger.info(f"✅ COMPRA EXECUTADA")
                logger.info(f"   {symbol}: {quantity} por ${amount_or_quantity:.2f}")
                logger.info(f"   Order ID: {order['orderId']}")
                
                return True, order
                
            elif action.upper() == "SELL":
                # Vender quantidade específica
                symbol_info = self.client.get_symbol_info(symbol)
                lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
                step_size = float(lot_size_filter['stepSize'])
                
                if step_size >= 1:
                    precision = 0
                else:
                    precision = len(str(step_size).split('.')[1].rstrip('0'))
                
                quantity = round(amount_or_quantity, precision)
                
                # Executar venda
                order = self.client.order_market_sell(
                    symbol=symbol,
                    quantity=quantity
                )
                
                logger.info(f"✅ VENDA EXECUTADA")
                logger.info(f"   {symbol}: {quantity}")
                logger.info(f"   Order ID: {order['orderId']}")
                
                return True, order
            
            return False, None
            
        except Exception as e:
            logger.error(f"❌ Erro executando {action} {symbol}: {e}")
            return False, None
    
    def trading_session(self, cycle_number):
        """Sessão de trading"""
        logger.info(f"🔄 CICLO {cycle_number}")
        logger.info("=" * 40)
        
        try:
            # 1. Verificar portfólio atual
            usdt_balance, crypto_positions, total_value = self.get_portfolio()
            
            if total_value == 0:
                logger.warning("❌ Portfólio vazio ou erro ao acessar")
                return
            
            # 2. Analisar vendas (posições existentes)
            for position in crypto_positions:
                symbol = position['symbol']
                score, reason, technical = self.analyze_market(symbol)
                
                # Critério de venda: Score muito alto (indica sobrecompra)
                if score >= 80:
                    logger.info(f"🚀 SINAL DE VENDA: {symbol}")
                    logger.info(f"   Score: {score} - {reason}")
                    
                    success, order = self.execute_trade("SELL", symbol, position['quantity'])
                    if success:
                        time.sleep(2)  # Aguardar processamento
            
            # 3. Buscar oportunidades de compra
            if usdt_balance >= 6:  # Mínimo $6 para operar
                symbols_to_check = [
                    'SOLUSDT', 'ADAUSDT', 'DOGEUSDT', 'BNBUSDT', 
                    'AVAXUSDT', 'MATICUSDT', 'DOTUSDT'
                ]
                
                opportunities = []
                
                for symbol in symbols_to_check:
                    score, reason, technical = self.analyze_market(symbol)
                    
                    # Filtrar oportunidades de compra
                    if score >= 65:  # Score alto
                        rsi = technical.get('rsi', 50)
                        
                        # RSI deve estar baixo para compra (sobrevenda)
                        if rsi <= 40:
                            opportunities.append({
                                'symbol': symbol,
                                'score': score,
                                'rsi': rsi,
                                'reason': reason
                            })
                
                # Executar melhor oportunidade
                if opportunities:
                    # Ordenar por score
                    opportunities.sort(key=lambda x: x['score'], reverse=True)
                    best = opportunities[0]
                    
                    # Calcular investimento (40% do USDT disponível ou máximo $15)
                    investment = min(usdt_balance * 0.4, 15.0)
                    
                    logger.info(f"🎯 MELHOR OPORTUNIDADE: {best['symbol']}")
                    logger.info(f"   Score: {best['score']}, RSI: {best['rsi']:.1f}")
                    logger.info(f"   Investimento: ${investment:.2f}")
                    
                    success, order = self.execute_trade("BUY", best['symbol'], investment)
                    if success:
                        time.sleep(2)
                else:
                    logger.info("ℹ️ Aguardando oportunidade (Score ≥65 + RSI ≤40)")
            else:
                logger.info(f"💰 Saldo insuficiente: ${usdt_balance:.2f} (mínimo $6)")
            
            # Status final
            final_usdt, final_positions, final_total = self.get_portfolio()
            logger.info(f"💼 Patrimônio do ciclo: ${final_total:.2f}")
            
        except Exception as e:
            logger.error(f"❌ Erro no ciclo {cycle_number}: {e}")
    
    def run(self, total_cycles=8):
        """Executa sistema completo"""
        logger.info("🤖 SISTEMA DAY TRADING - TIMESTAMP RESOLVIDO")
        logger.info("🎯 Estratégia: Compra em sobrevenda + Venda em sobrecompra")
        logger.info("=" * 55)
        
        try:
            # Portfólio inicial
            initial_usdt, initial_positions, initial_total = self.get_portfolio()
            self.saldo_inicial = max(initial_total, 1)  # Evitar divisão por zero
            
            logger.info(f"💰 PATRIMÔNIO INICIAL: ${self.saldo_inicial:.2f}")
            logger.info("🚀 Iniciando operações...")
            logger.info("=" * 55)
            
            # Loop principal de trading
            for cycle in range(1, total_cycles + 1):
                try:
                    self.trading_session(cycle)
                    
                    if cycle < total_cycles:
                        logger.info("⏰ Aguardando próximo ciclo (5 min)...")
                        time.sleep(300)  # 5 minutos
                    
                except KeyboardInterrupt:
                    logger.info("🛑 Sistema interrompido pelo usuário")
                    break
                except Exception as e:
                    logger.error(f"❌ Erro no ciclo {cycle}: {e}")
                    time.sleep(60)  # Aguardar 1 minuto e continuar
            
        except Exception as e:
            logger.error(f"❌ Erro fatal: {e}")
        
        finally:
            # Relatório final detalhado
            try:
                final_usdt, final_positions, final_total = self.get_portfolio()
                
                logger.info("=" * 55)
                logger.info("📈 RELATÓRIO FINAL COMPLETO")
                logger.info("=" * 55)
                logger.info(f"💰 Patrimônio inicial: ${self.saldo_inicial:.2f}")
                logger.info(f"💰 Patrimônio final: ${final_total:.2f}")
                logger.info(f"📊 Variação absoluta: ${final_total - self.saldo_inicial:+.2f}")
                
                if self.saldo_inicial > 0:
                    performance_pct = ((final_total / self.saldo_inicial - 1) * 100)
                    logger.info(f"🎯 Performance: {performance_pct:+.2f}%")
                    
                    if performance_pct > 5:
                        logger.info("🎉 EXCELENTE RESULTADO!")
                    elif performance_pct > 0:
                        logger.info("✅ Resultado positivo")
                    elif performance_pct > -2:
                        logger.info("📊 Resultado neutro")
                    else:
                        logger.info("⚠️ Necessário revisar estratégia")
                
                if final_positions:
                    logger.info("🏦 Posições finais:")
                    for pos in final_positions:
                        logger.info(f"   {pos['asset']}: ${pos['value']:.2f}")
                
                logger.info("=" * 55)
                logger.info("✅ Sistema finalizado com sucesso!")
                
            except Exception as e:
                logger.error(f"❌ Erro no relatório final: {e}")

def main():
    """Função principal"""
    try:
        logger.info("🔧 Inicializando sistema...")
        trader = DayTradingResolvido()
        trader.run(total_cycles=8)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal na inicialização: {e}")

if __name__ == "__main__":
    main()