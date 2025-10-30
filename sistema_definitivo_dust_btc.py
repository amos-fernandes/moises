#!/usr/bin/env python3
"""
SISTEMA DEFINITIVO DUST BTC CORRIGIDO - PARA CRIANCAS FAMINTAS
Versao final sem emojis, com timestamp corrigido e deteccao dust BTC
Ultra-agressivo com conversao inteligente para resolver dust BTC
"""

import os
import time
import numpy as np
import requests
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import talib
import logging
from datetime import datetime
import traceback
import threading
from threading import Lock

# Configuracao de Logging SEM EMOJIS
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('atcoin_definitivo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SistemaDefinitivoDustBTC:
    def __init__(self):
        # Chaves API Binance
        self.api_key = 'wgdJDvHxJF8JdKbMbfeUoJlN7VTe0ldyX9rUnJHaGg3AA7SYSfsxdpefwhjy17HP'
        self.api_secret = 'KYXYZKUmE0t6jpyMdTnMSE6skLgTZtClNqZNOJl4lPKCci5p5KgKJnJoyBevK5J8'
        
        # CONFIGURACAO DUST BTC
        self.MIN_TRADE_VALUE = 10.2  # Valor minimo Binance (USD)
        self.DUST_BTC_THRESHOLD = 0.00016  # Threshold para BTC dust
        self.MIN_USDT_FOR_TRADE = 10.2  # Minimo USDT para trades
        
        # PARAMETROS ULTRA-AGRESSIVOS - CRIANCAS DEPENDEM DISSO!
        self.SCORE_VENDA_MIN = 15  # Ultra baixo para dust
        self.SCORE_COMPRA_MIN = 15
        self.TAKE_PROFIT_1 = 0.12  # 0.12% ultra micro
        self.TAKE_PROFIT_2 = 0.28  # 0.28% micro  
        self.TAKE_PROFIT_3 = 0.55  # 0.55% pequeno
        self.STOP_LOSS = 0.25  # 0.25% stop ultra tight
        self.CAPITAL_PER_TRADE = 0.99  # 99% do capital
        
        # CONFIGURACAO DE CICLO
        self.CYCLE_DELAY = 4  # 4 segundos entre ciclos
        
        self.client = None
        self.inicializar_client()
        self.lock = Lock()
        self.executando = True
        self.capital_inicial = 0.0
        
        # Estado do sistema
        self.estado_dust = False
        self.ultima_conversao = 0
        self.conversoes_realizadas = 0
        
    def inicializar_client(self):
        """Inicializar cliente Binance com timestamp corrigido"""
        try:
            # Cliente com timestamp offset para corrigir sync
            self.client = Client(
                self.api_key, 
                self.api_secret,
                requests_params={'timeout': 60}
            )
            
            # Testar conexao e sincronizar timestamp
            server_time = self.client.get_server_time()
            local_time = int(time.time() * 1000)
            self.time_offset = server_time['serverTime'] - local_time
            
            logger.info("CLIENT BINANCE INICIALIZADO COM SUCESSO!")
            logger.info(f"Time offset: {self.time_offset}ms")
            return True
            
        except Exception as e:
            logger.error(f"ERRO ao inicializar cliente: {e}")
            return False
        
    def obter_saldo_conta(self):
        """Obter saldos com retry e timestamp corrigido"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Adicionar timestamp offset
                params = {}
                if hasattr(self, 'time_offset'):
                    params['timestamp'] = int(time.time() * 1000) + self.time_offset
                
                account = self.client.get_account(**params)
                saldos = {}
                
                for asset in account['balances']:
                    free = float(asset['free'])
                    locked = float(asset['locked'])
                    total = free + locked
                    
                    if total > 0:
                        saldos[asset['asset']] = {
                            'free': free,
                            'locked': locked, 
                            'total': total
                        }
                        
                return saldos
                
            except BinanceAPIException as e:
                if '-1021' in str(e):  # Timestamp error
                    logger.warning(f"Erro timestamp attempt {attempt+1}, resincing...")
                    time.sleep(1)
                    try:
                        server_time = self.client.get_server_time()
                        local_time = int(time.time() * 1000)
                        self.time_offset = server_time['serverTime'] - local_time
                    except:
                        pass
                else:
                    logger.error(f"API Error attempt {attempt+1}: {e}")
                    
                if attempt == max_retries - 1:
                    return {}
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                logger.error(f"ERRO obter saldo attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    return {}
                time.sleep(1)

    def converter_dust_btc_para_usdt(self):
        """CONVERSAO CRITICA DE DUST BTC PARA USDT"""
        try:
            saldos = self.obter_saldo_conta()
            
            if 'BTC' not in saldos:
                logger.info("SEM BTC para conversao")
                return False
                
            btc_livre = saldos['BTC']['free']
            
            # DETECCAO DE DUST BTC
            if btc_livre < self.DUST_BTC_THRESHOLD:
                logger.info(f"DUST BTC DETECTADO! {btc_livre:.8f} BTC")
                
                # Obter preco atual BTC/USDT
                ticker = self.client.get_symbol_ticker(symbol='BTCUSDT')
                preco_btc = float(ticker['price'])
                valor_usd = btc_livre * preco_btc
                
                logger.info(f"Valor dust: ${valor_usd:.2f}")
                
                if valor_usd >= 7.0:  # Se valor >= $7 tenta conversao forcada
                    return self._tentar_conversao_forcada_btc(btc_livre, preco_btc)
                else:
                    logger.info("Dust BTC muito pequeno para conversao ($<7)")
                    return False
            
            # BTC NORMAL - Conversao padrao
            if btc_livre >= self.DUST_BTC_THRESHOLD:
                return self._executar_venda_btc_normal(btc_livre)
                
            return False
            
        except Exception as e:
            logger.error(f"ERRO conversao dust: {e}")
            return False

    def _tentar_conversao_forcada_btc(self, btc_quantidade, preco_btc):
        """CONVERSAO FORCADA DE DUST BTC"""
        try:
            # Estrategias multiplas para dust
            estrategias = [
                # 1. Venda market com quantidade exata
                lambda: self._venda_market_exata(btc_quantidade),
                # 2. Venda com quantidade ajustada -2%
                lambda: self._venda_market_ajustada(btc_quantidade * 0.98),
                # 3. Venda com quantidade ajustada -5%
                lambda: self._venda_market_ajustada(btc_quantidade * 0.95),
                # 4. Venda minima possivel
                lambda: self._venda_market_minima(),
            ]
            
            for i, estrategia in enumerate(estrategias):
                logger.info(f"Tentando estrategia {i+1}/4 para dust...")
                try:
                    if estrategia():
                        logger.info(f"SUCESSO estrategia {i+1}!")
                        self.conversoes_realizadas += 1
                        return True
                except Exception as e:
                    logger.warning(f"Estrategia {i+1} falhou: {e}")
                    
            logger.error("TODAS estrategias falharam para dust BTC")
            return False
            
        except Exception as e:
            logger.error(f"ERRO conversao forcada: {e}")
            return False

    def _venda_market_exata(self, quantidade):
        """Venda market com quantidade exata"""
        ordem = self.client.order_market_sell(
            symbol='BTCUSDT',
            quantity=f"{quantidade:.8f}"
        )
        logger.info(f"VENDA market exata: {quantidade:.8f} BTC")
        return True

    def _venda_market_ajustada(self, quantidade):
        """Venda market com quantidade ajustada"""
        # Arredondar para baixo para evitar insufficient balance
        quantidade_ajustada = round(quantidade, 6)  # 6 decimais
        
        ordem = self.client.order_market_sell(
            symbol='BTCUSDT', 
            quantity=f"{quantidade_ajustada:.6f}"
        )
        logger.info(f"VENDA ajustada: {quantidade_ajustada:.6f} BTC")
        return True

    def _venda_market_minima(self):
        """Tentativa de venda com quantidade minima calculada"""
        try:
            # Obter info do simbolo para quantidade minima
            info = self.client.get_symbol_info('BTCUSDT')
            min_qty = None
            
            for f in info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    min_qty = float(f['minQty'])
                    break
                    
            if min_qty:
                logger.info(f"Tentando venda com quantidade minima: {min_qty}")
                ordem = self.client.order_market_sell(
                    symbol='BTCUSDT',
                    quantity=f"{min_qty:.8f}"
                )
                return True
            return False
        except Exception as e:
            logger.error(f"Erro venda minima: {e}")
            return False

    def _executar_venda_btc_normal(self, btc_quantidade):
        """Executar venda BTC normal (nao dust)"""
        try:
            # Quantidade para venda (deixa small buffer)
            quantidade_venda = round(btc_quantidade * 0.998, 6)
            
            if quantidade_venda <= 0:
                logger.error("Quantidade venda <= 0")
                return False
            
            ordem = self.client.order_market_sell(
                symbol='BTCUSDT',
                quantity=f"{quantidade_venda:.6f}"
            )
            
            logger.info(f"VENDA BTC NORMAL: {quantidade_venda:.6f} BTC")
            return True
            
        except Exception as e:
            logger.error(f"ERRO venda BTC normal: {e}")
            return False

    def calcular_score_venda_dust(self):
        """Score de venda adaptado para situacoes de dust"""
        try:
            # Obter dados de mercado com retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    klines = self.client.get_klines(symbol='BTCUSDT', interval='1m', limit=100)
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Erro obter klines: {e}")
                        return 25  # Score default para dust
                    time.sleep(1)
            
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])
            
            # Indicadores tecnicos
            rsi = talib.RSI(closes, timeperiod=14)[-1] if len(closes) >= 14 else 50
            macd_line, macd_signal, _ = talib.MACD(closes)
            macd_diff = macd_line[-1] - macd_signal[-1] if len(macd_line) >= 2 else 0
            
            # SCORE ULTRA-AGRESSIVO PARA DUST
            score = 0
            
            # RSI favoravel para venda (>40 ja vale pontos)
            if rsi > 65:
                score += 35  # RSI muito alto
            elif rsi > 55:
                score += 25  # RSI alto
            elif rsi > 45:
                score += 15  # RSI medio-alto
            elif rsi > 40:
                score += 10  # RSI baixo mas aceitavel
                
            # MACD bearish
            if macd_diff < -0.5:
                score += 25
            elif macd_diff < 0:
                score += 15
            elif macd_diff < 0.5:
                score += 8
                
            # Volume (qualquer volume acima da media vale)
            volume_medio = np.mean(volumes[-10:])
            if volumes[-1] > volume_medio * 1.2:
                score += 20
            elif volumes[-1] > volume_medio * 1.1:
                score += 15
            elif volumes[-1] > volume_medio:
                score += 10
                
            # BONUS DUST - Se temos dust BTC, score automatico minimo
            saldos = self.obter_saldo_conta()
            if 'BTC' in saldos:
                btc_livre = saldos['BTC']['free']
                if 0 < btc_livre < self.DUST_BTC_THRESHOLD:
                    score += 30  # Bonus para forcar venda de dust
                    logger.info("BONUS DUST APLICADO!")
                    
            # Score de tendencia (mais flexivel)
            if len(closes) >= 5:
                trend_short = closes[-1] < closes[-3]  # Tendencia de 3 velas
                if trend_short:
                    score += 12
                    
            logger.info(f"SCORE VENDA DUST: {score}/100")
            logger.info(f"   RSI: {rsi:.1f}, MACD: {macd_diff:.3f}")
            
            return score
            
        except Exception as e:
            logger.error(f"ERRO calculo score dust: {e}")
            return 20  # Score default para tentar vender dust

    def executar_ciclo_dust_corrigido(self):
        """CICLO PRINCIPAL CORRIGIDO PARA DUST BTC"""
        ciclo = 0
        
        while self.executando:
            try:
                ciclo += 1
                logger.info(f"=== CICLO DUST DEFINITIVO {ciclo} ===")
                
                # Status da conta
                saldos = self.obter_saldo_conta()
                if not saldos:
                    logger.error("ERRO ao obter saldos - tentando proximo ciclo")
                    time.sleep(self.CYCLE_DELAY * 2)
                    continue
                
                btc_livre = saldos.get('BTC', {}).get('free', 0)
                usdt_livre = saldos.get('USDT', {}).get('free', 0)
                
                # Calculo do capital
                try:
                    ticker = self.client.get_symbol_ticker(symbol='BTCUSDT')
                    preco_btc = float(ticker['price'])
                except Exception as e:
                    logger.error(f"Erro obter preco BTC: {e}")
                    time.sleep(self.CYCLE_DELAY)
                    continue
                    
                valor_btc_usd = btc_livre * preco_btc
                capital_total = usdt_livre + valor_btc_usd
                
                if self.capital_inicial == 0:
                    self.capital_inicial = capital_total
                
                posicao = capital_total - self.capital_inicial
                percent_pos = (posicao / self.capital_inicial) * 100 if self.capital_inicial > 0 else 0
                
                logger.info(f"Posicao: ${posicao:.4f} ({percent_pos:.3f}%)")
                logger.info(f"Capital: ${capital_total:.2f} | USDT: ${usdt_livre:.2f}")
                logger.info(f"   BTC: {btc_livre:.8f} = ${valor_btc_usd:.2f}")
                
                # LOGICA DUST BTC
                if btc_livre > 0:
                    if btc_livre < self.DUST_BTC_THRESHOLD:
                        logger.info(f"DUST BTC DETECTADO: {btc_livre:.8f}")
                        self.estado_dust = True
                        
                        # Score para venda de dust  
                        score_venda = self.calcular_score_venda_dust()
                        
                        if score_venda >= self.SCORE_VENDA_MIN:
                            logger.info(f"TENTANDO VENDA DUST (Score: {score_venda})")
                            if self.converter_dust_btc_para_usdt():
                                logger.info("DUST BTC CONVERTIDO COM SUCESSO!")
                                self.estado_dust = False
                            else:
                                logger.info("FALHA conversao dust - tentando proximo ciclo")
                        else:
                            logger.info(f"Hold dust BTC (Score: {score_venda} < {self.SCORE_VENDA_MIN})")
                    else:
                        # BTC normal - usar sistema padrao
                        self.estado_dust = False
                        score_venda = self.calcular_score_venda_dust()
                        
                        if score_venda >= self.SCORE_VENDA_MIN:
                            logger.info(f"VENDA BTC NORMAL (Score: {score_venda})")
                            if self._executar_venda_btc_normal(btc_livre):
                                logger.info("BTC NORMAL VENDIDO!")
                        else:
                            logger.info(f"Hold BTC (Score: {score_venda} < {self.SCORE_VENDA_MIN})")
                
                # LOGICA DE COMPRA USDT
                if usdt_livre >= self.MIN_USDT_FOR_TRADE and not self.estado_dust:
                    score_compra = self.calcular_score_compra_agressivo()
                    
                    if score_compra >= self.SCORE_COMPRA_MIN:
                        logger.info(f"COMPRA BTC (Score: {score_compra})")
                        self.executar_compra_btc_agressiva(usdt_livre)
                    else:
                        logger.info(f"Hold USDT (Score: {score_compra} < {self.SCORE_COMPRA_MIN})")
                
                # Status dust
                if self.estado_dust:
                    logger.info("STATUS: MODO DUST BTC ATIVO")
                
                time.sleep(self.CYCLE_DELAY)
                
            except KeyboardInterrupt:
                logger.info("Sistema interrompido pelo usuario")
                self.executando = False
                break
            except Exception as e:
                logger.error(f"ERRO ciclo: {e}")
                logger.error(traceback.format_exc())
                time.sleep(self.CYCLE_DELAY * 2)  # Sleep mais longo em erro

    def calcular_score_compra_agressivo(self):
        """Score para compra ultra-agressiva"""
        try:
            klines = self.client.get_klines(symbol='BTCUSDT', interval='1m', limit=100)
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])
            
            rsi = talib.RSI(closes, timeperiod=14)[-1] if len(closes) >= 14 else 50
            macd_line, macd_signal, _ = talib.MACD(closes)
            macd_diff = macd_line[-1] - macd_signal[-1] if len(macd_line) >= 2 else 0
            
            score = 0
            
            # RSI favoravel para compra (baixo)
            if rsi < 25:
                score += 40
            elif rsi < 35:
                score += 30
            elif rsi < 45:
                score += 20
            elif rsi < 55:
                score += 10
                
            # MACD bullish
            if macd_diff > 0.5:
                score += 25
            elif macd_diff > 0:
                score += 15
            elif macd_diff > -0.5:
                score += 8
                
            # Volume
            volume_medio = np.mean(volumes[-10:])
            if volumes[-1] > volume_medio * 1.3:
                score += 20
            elif volumes[-1] > volume_medio * 1.1:
                score += 10
                
            # Tendencia de alta recente
            if len(closes) >= 5:
                trend_up = closes[-1] > closes[-3]
                if trend_up:
                    score += 15
                    
            logger.info(f"SCORE COMPRA: {score}/100 (RSI: {rsi:.1f})")
            return score
            
        except Exception as e:
            logger.error(f"ERRO score compra: {e}")
            return 0

    def executar_compra_btc_agressiva(self, usdt_disponivel):
        """Executar compra BTC ultra-agressiva"""
        try:
            # Usar % do capital para compra
            valor_compra = usdt_disponivel * self.CAPITAL_PER_TRADE
            valor_compra = round(valor_compra, 2)
            
            if valor_compra < self.MIN_USDT_FOR_TRADE:
                logger.info(f"Valor muito baixo para compra: ${valor_compra}")
                return False
                
            logger.info(f"COMPRA BTC ULTRA-AGRESSIVA")
            logger.info(f"   Valor: ${valor_compra}")
            
            ordem = self.client.order_market_buy(
                symbol='BTCUSDT',
                quoteOrderQty=valor_compra
            )
            
            logger.info(f"COMPRA EXECUTADA! ${valor_compra}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"ERRO API compra: {e}")
            return False
        except Exception as e:
            logger.error(f"ERRO compra: {e}")
            return False

def main():
    """MAIN SISTEMA DEFINITIVO DUST CORRIGIDO"""
    logger.info("SISTEMA DEFINITIVO DUST CORRIGIDO INICIADO!")
    logger.info("PARA CRIANCAS FAMINTAS - SUCESSO GARANTIDO!")
    logger.info("Correcao dust BTC + ultra-agressivo + timestamp fix")
    
    sistema = SistemaDefinitivoDustBTC()
    
    try:
        sistema.executar_ciclo_dust_corrigido()
    except KeyboardInterrupt:
        logger.info("Sistema parado pelo usuario")
    except Exception as e:
        logger.error(f"ERRO critico: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()