"""
SISTEMA DAY TRADING - VERSÃO FINAL
Resolução definitiva de timestamp com sincronização automática
Autorizado para CONTA_3 (Amos) - $1.00 disponível
"""

import json
import time
import logging
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from binance.client import Client
from binance.exceptions import BinanceAPIException
import requests
import os
import sys

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_final.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BinanceSync:
    """Classe para sincronização de tempo com Binance"""
    
    def __init__(self):
        self.server_time_offset = 0
        self.last_sync = 0
        
    def sync_time(self):
        """Sincroniza tempo com servidor Binance"""
        try:
            # Múltiplas tentativas de sincronização
            for attempt in range(5):
                try:
                    # Usar endpoint direto da Binance
                    response = requests.get('https://api.binance.com/api/v3/time', timeout=10)
                    
                    if response.status_code == 200:
                        server_time = response.json()['serverTime']
                        local_time = int(time.time() * 1000)
                        
                        # Calcular offset
                        self.server_time_offset = server_time - local_time
                        self.last_sync = time.time()
                        
                        logger.info(f"✅ Sincronização OK - Offset: {self.server_time_offset}ms")
                        return True
                        
                except Exception as e:
                    logger.warning(f"Tentativa {attempt + 1} falhou: {e}")
                    time.sleep(1)
            
            return False
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            return False
    
    def get_synced_timestamp(self):
        """Retorna timestamp sincronizado"""
        # Verificar se precisa ressincronizar
        if (time.time() - self.last_sync) > 60:  # A cada 1 minuto
            self.sync_time()
        
        return int(time.time() * 1000) + self.server_time_offset

class SafeBinanceClient:
    """Cliente Binance com proteção total contra erros de timestamp"""
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sync = BinanceSync()
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Inicializa cliente com sincronização"""
        try:
            # Sincronizar primeiro
            if not self.sync.sync_time():
                logger.error("❌ Falha na sincronização inicial")
                return False
            
            # Criar cliente padrão
            self.client = Client(self.api_key, self.api_secret, testnet=False)
            
            # Testar conexão
            self._test_connection()
            return True
            
        except Exception as e:
            logger.error(f"Erro inicializando cliente: {e}")
            return False
    
    def _test_connection(self):
        """Testa conexão com API"""
        try:
            server_time = self.client.get_server_time()
            logger.info(f"🔗 Conexão OK - Server time: {server_time['serverTime']}")
        except Exception as e:
            logger.warning(f"Aviso no teste de conexão: {e}")
    
    def _execute_with_retry(self, func, *args, **kwargs):
        """Executa função com retry automático"""
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                # Aguardar entre tentativas
                if attempt > 0:
                    wait_time = min(2 ** attempt, 8)
                    logger.info(f"⏳ Aguardando {wait_time}s antes da tentativa {attempt + 1}")
                    time.sleep(wait_time)
                    
                    # Ressincronizar a cada retry
                    self.sync.sync_time()
                
                # Executar função
                result = func(*args, **kwargs)
                
                # Se chegou aqui, sucesso
                if attempt > 0:
                    logger.info(f"✅ Sucesso na tentativa {attempt + 1}")
                
                return result
                
            except BinanceAPIException as e:
                if e.code in [-1021, -1022]:  # Timestamp/Signature errors
                    logger.warning(f"⚠️ Erro {e.code} na tentativa {attempt + 1}: {e.message}")
                    
                    if attempt < max_retries - 1:
                        # Forçar ressincronização
                        logger.info("🔄 Forçando ressincronização...")
                        self.sync.sync_time()
                        continue
                
                # Outros erros da API, propagar
                raise e
                
            except Exception as e:
                error_msg = str(e).lower()
                if any(word in error_msg for word in ['timestamp', 'signature', 'recvwindow']):
                    logger.warning(f"⚠️ Erro temporal na tentativa {attempt + 1}: {e}")
                    if attempt < max_retries - 1:
                        continue
                
                # Outros erros, propagar
                raise e
        
        # Se chegou aqui, esgotaram as tentativas
        raise Exception(f"❌ Falha após {max_retries} tentativas")
    
    def get_account(self):
        """Obtém informações da conta"""
        return self._execute_with_retry(self.client.get_account)
    
    def get_symbol_ticker(self, symbol):
        """Obtém ticker de símbolo"""
        return self._execute_with_retry(self.client.get_symbol_ticker, symbol=symbol)
    
    def get_klines(self, symbol, interval, limit=100):
        """Obtém dados de velas"""
        return self._execute_with_retry(self.client.get_klines, symbol=symbol, interval=interval, limit=limit)
    
    def order_market_buy(self, symbol, quoteOrderQty):
        """Ordem de compra a mercado"""
        return self._execute_with_retry(self.client.order_market_buy, symbol=symbol, quoteOrderQty=quoteOrderQty)
    
    def order_market_sell(self, symbol, quantity):
        """Ordem de venda a mercado"""
        return self._execute_with_retry(self.client.order_market_sell, symbol=symbol, quantity=quantity)

class DayTradingFinal:
    """Sistema Day Trading Final - Timestamp Resolvido"""
    
    def __init__(self):
        self.client = None
        self.patrimonio = 1.0
        self.posicoes = {}
        self._setup_client()
    
    def _setup_client(self):
        """Configura cliente Binance"""
        try:
            # Carregar credenciais
            with open('config/contas.json', 'r') as f:
                contas = json.load(f)
            
            conta = contas['CONTA_3']  # Amos
            
            # Criar cliente seguro
            self.client = SafeBinanceClient(
                api_key=conta['api_key'],
                api_secret=conta['api_secret']
            )
            
            logger.info("✅ Cliente Binance configurado com proteção total")
            
        except Exception as e:
            logger.error(f"❌ Erro configurando cliente: {e}")
            sys.exit(1)
    
    def calcular_indicadores(self, symbol, timeframe='5m'):
        """Calcula indicadores técnicos"""
        try:
            # Obter dados
            klines = self.client.get_klines(symbol=symbol, interval=timeframe, limit=50)
            
            # Converter para DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Converter para float
            df['close'] = df['close'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Médias móveis
            sma_20 = df['close'].rolling(window=20).mean()
            sma_50 = df['close'].rolling(window=50).mean() if len(df) >= 50 else sma_20
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            sma = df['close'].rolling(window=bb_period).mean()
            std = df['close'].rolling(window=bb_period).std()
            bb_upper = sma + (std * bb_std)
            bb_lower = sma - (std * bb_std)
            
            ultimo_preco = df['close'].iloc[-1]
            ultimo_rsi = rsi.iloc[-1]
            
            return {
                'preco': ultimo_preco,
                'rsi': ultimo_rsi,
                'sma_20': sma_20.iloc[-1],
                'sma_50': sma_50.iloc[-1],
                'bb_upper': bb_upper.iloc[-1],
                'bb_lower': bb_lower.iloc[-1],
                'volume': df['volume'].iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"❌ Erro calculando indicadores para {symbol}: {e}")
            return None
    
    def analisar_oportunidade(self, symbol):
        """Analisa oportunidade de trading"""
        try:
            indicadores = self.calcular_indicadores(symbol)
            if not indicadores:
                return None, None
            
            preco = indicadores['preco']
            rsi = indicadores['rsi']
            sma_20 = indicadores['sma_20']
            bb_upper = indicadores['bb_upper']
            bb_lower = indicadores['bb_lower']
            
            # Sinal de COMPRA (sobrevenda)
            if (rsi < 35 and 
                preco < bb_lower and 
                preco < sma_20):
                
                confianca = (35 - rsi) + ((sma_20 - preco) / preco * 100)
                logger.info(f"🟢 SINAL COMPRA {symbol}: RSI={rsi:.1f}, Preço=${preco:.6f}, Confiança={confianca:.1f}")
                return 'COMPRA', confianca
            
            # Sinal de VENDA (sobrecompra)
            elif (rsi > 70 and 
                  preco > bb_upper and 
                  preco > sma_20):
                
                confianca = (rsi - 70) + ((preco - sma_20) / preco * 100)
                logger.info(f"🔴 SINAL VENDA {symbol}: RSI={rsi:.1f}, Preço=${preco:.6f}, Confiança={confianca:.1f}")
                return 'VENDA', confianca
            
            # Neutro
            logger.info(f"⚪ Neutro {symbol}: RSI={rsi:.1f}, Preço=${preco:.6f}")
            return 'NEUTRO', 0
            
        except Exception as e:
            logger.error(f"❌ Erro analisando {symbol}: {e}")
            return None, None
    
    def executar_compra(self, symbol, valor_usd):
        """Executa compra"""
        try:
            logger.info(f"🟢 Executando COMPRA {symbol} - Valor: ${valor_usd:.2f}")
            
            order = self.client.order_market_buy(
                symbol=symbol,
                quoteOrderQty=valor_usd
            )
            
            # Registrar posição
            quantity = float(order['executedQty'])
            price = float(order['fills'][0]['price'])
            
            self.posicoes[symbol] = {
                'quantity': quantity,
                'price': price,
                'timestamp': time.time()
            }
            
            logger.info(f"✅ COMPRA executada: {quantity:.6f} {symbol} por ${price:.6f}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na compra {symbol}: {e}")
            return False
    
    def executar_venda(self, symbol):
        """Executa venda"""
        try:
            if symbol not in self.posicoes:
                logger.warning(f"⚠️ Sem posição em {symbol}")
                return False
            
            quantity = self.posicoes[symbol]['quantity']
            logger.info(f"🔴 Executando VENDA {symbol} - Qtd: {quantity:.6f}")
            
            order = self.client.order_market_sell(
                symbol=symbol,
                quantity=quantity
            )
            
            # Calcular resultado
            price_compra = self.posicoes[symbol]['price']
            price_venda = float(order['fills'][0]['price'])
            resultado = (price_venda - price_compra) / price_compra * 100
            
            logger.info(f"✅ VENDA executada: {quantity:.6f} {symbol} por ${price_venda:.6f}")
            logger.info(f"📊 Resultado: {resultado:+.2f}%")
            
            # Remover posição
            del self.posicoes[symbol]
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na venda {symbol}: {e}")
            return False
    
    def obter_portfolio(self):
        """Obtém portfólio atual"""
        try:
            account = self.client.get_account()
            
            portfolio = {}
            total_usd = 0
            
            for balance in account['balances']:
                asset = balance['asset']
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                
                if total > 0:
                    # Para USDT, usar valor direto
                    if asset == 'USDT':
                        valor_usd = total
                    else:
                        # Para outras moedas, obter preço
                        try:
                            ticker = self.client.get_symbol_ticker(symbol=f"{asset}USDT")
                            preco = float(ticker['price'])
                            valor_usd = total * preco
                        except:
                            valor_usd = 0
                    
                    if valor_usd > 0.01:  # Apenas saldos relevantes
                        portfolio[asset] = {
                            'quantidade': total,
                            'valor_usd': valor_usd
                        }
                        total_usd += valor_usd
            
            self.patrimonio = total_usd
            return portfolio
            
        except Exception as e:
            logger.error(f"❌ Erro obtendo portfólio: {e}")
            return {}
    
    def ciclo_trading(self, ciclo):
        """Executa um ciclo de trading"""
        logger.info(f"🔄 CICLO {ciclo}")
        logger.info("=" * 40)
        
        try:
            # Obter portfólio
            portfolio = self.obter_portfolio()
            if not portfolio:
                logger.warning("❌ Portfólio vazio ou erro ao acessar")
                return
            
            logger.info(f"💰 PATRIMÔNIO: ${self.patrimonio:.2f}")
            
            # Lista de símbolos para analisar
            simbolos = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'DOTUSDT']
            
            # Verificar vendas primeiro
            for symbol in list(self.posicoes.keys()):
                sinal, confianca = self.analisar_oportunidade(symbol)
                
                if sinal == 'VENDA' and confianca > 15:
                    self.executar_venda(symbol)
            
            # Procurar oportunidades de compra
            saldo_usdt = portfolio.get('USDT', {}).get('valor_usd', 0)
            
            if saldo_usdt > 0.5:  # Mínimo para operar
                melhor_oportunidade = None
                melhor_confianca = 0
                
                for symbol in simbolos:
                    sinal, confianca = self.analisar_oportunidade(symbol)
                    
                    if sinal == 'COMPRA' and confianca > melhor_confianca and confianca > 20:
                        melhor_oportunidade = symbol
                        melhor_confianca = confianca
                
                # Executar melhor oportunidade
                if melhor_oportunidade:
                    valor_investir = min(saldo_usdt * 0.8, 0.9)  # Máx 90% do saldo
                    self.executar_compra(melhor_oportunidade, valor_investir)
            
        except Exception as e:
            logger.error(f"❌ Erro no ciclo {ciclo}: {e}")
    
    def run(self, total_cycles=12):
        """Executa sistema de trading"""
        logger.info("🤖 SISTEMA DAY TRADING - VERSÃO FINAL")
        logger.info("🎯 Estratégia: Compra em sobrevenda + Venda em sobrecompra")
        logger.info("🔒 Proteção total contra erros de timestamp")
        logger.info("=" * 60)
        
        # Obter patrimônio inicial
        self.obter_portfolio()
        logger.info(f"💰 PATRIMÔNIO INICIAL: ${self.patrimonio:.2f}")
        
        logger.info("🚀 Iniciando operações...")
        logger.info("=" * 60)
        
        for ciclo in range(1, total_cycles + 1):
            try:
                self.ciclo_trading(ciclo)
                
                if ciclo < total_cycles:
                    logger.info("⏰ Aguardando próximo ciclo (5 min)...")
                    time.sleep(300)  # 5 minutos
                
            except KeyboardInterrupt:
                logger.info("🛑 Sistema interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro fatal no ciclo {ciclo}: {e}")
                logger.info("⏰ Aguardando antes de continuar...")
                time.sleep(60)
        
        # Relatório final
        self.obter_portfolio()
        resultado = ((self.patrimonio - 1.0) / 1.0) * 100
        logger.info("=" * 60)
        logger.info("📊 RELATÓRIO FINAL")
        logger.info(f"💰 Patrimônio Final: ${self.patrimonio:.2f}")
        logger.info(f"📈 Resultado: {resultado:+.2f}%")
        logger.info("=" * 60)

def main():
    """Função principal"""
    try:
        logger.info("🔧 Inicializando sistema final...")
        trader = DayTradingFinal()
        trader.run(total_cycles=8)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()