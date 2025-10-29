#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SISTEMA TRADING CORRIGIDO - Baseado no trading_original_funcionando.py
Correções implementadas para resolver as perdas identificadas:
1. Gestão dinâmica de capital
2. Valores de trade adaptativos  
3. Melhor seleção de oportunidades
4. Relatórios de performance aprimorados
"""

import json
import time
import logging
import hmac
import hashlib
import requests
import numpy as np
from urllib.parse import urlencode
from datetime import datetime
import sys

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_corrigido.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingCorrigido:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # CORREÇÕES IMPLEMENTADAS - Gestão dinâmica de capital
        self.min_trade_value = 5.0  # Valor mínimo por trade
        self.max_position_pct = 0.3  # Máximo 30% do capital em uma posição
        self.reserve_pct = 0.2  # Manter 20% de reserva
        
        # Sistema de monitoramento aprimorado
        self.trades_executados = []
        self.oportunidades_perdidas = []
        self.performance_historico = []
        self.melhor_rsi_encontrado = {'buy': 100, 'sell': 0}
        self.ciclos_sem_trade = 0
        self.total_lucro = 0
        self.portfolio_inicial = 0
        self.usdt_inicial = 0
        
        logger.info(f"=== TRADING CORRIGIDO INICIADO - {conta_nome} ===")
        logger.info("CORREÇÕES IMPLEMENTADAS:")
        logger.info("- Gestão dinâmica de capital (20% reserva)")
        logger.info("- Valores de trade adaptativos")
        logger.info("- Melhor seleção de oportunidades")
        logger.info("- Sistema anti-overtrading")
    
    def _request(self, method, path, params, signed: bool):
        """Requisição original que funcionava sem erros de timestamp"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
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
            logger.error(f"Erro obtendo saldo: {account}")
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0
    
    def get_portfolio_total(self):
        """Obter valor total do portfolio (USDT + outras criptos)"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            logger.error(f"Erro obtendo portfolio: {account}")
            return 0, 0, {}
        
        total_usd = 0
        usdt_balance = 0
        portfolio_details = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            
            if free > 0:
                if asset == 'USDT':
                    usdt_balance = free
                    total_usd += free
                    portfolio_details[asset] = free
                    logger.info(f"  {asset}: {free:.6f} = ${free:.2f}")
                else:
                    # Tentar obter preço atual para outras criptos
                    try:
                        ticker = self._request('GET', '/api/v3/ticker/price', {'symbol': f"{asset}USDT"}, signed=False)
                        if not ticker.get('error'):
                            price = float(ticker['price'])
                            usd_value = free * price
                            if usd_value > 0.1:  # Só considerar valores > $0.10
                                total_usd += usd_value
                                portfolio_details[asset] = {'amount': free, 'price': price, 'usd_value': usd_value}
                                logger.info(f"  {asset}: {free:.6f} = ${usd_value:.2f}")
                    except:
                        continue
        
        return total_usd, usdt_balance, portfolio_details

    def calcular_rsi(self, symbol, timeframe='1m', periods=14):
        """Calcular RSI para um símbolo"""
        try:
            klines = self._request('GET', '/api/v3/klines', {
                'symbol': symbol,
                'interval': timeframe,
                'limit': periods + 20
            }, signed=False)
            
            if klines.get('error') or len(klines) < periods:
                return None
            
            closes = [float(kline[4]) for kline in klines]
            
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = np.convolve(gains, np.ones(periods), 'valid') / periods
            avg_losses = np.convolve(losses, np.ones(periods), 'valid') / periods
            
            rs = avg_gains[-1] / avg_losses[-1] if avg_losses[-1] != 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 1)
        except Exception as e:
            logger.error(f"Erro calculando RSI para {symbol}: {e}")
            return None

    def calcular_valor_trade_dinamico(self, saldo_usdt: float, rsi: float, confianca: float) -> float:
        """
        CORREÇÃO: Cálculo dinâmico do valor do trade
        Evita esgotar o capital muito rapidamente
        """
        try:
            # Capital disponível para trading (menos reserva)
            capital_disponivel = saldo_usdt * (1 - self.reserve_pct)
            
            if capital_disponivel < self.min_trade_value:
                return 0
            
            # Base: 15% do capital disponível
            valor_base = capital_disponivel * 0.15
            
            # Ajuste por RSI extremo (mais agressivo quando RSI muito baixo)
            if rsi < 25:
                multiplicador_rsi = 1.5  # 50% mais agressivo
            elif rsi < 30:
                multiplicador_rsi = 1.2  # 20% mais agressivo
            else:
                multiplicador_rsi = 1.0
            
            # Ajuste por confiança
            multiplicador_confianca = confianca / 100.0
            
            # Valor final
            valor_final = valor_base * multiplicador_rsi * multiplicador_confianca
            
            # Limites de segurança
            valor_final = max(self.min_trade_value, valor_final)
            valor_final = min(valor_final, saldo_usdt * self.max_position_pct)
            
            return round(valor_final, 2)
            
        except Exception as e:
            logger.error(f"Erro no cálculo dinâmico: {e}")
            return self.min_trade_value

    def executar_compra(self, symbol, valor_usdt):
        """Executar ordem de compra"""
        try:
            # Validação mínima da Binance
            if valor_usdt < 5.0:
                logger.warning(f"Valor muito baixo para {symbol}: ${valor_usdt}")
                return False
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': str(valor_usdt)
            }
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            if result.get('error'):
                logger.error(f"Erro na compra {symbol}: {result}")
                return False
            
            logger.info(f"Compra executada: Order ID {result.get('orderId')}")
            
            # Calcular quantidade aproximada
            ticker = self._request('GET', '/api/v3/ticker/price', {'symbol': symbol}, signed=False)
            if not ticker.get('error'):
                price = float(ticker['price'])
                qty_approx = valor_usdt / price
                logger.info(f"Quantidade: {qty_approx:.8f}")
            
            # Registrar trade
            self.trades_executados.append({
                'symbol': symbol,
                'valor': valor_usdt,
                'timestamp': datetime.now(),
                'order_id': result.get('orderId')
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Erro executando compra {symbol}: {e}")
            return False

    def analisar_oportunidades_melhorado(self):
        """
        CORREÇÃO: Análise melhorada de oportunidades
        Seleciona a melhor oportunidade considerando múltiplos fatores
        """
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        # Obter saldo atual
        portfolio_total, saldo_usdt, portfolio_details = self.get_portfolio_total()
        logger.info(f"Portfolio total: ${portfolio_total:.2f}")
        logger.info(f"USDT disponível: ${saldo_usdt:.2f}")
        
        if saldo_usdt < self.min_trade_value:
            logger.warning(f"USDT insuficiente para trading: ${saldo_usdt:.2f}")
            return
        
        # Analisar todos os símbolos
        oportunidades = []
        
        for symbol in symbols:
            rsi = self.calcular_rsi(symbol)
            
            if rsi is None:
                continue
            
            # Atualizar extremos
            if rsi < self.melhor_rsi_encontrado['buy']:
                self.melhor_rsi_encontrado['buy'] = rsi
                logger.info(f"Novo RSI mínimo encontrado: {rsi} em {symbol}")
            
            # Calcular confiança baseada no RSI
            if rsi <= 35:
                confianca = min(95, 50 + (35 - rsi) * 2.5)
                sinal = "COMPRA"
            else:
                confianca = 50
                sinal = "NEUTRO"
            
            logger.info(f"{symbol}: RSI {rsi} | Sinal: {sinal} | Conf: {confianca:.1f}%")
            
            # Se é uma boa oportunidade, calcular valor do trade
            if rsi <= 35 and confianca >= 75:
                valor_trade = self.calcular_valor_trade_dinamico(saldo_usdt, rsi, confianca)
                
                if valor_trade >= self.min_trade_value:
                    # Score de prioridade (confiança + quão extremo é o RSI)
                    score_prioridade = confianca + (35 - rsi) * 2
                    
                    oportunidades.append({
                        'symbol': symbol,
                        'rsi': rsi,
                        'confianca': confianca,
                        'valor_trade': valor_trade,
                        'score': score_prioridade
                    })
                else:
                    # Registrar como oportunidade perdida por capital
                    self.oportunidades_perdidas.append({
                        'symbol': symbol,
                        'rsi': rsi,
                        'confianca': confianca,
                        'motivo': 'capital_insuficiente',
                        'timestamp': datetime.now()
                    })
            elif rsi <= 35:
                # RSI bom mas confiança insuficiente
                self.oportunidades_perdidas.append({
                    'symbol': symbol,
                    'rsi': rsi,
                    'confianca': confianca,
                    'motivo': 'confianca_insuficiente',
                    'timestamp': datetime.now()
                })
        
        # Executar a melhor oportunidade
        if oportunidades:
            # Ordenar por score (melhor primeiro)
            oportunidades.sort(key=lambda x: x['score'], reverse=True)
            
            melhor = oportunidades[0]
            logger.info(f"Melhor oportunidade: {melhor['symbol']} - RSI {melhor['rsi']} - Confiança {melhor['confianca']:.1f}%")
            logger.info(f"Executando compra {melhor['symbol']} - ${melhor['valor_trade']}")
            
            sucesso = self.executar_compra(melhor['symbol'], melhor['valor_trade'])
            
            if sucesso:
                self.ciclos_sem_trade = 0
            else:
                self.ciclos_sem_trade += 1
            
            # Registrar outras oportunidades como perdidas
            for opp in oportunidades[1:]:
                self.oportunidades_perdidas.append({
                    'symbol': opp['symbol'],
                    'rsi': opp['rsi'],
                    'confianca': opp['confianca'],
                    'motivo': 'substituida_por_melhor',
                    'timestamp': datetime.now()
                })
        else:
            logger.info("Aguardando melhores oportunidades...")
            self.ciclos_sem_trade += 1
            
            # Alerta se muitos ciclos sem trade
            if self.ciclos_sem_trade >= 5 and saldo_usdt > 10:
                logger.warning(f"ALERTA: {self.ciclos_sem_trade} ciclos consecutivos sem trades!")
                logger.warning("Considerar ajustar parâmetros ou estratégia")

    def gerar_relatorio_progresso(self, ciclo_atual: int):
        """Gerar relatório de progresso aprimorado"""
        try:
            portfolio_atual, usdt_atual, _ = self.get_portfolio_total()
            
            # Cálculos de performance
            progresso = portfolio_atual - self.portfolio_inicial
            progresso_pct = (progresso / self.portfolio_inicial * 100) if self.portfolio_inicial > 0 else 0
            
            trades_total = len(self.trades_executados)
            oportunidades_total = len(self.oportunidades_perdidas)
            
            logger.info(f"\n--- RELATÓRIO PROGRESSO CICLO {ciclo_atual} ---")
            logger.info(f"Portfolio atual: ${portfolio_atual:.2f}")
            logger.info(f"Progresso: ${progresso:.2f} ({progresso_pct:.2f}%)")
            logger.info(f"Trades executados: {trades_total}")
            logger.info(f"Ciclos sem trade: {self.ciclos_sem_trade}")
            logger.info(f"Oportunidades perdidas: {oportunidades_total}")
            
            # ANÁLISE E RECOMENDAÇÕES
            if trades_total == 0 and ciclo_atual >= 5:
                logger.warning("CRÍTICO: Nenhum trade executado em 5+ ciclos")
                logger.warning("Considerar: RSI threshold mais alto ou menos reserva")
            
            if oportunidades_total > trades_total * 3:
                logger.warning("Muitas oportunidades perdidas vs trades")
                logger.warning("Possível problema: Capital insuficiente ou muito conservador")
            
            if progresso < -5:  # Perda > $5
                logger.warning(f"Performance negativa: ${progresso:.2f}")
                logger.warning("Revisar estratégia de entrada/saída")
                
            logger.info("----------------------------------------")
            
        except Exception as e:
            logger.error(f"Erro no relatório de progresso: {e}")

    def executar_trading_loop(self, max_cycles=50, cycle_interval=180):
        """Loop principal de trading com correções"""
        try:
            # Estado inicial
            self.portfolio_inicial, self.usdt_inicial, _ = self.get_portfolio_total()
            logger.info(f"Portfolio inicial total: ${self.portfolio_inicial:.2f}")
            logger.info(f"USDT inicial: ${self.usdt_inicial:.2f}")
            
            logger.info("==================================================")
            
            for ciclo in range(1, max_cycles + 1):
                logger.info(f"=== CICLO {ciclo} ===")
                
                self.analisar_oportunidades_melhorado()
                
                # Relatório a cada 5 ciclos
                if ciclo % 5 == 0:
                    self.gerar_relatorio_progresso(ciclo)
                
                # Pausa entre ciclos (exceto no último)
                if ciclo < max_cycles:
                    logger.info(f"Aguardando próximo ciclo ({cycle_interval//60} min)...")
                    time.sleep(cycle_interval)
            
            self.gerar_relatorio_final()
            
        except KeyboardInterrupt:
            logger.info("Sistema interrompido")
            self.gerar_relatorio_final()
        except Exception as e:
            logger.error(f"Erro crítico no loop: {e}")
            self.gerar_relatorio_final()

    def gerar_relatorio_final(self):
        """Relatório final com análises detalhadas"""
        try:
            portfolio_final, usdt_final, portfolio_details = self.get_portfolio_total()
            
            logger.info("==================================================")
            logger.info("RELATÓRIO FINAL DETALHADO - TRADING CORRIGIDO")
            logger.info("==================================================")
            
            # Performance
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
            
            # Estatísticas
            trades_total = len(self.trades_executados)
            oportunidades_total = len(self.oportunidades_perdidas)
            
            logger.info(f"\nESTATÍSTICAS DE TRADING:")
            logger.info(f"Trades executados: {trades_total}")
            logger.info(f"Oportunidades perdidas: {oportunidades_total}")
            logger.info(f"RSI mínimo encontrado: {self.melhor_rsi_encontrado['buy']:.1f}")
            
            # Oportunidades perdidas (últimas 5)
            if self.oportunidades_perdidas:
                logger.info(f"\nOPORTUNIDADES PERDIDAS (últimas 5):")
                for opp in self.oportunidades_perdidas[-5:]:
                    logger.info(f"  {opp['symbol']}: RSI {opp['rsi']:.1f}, Conf {opp['confianca']:.1f}% - {opp['motivo']}")
            
            # Trades executados
            if self.trades_executados:
                logger.info(f"\nTRADES EXECUTADOS:")
                for trade in self.trades_executados:
                    timestamp_str = trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    logger.info(f"  {trade['symbol']}: ${trade['valor']:.2f} - {timestamp_str}")
            
            # Recomendações finais
            logger.info(f"\nRECOMENDAÇÕES FINAIS:")
            
            if trades_total == 0:
                logger.info("- CRÍTICO: Sistema muito conservador - zero trades!")
                logger.info("- Sugestão: Aumentar RSI threshold para 40 ou reduzir confiança mínima")
            elif resultado < 0:
                logger.info(f"- Performance negativa: {resultado_pct:.1f}%")
                logger.info("- Considerar implementar stop-loss automático")
                logger.info("- Revisar timing de entrada nos trades")
            else:
                logger.info(f"- Performance positiva: {resultado_pct:.1f}%")
                logger.info("- Sistema funcionando adequadamente")
            
            if oportunidades_total > trades_total * 2:
                logger.info("- Muitas oportunidades perdidas")
                logger.info("- Considerar reduzir reserva ou aumentar capital")
            
            logger.info("==================================================")
            
        except Exception as e:
            logger.error(f"Erro no relatório final: {e}")

def main():
    """Função principal"""
    logger.info("Carregando configuração...")
    
    # Credenciais CONTA_3 (Amos) - que funcionavam
    API_KEY = "TKrbHDhUh5VxlBGWPQLZ3PhdaH0K9WGcRu5jwMJzg7hkaOSmcKHVqRMKBbiKSPOC"
    SECRET_KEY = "YJJwfVhRU0eJyf3PigFybsD3UHZW0aXUNfQb7beeT9x7TTu6sLhhfAKVi1G7A27l"
    
    try:
        trader = TradingCorrigido(API_KEY, SECRET_KEY, "AMOS_CORRIGIDO")
        trader.executar_trading_loop(max_cycles=50, cycle_interval=180)
    except Exception as e:
        logger.error(f"Erro crítico: {e}")

if __name__ == "__main__":
    main()