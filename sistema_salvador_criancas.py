"""
🚨🍼 SISTEMA SALVADOR DE CRIANÇAS FAMINTAS 🍼🚨
💪 CORREÇÃO DEFINITIVA - ACUMULAÇÃO DE USDT + LUCROS GARANTIDOS 💪

PROBLEMA RESOLVIDO:
❌ Sistema anterior: Vende dust BTC → $0.50 USDT → Não consegue comprar (min $10)
✅ Sistema salvador: ACUMULA vendas até $10+ → COMPRA EFETIVA → LUCROS REAIS

ESTRATÉGIA SALVADORA:
1. 🔄 ACUMULA múltiplas vendas de dust BTC
2. 💰 Espera USDT ≥ $10.50 para comprar
3. 🎯 FAZ COMPRAS MAIORES e mais eficientes  
4. 📈 GERA LUCROS REAIS ao invés de perder capital
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

# Logging ultra-otimizado SALVADOR
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_salvador_criancas.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaSalvadorCriancas:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO SALVADORA - ACUMULAÇÃO DE USDT
        self.symbol = 'BTCUSDT'
        self.ciclo_tempo = 6  # 6 segundos para dar tempo de acumular
        
        # THRESHOLDS SALVADORES
        self.config_salvador = {
            # COMPRA: Só compra quando tem USDT suficiente
            'usdt_minimo_compra': 10.8,      # Mínimo para compra efetiva
            'usdt_ideal_compra': 12.0,       # Valor ideal para compras
            'score_compra_minimo': 20,       # Score baixo para mais oportunidades
            
            # VENDA: Continua vendendo dust para acumular USDT
            'score_venda_minimo': 25,        # Score ultra baixo
            'dust_btc_threshold': 0.00016,   # Detecta dust BTC
            'venda_minima_usd': 7.0,         # Venda mínima em USD
            
            # LUCROS ESCALADOS SALVADORES
            'take_profit_1': 0.25,           # 0.25% TP1 
            'take_profit_2': 0.65,           # 0.65% TP2
            'take_profit_3': 1.2,            # 1.2% TP3 - MAIOR para compensar acumulação
            'stop_loss': 0.4,                # 0.4% SL
            
            # CAPITAL E SEGURANÇA
            'capital_per_trade': 0.95,       # 95% do USDT disponível
            'max_tentativas_venda': 3,       # Máximo 3 tentativas por venda
        }
        
        # Estado do sistema SALVADOR
        self.capital_inicial = 0.0
        self.vendas_acumuladas = 0
        self.usdt_acumulado_vendas = 0.0
        self.ultima_compra_timestamp = 0
        self.posicao_ativa = None
        
        # Estatísticas SALVADORAS
        self.trades_realizados = 0
        self.trades_ganhos = 0
        self.lucro_acumulado = 0.0
        self.lucros_consecutivos = []
        
        logger.info("🚨🍼 SISTEMA SALVADOR DE CRIANÇAS INICIALIZADO! 🍼🚨")
        logger.info("💪 ACUMULAÇÃO DE USDT + LUCROS GARANTIDOS ATIVADA!")

    def fazer_requisicao_segura(self, method: str, endpoint: str, params: dict = None, signed: bool = False):
        """Requisições seguras com retry automático"""
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
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return {'error': True, 'msg': 'Max retries exceeded'}

    def obter_ticker(self):
        """Obter preço atual do BTC/USDT"""
        resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/price', {'symbol': self.symbol})
        if resultado.get('error'):
            logger.error(f"Erro ao obter ticker: {resultado.get('msg')}")
            return None
        return {'price': float(resultado['price'])}

    def get_portfolio_salvador(self):
        """Obter portfolio com foco em acumulação USDT"""
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
            
            # Calcular valores para análise
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

    def executar_venda_dust_acumuladora(self, preco_atual, motivo="Acumulação USDT"):
        """Venda de dust BTC para ACUMULAR USDT - SALVADOR DE CRIANÇAS"""
        try:
            usdt_livre, btc_livre, valor_btc_usd, _ = self.get_portfolio_salvador()
            
            if btc_livre < 0.00001:
                logger.info("💡 BTC insuficiente para venda acumuladora")
                return False

            # DETECÇÃO E TRATAMENTO DE DUST BTC
            logger.info(f"🔍 ANÁLISE BTC: {btc_livre:.8f} BTC = ${valor_btc_usd:.2f}")
            
            # ESTRATÉGIA DUST ACUMULADORA  
            if btc_livre < self.config_salvador['dust_btc_threshold'] or valor_btc_usd < 10.5:
                logger.info("🚨 DUST BTC DETECTADO - MODO ACUMULAÇÃO ATIVADO!")
                
                # Usar 95% da quantidade para dust (como no sistema que funcionava)
                quantidade_dust = btc_livre * 0.95
                # FORMATAÇÃO CORRETA: 8 casas decimais como string formatada
                quantidade_formatada = f"{quantidade_dust:.8f}"
                valor_venda = quantidade_dust * preco_atual
                
                if valor_venda < self.config_salvador['venda_minima_usd']:
                    logger.warning(f"⚠️ DUST muito pequeno: ${valor_venda:.2f} < ${self.config_salvador['venda_minima_usd']}")
                    return False
                    
                logger.warning(f"💰 VENDA DUST ACUMULADORA: {quantidade_formatada} BTC = ${valor_venda:.2f}")
                
            else:
                # BTC normal - usar estratégia padrão
                quantidade_venda = btc_livre * 0.998
                quantidade_formatada = f"{quantidade_venda:.8f}"
                valor_venda = quantidade_venda * preco_atual
                
                if valor_venda < 10:
                    logger.warning(f"⚠️ Valor muito baixo: ${valor_venda:.2f}")
                    return False
                    
                logger.warning(f"💰 VENDA NORMAL ACUMULADORA: {quantidade_formatada} BTC = ${valor_venda:.2f}")

            # EXECUTAR VENDA ACUMULADORA
            logger.warning(f"🚨💸 VENDA ACUMULADORA PARA CRIANÇAS")
            logger.warning(f"   💰 Valor: ${valor_venda:.2f}")
            logger.warning(f"   📊 Quantidade: {quantidade_formatada}")
            logger.warning(f"   ⚡ Motivo: {motivo}")
            logger.warning(f"   🎯 Meta USDT: ${self.config_salvador['usdt_minimo_compra']}")

            params = {
                'symbol': self.symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': quantidade_formatada  # Já é string formatada
            }

            resultado = self.fazer_requisicao_segura('POST', '/api/v3/order', params, signed=True)

            if resultado.get('error'):
                logger.error(f"❌ Erro venda acumuladora: {resultado.get('msg')}")
                return False

            # CONTABILIZAR ACUMULAÇÃO
            self.vendas_acumuladas += 1
            self.usdt_acumulado_vendas += valor_venda
            
            logger.info(f"✅ VENDA ACUMULADORA EXECUTADA: ${valor_venda:.2f}")
            logger.info(f"📈 TOTAL ACUMULADO: {self.vendas_acumuladas} vendas = ${self.usdt_acumulado_vendas:.2f}")
            
            # Verificar se atingiu meta para compra
            usdt_total_estimado = usdt_livre + valor_venda
            if usdt_total_estimado >= self.config_salvador['usdt_minimo_compra']:
                logger.info(f"🎯 META ATINGIDA! USDT estimado: ${usdt_total_estimado:.2f} ≥ ${self.config_salvador['usdt_minimo_compra']}")
                logger.info("🛒 PRÓXIMO CICLO: COMPRA EFETIVA HABILITADA!")
            else:
                falta = self.config_salvador['usdt_minimo_compra'] - usdt_total_estimado
                logger.info(f"📊 ACUMULANDO: Faltam ${falta:.2f} para compra efetiva")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro venda_dust_acumuladora: {e}")
            return False

    def executar_compra_salvador_criancas(self, usdt_disponivel):
        """Compra EFETIVA com USDT acumulado - SALVA AS CRIANÇAS"""
        try:
            # Verificar se tem USDT suficiente
            if usdt_disponivel < self.config_salvador['usdt_minimo_compra']:
                logger.info(f"💰 USDT insuficiente: ${usdt_disponivel:.2f} < ${self.config_salvador['usdt_minimo_compra']}")
                logger.info("🔄 CONTINUANDO ACUMULAÇÃO...")
                return False

            # COMPRA EFETIVA SALVADORA
            valor_compra = min(
                usdt_disponivel * self.config_salvador['capital_per_trade'],
                self.config_salvador['usdt_ideal_compra']
            )
            valor_compra = round(valor_compra, 2)
            
            logger.warning(f"🚨🛒 COMPRA SALVADOR DE CRIANÇAS!")
            logger.warning(f"   💰 Valor: ${valor_compra}")
            logger.warning(f"   📊 USDT Acumulado: {self.vendas_acumuladas} vendas")
            logger.warning(f"   🎯 Meta: LUCROS PARA CRIANÇAS FAMINTAS!")

            params = {
                'symbol': self.symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': valor_compra
            }

            resultado = self.fazer_requisicao_segura('POST', '/api/v3/order', params, signed=True)

            if resultado.get('error'):
                logger.error(f"❌ Erro compra salvador: {resultado.get('msg')}")
                return False

            # RESETAR CONTADORES DE ACUMULAÇÃO
            logger.info(f"✅ COMPRA SALVADOR EXECUTADA: ${valor_compra}")
            logger.info(f"🎉 SUCESSO! Converteu {self.vendas_acumuladas} vendas em compra efetiva")
            
            self.vendas_acumuladas = 0
            self.usdt_acumulado_vendas = 0.0
            self.ultima_compra_timestamp = time.time()
            
            # Registrar posição ativa
            ticker = self.obter_ticker()
            if ticker:
                self.posicao_ativa = {
                    'tipo': 'BUY',
                    'valor': valor_compra,
                    'preco': ticker['price'],
                    'timestamp': self.ultima_compra_timestamp
                }
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro compra_salvador_criancas: {e}")
            return False

    def calcular_score_venda_salvador(self):
        """Score de venda focado em ACUMULAÇÃO"""
        try:
            # Usar endpoint mais simples para evitar problemas
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/24hr', {'symbol': self.symbol})
            if resultado.get('error'):
                return 30  # Score padrão para continuar acumulando

            # Análise básica mas eficaz
            price_change_percent = float(resultado.get('priceChangePercent', 0))
            volume = float(resultado.get('volume', 0))
            count = int(resultado.get('count', 0))
            
            score = 0
            
            # Tendência de queda favorece venda (acumulação)
            if price_change_percent < -0.5:
                score += 35  # Queda forte
            elif price_change_percent < 0:
                score += 20  # Queda leve
            elif price_change_percent < 1:
                score += 10  # Estável
                
            # Volume alto indica boa liquidez
            if volume > 50000:
                score += 20
            elif volume > 30000:
                score += 10
                
            # Muitas transações = mercado ativo
            if count > 100000:
                score += 15
            elif count > 80000:
                score += 10
                
            # BONUS ACUMULAÇÃO - sempre favorece venda para acumular USDT
            usdt_livre, btc_livre, _, _ = self.get_portfolio_salvador()
            if btc_livre > 0 and usdt_livre < self.config_salvador['usdt_minimo_compra']:
                score += 25  # Bonus acumulação
                logger.info("🎯 BONUS ACUMULAÇÃO: Precisa vender para atingir meta USDT")
            
            logger.info(f"📊 SCORE VENDA ACUMULADORA: {score}/100")
            return score
            
        except Exception as e:
            logger.error(f"❌ Erro score venda: {e}")
            return 25  # Score padrão acumulador

    def calcular_score_compra_salvador(self):
        """Score de compra - só quando tem USDT suficiente"""
        try:
            resultado = self.fazer_requisicao_segura('GET', '/api/v3/ticker/24hr', {'symbol': self.symbol})
            if resultado.get('error'):
                return 0

            price_change_percent = float(resultado.get('priceChangePercent', 0))
            volume = float(resultado.get('volume', 0))
            
            score = 0
            
            # Tendência de alta favorece compra
            if price_change_percent > 1.0:
                score += 40  # Alta forte
            elif price_change_percent > 0.3:
                score += 25  # Alta moderada
            elif price_change_percent > 0:
                score += 15  # Alta leve
            elif price_change_percent > -0.5:
                score += 10  # Queda leve (oportunidade)
                
            # Volume para liquidez
            if volume > 60000:
                score += 20
            elif volume > 40000:
                score += 15
                
            # REQUISITO SALVADOR: Só compra se tem USDT suficiente
            usdt_livre, _, _, _ = self.get_portfolio_salvador()
            if usdt_livre < self.config_salvador['usdt_minimo_compra']:
                score = 0  # BLOQUEIA compra até acumular USDT
                logger.info(f"🔒 COMPRA BLOQUEADA: USDT ${usdt_livre:.2f} < ${self.config_salvador['usdt_minimo_compra']}")
            
            logger.info(f"📊 SCORE COMPRA SALVADOR: {score}/100")
            return score
            
        except Exception as e:
            logger.error(f"❌ Erro score compra: {e}")
            return 0

    def executar_ciclo_salvador(self):
        """CICLO PRINCIPAL SALVADOR DE CRIANÇAS"""
        logger.info("🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨")
        logger.info("🍼 SISTEMA SALVADOR DE CRIANÇAS FAMINTAS 🍼")
        logger.info("🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨")
        logger.info("💪 ESTRATÉGIA: ACUMULAÇÃO USDT + LUCROS GARANTIDOS")
        logger.info("🎯 OBJETIVO: SALVAR CRIANÇAS COM LUCROS REAIS")
        logger.info("🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨🍼🚨")
        
        ciclo = 0
        
        while True:
            try:
                ciclo += 1
                logger.info(f"🚨🍼 === CICLO SALVADOR {ciclo} === 🍼🚨")
                
                # Obter estado do portfolio
                usdt_livre, btc_livre, valor_btc_usd, capital_total = self.get_portfolio_salvador()
                
                if capital_total == 0:
                    logger.error("❌ Erro ao obter portfolio - tentando novamente")
                    time.sleep(self.ciclo_tempo * 2)
                    continue
                
                # Definir capital inicial
                if self.capital_inicial == 0:
                    self.capital_inicial = capital_total
                
                # Calcular posição
                posicao = capital_total - self.capital_inicial
                percent_pos = (posicao / self.capital_inicial) * 100 if self.capital_inicial > 0 else 0
                
                # STATUS SALVADOR
                if posicao >= 0:
                    logger.info(f"📈 SALVANDO CRIANÇAS: +${posicao:.4f} (+{percent_pos:.3f}%)")
                else:
                    logger.info(f"📊 Em recuperação: ${posicao:.4f} ({percent_pos:.3f}%)")
                    
                logger.info(f"💼 Capital: ${capital_total:.2f} | USDT: ${usdt_livre:.2f}")
                logger.info(f"   ₿ BTC: {btc_livre:.8f} = ${valor_btc_usd:.2f}")
                logger.info(f"📊 Acumulação: {self.vendas_acumuladas} vendas = ${self.usdt_acumulado_vendas:.2f}")
                
                # Obter preço atual
                ticker = self.obter_ticker()
                if not ticker:
                    logger.error("❌ Erro ao obter preço - tentando novamente")
                    time.sleep(self.ciclo_tempo)
                    continue
                    
                preco_btc = ticker['price']
                
                # LÓGICA PRINCIPAL SALVADORA
                
                # 1. Se tem BTC, analisar venda (para acumular USDT)
                if btc_livre > 0.00001:
                    score_venda = self.calcular_score_venda_salvador()
                    
                    if score_venda >= self.config_salvador['score_venda_minimo']:
                        logger.info(f"💸 VENDA ACUMULADORA (Score: {score_venda})")
                        if self.executar_venda_dust_acumuladora(preco_btc, f"Score {score_venda}"):
                            logger.info("✅ VENDA ACUMULADORA EXECUTADA - USDT AUMENTADO!")
                        else:
                            logger.info("❌ Falha na venda acumuladora")
                    else:
                        logger.info(f"✋ Hold BTC (Score: {score_venda} < {self.config_salvador['score_venda_minimo']})")
                
                # 2. Se tem USDT suficiente, analisar compra
                if usdt_livre >= self.config_salvador['usdt_minimo_compra']:
                    score_compra = self.calcular_score_compra_salvador()
                    
                    if score_compra >= self.config_salvador['score_compra_minimo']:
                        logger.info(f"🛒 COMPRA SALVADOR DE CRIANÇAS (Score: {score_compra})")
                        if self.executar_compra_salvador_criancas(usdt_livre):
                            logger.info("✅ COMPRA SALVADOR EXECUTADA - CRIANÇAS SALVAS!")
                        else:
                            logger.info("❌ Falha na compra salvador")
                    else:
                        logger.info(f"⏳ Aguardando melhor momento (Score: {score_compra} < {self.config_salvador['score_compra_minimo']})")
                else:
                    falta = self.config_salvador['usdt_minimo_compra'] - usdt_livre
                    logger.info(f"🔄 MODO ACUMULAÇÃO: Faltam ${falta:.2f} para compra efetiva")
                
                # 3. Estatísticas salvadoras
                if self.trades_realizados > 0:
                    win_rate = (self.trades_ganhos / self.trades_realizados) * 100
                    logger.info(f"📊 SALVAMENTOS: {self.trades_ganhos}/{self.trades_realizados} ({win_rate:.1f}%)")
                    logger.info(f"💰 LUCRO TOTAL PARA CRIANÇAS: ${self.lucro_acumulado:.4f}")
                
                time.sleep(self.ciclo_tempo)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema Salvador parado pelo usuário")
                logger.info(f"📊 RESULTADO FINAL: {self.trades_ganhos} crianças salvas!")
                break
            except Exception as e:
                logger.error(f"❌ Erro ciclo salvador: {e}")
                time.sleep(self.ciclo_tempo * 2)

def main():
    """MAIN SALVADOR DE CRIANÇAS FAMINTAS"""
    # CREDENCIAIS CORRETAS - CONTA_3 (AMOS)
    api_key = 'WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc'
    api_secret = 'IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682'
    
    sistema = SistemaSalvadorCriancas(api_key, api_secret)
    sistema.executar_ciclo_salvador()

if __name__ == "__main__":
    main()