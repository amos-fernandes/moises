"""
SISTEMA DAY TRADING - VERSAO ORIGINAL FUNCIONANDO
Baseado no moises_estrategias_avancadas.py que estava funcionando sem erros de timestamp
Autorizado para CONTA_3 (Amos) - $1.00 disponivel
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

# Configuracao de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_original.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingOriginal:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        self.server_time_offset = 0
        
        # Sistema de monitoramento avancado
        self.trades_executados = []
        self.oportunidades_perdidas = []
        self.performance_historico = []
        self.melhor_rsi_encontrado = {'buy': 100, 'sell': 0}
        self.ciclos_sem_trade = 0
        self.total_lucro = 0
        
        logger.info(f"Trading Original iniciado - {conta_nome}")
        logger.info("Monitoramento avancado ativado")
    
    def _request(self, method, path, params, signed: bool):
        """Requisicao original que funcionava sem erros de timestamp"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # Obter timestamp da Binance para garantir precisao - METODO ORIGINAL
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
        """Obter saldo USDT disponivel"""
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
            return 0
        
        total_value = 0
        portfolio_details = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    # USDT tem valor 1:1
                    value_usdt = total
                else:
                    # Obter preco atual de outras criptos
                    try:
                        ticker_symbol = f"{asset}USDT"
                        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={ticker_symbol}", timeout=5)
                        if r.status_code == 200:
                            price = float(r.json()['price'])
                            value_usdt = total * price
                        else:
                            value_usdt = 0
                    except:
                        value_usdt = 0
                
                if value_usdt > 0.01:  # Apenas valores relevantes (> $0.01)
                    total_value += value_usdt
                    portfolio_details[asset] = {
                        'quantidade': total,
                        'valor_usdt': value_usdt,
                        'free': free,
                        'locked': locked
                    }
        
        # Log do portfolio detalhado
        logger.info(f"Portfolio total: ${total_value:.2f}")
        for asset, details in portfolio_details.items():
            logger.info(f"  {asset}: {details['quantidade']:.6f} = ${details['valor_usdt']:.2f}")
        
        return total_value
    
    def get_candles_rapidos(self, symbol: str, interval: str, limit: int = 50):
        """Obter candles para analise rapida"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            r.raise_for_status()
            
            candles = []
            for kline in r.json():
                candles.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Erro ao obter candles {symbol}: {e}")
            return []
    
    def calcular_rsi_rapido(self, prices, period=14):
        """RSI otimizado para trading rapido"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def analisar_simbolo(self, symbol):
        """Analise simples de um simbolo"""
        candles = self.get_candles_rapidos(symbol, '5m', 20)
        if len(candles) < 20:
            return None
        
        closes = [c['close'] for c in candles]
        preco_atual = closes[-1]
        rsi = self.calcular_rsi_rapido(closes)
        
        # Media movel simples
        sma_10 = np.mean(closes[-10:])
        
        # Logica mais agressiva para encontrar oportunidades
        sinal = None
        confianca = 0
        
        if rsi < 35:  # Oversold mais amplo
            sinal = 'COMPRA'
            confianca = 70 + (35 - rsi) * 1.5
        elif rsi > 65:  # Overbought mais amplo
            sinal = 'VENDA'
            confianca = 70 + (rsi - 65) * 1.5
        else:
            sinal = 'NEUTRO'
            confianca = 50
        
        # Bonus de confianca se preco esta abaixo da media movel
        if preco_atual < sma_10 and sinal == 'COMPRA':
            confianca += 10
        
        confianca = min(95, confianca)  # Limitar a 95%
        
        # Registrar RSI extremos para monitoramento
        if rsi < self.melhor_rsi_encontrado['buy'] and sinal == 'COMPRA':
            self.melhor_rsi_encontrado['buy'] = rsi
            logger.info(f"Novo RSI minimo encontrado: {rsi:.1f} em {symbol}")
        
        if rsi > self.melhor_rsi_encontrado['sell'] and sinal == 'VENDA':
            self.melhor_rsi_encontrado['sell'] = rsi
            logger.info(f"Novo RSI maximo encontrado: {rsi:.1f} em {symbol}")
        
        return {
            'symbol': symbol,
            'preco': preco_atual,
            'rsi': rsi,
            'sma_10': sma_10,
            'sinal': sinal,
            'confianca': confianca
        }
    
    def executar_compra(self, symbol, valor_usdt):
        """Executar compra usando o metodo original"""
        try:
            logger.info(f"Executando compra {symbol} - ${valor_usdt:.2f}")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_usdt:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"Erro na compra: {resultado}")
                return None
            
            logger.info(f"Compra executada: Order ID {resultado.get('orderId')}")
            logger.info(f"Quantidade: {resultado.get('executedQty')}")
            
            # Registrar trade para monitoramento
            trade_info = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'order_id': resultado.get('orderId'),
                'valor_usdt': valor_usdt,
                'quantidade': resultado.get('executedQty'),
                'tipo': 'COMPRA'
            }
            self.trades_executados.append(trade_info)
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro executando compra: {e}")
            return None
    
    def ciclo_trading(self, ciclo):
        """Um ciclo completo de trading"""
        logger.info(f"=== CICLO {ciclo} ===")
        
        # Verificar portfolio total
        portfolio_total = self.get_portfolio_total()
        saldo_usdt = self.get_saldo_usdt()
        
        logger.info(f"Portfolio total: ${portfolio_total:.2f}")
        logger.info(f"USDT disponivel: ${saldo_usdt:.2f}")
        
        if saldo_usdt < 0.5:
            logger.warning("USDT insuficiente para trades")
            return True  # Continuar monitorando, pode ter outras criptos
        
        # Analisar simbolos principais
        simbolos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        
        melhor_oportunidade = None
        melhor_confianca = 0
        
        for symbol in simbolos:
            analise = self.analisar_simbolo(symbol)
            
            if analise:
                logger.info(f"{symbol}: RSI {analise['rsi']:.1f} | Sinal: {analise['sinal']} | Conf: {analise['confianca']:.1f}%")
                
                # Registrar oportunidade perdida se for boa mas nao a melhor
                if analise['sinal'] == 'COMPRA' and analise['confianca'] > 70:
                    if analise['confianca'] > melhor_confianca:
                        if melhor_oportunidade:  # Se havia uma anterior, registrar como perdida
                            self.oportunidades_perdidas.append({
                                'ciclo': ciclo,
                                'symbol': melhor_oportunidade['symbol'],
                                'rsi': melhor_oportunidade['rsi'],
                                'confianca': melhor_oportunidade['confianca'],
                                'motivo': 'substituida_por_melhor'
                            })
                        melhor_oportunidade = analise
                        melhor_confianca = analise['confianca']
                    else:
                        self.oportunidades_perdidas.append({
                            'ciclo': ciclo,
                            'symbol': analise['symbol'],
                            'rsi': analise['rsi'],
                            'confianca': analise['confianca'],
                            'motivo': 'confianca_insuficiente'
                        })
        
        # Se encontrou boa oportunidade (limiar reduzido)
        if melhor_oportunidade and melhor_confianca > 75:
            symbol = melhor_oportunidade['symbol']
            logger.info(f"Oportunidade: {symbol} - RSI {melhor_oportunidade['rsi']:.1f} - Confianca {melhor_confianca:.1f}%")
            
            # Calcular valor do trade baseado no USDT disponivel
            if saldo_usdt >= 1.0:  # Aumentar mínimo para $1
                # Valor mais conservador e acima do mínimo da Binance
                if saldo_usdt > 10:
                    valor_trade = min(saldo_usdt * 0.15, 2.0)  # Max $2 ou 15% do USDT
                else:
                    valor_trade = min(saldo_usdt * 0.10, 1.0)  # Max $1 ou 10% do USDT
                
                # Garantir valor mínimo da Binance (aproximadamente $5-10)
                valor_trade = max(valor_trade, 5.0)
                
                if valor_trade <= saldo_usdt and valor_trade >= 5.0:
                    resultado = self.executar_compra(symbol, valor_trade)
                    self.ciclos_sem_trade = 0  # Reset contador
                    return resultado is not None
                else:
                    logger.info(f"Valor ajustado: ${valor_trade:.2f} (disponível: ${saldo_usdt:.2f})")
                    self.ciclos_sem_trade += 1
            else:
                logger.info("USDT insuficiente para trade (mínimo $1)")
                self.ciclos_sem_trade += 1
        
        logger.info("Aguardando melhores oportunidades...")
        self.ciclos_sem_trade += 1
        
        # Alertar se muitos ciclos sem trade
        if self.ciclos_sem_trade >= 5:
            logger.warning(f"ALERTA: {self.ciclos_sem_trade} ciclos consecutivos sem trades!")
            logger.warning("Considerar ajustar parametros ou estrategia")
        
        return True
    
    def run(self, max_ciclos=10):
        """Executar sistema de trading"""
        logger.info("=== SISTEMA DAY TRADING - VERSAO ORIGINAL ===")
        logger.info("Metodo de timestamp que funcionava sem erros")
        logger.info("Estrategia: RSI oversold + SMA")
        logger.info("Portfolio: USDT + SOL + outras criptos")
        logger.info("=" * 50)
        
        portfolio_inicial = self.get_portfolio_total()
        saldo_usdt_inicial = self.get_saldo_usdt()
        
        logger.info(f"Portfolio inicial total: ${portfolio_inicial:.2f}")
        logger.info(f"USDT inicial: ${saldo_usdt_inicial:.2f}")
        
        if portfolio_inicial < 0.5:
            logger.error("Portfolio insuficiente para operar")
            return
        
        for ciclo in range(1, max_ciclos + 1):
            try:
                sucesso = self.ciclo_trading(ciclo)
                
                if not sucesso:
                    logger.info("Parando sistema")
                    break
                
                # Relatorio de progresso a cada 5 ciclos
                if ciclo % 5 == 0:
                    portfolio_atual = self.get_portfolio_total()
                    progresso = portfolio_atual - portfolio_inicial
                    logger.info(f"\n--- RELATORIO PROGRESSO CICLO {ciclo} ---")
                    logger.info(f"Portfolio atual: ${portfolio_atual:.2f}")
                    logger.info(f"Progresso: ${progresso:+.2f} ({(progresso/portfolio_inicial)*100:+.2f}%)")
                    logger.info(f"Trades executados: {len(self.trades_executados)}")
                    logger.info(f"Ciclos sem trade: {self.ciclos_sem_trade}")
                    logger.info(f"Oportunidades perdidas: {len(self.oportunidades_perdidas)}")
                    logger.info("----------------------------------------\n")
                
                if ciclo < max_ciclos:
                    logger.info("Aguardando proximo ciclo (3 min)...")
                    time.sleep(180)  # 3 minutos
                
            except KeyboardInterrupt:
                logger.info("Sistema interrompido")
                break
            except Exception as e:
                logger.error(f"Erro no ciclo {ciclo}: {e}")
                time.sleep(60)
        
        # Portfolio final
        portfolio_final = self.get_portfolio_total()
        saldo_usdt_final = self.get_saldo_usdt()
        
        lucro_total = portfolio_final - portfolio_inicial
        lucro_usdt = saldo_usdt_final - saldo_usdt_inicial
        
        percentual_total = (lucro_total / portfolio_inicial) * 100 if portfolio_inicial > 0 else 0
        
        logger.info("=" * 50)
        logger.info("RELATORIO FINAL DETALHADO")
        logger.info("=" * 50)
        logger.info("PERFORMANCE FINANCEIRA:")
        logger.info(f"Portfolio inicial: ${portfolio_inicial:.2f}")
        logger.info(f"Portfolio final: ${portfolio_final:.2f}")
        logger.info(f"USDT inicial: ${saldo_usdt_inicial:.2f}")
        logger.info(f"USDT final: ${saldo_usdt_final:.2f}")
        logger.info(f"Resultado total: ${lucro_total:+.2f} ({percentual_total:+.2f}%)")
        logger.info(f"Variacao USDT: ${lucro_usdt:+.2f}")
        
        logger.info("\nESTATISTICAS DE TRADING:")
        logger.info(f"Trades executados: {len(self.trades_executados)}")
        logger.info(f"Oportunidades perdidas: {len(self.oportunidades_perdidas)}")
        logger.info(f"Ciclos sem trades: {self.ciclos_sem_trade}")
        logger.info(f"RSI minimo encontrado: {self.melhor_rsi_encontrado['buy']:.1f}")
        logger.info(f"RSI maximo encontrado: {self.melhor_rsi_encontrado['sell']:.1f}")
        
        if len(self.oportunidades_perdidas) > 0:
            logger.info("\nOPORTUNIDADES PERDIDAS (ultimas 5):")
            for op in self.oportunidades_perdidas[-5:]:
                logger.info(f"  {op['symbol']}: RSI {op['rsi']:.1f}, Conf {op['confianca']:.1f}% - {op['motivo']}")
        
        if len(self.trades_executados) > 0:
            logger.info("\nTRADES EXECUTADOS:")
            for trade in self.trades_executados:
                logger.info(f"  {trade['symbol']}: ${trade['valor_usdt']:.2f} - {trade['timestamp']}")
        
        logger.info("\nRECOMENDACAOES DE MELHORIA:")
        if len(self.trades_executados) == 0:
            logger.info("- Considerar reduzir limiar de confianca (atual: 75%)")
            logger.info("- Considerar ampliar RSI oversold (atual: < 35)")
            
        if self.ciclos_sem_trade > 5:
            logger.info("- Sistema muito conservador, poucos trades")
            logger.info("- Considerar estrategias mais agressivas")
            
        if len(self.oportunidades_perdidas) > len(self.trades_executados) * 3:
            logger.info("- Muitas oportunidades perdidas vs trades executados")
            logger.info("- Revisar logica de selecao de trades")
        
        logger.info("=" * 50)

def main():
    """Funcao principal"""
    try:
        logger.info("Carregando configuracao...")
        
        with open('config/contas.json', 'r') as f:
            contas = json.load(f)
        
        conta = contas['CONTA_3']  # Amos
        
        trader = TradingOriginal(
            api_key=conta['api_key'],
            api_secret=conta['api_secret'],
            conta_nome="AMOS_ORIGINAL"
        )
        
        logger.info("Sistema configurado - metodo original")
        trader.run(max_ciclos=50)  # Monitoramento estendido
        
    except Exception as e:
        logger.error(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()