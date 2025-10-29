#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA DE TRADING MELHORADO V2.0
- Gestão dinâmica de capital
- Stop-loss e take-profit automáticos
- Diversificação inteligente
- Valores de trade adaptativos
"""

import time
import requests
import hmac
import hashlib
import json
import logging
from datetime import datetime, timedelta
import numpy as np
from typing import Dict, List, Optional, Tuple

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_melhorado.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingMelhorado:
    def __init__(self):
        # Configurações da API Binance (CONTA_3 - Amos)
        self.api_key = "TKrbHDhUh5VxlBGWPQLZ3PhdaH0K9WGcRu5jwMJzg7hkaOSmcKHVqRMKBbiKSPOC"
        self.secret_key = "YJJwfVhRU0eJyf3PigFybsD3UHZW0aXUNfQb7beeT9x7TTu6sLhhfAKVi1G7A27l"
        self.base_url = "https://api.binance.com"
        
        # Configurações de trading melhoradas
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        self.rsi_period = 14
        self.rsi_threshold = 35
        self.confidence_threshold = 75
        self.max_cycles = 50
        self.cycle_interval = 180  # 3 minutos
        
        # Gestão de capital inteligente
        self.min_usdt_reserve = 5.0  # Reserva mínima
        self.max_position_pct = 0.25  # Máximo 25% por posição
        self.trade_size_pct = 0.15   # 15% do capital por trade
        
        # Stop-loss e Take-profit
        self.stop_loss_pct = -0.03   # -3%
        self.take_profit_pct = 0.05  # +5%
        
        # Controle de estado
        self.current_cycle = 0
        self.portfolio_inicial = 0
        self.usdt_inicial = 0
        self.trades_executados = []
        self.oportunidades_perdidas = []
        self.positions = {}  # Controle de posições abertas
        
        # Histórico RSI para análise
        self.rsi_history = {}
        self.rsi_min_encontrado = 100.0
        self.rsi_max_encontrado = 0.0
        
        logger.info("=== TRADING MELHORADO V2.0 INICIADO ===")
        logger.info("Melhorias: Gestão dinâmica de capital, Stop-loss/Take-profit")
        logger.info("Capital adaptativo: 15% por trade, reserva 25%")

    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, signed: bool = False) -> Dict:
        """Método de requisição original que funcionava sem erros"""
        try:
            from urllib.parse import urlencode
            
            url = f"{self.base_url}{endpoint}"
            if params is None:
                params = {}
            
            headers = {}
            
            if signed:
                params['recvWindow'] = 5000
                # Obter timestamp da Binance - MÉTODO ORIGINAL que funcionava
                try:
                    r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                    if r.status_code == 200:
                        params['timestamp'] = r.json()['serverTime']
                    else:
                        # Fallback para timestamp local
                        import datetime
                        params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
                except:
                    import datetime
                    params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
                
                query_string = urlencode(params)
                signature = hmac.new(
                    self.secret_key.encode('utf-8'), 
                    query_string.encode('utf-8'), 
                    hashlib.sha256
                ).hexdigest()
                params['signature'] = signature
                headers['X-MBX-APIKEY'] = self.api_key
            
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            else:
                raise ValueError(f"Método HTTP não suportado: {method}")
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Erro na requisição {method} {endpoint}: {e}")
            return {'error': True, 'detail': str(e)}

    def get_portfolio_total(self) -> Tuple[float, float, Dict[str, float]]:
        """Obtém portfolio total e breakdown detalhado"""
        try:
            account_info = self._request('GET', '/api/v3/account', signed=True)
            
            if account_info.get('error'):
                logger.error(f"Erro ao obter portfolio: {account_info}")
                return 0, 0, {}
            
            portfolio_details = {}
            total_usd = 0
            usdt_balance = 0
            
            for balance in account_info.get('balances', []):
                symbol = balance['asset']
                free_amount = float(balance['free'])
                
                if free_amount > 0:
                    if symbol == 'USDT':
                        usdt_balance = free_amount
                        portfolio_details[symbol] = free_amount
                        total_usd += free_amount
                    else:
                        # Obter preço atual
                        try:
                            price_data = self._request('GET', '/api/v3/ticker/price', 
                                                     {'symbol': f"{symbol}USDT"})
                            price = float(price_data['price'])
                            usd_value = free_amount * price
                            
                            if usd_value > 0.1:  # Apenas valores > $0.10
                                portfolio_details[symbol] = {
                                    'amount': free_amount,
                                    'price': price,
                                    'usd_value': usd_value
                                }
                                total_usd += usd_value
                        except:
                            continue
            
            return total_usd, usdt_balance, portfolio_details
            
        except Exception as e:
            logger.error(f"Erro ao obter portfolio: {e}")
            return 0, 0, {}

    def calculate_rsi(self, symbol: str, interval: str = '1m', limit: int = 100) -> Optional[float]:
        """Calcula RSI para um símbolo"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            klines = self._request('GET', '/api/v3/klines', params)
            
            if len(klines) < self.rsi_period + 1:
                return None
                
            closes = [float(kline[4]) for kline in klines]
            
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-self.rsi_period:])
            avg_loss = np.mean(losses[-self.rsi_period:])
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # Atualizar histórico
            if symbol not in self.rsi_history:
                self.rsi_history[symbol] = []
            self.rsi_history[symbol].append(rsi)
            
            # Manter apenas últimos 50 valores
            if len(self.rsi_history[symbol]) > 50:
                self.rsi_history[symbol] = self.rsi_history[symbol][-50:]
            
            return round(rsi, 1)
            
        except Exception as e:
            logger.error(f"Erro ao calcular RSI para {symbol}: {e}")
            return None

    def calculate_trade_size(self, usdt_available: float, rsi: float, confidence: float) -> float:
        """Calcula tamanho do trade baseado em capital disponível e confiança"""
        try:
            # Capital disponível menos reserva
            capital_tradeable = max(0, usdt_available - self.min_usdt_reserve)
            
            if capital_tradeable < 2.0:
                return 0
            
            # Tamanho base: 15% do capital
            base_size = capital_tradeable * self.trade_size_pct
            
            # Ajuste por RSI extremo (mais agressivo em RSI muito baixo)
            rsi_multiplier = 1.0
            if rsi < 25:
                rsi_multiplier = 1.5
            elif rsi < 30:
                rsi_multiplier = 1.2
            
            # Ajuste por confiança
            confidence_multiplier = confidence / 100.0
            
            # Tamanho final
            trade_size = base_size * rsi_multiplier * confidence_multiplier
            
            # Limites
            trade_size = max(2.0, min(trade_size, capital_tradeable * 0.4))
            
            return round(trade_size, 2)
            
        except Exception as e:
            logger.error(f"Erro ao calcular tamanho do trade: {e}")
            return 0

    def should_sell_position(self, symbol: str) -> Tuple[bool, str]:
        """Verifica se deve vender uma posição (stop-loss/take-profit)"""
        try:
            if symbol not in self.positions:
                return False, "sem_posicao"
            
            position = self.positions[symbol]
            entry_price = position['price']
            
            # Obter preço atual
            price_data = self._request('GET', '/api/v3/ticker/price', {'symbol': symbol})
            current_price = float(price_data['price'])
            
            # Calcular variação
            price_change = (current_price - entry_price) / entry_price
            
            # Stop-loss
            if price_change <= self.stop_loss_pct:
                return True, f"stop_loss_{price_change:.2%}"
            
            # Take-profit
            if price_change >= self.take_profit_pct:
                return True, f"take_profit_{price_change:.2%}"
            
            return False, f"holding_{price_change:.2%}"
            
        except Exception as e:
            logger.error(f"Erro ao verificar posição {symbol}: {e}")
            return False, "erro"

    def execute_sell_order(self, symbol: str, reason: str) -> bool:
        """Executa ordem de venda"""
        try:
            if symbol not in self.positions:
                return False
            
            position = self.positions[symbol]
            quantity = position['quantity']
            
            # Obter informações do símbolo para ajustar quantidade
            symbol_info = self._request('GET', '/api/v3/exchangeInfo')
            symbol_filters = None
            
            for s in symbol_info['symbols']:
                if s['symbol'] == symbol:
                    symbol_filters = s['filters']
                    break
            
            if symbol_filters:
                for f in symbol_filters:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        quantity = round(quantity / step_size) * step_size
                        break
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': f"{quantity:.8f}".rstrip('0').rstrip('.')
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            logger.info(f"VENDA executada: {symbol} - {quantity} - {reason}")
            logger.info(f"Order ID: {result.get('orderId')}")
            
            # Remover da posição
            del self.positions[symbol]
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao executar venda {symbol}: {e}")
            return False

    def execute_buy_order(self, symbol: str, usdt_amount: float, rsi: float, confidence: float) -> bool:
        """Executa ordem de compra com gestão de posição"""
        try:
            # Obter preço atual
            price_data = self._request('GET', '/api/v3/ticker/price', {'symbol': symbol})
            price = float(price_data['price'])
            
            # Calcular quantidade
            quantity = usdt_amount / price
            
            # Obter informações do símbolo para ajustar quantidade
            symbol_info = self._request('GET', '/api/v3/exchangeInfo')
            symbol_filters = None
            
            for s in symbol_info['symbols']:
                if s['symbol'] == symbol:
                    symbol_filters = s['filters']
                    break
            
            if symbol_filters:
                for f in symbol_filters:
                    if f['filterType'] == 'LOT_SIZE':
                        step_size = float(f['stepSize'])
                        quantity = round(quantity / step_size) * step_size
                        break
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{usdt_amount:.2f}"
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            # Registrar posição
            self.positions[symbol] = {
                'price': price,
                'quantity': quantity,
                'timestamp': datetime.now(),
                'entry_rsi': rsi,
                'confidence': confidence
            }
            
            logger.info(f"COMPRA executada: {symbol} - ${usdt_amount} - RSI: {rsi} - Conf: {confidence}%")
            logger.info(f"Order ID: {result.get('orderId')}")
            logger.info(f"Preço entrada: ${price:.4f}")
            
            self.trades_executados.append({
                'symbol': symbol,
                'tipo': 'BUY',
                'valor': usdt_amount,
                'timestamp': datetime.now(),
                'rsi': rsi,
                'confidence': confidence
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao executar compra {symbol}: {e}")
            return False

    def analyze_market_and_trade(self):
        """Análise de mercado e execução de trades melhorada"""
        try:
            # Obter portfolio atual
            portfolio_total, usdt_available, portfolio_details = self.get_portfolio_total()
            
            logger.info(f"Portfolio total: ${portfolio_total:.2f}")
            for asset, details in portfolio_details.items():
                if asset == 'USDT':
                    logger.info(f"  {asset}: ${details:.2f}")
                else:
                    logger.info(f"  {asset}: {details['amount']:.6f} = ${details['usd_value']:.2f}")
            
            logger.info(f"USDT disponível: ${usdt_available:.2f}")
            
            # Verificar posições existentes (stop-loss/take-profit)
            positions_to_sell = []
            for symbol in list(self.positions.keys()):
                should_sell, reason = self.should_sell_position(symbol)
                if should_sell:
                    positions_to_sell.append((symbol, reason))
            
            # Executar vendas se necessário
            for symbol, reason in positions_to_sell:
                logger.info(f"Executando venda {symbol}: {reason}")
                self.execute_sell_order(symbol, reason)
            
            # Analisar oportunidades de compra
            opportunities = []
            
            for symbol in self.symbols:
                rsi = self.calculate_rsi(symbol)
                
                if rsi is not None:
                    # Atualizar extremos
                    if rsi < self.rsi_min_encontrado:
                        self.rsi_min_encontrado = rsi
                        logger.info(f"Novo RSI mínimo encontrado: {rsi} em {symbol}")
                    
                    if rsi > self.rsi_max_encontrado:
                        self.rsi_max_encontrado = rsi
                    
                    # Calcular confiança baseada em RSI
                    if rsi <= self.rsi_threshold:
                        confidence = min(95, 50 + (self.rsi_threshold - rsi) * 2.5)
                        sinal = "COMPRA"
                    else:
                        confidence = 50
                        sinal = "NEUTRO"
                    
                    logger.info(f"{symbol}: RSI {rsi} | Sinal: {sinal} | Conf: {confidence:.1f}%")
                    
                    # Verificar se é uma oportunidade válida
                    if (rsi <= self.rsi_threshold and 
                        confidence >= self.confidence_threshold and
                        symbol not in self.positions):  # Não comprar se já tem posição
                        
                        trade_size = self.calculate_trade_size(usdt_available, rsi, confidence)
                        
                        if trade_size >= 2.0:
                            opportunities.append({
                                'symbol': symbol,
                                'rsi': rsi,
                                'confidence': confidence,
                                'trade_size': trade_size,
                                'priority': confidence + (self.rsi_threshold - rsi)
                            })
            
            # Ordenar oportunidades por prioridade (confiança + quão baixo é o RSI)
            opportunities.sort(key=lambda x: x['priority'], reverse=True)
            
            # Executar a melhor oportunidade se houver
            if opportunities:
                best_opportunity = opportunities[0]
                symbol = best_opportunity['symbol']
                rsi = best_opportunity['rsi']
                confidence = best_opportunity['confidence']
                trade_size = best_opportunity['trade_size']
                
                logger.info(f"Oportunidade: {symbol} - RSI {rsi} - Confiança {confidence:.1f}%")
                logger.info(f"Executando compra {symbol} - ${trade_size}")
                
                success = self.execute_buy_order(symbol, trade_size, rsi, confidence)
                
                if success:
                    # Atualizar USDT disponível
                    usdt_available -= trade_size
                else:
                    self.oportunidades_perdidas.append({
                        'symbol': symbol,
                        'rsi': rsi,
                        'confidence': confidence,
                        'motivo': 'erro_execucao',
                        'timestamp': datetime.now()
                    })
                
                # Registrar outras oportunidades como perdidas
                for opp in opportunities[1:]:
                    self.oportunidades_perdidas.append({
                        'symbol': opp['symbol'],
                        'rsi': opp['rsi'],
                        'confidence': opp['confidence'],
                        'motivo': 'substituida_por_melhor',
                        'timestamp': datetime.now()
                    })
            else:
                logger.info("Aguardando melhores oportunidades...")
                
                # Registrar RSIs atuais como oportunidades perdidas se foram boas
                for symbol in self.symbols:
                    rsi = self.calculate_rsi(symbol)
                    if rsi and rsi <= self.rsi_threshold:
                        confidence = min(95, 50 + (self.rsi_threshold - rsi) * 2.5)
                        if confidence >= 70:  # Registrar apenas oportunidades razoáveis
                            motivo = "capital_insuficiente" if usdt_available < 5 else "posicao_existente" if symbol in self.positions else "confianca_insuficiente"
                            
                            self.oportunidades_perdidas.append({
                                'symbol': symbol,
                                'rsi': rsi,
                                'confidence': confidence,
                                'motivo': motivo,
                                'timestamp': datetime.now()
                            })
            
        except Exception as e:
            logger.error(f"Erro na análise de mercado: {e}")

    def generate_progress_report(self):
        """Gera relatório de progresso a cada 5 ciclos"""
        try:
            portfolio_atual, usdt_atual, _ = self.get_portfolio_total()
            
            progresso = portfolio_atual - self.portfolio_inicial
            progresso_pct = (progresso / self.portfolio_inicial * 100) if self.portfolio_inicial > 0 else 0
            
            trades_total = len(self.trades_executados)
            oportunidades_total = len(self.oportunidades_perdidas)
            ciclos_sem_trade = self.current_cycle - trades_total
            
            logger.info("\n--- RELATÓRIO PROGRESSO CICLO {} ---".format(self.current_cycle))
            logger.info(f"Portfolio atual: ${portfolio_atual:.2f}")
            logger.info(f"Progresso: ${progresso:.2f} ({progresso_pct:.2f}%)")
            logger.info(f"Trades executados: {trades_total}")
            logger.info(f"Posições abertas: {len(self.positions)}")
            logger.info(f"Oportunidades perdidas: {oportunidades_total}")
            logger.info("----------------------------------------")
            
            # Alertas
            if ciclos_sem_trade >= 3 and usdt_atual > 5:
                logger.warning(f"ALERTA: {ciclos_sem_trade} ciclos sem trades com capital disponível!")
            
            if len(self.positions) > 3:
                logger.warning("ALERTA: Muitas posições abertas - risco concentrado!")
                
        except Exception as e:
            logger.error(f"Erro ao gerar relatório: {e}")

    def run_trading_cycles(self):
        """Executa os ciclos de trading principal"""
        try:
            # Portfolio inicial
            self.portfolio_inicial, self.usdt_inicial, _ = self.get_portfolio_total()
            logger.info(f"Portfolio inicial total: ${self.portfolio_inicial:.2f}")
            logger.info(f"USDT inicial: ${self.usdt_inicial:.2f}")
            
            for cycle in range(1, self.max_cycles + 1):
                self.current_cycle = cycle
                logger.info(f"=== CICLO {cycle} ===")
                
                self.analyze_market_and_trade()
                
                # Relatório a cada 5 ciclos
                if cycle % 5 == 0:
                    self.generate_progress_report()
                
                # Pausa entre ciclos (exceto no último)
                if cycle < self.max_cycles:
                    logger.info(f"Aguardando próximo ciclo ({self.cycle_interval//60} min)...")
                    time.sleep(self.cycle_interval)
            
            self.generate_final_report()
            
        except KeyboardInterrupt:
            logger.info("Sistema interrompido pelo usuário")
            self.generate_final_report()
        except Exception as e:
            logger.error(f"Erro durante execução: {e}")
            self.generate_final_report()

    def generate_final_report(self):
        """Gera relatório final detalhado"""
        try:
            portfolio_final, usdt_final, portfolio_details = self.get_portfolio_total()
            
            logger.info("==================================================")
            logger.info("RELATÓRIO FINAL DETALHADO - TRADING MELHORADO V2")
            logger.info("==================================================")
            
            # Performance financeira
            resultado = portfolio_final - self.portfolio_inicial
            resultado_pct = (resultado / self.portfolio_inicial * 100) if self.portfolio_inicial > 0 else 0
            variacao_usdt = usdt_final - self.usdt_inicial
            
            logger.info("PERFORMANCE FINANCEIRA:")
            logger.info(f"Portfolio inicial: ${self.portfolio_inicial:.2f}")
            logger.info(f"Portfolio final: ${portfolio_final:.2f}")
            logger.info(f"USDT inicial: ${self.usdt_inicial:.2f}")
            logger.info(f"USDT final: ${usdt_final:.2f}")
            logger.info(f"Resultado total: ${resultado:.2f} ({resultado_pct:.2f}%)")
            logger.info(f"Variação USDT: ${variacao_usdt:.2f}")
            
            # Posições abertas
            logger.info("\nPOSIÇÕES ABERTAS:")
            if self.positions:
                for symbol, pos in self.positions.items():
                    logger.info(f"  {symbol}: {pos['quantity']:.6f} @ ${pos['price']:.4f}")
            else:
                logger.info("  Nenhuma posição aberta")
            
            # Estatísticas de trading
            trades_total = len(self.trades_executados)
            oportunidades_total = len(self.oportunidades_perdidas)
            
            logger.info(f"\nESTATÍSTICAS DE TRADING:")
            logger.info(f"Trades executados: {trades_total}")
            logger.info(f"Oportunidades perdidas: {oportunidades_total}")
            logger.info(f"Ciclos executados: {self.current_cycle}")
            logger.info(f"RSI mínimo encontrado: {self.rsi_min_encontrado:.1f}")
            logger.info(f"RSI máximo encontrado: {self.rsi_max_encontrado:.1f}")
            
            # Últimas oportunidades perdidas
            if self.oportunidades_perdidas:
                logger.info(f"\nOPORTUNIDADES PERDIDAS (últimas 5):")
                for opp in self.oportunidades_perdidas[-5:]:
                    logger.info(f"  {opp['symbol']}: RSI {opp['rsi']:.1f}, Conf {opp['confidence']:.1f}% - {opp['motivo']}")
            
            # Trades executados
            if self.trades_executados:
                logger.info(f"\nTRADES EXECUTADOS:")
                for trade in self.trades_executados:
                    timestamp_str = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"  {trade['symbol']}: ${trade['valor']:.2f} - {timestamp_str}")
            
            # Recomendações inteligentes
            logger.info(f"\nRECOMENDAÇÕES DE MELHORIA:")
            
            if trades_total == 0:
                logger.info("- CRÍTICO: Nenhum trade executado!")
                logger.info("- Verificar configurações de RSI e confiança")
                logger.info("- Considerar aumentar capital inicial")
            elif trades_total < 3:
                logger.info("- Poucos trades executados")
                logger.info("- Considerar estratégias menos conservadoras")
            
            if oportunidades_total > trades_total * 3:
                logger.info("- Muitas oportunidades perdidas")
                logger.info("- Revisar gestão de capital")
                logger.info("- Considerar aumentar tamanho dos trades")
            
            if resultado < 0:
                logger.info("- Performance negativa")
                logger.info("- Revisar stop-loss e take-profit")
                logger.info("- Analisar timing de entrada")
            
            success_rate = (trades_total / max(1, trades_total + oportunidades_total)) * 100
            if success_rate < 30:
                logger.info(f"- Taxa de sucesso baixa: {success_rate:.1f}%")
                logger.info("- Revisar critérios de seleção")
            
            logger.info("==================================================")
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório final: {e}")

def main():
    """Função principal"""
    try:
        trader = TradingMelhorado()
        trader.run_trading_cycles()
    except Exception as e:
        logger.error(f"Erro crítico: {e}")

if __name__ == "__main__":
    main()