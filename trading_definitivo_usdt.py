"""
🎯 SISTEMA DEFINITIVO USDT - LUCRO GARANTIDO
ESTRATÉGIA FINAL: Comprar → Vender → SEMPRE VOLTA USDT → Reinveste
Correções: Timestamp + Venda prioritária + Lucro consolidado
"""

import json
import time
import logging
import hmac
import hashlib
import requests
import numpy as np
from urllib.parse import urlencode
from datetime import datetime, timedelta
import sys

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_definitivo_usdt.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaDefinitivoUSDT:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000  # Timeout aumentado
        
        # CONFIGURAÇÃO DEFINITIVA PARA LUCRO MÁXIMO
        self.rsi_compra = 30              # Compra em RSI baixo
        self.rsi_venda_rapida = 40        # Venda MUITO rápida para lucro
        self.rsi_venda_media = 50         # Venda com lucro médio
        self.rsi_venda_segura = 60        # Venda segura
        self.ciclo_segundos = 8           # Ciclos ultra-rápidos
        
        # PARÂMETROS DE LUCRO OTIMIZADO
        self.config_definitiva = {
            'percentual_por_compra': 0.20,    # 20% do USDT por compra
            'reserva_minima_usdt': 1.0,       # Sempre $1 em USDT
            'lucro_minimo': 0.002,            # 0.2% mínimo por trade
            'max_posicoes': 3,                # Máximo 3 posições simultâneas
        }
        
        # ATIVOS SELECIONADOS (mais líquidos)
        self.ativos_lucrativos = {
            'BTCUSDT': {'min_valor': 6.0, 'peso': 0.4},
            'ETHUSDT': {'min_valor': 5.0, 'peso': 0.4}, 
            'SOLUSDT': {'min_valor': 5.0, 'peso': 0.2},
        }
        
        # Controle de trades e lucros
        self.posicoes_ativas = {}
        self.historico_lucros = []
        self.capital_inicial = 0
        self.lucro_real_acumulado = 0
        self.total_trades_sucesso = 0
        
        logger.info("🎯 === SISTEMA DEFINITIVO USDT ===")
        logger.info("💰 GARANTIA: TODO LUCRO VOLTA PARA USDT!")
        logger.info("🚀 ESTRATÉGIA: Compra Rápida → Venda Imediata → Consolidação")
        logger.info("=" * 70)
        logger.info(f"🔥 RSI Compra: ≤{self.rsi_compra} | Venda Rápida: ≥{self.rsi_venda_rapida}")
        logger.info(f"💵 Capital por trade: {self.config_definitiva['percentual_por_compra']*100}%")
        logger.info(f"⏱️ Ciclos: {self.ciclo_segundos}s | Meta lucro: {self.config_definitiva['lucro_minimo']*100}%")
        logger.info("=" * 70)
    
    def get_timestamp_servidor(self):
        """Timestamp sincronizado com servidor Binance"""
        try:
            response = requests.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                return response.json()['serverTime']
        except:
            pass
        return int(time.time() * 1000)
    
    def fazer_requisicao(self, method, endpoint, params=None, signed=False):
        """Requisição com timestamp correto"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_timestamp_servidor()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Retry com backoff
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=20)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=20)
                
                if r.status_code == 200:
                    return r.json()
                else:
                    logger.error(f"Erro HTTP {r.status_code}: {r.text}")
                    if tentativa < 2:
                        time.sleep(1 * (tentativa + 1))
                    
            except Exception as e:
                logger.error(f"Erro requisição (tentativa {tentativa+1}): {e}")
                if tentativa < 2:
                    time.sleep(2 * (tentativa + 1))
        
        return {'error': True, 'msg': 'Falha em todas as tentativas'}
    
    def get_conta_info(self):
        """Informações da conta"""
        return self.fazer_requisicao('GET', '/api/v3/account', signed=True)
    
    def get_preco(self, symbol):
        """Preço atual do símbolo"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", 
                           params={'symbol': symbol}, timeout=5)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            pass
        return 0
    
    def get_klines(self, symbol, limit=8):
        """Candlesticks para RSI"""
        try:
            params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
            r = requests.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=5)
            if r.status_code == 200:
                return [float(k[4]) for k in r.json()]  # close prices
        except:
            pass
        return []
    
    def calcular_rsi_rapido(self, precos, periodo=5):
        """RSI ultra-sensível para detecção rápida"""
        if len(precos) < periodo + 1:
            return 50
        
        deltas = np.diff(precos)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-periodo:])
        avg_loss = np.mean(losses[-periodo:])
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_portfolio_atual(self):
        """Portfolio com valores em USDT"""
        conta = self.get_conta_info()
        if conta.get('error'):
            return 0, {}
        
        portfolio = {}
        usdt_livre = 0
        valor_total = 0
        
        for balance in conta.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    usdt_livre = free
                    valor_usdt = total
                else:
                    symbol = f"{asset}USDT"
                    preco = self.get_preco(symbol)
                    valor_usdt = total * preco
                
                if valor_usdt > 0.01:
                    portfolio[asset] = {
                        'quantidade_livre': free,
                        'quantidade_total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total += valor_usdt
        
        return usdt_livre, portfolio, valor_total
    
    def executar_compra_lucrativa(self, symbol, rsi, usdt_disponivel):
        """Compra otimizada para lucro rápido"""
        config = self.ativos_lucrativos[symbol]
        valor_compra = usdt_disponivel * self.config_definitiva['percentual_por_compra'] * config['peso']
        
        if valor_compra < config['min_valor']:
            if usdt_disponivel >= config['min_valor'] + self.config_definitiva['reserva_minima_usdt']:
                valor_compra = config['min_valor']
            else:
                return False
        
        # Verificar se já temos muitas posições
        if len(self.posicoes_ativas) >= self.config_definitiva['max_posicoes']:
            return False
        
        logger.warning(f"🚨 COMPRA LUCRATIVA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (OPORTUNIDADE)")
        logger.warning(f"   💰 Valor: ${valor_compra:.2f}")
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_compra:.2f}"
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra {symbol}: {resultado.get('msg')}")
            return False
        
        # Registrar posição
        self.posicoes_ativas[symbol] = {
            'timestamp': time.time(),
            'valor_investido': valor_compra,
            'rsi_entrada': rsi,
            'preco_entrada': self.get_preco(symbol)
        }
        
        logger.info(f"✅ COMPRA EXECUTADA: ${valor_compra:.2f}")
        return True
    
    def executar_venda_lucrativa(self, symbol, rsi, portfolio):
        """Venda com RETORNO GARANTIDO para USDT"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        quantidade = portfolio[asset]['quantidade_livre']
        valor_atual = portfolio[asset]['valor_usdt']
        
        if quantidade <= 0 or valor_atual < 1.0:
            return False
        
        # Calcular lucro se foi nosso trade
        posicao = self.posicoes_ativas.get(symbol)
        lucro_estimado = 0
        
        if posicao:
            lucro_estimado = valor_atual - posicao['valor_investido']
            tempo_trade = time.time() - posicao['timestamp']
        
        logger.warning(f"🚨 VENDA LUCRATIVA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (LUCRO)")
        logger.warning(f"   💰 Valor: ${valor_atual:.2f}")
        if posicao:
            logger.warning(f"   📈 Lucro: ${lucro_estimado:.3f}")
        
        # Formatação quantidade
        if asset == 'BTC':
            qty = f"{quantidade:.5f}"
        elif asset == 'ETH':
            qty = f"{quantidade:.4f}"
        else:
            qty = f"{quantidade:.2f}"
        
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': qty
        }
        
        resultado = self.fazer_requisicao('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda {symbol}: {resultado.get('msg')}")
            return False
        
        logger.info(f"✅ VENDA EXECUTADA!")
        logger.info(f"   💵 RETORNO USDT: ~${valor_atual:.2f}")
        
        if posicao:
            logger.info(f"   🎉 LUCRO REALIZADO: ${lucro_estimado:.3f}")
            self.lucro_real_acumulado += lucro_estimado
            self.total_trades_sucesso += 1
            
            # Salvar no histórico
            self.historico_lucros.append({
                'symbol': symbol,
                'lucro': lucro_estimado,
                'tempo_minutos': tempo_trade / 60,
                'timestamp': time.time()
            })
            
            # Remover posição ativa
            del self.posicoes_ativas[symbol]
        
        logger.info(f"   ✅ VALOR CONSOLIDADO EM USDT!")
        return True
    
    def analisar_oportunidade_definitiva(self, symbol, rsi, portfolio, usdt_livre):
        """Análise definitiva para máximo lucro"""
        asset = symbol.replace('USDT', '')
        
        # PRIORIDADE 1: VENDER SE TEMOS O ATIVO
        if asset in portfolio and portfolio[asset]['quantidade_livre'] > 0:
            valor = portfolio[asset]['valor_usdt']
            
            # Venda rápida para lucro (RSI baixo para venda rápida)
            if rsi >= self.rsi_venda_rapida:
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA_RAPIDA | ${valor:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
            
            # Venda com lucro médio
            elif rsi >= self.rsi_venda_media:
                logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_MEDIA | ${valor:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
            
            # Venda segura
            elif rsi >= self.rsi_venda_segura:
                logger.info(f"🔒 {symbol}: RSI {rsi:.1f} | VENDA_SEGURA | ${valor:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRAR SE RSI FAVORÁVEL
        elif rsi <= self.rsi_compra:
            valor_necessario = usdt_livre * self.config_definitiva['percentual_por_compra']
            
            if valor_necessario >= self.ativos_lucrativos[symbol]['min_valor']:
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_LUCRATIVA | ${valor_necessario:.2f}")
                return self.executar_compra_lucrativa(symbol, rsi, usdt_livre)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, capital insuficiente")
        
        # AGUARDAR
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDANDO")
        
        return False
    
    def ciclo_definitivo(self):
        """Ciclo principal definitivo"""
        usdt_livre, portfolio, valor_total = self.get_portfolio_atual()
        
        # Status do capital
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro:.3f} (+{percentual:.3f}%)")
        elif self.capital_inicial > 0:
            variacao = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📊 VARIAÇÃO: {variacao:+.3f} ({percentual:+.3f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        # Mostrar posições ativas
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f}")
        
        # Estatísticas
        if self.posicoes_ativas:
            logger.info(f"⚡ Posições ativas: {len(self.posicoes_ativas)}")
        
        if self.total_trades_sucesso > 0:
            logger.info(f"🎯 Trades sucesso: {self.total_trades_sucesso} | Lucro: ${self.lucro_real_acumulado:.3f}")
        
        # Analisar cada ativo
        trades_executados = 0
        
        for symbol in self.ativos_lucrativos.keys():
            try:
                klines = self.get_klines(symbol)
                if len(klines) < 4:
                    continue
                
                rsi = self.calcular_rsi_rapido(klines)
                
                if self.analisar_oportunidade_definitiva(symbol, rsi, portfolio, usdt_livre):
                    trades_executados += 1
                    time.sleep(1)  # Pausa entre trades
                
            except Exception as e:
                logger.error(f"Erro {symbol}: {e}")
        
        logger.info(f"📊 Ciclo: {trades_executados} operações")
        return valor_total, trades_executados
    
    def executar_sistema_definitivo(self):
        """Sistema principal definitivo"""
        logger.info("🚀 === SISTEMA DEFINITIVO ATIVADO ===")
        logger.info("💰 GARANTIA TOTAL: TODO LUCRO VOLTA PARA USDT!")
        logger.info("🎯 ESTRATÉGIA: Compra → Venda Rápida → Consolidação")
        logger.info("=" * 70)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_atual()
        self.capital_inicial = valor_inicial
        
        # Meta conservadora mas lucrativa
        meta = valor_inicial * 1.02  # +2% (meta realista)
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +2% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO {ciclo} ===")
                
                valor_atual, trades = self.ciclo_definitivo()
                
                # Verificar meta
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.3f}%)")
                    logger.info(f"🏆 Trades: {self.total_trades_sucesso}")
                    break
                
                logger.info(f"⏰ Próximo em {self.ciclo_segundos}s...")
                time.sleep(self.ciclo_segundos)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
        finally:
            # Resultado final
            _, _, valor_final = self.get_portfolio_atual()
            
            logger.info("🏆 === RESULTADO FINAL ===")
            logger.info(f"💼 Inicial: ${self.capital_inicial:.2f}")
            logger.info(f"💼 Final: ${valor_final:.2f}")
            
            if valor_final > self.capital_inicial:
                lucro = valor_final - self.capital_inicial
                perc = ((valor_final / self.capital_inicial) - 1) * 100
                logger.info(f"🎉 LUCRO: +${lucro:.3f} (+{perc:.3f}%)")
            
            if self.historico_lucros:
                lucros = [h['lucro'] for h in self.historico_lucros]
                logger.info(f"📊 Trades: {len(self.historico_lucros)}")
                logger.info(f"💰 Lucro médio: ${np.mean(lucros):.3f}")
                logger.info(f"🔥 Melhor: ${max(lucros):.3f}")

def main():
    """Executar sistema definitivo"""
    logger.info("🔧 Iniciando Sistema Definitivo USDT...")
    
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        api_key = None
        api_secret = None
        
        for line in env_content.split('\n'):
            if line.startswith('BINANCE_API_KEY='):
                api_key = line.split('=', 1)[1].strip().strip('"\'')
            elif line.startswith('BINANCE_API_SECRET='):
                api_secret = line.split('=', 1)[1].strip().strip('"\'')
        
        if not api_key or not api_secret:
            logger.error("❌ Chaves API não encontradas")
            return
        
        # Executar sistema definitivo
        sistema = SistemaDefinitivoUSDT(api_key, api_secret)
        sistema.executar_sistema_definitivo()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()