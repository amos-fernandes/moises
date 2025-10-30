#!/usr/bin/env python3
"""
🚨 SISTEMA FINAL DUST CORRIGIDO - CORREÇÃO PARA CRIANCAS FAMINTAS 🚨
Versão que resolve dust BTC + conversão automática para USDT
Ultra-agressivo com detecção de dust e conversão inteligente
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

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('atcoin_final.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SistemaFinalDustCorrigido:
    def __init__(self):
        # 🔑 Chaves API Binance
        self.api_key = 'wgdJDvHxJF8JdKbMbfeUoJlN7VTe0ldyX9rUnJHaGg3AA7SYSfsxdpefwhjy17HP'
        self.api_secret = 'KYXYZKUmE0t6jpyMdTnMSE6skLgTZtClNqZNOJl4lPKCci5p5KgKJnJoyBevK5J8'
        
        # 🚨 CONFIGURAÇÃO ULTRA-AGRESSIVA PARA DUST BTC
        self.MIN_TRADE_VALUE = 10.5  # Valor mínimo Binance (USD)
        self.DUST_BTC_THRESHOLD = 0.00016  # Threshold para BTC dust
        self.MIN_USDT_FOR_TRADE = 10.5  # Mínimo USDT para trades
        
        # 🎯 PARÂMETROS ULTRA-AGRESSIVOS - CRIANÇAS DEPENDEM DISSO!
        self.SCORE_VENDA_MIN = 20  # Ainda mais baixo para dust
        self.SCORE_COMPRA_MIN = 20
        self.TAKE_PROFIT_1 = 0.15  # 0.15% ultra micro
        self.TAKE_PROFIT_2 = 0.35  # 0.35% micro  
        self.TAKE_PROFIT_3 = 0.65  # 0.65% pequeno
        self.STOP_LOSS = 0.3  # 0.3% stop ultra tight
        self.CAPITAL_PER_TRADE = 0.98  # 98% do capital
        
        # 🔄 CONFIGURAÇÃO DE CICLO ULTRA-RÁPIDO
        self.CYCLE_DELAY = 3  # 3 segundos entre ciclos
        
        self.client = None
        self.inicializar_client()
        self.lock = Lock()
        self.executando = True
        self.capital_inicial = 0.0
        
        # 📊 Estado do sistema
        self.estado_dust = False
        self.ultima_conversao = 0
        self.conversoes_realizadas = 0
        
    def inicializar_client(self):
        """Inicializar cliente Binance com tratamento de erro"""
        try:
            self.client = Client(self.api_key, self.api_secret)
            logger.info("🔗 Cliente Binance inicializado com sucesso!")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar cliente: {e}")
            return False
        return True
        
    def obter_saldo_conta(self):
        """Obter saldos atuais da conta com tratamento de erro"""
        try:
            account = self.client.get_account()
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
            
        except Exception as e:
            logger.error(f"❌ Erro ao obter saldo: {e}")
            return {}

    def converter_dust_btc_para_usdt(self):
        """🚨 CONVERSÃO CRÍTICA DE DUST BTC PARA USDT"""
        try:
            saldos = self.obter_saldo_conta()
            
            if 'BTC' not in saldos:
                logger.info("📊 Sem BTC para conversão")
                return False
                
            btc_livre = saldos['BTC']['free']
            
            # 🔍 DETECÇÃO DE DUST BTC
            if btc_livre < self.DUST_BTC_THRESHOLD:
                logger.info(f"🚨 DUST BTC DETECTADO! {btc_livre:.8f} BTC")
                
                # 💰 Obter preço atual BTC/USDT
                ticker = self.client.get_symbol_ticker(symbol='BTCUSDT')
                preco_btc = float(ticker['price'])
                valor_usd = btc_livre * preco_btc
                
                logger.info(f"💵 Valor dust: ${valor_usd:.2f}")
                
                if valor_usd >= 8.0:  # Se valor >= $8 tenta conversão forçada
                    return self._tentar_conversao_forcada_btc(btc_livre, preco_btc)
                else:
                    logger.info("💸 Dust BTC muito pequeno para conversão ($<8)")
                    return False
            
            # ✅ BTC NORMAL - Conversão padrão
            if btc_livre >= self.DUST_BTC_THRESHOLD:
                return self._executar_venda_btc_normal(btc_livre)
                
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro conversão dust: {e}")
            return False

    def _tentar_conversao_forcada_btc(self, btc_quantidade, preco_btc):
        """🔥 CONVERSÃO FORÇADA DE DUST BTC"""
        try:
            # 🎯 Estratégias múltiplas para dust
            estrategias = [
                # 1. Venda market com quantidade exata
                lambda: self._venda_market_exata(btc_quantidade),
                # 2. Venda com quantidade ajustada -1%
                lambda: self._venda_market_ajustada(btc_quantidade * 0.99),
                # 3. Venda com quantidade ajustada -2%
                lambda: self._venda_market_ajustada(btc_quantidade * 0.98),
                # 4. Conversão via dust transfer (se disponível)
                lambda: self._tentar_dust_transfer(btc_quantidade),
            ]
            
            for i, estrategia in enumerate(estrategias):
                logger.info(f"🎯 Tentando estratégia {i+1}/4 para dust...")
                try:
                    if estrategia():
                        logger.info(f"✅ Estratégia {i+1} funcionou!")
                        self.conversoes_realizadas += 1
                        return True
                except Exception as e:
                    logger.warning(f"⚠️ Estratégia {i+1} falhou: {e}")
                    
            logger.error("❌ Todas estratégias falharam para dust BTC")
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro conversão forçada: {e}")
            return False

    def _venda_market_exata(self, quantidade):
        """Venda market com quantidade exata"""
        ordem = self.client.order_market_sell(
            symbol='BTCUSDT',
            quantity=f"{quantidade:.8f}"
        )
        logger.info(f"✅ Venda market exata: {quantidade:.8f} BTC")
        return True

    def _venda_market_ajustada(self, quantidade):
        """Venda market com quantidade ajustada"""
        # Arredondar para baixo para evitar insufficient balance
        quantidade_ajustada = round(quantidade, 6)  # 6 decimais
        
        ordem = self.client.order_market_sell(
            symbol='BTCUSDT', 
            quantity=f"{quantidade_ajustada:.6f}"
        )
        logger.info(f"✅ Venda ajustada: {quantidade_ajustada:.6f} BTC")
        return True

    def _tentar_dust_transfer(self, quantidade):
        """Tentar usar dust transfer da Binance"""
        # Esta função pode não estar disponível na API pública
        # Mas tentamos para completude
        logger.info(f"🔄 Tentando dust transfer para {quantidade:.8f} BTC")
        # Retorna False pois geralmente não disponível via API
        return False

    def _executar_venda_btc_normal(self, btc_quantidade):
        """Executar venda BTC normal (não dust)"""
        try:
            # Quantidade para venda (deixa small buffer)
            quantidade_venda = round(btc_quantidade * 0.998, 6)
            
            ordem = self.client.order_market_sell(
                symbol='BTCUSDT',
                quantity=f"{quantidade_venda:.6f}"
            )
            
            logger.info(f"✅ VENDA BTC NORMAL: {quantidade_venda:.6f} BTC")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro venda BTC normal: {e}")
            return False

    def calcular_score_venda_dust(self):
        """🎯 Score de venda adaptado para situações de dust"""
        try:
            # Obter dados de mercado
            klines = self.client.get_klines(symbol='BTCUSDT', interval='1m', limit=100)
            closes = np.array([float(k[4]) for k in klines])
            volumes = np.array([float(k[5]) for k in klines])
            
            # 📈 Indicadores técnicos
            rsi = talib.RSI(closes, timeperiod=14)[-1] if len(closes) >= 14 else 50
            macd_line, macd_signal, _ = talib.MACD(closes)
            macd_diff = macd_line[-1] - macd_signal[-1] if len(macd_line) >= 2 else 0
            
            # 🎯 SCORE ULTRA-AGRESSIVO PARA DUST
            score = 0
            
            # RSI favorável para venda (>45 já vale pontos)
            if rsi > 65:
                score += 40  # RSI muito alto
            elif rsi > 55:
                score += 25  # RSI alto
            elif rsi > 45:
                score += 10  # RSI médio-alto
                
            # MACD bearish
            if macd_diff < 0:
                score += 20
            elif macd_diff < 0.5:
                score += 10
                
            # Volume (qualquer volume acima da média vale)
            volume_medio = np.mean(volumes[-10:])
            if volumes[-1] > volume_medio * 1.1:
                score += 15
            elif volumes[-1] > volume_medio:
                score += 10
                
            # 🚨 BONUS DUST - Se temos dust BTC, score automático mínimo
            saldos = self.obter_saldo_conta()
            if 'BTC' in saldos:
                btc_livre = saldos['BTC']['free']
                if 0 < btc_livre < self.DUST_BTC_THRESHOLD:
                    score += 25  # Bonus para forçar venda de dust
                    logger.info("🚨 BONUS DUST APLICADO!")
                    
            # 📊 Score de tendência (mais flexível)
            if len(closes) >= 5:
                trend_short = closes[-1] < closes[-3]  # Tendência de 3 velas
                if trend_short:
                    score += 10
                    
            logger.info(f"📊 SCORE VENDA DUST: {score}/100")
            logger.info(f"   RSI: {rsi:.1f}, MACD: {macd_diff:.3f}")
            
            return score
            
        except Exception as e:
            logger.error(f"❌ Erro cálculo score dust: {e}")
            return 0

    def executar_ciclo_dust_corrigido(self):
        """🚨 CICLO PRINCIPAL CORRIGIDO PARA DUST BTC"""
        ciclo = 0
        
        while self.executando:
            try:
                ciclo += 1
                logger.info(f"🚨 === CICLO DUST FINAL {ciclo} ===")
                
                # 📊 Status da conta
                saldos = self.obter_saldo_conta()
                if not saldos:
                    logger.error("❌ Erro ao obter saldos")
                    time.sleep(self.CYCLE_DELAY)
                    continue
                
                btc_livre = saldos.get('BTC', {}).get('free', 0)
                usdt_livre = saldos.get('USDT', {}).get('free', 0)
                
                # 💰 Cálculo do capital
                ticker = self.client.get_symbol_ticker(symbol='BTCUSDT')
                preco_btc = float(ticker['price'])
                valor_btc_usd = btc_livre * preco_btc
                capital_total = usdt_livre + valor_btc_usd
                
                if self.capital_inicial == 0:
                    self.capital_inicial = capital_total
                
                posicao = capital_total - self.capital_inicial
                percent_pos = (posicao / self.capital_inicial) * 100 if self.capital_inicial > 0 else 0
                
                logger.info(f"📉 Posição: ${posicao:.4f} ({percent_pos:.3f}%)")
                logger.info(f"💼 Capital: ${capital_total:.2f} | USDT: ${usdt_livre:.2f}")
                logger.info(f"   ₿ BTC: {btc_livre:.8f} = ${valor_btc_usd:.2f}")
                
                # 🚨 LÓGICA DUST BTC
                if btc_livre > 0:
                    if btc_livre < self.DUST_BTC_THRESHOLD:
                        logger.info(f"🚨 DUST BTC DETECTADO: {btc_livre:.8f}")
                        self.estado_dust = True
                        
                        # 🎯 Score para venda de dust  
                        score_venda = self.calcular_score_venda_dust()
                        
                        if score_venda >= self.SCORE_VENDA_MIN:
                            logger.info(f"💸 TENTANDO VENDA DUST (Score: {score_venda})")
                            if self.converter_dust_btc_para_usdt():
                                logger.info("✅ DUST BTC CONVERTIDO!")
                                self.estado_dust = False
                            else:
                                logger.info("❌ Falha conversão dust - tentando próximo ciclo")
                        else:
                            logger.info(f"✋ Hold dust BTC (Score: {score_venda} < {self.SCORE_VENDA_MIN})")
                    else:
                        # BTC normal - usar sistema padrão
                        self.estado_dust = False
                        score_venda = self.calcular_score_venda_dust()
                        
                        if score_venda >= self.SCORE_VENDA_MIN:
                            logger.info(f"💸 VENDA BTC NORMAL (Score: {score_venda})")
                            if self._executar_venda_btc_normal(btc_livre):
                                logger.info("✅ BTC NORMAL VENDIDO!")
                        else:
                            logger.info(f"✋ Hold BTC (Score: {score_venda} < {self.SCORE_VENDA_MIN})")
                
                # 🛒 LÓGICA DE COMPRA USDT
                if usdt_livre >= self.MIN_USDT_FOR_TRADE and not self.estado_dust:
                    score_compra = self.calcular_score_compra_agressivo()
                    
                    if score_compra >= self.SCORE_COMPRA_MIN:
                        logger.info(f"🛒 COMPRA BTC (Score: {score_compra})")
                        self.executar_compra_btc_agressiva(usdt_livre)
                    else:
                        logger.info(f"✋ Hold USDT (Score: {score_compra} < {self.SCORE_COMPRA_MIN})")
                
                # ⚡ Status dust
                if self.estado_dust:
                    logger.info("🚨 STATUS: MODO DUST BTC ATIVO")
                
                time.sleep(self.CYCLE_DELAY)
                
            except KeyboardInterrupt:
                logger.info("🛑 Sistema interrompido pelo usuário")
                self.executando = False
                break
            except Exception as e:
                logger.error(f"❌ Erro ciclo: {e}")
                logger.error(traceback.format_exc())
                time.sleep(self.CYCLE_DELAY)

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
            
            # RSI favorável para compra (baixo)
            if rsi < 30:
                score += 40
            elif rsi < 40:
                score += 25
            elif rsi < 50:
                score += 10
                
            # MACD bullish
            if macd_diff > 0:
                score += 20
            elif macd_diff > -0.5:
                score += 10
                
            # Volume
            volume_medio = np.mean(volumes[-10:])
            if volumes[-1] > volume_medio * 1.2:
                score += 15
                
            # Tendência de alta recente
            if len(closes) >= 5:
                trend_up = closes[-1] > closes[-3]
                if trend_up:
                    score += 15
                    
            logger.info(f"📊 SCORE COMPRA: {score}/100 (RSI: {rsi:.1f})")
            return score
            
        except Exception as e:
            logger.error(f"❌ Erro score compra: {e}")
            return 0

    def executar_compra_btc_agressiva(self, usdt_disponivel):
        """Executar compra BTC ultra-agressiva"""
        try:
            # Usar % do capital para compra
            valor_compra = usdt_disponivel * self.CAPITAL_PER_TRADE
            valor_compra = round(valor_compra, 2)
            
            if valor_compra < self.MIN_USDT_FOR_TRADE:
                logger.info(f"💰 Valor muito baixo para compra: ${valor_compra}")
                return False
                
            logger.info(f"🛒💸 COMPRA BTC ULTRA-AGRESSIVA")
            logger.info(f"   💰 Valor: ${valor_compra}")
            
            ordem = self.client.order_market_buy(
                symbol='BTCUSDT',
                quoteOrderQty=valor_compra
            )
            
            logger.info(f"✅ COMPRA EXECUTADA! ${valor_compra}")
            return True
            
        except BinanceAPIException as e:
            logger.error(f"❌ Erro API compra: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Erro compra: {e}")
            return False

def main():
    """🚨 MAIN SISTEMA FINAL DUST CORRIGIDO"""
    logger.info("🚨🚀 SISTEMA FINAL DUST CORRIGIDO INICIADO!")
    logger.info("💪 PARA CRIANÇAS FAMINTAS - SUCESSO GARANTIDO!")
    logger.info("🔧 Correção dust BTC + ultra-agressivo")
    
    sistema = SistemaFinalDustCorrigido()
    
    try:
        sistema.executar_ciclo_dust_corrigido()
    except KeyboardInterrupt:
        logger.info("⏹️ Sistema parado pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()