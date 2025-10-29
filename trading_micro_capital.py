#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TRADING MICRO CAPITAL - Solução para capital baixo
Adaptado para funcionar com USDT limitado ($2.34)
Versão otimizada para trades de valor baixo
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

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_micro_capital.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingMicroCapital:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 5000
        
        # CONFIGURAÇÃO PARA MICRO CAPITAL
        self.valor_trade_fixo = 6.0  # Ligeiramente acima do mínimo da Binance
        self.rsi_oversold = 35       # Detectar oversold
        self.confianca_minima = 80   # Confiança mínima para trade
        
        # Controle de estado
        self.trades_executados = []
        self.oportunidades_perdidas = []
        self.melhor_rsi = 100.0
        self.portfolio_inicial = 0
        self.usdt_inicial = 0
        
        logger.info("=== TRADING MICRO CAPITAL INICIADO ===")
        logger.info(f"Valor fixo por trade: ${self.valor_trade_fixo}")
        logger.info("Otimizado para capital limitado")
        logger.info("Focus: RSI extremo + alta confiança")
        
    def _request(self, method, path, params, signed: bool):
        """Requisição original que funcionava"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # Timestamp do servidor Binance
            try:
                r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                if r.status_code == 200:
                    params['timestamp'] = r.json()['serverTime']
                else:
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

    def get_portfolio_info(self):
        """Obter informações do portfolio"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
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
                    try:
                        ticker = self._request('GET', '/api/v3/ticker/price', {'symbol': f"{asset}USDT"}, signed=False)
                        if not ticker.get('error'):
                            price = float(ticker['price'])
                            usd_value = free * price
                            if usd_value > 0.1:
                                total_usd += usd_value
                                portfolio_details[asset] = {'amount': free, 'price': price, 'usd_value': usd_value}
                                logger.info(f"  {asset}: {free:.6f} = ${usd_value:.2f}")
                    except:
                        continue
        
        return total_usd, usdt_balance, portfolio_details

    def calcular_rsi(self, symbol, timeframe='1m', periods=14):
        """Calcular RSI"""
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
        except:
            return None

    def executar_trade_micro(self, symbol, usdt_amount):
        """Executar trade otimizado para micro capital"""
        try:
            logger.info(f">>> EXECUTANDO TRADE MICRO <<<")
            logger.info(f"Símbolo: {symbol}")
            logger.info(f"Valor: ${usdt_amount}")
            
            # Verificar se temos USDT suficiente
            portfolio_total, usdt_disponivel, _ = self.get_portfolio_info()
            
            if usdt_disponivel < usdt_amount:
                logger.error(f"USDT insuficiente: Disponível ${usdt_disponivel:.2f}, necessário ${usdt_amount}")
                return False
            
            # Executar ordem
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{usdt_amount:.2f}"
            }
            
            logger.info(f"Parâmetros da ordem: {params}")
            
            result = self._request('POST', '/api/v3/order', params, signed=True)
            
            if result.get('error'):
                logger.error(f"Erro na execução: {result}")
                return False
            
            # Trade executado com sucesso!
            logger.info("🎉 TRADE EXECUTADO COM SUCESSO!")
            logger.info(f"Order ID: {result.get('orderId')}")
            logger.info(f"Status: {result.get('status')}")
            
            # Calcular quantidade comprada
            if 'fills' in result:
                qty_total = sum(float(fill['qty']) for fill in result['fills'])
                price_avg = sum(float(fill['price']) * float(fill['qty']) for fill in result['fills']) / qty_total
                logger.info(f"Quantidade: {qty_total:.8f}")
                logger.info(f"Preço médio: ${price_avg:.6f}")
            
            # Registrar trade
            self.trades_executados.append({
                'symbol': symbol,
                'valor': usdt_amount,
                'timestamp': datetime.now(),
                'order_id': result.get('orderId'),
                'status': 'SUCCESS'
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Erro crítico na execução: {e}")
            return False

    def buscar_melhor_oportunidade(self):
        """Buscar a melhor oportunidade no mercado"""
        symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        portfolio_total, usdt_disponivel, _ = self.get_portfolio_info()
        logger.info(f"Portfolio total: ${portfolio_total:.2f}")
        logger.info(f"USDT disponível: ${usdt_disponivel:.2f}")
        
        if usdt_disponivel < self.valor_trade_fixo:
            logger.warning(f"Capital insuficiente: ${usdt_disponivel:.2f} < ${self.valor_trade_fixo}")
            logger.warning("RECOMENDAÇÃO: Vender parte do SOL para liberar USDT")
            return
        
        melhor_oportunidade = None
        melhor_score = 0
        
        for symbol in symbols:
            rsi = self.calcular_rsi(symbol)
            
            if rsi is None:
                continue
            
            # Atualizar melhor RSI
            if rsi < self.melhor_rsi:
                self.melhor_rsi = rsi
                logger.info(f"🔥 Novo RSI mínimo: {rsi} em {symbol}")
            
            # Calcular confiança
            if rsi <= self.rsi_oversold:
                confianca = min(95, 50 + (self.rsi_oversold - rsi) * 2.5)
                sinal = "COMPRA"
            else:
                confianca = 50
                sinal = "NEUTRO"
            
            logger.info(f"{symbol}: RSI {rsi} | {sinal} | Conf: {confianca:.1f}%")
            
            # Calcular score da oportunidade
            if rsi <= self.rsi_oversold and confianca >= self.confianca_minima:
                score = confianca + (self.rsi_oversold - rsi) * 3  # Peso extra para RSI baixo
                
                if score > melhor_score:
                    melhor_score = score
                    melhor_oportunidade = {
                        'symbol': symbol,
                        'rsi': rsi,
                        'confianca': confianca,
                        'score': score
                    }
            elif rsi <= self.rsi_oversold:
                # Registrar como perdida por confiança
                self.oportunidades_perdidas.append({
                    'symbol': symbol,
                    'rsi': rsi,
                    'confianca': confianca,
                    'motivo': 'confianca_insuficiente'
                })
        
        # Executar a melhor oportunidade
        if melhor_oportunidade:
            logger.info("🎯 EXCELENTE OPORTUNIDADE ENCONTRADA!")
            logger.info(f"Símbolo: {melhor_oportunidade['symbol']}")
            logger.info(f"RSI: {melhor_oportunidade['rsi']}")
            logger.info(f"Confiança: {melhor_oportunidade['confianca']:.1f}%")
            logger.info(f"Score: {melhor_oportunidade['score']:.1f}")
            
            sucesso = self.executar_trade_micro(
                melhor_oportunidade['symbol'], 
                self.valor_trade_fixo
            )
            
            if sucesso:
                logger.info("✅ Trade executado com sucesso!")
                return True
            else:
                logger.error("❌ Falha na execução do trade")
                return False
        else:
            logger.info("⏳ Aguardando melhores oportunidades...")
            return False

    def executar_ciclos_micro(self, max_cycles=20, interval=180):
        """Executar ciclos otimizados para micro capital"""
        try:
            # Estado inicial
            self.portfolio_inicial, self.usdt_inicial, _ = self.get_portfolio_info()
            logger.info(f"Portfolio inicial: ${self.portfolio_inicial:.2f}")
            logger.info(f"USDT inicial: ${self.usdt_inicial:.2f}")
            
            trades_executados = 0
            
            for ciclo in range(1, max_cycles + 1):
                logger.info(f"\n=== CICLO {ciclo} ===")
                
                trade_executado = self.buscar_melhor_oportunidade()
                
                if trade_executado:
                    trades_executados += 1
                    logger.info(f"Trades executados até agora: {trades_executados}")
                    
                    # Se executou um trade, fazer pausa maior para análise
                    if ciclo < max_cycles:
                        logger.info("⏱️ Pausa estendida após trade (5 min)...")
                        time.sleep(300)  # 5 minutos
                else:
                    # Pausa normal
                    if ciclo < max_cycles:
                        logger.info(f"⏱️ Próximo ciclo em {interval//60} minutos...")
                        time.sleep(interval)
            
            self.relatorio_final_micro()
            
        except KeyboardInterrupt:
            logger.info("Sistema interrompido")
            self.relatorio_final_micro()
        except Exception as e:
            logger.error(f"Erro crítico: {e}")
            self.relatorio_final_micro()

    def relatorio_final_micro(self):
        """Relatório final otimizado"""
        try:
            portfolio_final, usdt_final, _ = self.get_portfolio_info()
            
            logger.info("\n" + "="*60)
            logger.info("RELATÓRIO FINAL - TRADING MICRO CAPITAL")
            logger.info("="*60)
            
            resultado = portfolio_final - self.portfolio_inicial
            resultado_pct = (resultado / self.portfolio_inicial * 100) if self.portfolio_inicial > 0 else 0
            
            logger.info(f"Portfolio inicial: ${self.portfolio_inicial:.2f}")
            logger.info(f"Portfolio final: ${portfolio_final:.2f}")
            logger.info(f"Resultado: ${resultado:.2f} ({resultado_pct:+.2f}%)")
            logger.info(f"USDT inicial: ${self.usdt_inicial:.2f}")
            logger.info(f"USDT final: ${usdt_final:.2f}")
            
            trades_total = len(self.trades_executados)
            oportunidades_total = len(self.oportunidades_perdidas)
            
            logger.info(f"\nTrades executados: {trades_total}")
            logger.info(f"Oportunidades perdidas: {oportunidades_total}")
            logger.info(f"Melhor RSI encontrado: {self.melhor_rsi:.1f}")
            
            if trades_total > 0:
                logger.info(f"\nTRADES EXECUTADOS:")
                for i, trade in enumerate(self.trades_executados, 1):
                    timestamp_str = trade['timestamp'].strftime('%H:%M:%S')
                    logger.info(f"{i}. {trade['symbol']}: ${trade['valor']:.2f} - {timestamp_str}")
            
            # Recomendações específicas
            logger.info(f"\nRECOMENDAÇÕES:")
            if trades_total == 0:
                if usdt_final < 6:
                    logger.info("💡 VENDER PARTE DO SOL para liberar mais USDT")
                    logger.info("💡 Considerar reduzir valor mínimo do trade")
                else:
                    logger.info("💡 Aguardar RSI mais extremo (< 30)")
                    logger.info("💡 Mercado pode estar em tendência de alta")
            else:
                logger.info("✅ Sistema funcionando adequadamente")
                if resultado > 0:
                    logger.info("📈 Performance positiva - manter estratégia")
                else:
                    logger.info("📉 Aguardar melhores pontos de entrada")
            
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Erro no relatório: {e}")

def main():
    """Função principal"""
    logger.info("Inicializando Trading Micro Capital...")
    
    # Credenciais CONTA_3 (Amos)
    API_KEY = "TKrbHDhUh5VxlBGWPQLZ3PhdaH0K9WGcRu5jwMJzg7hkaOSmcKHVqRMKBbiKSPOC"
    SECRET_KEY = "YJJwfVhRU0eJyf3PigFybsD3UHZW0aXUNfQb7beeT9x7TTu6sLhhfAKVi1G7A27l"
    
    try:
        trader = TradingMicroCapital(API_KEY, SECRET_KEY)
        trader.executar_ciclos_micro(max_cycles=20, interval=180)  # 20 ciclos, 3 min
    except Exception as e:
        logger.error(f"Erro crítico: {e}")

if __name__ == "__main__":
    main()