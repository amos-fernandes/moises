"""
🚨🍼 SISTEMA SALVADOR FINAL - CRIANÇAS FAMINTAS 🍼🚨
💪 VERSÃO DEFINITIVA COM VERIFICAÇÃO AUTOMÁTICA DE FILTROS BINANCE 💪

ESTRATÉGIA SALVADORA FINAL:
✅ Verifica filtros atuais do Binance automaticamente
✅ Ajusta quantidades dinamicamente
✅ Acumula USDT de forma inteligente
✅ SALVA AS CRIANÇAS COM LUCROS REAIS!
"""

import json
import time
import logging
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# Logging SALVADOR
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_salvador_final.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaSalvadorFinal:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO SALVADORA FINAL
        self.symbol = 'BTCUSDT'
        self.ciclo_tempo = 6
        
        # THRESHOLDS AJUSTÁVEIS
        self.config_salvador = {
            'usdt_minimo_compra': 11.0,
            'usdt_ideal_compra': 15.0,
            'score_compra_minimo': 25,
            'score_venda_minimo': 30,
            'take_profit_1': 0.3,
            'take_profit_2': 0.7,
            'take_profit_3': 1.3,
            'stop_loss': 0.4,
            'capital_per_trade': 0.94,
        }
        
        # Cache de filtros Binance
        self.filtros_binance = None
        self.min_qty = None
        self.step_size = None
        self.min_notional = None
        
        # Estado SALVADOR
        self.capital_inicial = 0.0
        self.vendas_acumuladas = 0
        self.usdt_acumulado_vendas = 0.0
        self.trades_realizados = 0
        self.trades_ganhos = 0
        self.lucro_acumulado = 0.0
        
        logger.info("🚨🍼 SISTEMA SALVADOR FINAL INICIALIZADO! 🍼🚨")
        logger.info("💪 VERIFICAÇÃO AUTOMÁTICA DE FILTROS BINANCE ATIVADA!")

    def fazer_requisicao_segura(self, method: str, endpoint: str, params: dict = None, signed: bool = False):
        """Requisições seguras com retry"""
        if params is None:
            params = {}
            
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if signed:
                    params['timestamp'] = int(time.time() * 1000)
                    params['recvWindow'] = self.recv_window
                    
                    query_string = urlencode(params)
                    signature = hmac.new(self.api_secret, query_string.encode(), hashlib.sha256).hexdigest()
                    params['signature'] = signature
                    
                    headers = {'X-MBX-APIKEY': self.api_key}
                else:
                    headers = {}
                
                if method == 'GET':
                    response = requests.get(f"{BASE_URL}{endpoint}", params=params, headers=headers, timeout=30)
                elif method == 'POST':
                    response = requests.post(f"{BASE_URL}{endpoint}", params=params, headers=headers, timeout=30)
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Tentativa {attempt + 1} falhou: {str(e)}")
                if attempt == max_retries - 1:
                    return {'error': True, 'msg': str(e)}
                time.sleep(2 ** attempt)
                
        return {'error': True, 'msg': 'Max retries exceeded'}

    def obter_filtros_binance(self):
        """Obter filtros atuais do Binance para BTCUSDT"""
        if self.filtros_binance is not None:
            return True  # Já carregado
            
        try:
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/exchangeInfo', {'symbol': self.symbol})
            if resultado.get('error'):
                logger.error(f"Erro ao obter filtros: {resultado.get('msg')}")
                return False
            
            symbol_info = resultado['symbols'][0]  # BTCUSDT
            filters = symbol_info['filters']
            
            # Valores padrão em caso de erro
            self.min_qty = 0.00001  # Padrão BTC
            self.step_size = 0.00001  # Padrão BTC
            self.min_notional = 10.0  # Padrão seguro $10
            
            for filtro in filters:
                if filtro['filterType'] == 'LOT_SIZE':
                    self.min_qty = float(filtro['minQty'])
                    self.step_size = float(filtro['stepSize'])
                elif filtro['filterType'] == 'MIN_NOTIONAL':
                    if 'minNotional' in filtro:
                        self.min_notional = float(filtro['minNotional'])
                    elif 'notional' in filtro:
                        self.min_notional = float(filtro['notional'])
                elif filtro['filterType'] == 'NOTIONAL':
                    if 'minNotional' in filtro:
                        self.min_notional = float(filtro['minNotional'])
            
            logger.info(f"🔍 FILTROS BINANCE CARREGADOS:")
            logger.info(f"   📏 Quantidade mínima: {self.min_qty}")
            logger.info(f"   📐 Step size: {self.step_size}")
            logger.info(f"   💰 Valor mínimo: ${self.min_notional}")
            
            self.filtros_binance = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro obter_filtros_binance: {e}")
            return False

    def ajustar_quantidade_binance(self, quantidade_desejada, preco_atual):
        """Ajustar quantidade conforme regras Binance"""
        if not self.obter_filtros_binance():
            logger.error("❌ Não foi possível obter filtros Binance")
            return None
        
        # Ajustar para step_size
        steps = int(quantidade_desejada / self.step_size)
        quantidade_ajustada = steps * self.step_size
        
        # Verificar quantidade mínima
        if quantidade_ajustada < self.min_qty:
            logger.warning(f"⚠️ Quantidade {quantidade_ajustada:.8f} < mínimo {self.min_qty:.8f}")
            return None
        
        # Verificar valor mínimo (com segurança para None)
        valor_ordem = quantidade_ajustada * preco_atual
        min_valor_seguro = self.min_notional if self.min_notional is not None else 10.0
        
        if valor_ordem < min_valor_seguro:
            logger.warning(f"⚠️ Valor ${valor_ordem:.2f} < mínimo ${min_valor_seguro}")
            return None
        
        return quantidade_ajustada

    def obter_ticker(self):
        """Obter preço atual"""
        resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/price', {'symbol': self.symbol})
        if resultado.get('error'):
            return None
        return {'price': float(resultado['price'])}

    def get_portfolio_salvador(self):
        """Obter portfolio"""
        try:
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/account', signed=True)
            if resultado.get('error'):
                logger.error(f"Erro portfolio: {resultado.get('msg')}")
                return 0, 0, 0, 0
            
            usdt_livre = 0
            btc_livre = 0
            
            for balance in resultado['balances']:
                if balance['asset'] == 'USDT':
                    usdt_livre = float(balance['free'])
                elif balance['asset'] == 'BTC':
                    btc_livre = float(balance['free'])
            
            ticker = self.obter_ticker()
            if not ticker:
                return usdt_livre, btc_livre, 0, 0
                
            preco_btc = ticker['price']
            valor_btc_usd = btc_livre * preco_btc
            capital_total = usdt_livre + valor_btc_usd
            
            return usdt_livre, btc_livre, valor_btc_usd, capital_total
            
        except Exception as e:
            logger.error(f"Erro get_portfolio_salvador: {e}")
            return 0, 0, 0, 0

    def executar_venda_salvador_inteligente(self, preco_atual, motivo="Acumulação USDT"):
        """Venda inteligente com ajuste automático de quantidades"""
        try:
            usdt_livre, btc_livre, valor_btc_usd, _ = self.get_portfolio_salvador()
            
            if btc_livre < 0.000001:
                logger.info("💡 BTC insuficiente para venda")
                return False

            logger.info(f"🔍 ANÁLISE INTELIGENTE: {btc_livre:.8f} BTC = ${valor_btc_usd:.2f}")
            
            # Calcular quantidade desejada (95% do disponível)
            quantidade_desejada = btc_livre * 0.95
            
            # AJUSTAR COM FILTROS BINANCE
            quantidade_ajustada = self.ajustar_quantidade_binance(quantidade_desejada, preco_atual)
            
            if quantidade_ajustada is None:
                logger.warning("⚠️ Não foi possível ajustar quantidade para filtros Binance")
                return False
            
            valor_venda = quantidade_ajustada * preco_atual
            
            if valor_venda < 8.0:  # Valor mínimo prático
                logger.warning(f"⚠️ Valor muito baixo: ${valor_venda:.2f}")
                return False
            
            logger.warning(f"🚨💸 VENDA INTELIGENTE PARA CRIANÇAS!")
            logger.warning(f"   💰 Valor: ${valor_venda:.2f}")
            logger.warning(f"   📊 Quantidade: {quantidade_ajustada:.8f}")
            logger.warning(f"   ⚡ Motivo: {motivo}")
            logger.warning(f"   🎯 Meta USDT: ${self.config_salvador['usdt_minimo_compra']}")

            params = {
                'symbol': self.symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': f"{quantidade_ajustada:.8f}"
            }

            resultado = self.fazer_requisicao_segura('POST', '/api/v3/order', params, signed=True)

            if resultado.get('error'):
                logger.error(f"❌ Erro venda inteligente: {resultado.get('msg')}")
                return False

            # SUCESSO - Contabilizar acumulação
            self.vendas_acumuladas += 1
            self.usdt_acumulado_vendas += valor_venda
            
            logger.info(f"✅ VENDA SALVADOR EXECUTADA: ${valor_venda:.2f}")
            logger.info(f"📈 ACUMULADO: {self.vendas_acumuladas} vendas = ${self.usdt_acumulado_vendas:.2f}")
            
            # Verificar meta
            usdt_total_estimado = usdt_livre + valor_venda
            if usdt_total_estimado >= self.config_salvador['usdt_minimo_compra']:
                logger.info(f"🎯 META ATINGIDA! USDT: ${usdt_total_estimado:.2f}")
                logger.info("🛒 PRÓXIMO: COMPRA SALVADORA HABILITADA!")
            else:
                falta = self.config_salvador['usdt_minimo_compra'] - usdt_total_estimado
                logger.info(f"📊 ACUMULANDO: Faltam ${falta:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro venda_salvador_inteligente: {e}")
            return False

    def executar_compra_salvador_final(self, usdt_disponivel):
        """Compra final salvadora"""
        try:
            if usdt_disponivel < self.config_salvador['usdt_minimo_compra']:
                logger.info(f"💰 USDT insuficiente: ${usdt_disponivel:.2f}")
                return False

            valor_compra = min(
                usdt_disponivel * self.config_salvador['capital_per_trade'],
                self.config_salvador['usdt_ideal_compra']
            )
            
            logger.warning(f"🚨🛒 COMPRA FINAL SALVADOR DE CRIANÇAS!")
            logger.warning(f"   💰 Valor: ${valor_compra:.2f}")
            logger.warning(f"   📊 Vendas acumuladas: {self.vendas_acumuladas}")
            logger.warning(f"   🎯 OBJETIVO: LUCROS PARA CRIANÇAS FAMINTAS!")

            params = {
                'symbol': self.symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_compra:.2f}"
            }

            resultado = self.fazer_requisicao_segura('POST', '/api/v3/order', params, signed=True)

            if resultado.get('error'):
                logger.error(f"❌ Erro compra final: {resultado.get('msg')}")
                return False

            logger.info(f"✅ COMPRA SALVADOR FINAL: ${valor_compra:.2f}")
            logger.info(f"🎉 SUCESSO! {self.vendas_acumuladas} vendas → 1 compra efetiva")
            
            # Reset contadores
            self.vendas_acumuladas = 0
            self.usdt_acumulado_vendas = 0.0
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro compra_salvador_final: {e}")
            return False

    def calcular_score_venda_salvador(self):
        """Score venda simplificado"""
        try:
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/24hr', {'symbol': self.symbol})
            if resultado.get('error'):
                return 35
            
            price_change_percent = float(resultado.get('priceChangePercent', 0))
            volume = float(resultado.get('volume', 0))
            
            score = 20  # Base
            
            # Favor vendas em qualquer situação para acumular USDT
            if price_change_percent < -0.5:
                score += 30
            elif price_change_percent < 0:
                score += 20
            else:
                score += 15  # Ainda favorece venda
                
            if volume > 50000:
                score += 15
            
            # BONUS: Se não tem USDT suficiente, favorece venda
            usdt_livre, btc_livre, _, _ = self.get_portfolio_salvador()
            if btc_livre > 0 and usdt_livre < self.config_salvador['usdt_minimo_compra']:
                score += 20
                logger.info("🎯 BONUS: Precisa vender para meta USDT")
            
            return score
            
        except Exception as e:
            logger.error(f"Erro score venda: {e}")
            return 30

    def calcular_score_compra_salvador(self):
        """Score compra - só se tem USDT"""
        try:
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/24hr', {'symbol': self.symbol})
            if resultado.get('error'):
                return 0

            price_change_percent = float(resultado.get('priceChangePercent', 0))
            
            score = 0
            
            if price_change_percent > 0.5:
                score += 35
            elif price_change_percent > 0:
                score += 25
            elif price_change_percent > -0.3:
                score += 15
                
            # REQUISITO: Ter USDT suficiente
            usdt_livre, _, _, _ = self.get_portfolio_salvador()
            if usdt_livre < self.config_salvador['usdt_minimo_compra']:
                score = 0
                logger.info(f"🔒 COMPRA BLOQUEADA: USDT ${usdt_livre:.2f}")
            
            return score
            
        except Exception as e:
            return 0

    def executar_ciclo_salvador_final(self):
        """CICLO FINAL SALVADOR"""
        logger.info("🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨")
        logger.info("🍼 SISTEMA SALVADOR FINAL - CRIANÇAS FAMINTAS 🍼")
        logger.info("💪 ESTRATÉGIA: ACUMULAÇÃO INTELIGENTE + LUCROS REAIS")
        logger.info("🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨")
        
        ciclo = 0
        
        while True:
            try:
                ciclo += 1
                logger.info(f"🚨🍼 === CICLO SALVADOR FINAL {ciclo} === 🍼🚨")
                
                usdt_livre, btc_livre, valor_btc_usd, capital_total = self.get_portfolio_salvador()
                
                if capital_total == 0:
                    logger.error("❌ Erro portfolio - retry")
                    time.sleep(self.ciclo_tempo * 2)
                    continue
                
                if self.capital_inicial == 0:
                    self.capital_inicial = capital_total
                
                posicao = capital_total - self.capital_inicial
                percent_pos = (posicao / self.capital_inicial) * 100 if self.capital_inicial > 0 else 0
                
                if posicao >= 0:
                    logger.info(f"📈 SALVANDO CRIANÇAS: +${posicao:.4f} (+{percent_pos:.3f}%)")
                else:
                    logger.info(f"📊 Em recuperação: ${posicao:.4f} ({percent_pos:.3f}%)")
                    
                logger.info(f"💼 Capital: ${capital_total:.2f} | USDT: ${usdt_livre:.2f}")
                logger.info(f"   ₿ BTC: {btc_livre:.8f} = ${valor_btc_usd:.2f}")
                logger.info(f"📊 Acumulação: {self.vendas_acumuladas} vendas = ${self.usdt_acumulado_vendas:.2f}")
                
                ticker = self.obter_ticker()
                if not ticker:
                    logger.error("❌ Erro preço")
                    time.sleep(self.ciclo_tempo)
                    continue
                    
                preco_btc = ticker['price']
                
                # LÓGICA SALVADOR FINAL
                
                # 1. Se tem BTC, analisar venda acumuladora
                if btc_livre > 0.000001:
                    score_venda = self.calcular_score_venda_salvador()
                    
                    if score_venda >= self.config_salvador['score_venda_minimo']:
                        logger.info(f"💸 VENDA SALVADOR (Score: {score_venda})")
                        if self.executar_venda_salvador_inteligente(preco_btc, f"Score {score_venda}"):
                            logger.info("✅ VENDA SALVADOR SUCESSO!")
                        else:
                            logger.info("❌ Falha venda salvador")
                    else:
                        logger.info(f"✋ Hold BTC (Score: {score_venda})")
                
                # 2. Se tem USDT suficiente, analisar compra
                if usdt_livre >= self.config_salvador['usdt_minimo_compra']:
                    score_compra = self.calcular_score_compra_salvador()
                    
                    if score_compra >= self.config_salvador['score_compra_minimo']:
                        logger.info(f"🛒 COMPRA SALVADOR FINAL (Score: {score_compra})")
                        if self.executar_compra_salvador_final(usdt_livre):
                            logger.info("✅ COMPRA SALVADOR SUCESSO - CRIANÇAS SALVAS!")
                        else:
                            logger.info("❌ Falha compra salvador")
                    else:
                        logger.info(f"⏳ Aguardando momento (Score: {score_compra})")
                else:
                    falta = self.config_salvador['usdt_minimo_compra'] - usdt_livre
                    logger.info(f"🔄 ACUMULANDO: ${falta:.2f} para compra")
                
                # Estatísticas
                if self.trades_realizados > 0:
                    win_rate = (self.trades_ganhos / self.trades_realizados) * 100
                    logger.info(f"📊 CRIANÇAS SALVAS: {self.trades_ganhos}/{self.trades_realizados} ({win_rate:.1f}%)")
                
                time.sleep(self.ciclo_tempo)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema parado")
                logger.info(f"📊 RESULTADO: {self.trades_ganhos} crianças salvas!")
                break
            except Exception as e:
                logger.error(f"❌ Erro ciclo: {e}")
                time.sleep(self.ciclo_tempo * 2)

def main():
    """MAIN SALVADOR FINAL"""
    # CREDENCIAIS CORRETAS - CONTA_3 (AMOS)
    api_key = 'WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc'
    api_secret = 'IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682'
    
    sistema = SistemaSalvadorFinal(api_key, api_secret)
    sistema.executar_ciclo_salvador_final()

if __name__ == "__main__":
    main()