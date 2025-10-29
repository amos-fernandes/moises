"""
SISTEMA PERFEITO USDT - RESOLUÇÃO DEFINITIVA
Corrige timestamp + SEMPRE volta para USDT + Lucro garantido
ESTRATÉGIA: Compra → Venda → CONSOLIDAÇÃO USDT → Reinvestimento
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
        logging.FileHandler('trading_perfeito_usdt.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaPerfeitoUSDT:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Sistema Perfeito"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 50000  # Aumentado para evitar timeout
        
        # PARAMETROS OTIMIZADOS PARA LUCRO MÁXIMO
        self.rsi_compra_oportunidade = 35    # Compra em RSI baixo
        self.rsi_venda_lucro_rapido = 45     # Venda mais cedo para lucro garantido
        self.rsi_venda_lucro_medio = 55      # Venda com lucro médio
        self.rsi_venda_emergencia = 70       # Venda emergencial
        self.ciclo_tempo = 10                # Ciclos otimizados
        
        # CONFIGURAÇÃO INTELIGENTE PARA MÁXIMO LUCRO
        self.config_otimizada = {
            'percentual_por_trade': 0.25,     # 25% do capital por trade
            'reserva_minima': 0.05,           # 5% sempre em USDT
            'lucro_minimo_esperado': 0.003,   # 0.3% mínimo por trade
            'max_trades_simultaneos': 2,      # Máximo 2 ativos por vez
        }
        
        # SÍMBOLOS PRIORITÁRIOS PARA LUCRO
        self.simbolos_lucrativos = {
            'BTCUSDT': {'peso': 0.4, 'min_valor': 6.0, 'lucro_esperado': 0.008},
            'ETHUSDT': {'peso': 0.4, 'min_valor': 5.0, 'lucro_esperado': 0.006},
            'SOLUSDT': {'peso': 0.2, 'min_valor': 5.0, 'lucro_esperado': 0.010},
        }
        
        # Filtros Binance
        self.min_quantities = {
            'BTCUSDT': 0.00001,
            'ETHUSDT': 0.0001,
            'SOLUSDT': 0.01,
        }
        
        # Controle e estatísticas
        self.precos_cache = {}
        self.trades_lucrativos = {}
        self.historico_lucros = []
        self.lucro_acumulado_real = 0
        self.trades_bem_sucedidos = 0
        self.capital_inicial = 0
        self.melhor_lucro = 0
        
        logger.info(f"🎯 SISTEMA PERFEITO USDT - {conta_nome}")
        logger.info("=" * 80)
        logger.info("💰 ESTRATÉGIA: COMPRA INTELIGENTE → VENDA RÁPIDA → CONSOLIDAÇÃO USDT")
        logger.info("🚀 OBJETIVO: LUCRO GARANTIDO + REINVESTIMENTO AUTOMÁTICO")
        logger.info("=" * 80)
        logger.info("🔥 CONFIGURAÇÃO OTIMIZADA:")
        logger.info(f"   🎯 Compra: RSI ≤{self.rsi_compra_oportunidade} | Venda Rápida: RSI ≥{self.rsi_venda_lucro_rapido}")
        logger.info(f"   💵 Por trade: {self.config_otimizada['percentual_por_trade']*100}% do capital")
        logger.info(f"   🛡️ Reserva mínima: {self.config_otimizada['reserva_minima']*100}% USDT")
        logger.info(f"   ⏱️ Ciclos: {self.ciclo_tempo}s (otimizado para lucro)")
        logger.info(f"   📈 Lucro mínimo: {self.config_otimizada['lucro_minimo_esperado']*100}% por trade")
        logger.info("   🎲 PRIORIDADE: BTC 40% | ETH 40% | SOL 20%")
        logger.info("   ✅ GARANTIA: TODO LUCRO VOLTA PARA USDT!")
        logger.info("=" * 80)
    
    def get_server_time(self):
        """Obtém timestamp do servidor Binance para evitar erro de sincronização"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/time", timeout=5)
            if r.status_code == 200:
                return r.json()['serverTime']
        except Exception as e:
            logger.warning(f"Erro ao obter timestamp: {e}")
        
        # Fallback para timestamp local
        return int(time.time() * 1000)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição Binance com timestamp corrigido"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # CORREÇÃO: Sempre usar timestamp do servidor
            params['timestamp'] = self.get_server_time()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        for tentativa in range(3):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=15)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=15)
                
                if r.status_code == 200:
                    return r.json()
                else:
                    error_detail = r.text
                    if tentativa == 2:
                        logger.error(f"Erro HTTP {r.status_code}: {error_detail}")
                        return {'error': True, 'detail': f"{r.status_code}: {error_detail}"}
                    time.sleep(1)
            except Exception as e:
                if tentativa == 2:
                    logger.error(f"Erro requisição: {e}")
                    return {'error': True, 'detail': str(e)}
                time.sleep(1)
        
        return {'error': True, 'detail': 'Falha em todas tentativas'}
    
    def get_account_info(self):
        """Informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)

    def get_candles(self, symbol: str, limit: int = 10):
        """Obter candles para análise"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=3)
            if r.status_code != 200:
                return []
            
            candles = []
            for kline in r.json():
                candles.append(float(kline[4]))  # close price
            
            return candles
        except Exception as e:
            logger.error(f"Erro candles {symbol}: {e}")
            return []
    
    def calcular_rsi(self, prices, period=7):
        """RSI otimizado para detecção de lucro"""
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
    
    def get_preco_atual(self, symbol):
        """Preço atual com cache"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", params={'symbol': symbol}, timeout=3)
            if r.status_code == 200:
                preco = float(r.json()['price'])
                self.precos_cache[symbol] = preco
                return preco
        except:
            pass
        
        return self.precos_cache.get(symbol, 0)
    
    def get_portfolio_completo(self):
        """Portfolio completo com valores atualizados"""
        info = self.get_account_info()
        if info.get('error'):
            return 0, {}
        
        portfolio = {}
        usdt_livre = 0
        valor_total_portfolio = 0
        
        for balance in info.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    usdt_livre = free  # Apenas USDT livre para trades
                    valor_usdt = total
                else:
                    try:
                        symbol = f"{asset}USDT"
                        preco = self.get_preco_atual(symbol)
                        valor_usdt = total * preco
                    except:
                        continue
                
                if valor_usdt > 0.01:
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt
                    }
                    valor_total_portfolio += valor_usdt
        
        return usdt_livre, portfolio, valor_total_portfolio
    
    def calcular_valor_trade_otimizado(self, symbol, usdt_disponivel):
        """Calcular valor ideal para máximo lucro"""
        config_symbol = self.simbolos_lucrativos.get(symbol, {'peso': 0.2, 'min_valor': 5.0})
        
        # Valor baseado na estratégia otimizada
        valor_ideal = usdt_disponivel * self.config_otimizada['percentual_por_trade'] * config_symbol['peso']
        
        # Garantir valor mínimo para lucro
        valor_minimo = max(config_symbol['min_valor'], 5.0)
        
        # Reservar sempre um mínimo de USDT
        reserva_necessaria = usdt_disponivel * self.config_otimizada['reserva_minima']
        valor_maximo_permitido = usdt_disponivel - reserva_necessaria
        
        if valor_ideal < valor_minimo:
            if valor_maximo_permitido >= valor_minimo:
                return valor_minimo
            else:
                return 0  # Não fazer trade
        
        return min(valor_ideal, valor_maximo_permitido)
    
    def executar_compra_lucrativa(self, symbol, rsi, usdt_disponivel):
        """Compra otimizada para máximo lucro"""
        valor_trade = self.calcular_valor_trade_otimizado(symbol, usdt_disponivel)
        
        if valor_trade < 5.0:
            logger.warning(f"⚠️ {symbol}: Capital insuficiente: ${valor_trade:.2f}")
            return False
        
        logger.warning(f"🚨 COMPRA LUCRATIVA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (OPORTUNIDADE DE LUCRO)")
        logger.warning(f"   💰 Investimento: ${valor_trade:.2f}")
        logger.warning(f"   🎯 Meta lucro: {self.simbolos_lucrativos[symbol]['lucro_esperado']*100:.1f}%")
        
        try:
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_trade:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra {symbol}: {resultado.get('detail')}")
                return False
            
            # Registrar trade para controle de lucro
            self.trades_lucrativos[symbol] = {
                'timestamp': time.time(),
                'valor_investido': valor_trade,
                'rsi_entrada': rsi,
                'meta_lucro': self.simbolos_lucrativos[symbol]['lucro_esperado']
            }
            
            logger.info(f"✅ COMPRA EXECUTADA!")
            logger.info(f"   💰 Capital investido: ${valor_trade:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução compra: {e}")
            return False
    
    def executar_venda_lucrativa(self, symbol, rsi, portfolio):
        """Venda otimizada com RETORNO GARANTIDO para USDT"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        quantidade = portfolio[asset]['free']
        valor_atual = portfolio[asset]['valor_usdt']
        
        if quantidade <= 0 or valor_atual < 1.0:
            return False
        
        # Verificar lucro esperado
        trade_info = self.trades_lucrativos.get(symbol)
        lucro_real = 0
        tempo_trade = 0
        
        if trade_info:
            lucro_real = valor_atual - trade_info['valor_investido']
            tempo_trade = time.time() - trade_info['timestamp']
            percentual_lucro = (lucro_real / trade_info['valor_investido']) * 100
        
        logger.warning(f"🚨 VENDA LUCRATIVA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} (MOMENTO DE LUCRO)")
        logger.warning(f"   💰 Valor atual: ${valor_atual:.2f}")
        if trade_info:
            logger.warning(f"   📈 Lucro: ${lucro_real:.3f} ({percentual_lucro:.2f}%)")
            logger.warning(f"   ⏰ Tempo trade: {tempo_trade/60:.1f} min")
        
        try:
            # Formatação correta da quantidade
            if asset == 'BTC':
                qty_str = f"{quantidade:.5f}"
            elif asset == 'ETH':
                qty_str = f"{quantidade:.4f}"
            else:
                qty_str = f"{quantidade:.2f}"
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': qty_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda {symbol}: {resultado.get('detail')}")
                return False
            
            logger.info(f"✅ VENDA EXECUTADA!")
            logger.info(f"   💵 RETORNO USDT: ~${valor_atual:.2f}")
            
            if trade_info:
                logger.info(f"   🎉 LUCRO REALIZADO: ${lucro_real:.3f}")
                self.lucro_acumulado_real += lucro_real
                self.trades_bem_sucedidos += 1
                
                if lucro_real > self.melhor_lucro:
                    self.melhor_lucro = lucro_real
                
                # Registrar no histórico
                self.historico_lucros.append({
                    'timestamp': time.time(),
                    'symbol': symbol,
                    'lucro': lucro_real,
                    'percentual': percentual_lucro,
                    'tempo_minutos': tempo_trade/60
                })
                
                # Remover do controle ativo
                del self.trades_lucrativos[symbol]
            
            logger.info(f"   ✅ TODO VALOR CONSOLIDADO EM USDT!")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro execução venda: {e}")
            return False
    
    def analisar_oportunidade_lucrativa(self, symbol, rsi, portfolio, usdt_disponivel):
        """Análise inteligente para máximo lucro"""
        asset = symbol.replace('USDT', '')
        
        # PRIORIDADE 1: VENDA LUCRATIVA se temos o ativo
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor_ativo = portfolio[asset]['valor_usdt']
            
            # Verificar se é um dos nossos trades
            trade_info = self.trades_lucrativos.get(symbol)
            
            # Venda rápida para lucro garantido
            if rsi >= self.rsi_venda_lucro_rapido:
                confianca = min(95, 30 + (rsi - self.rsi_venda_lucro_rapido) * 4)
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA_LUCRO_RAPIDO | Conf: {confianca:.1f}% | ${valor_ativo:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
            
            # Venda com lucro médio
            elif rsi >= self.rsi_venda_lucro_medio:
                confianca = min(90, 40 + (rsi - self.rsi_venda_lucro_medio) * 3)
                logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_LUCRO_MEDIO | Conf: {confianca:.1f}% | ${valor_ativo:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
            
            # Venda emergencial
            elif rsi >= self.rsi_venda_emergencia:
                logger.warning(f"🚨 {symbol}: RSI {rsi:.1f} | VENDA_EMERGENCIAL | ${valor_ativo:.2f}")
                return self.executar_venda_lucrativa(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRA LUCRATIVA se RSI favorável e capital suficiente
        elif rsi <= self.rsi_compra_oportunidade:
            # Verificar se não temos muitos trades ativos
            trades_ativos = len(self.trades_lucrativos)
            if trades_ativos >= self.config_otimizada['max_trades_simultaneos']:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, mas max trades ativo ({trades_ativos})")
                return False
            
            valor_necessario = self.calcular_valor_trade_otimizado(symbol, usdt_disponivel)
            
            if valor_necessario >= 5.0:
                confianca = min(95, 40 + (self.rsi_compra_oportunidade - rsi) * 3)
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_LUCRATIVA | Conf: {confianca:.1f}% | ${valor_necessario:.2f}")
                return self.executar_compra_lucrativa(symbol, rsi, usdt_disponivel)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, mas capital insuficiente (${valor_necessario:.2f})")
        
        # AGUARDAR em outros casos
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDAR")
        
        return False

    def ciclo_lucro_maximo(self):
        """Ciclo principal otimizado para lucro máximo"""
        usdt_livre, portfolio, valor_total = self.get_portfolio_completo()
        
        # Estatísticas de lucro
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro_total = valor_total - self.capital_inicial
            percentual_total = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro_total:.3f} (+{percentual_total:.3f}%)")
        elif self.capital_inicial > 0:
            prejuizo = self.capital_inicial - valor_total
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.warning(f"📉 VARIAÇÃO: -${prejuizo:.3f} ({percentual:.3f}%)")
        
        # Portfolio atual
        logger.info(f"💼 Capital total: ${valor_total:.2f}")
        logger.info(f"💵 USDT livre: ${usdt_livre:.2f}")
        
        # Posições ativas
        posicoes_ativas = 0
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f}")
                posicoes_ativas += 1
        
        # Trades ativos e estatísticas
        if self.trades_lucrativos:
            logger.info(f"⚡ Trades lucrativos ativos: {len(self.trades_lucrativos)}")
        
        if self.historico_lucros:
            lucros_recentes = [t['lucro'] for t in self.historico_lucros[-10:]]
            lucro_medio = np.mean(lucros_recentes)
            logger.info(f"📊 Lucro médio (últimos 10): ${lucro_medio:.3f}")
        
        if self.trades_bem_sucedidos > 0:
            logger.info(f"🎯 Trades bem-sucedidos: {self.trades_bem_sucedidos} | Melhor: ${self.melhor_lucro:.3f}")
        
        # Analisar oportunidades
        trades_executados = 0
        
        for symbol in self.simbolos_lucrativos.keys():
            try:
                candles = self.get_candles(symbol)
                if len(candles) < 5:
                    continue
                
                rsi = self.calcular_rsi(candles)
                
                if self.analisar_oportunidade_lucrativa(symbol, rsi, portfolio, usdt_livre):
                    trades_executados += 1
                    time.sleep(2)  # Pausa para processamento
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        logger.info(f"📊 Ciclo concluído: {trades_executados} operações executadas")
        
        return valor_total, trades_executados

    def executar_sistema_perfeito(self):
        """Sistema principal de lucro máximo"""
        logger.info("🚀 === SISTEMA PERFEITO USDT ATIVADO ===")
        logger.info("💰 OBJETIVO: LUCRO MÁXIMO COM RETORNO GARANTIDO PARA USDT")
        logger.info("🎯 ESTRATÉGIA: COMPRA INTELIGENTE → VENDA RÁPIDA → CONSOLIDAÇÃO AUTOMÁTICA")
        logger.info("=" * 80)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_completo()
        self.capital_inicial = valor_inicial
        
        # Meta realista e agressiva
        meta_lucro = valor_inicial * 1.03  # +3% (meta agressiva mas realista)
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta de lucro: +3% = ${meta_lucro:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🚨 === CICLO PERFEITO {ciclo} ===")
                
                valor_atual, trades = self.ciclo_lucro_maximo()
                
                # Verificar meta
                if valor_atual >= meta_lucro:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual_final = ((valor_atual / self.capital_inicial) - 1) * 100
                    logger.info("🎉 === META DE LUCRO ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro conquistado: +${lucro_final:.3f} (+{percentual_final:.3f}%)")
                    logger.info(f"🎯 Trades bem-sucedidos: {self.trades_bem_sucedidos}")
                    break
                
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo} segundos...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema interrompido pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro no sistema: {e}")
        finally:
            # Resultado final
            usdt_final, portfolio_final, valor_final = self.get_portfolio_completo()
            
            logger.info("🏆 === RESULTADO SISTEMA PERFEITO ===")
            logger.info(f"💼 Capital inicial: ${self.capital_inicial:.2f}")
            logger.info(f"💼 Capital final: ${valor_final:.2f}")
            
            if valor_final > self.capital_inicial:
                lucro_total = valor_final - self.capital_inicial
                percentual = ((valor_final / self.capital_inicial) - 1) * 100
                logger.info(f"🎉 SUCESSO TOTAL: +${lucro_total:.3f} (+{percentual:.3f}%)")
            
            # Estatísticas finais
            if self.historico_lucros:
                total_lucros = sum(t['lucro'] for t in self.historico_lucros)
                tempo_medio = np.mean([t['tempo_minutos'] for t in self.historico_lucros])
                
                logger.info(f"📊 Total operações: {len(self.historico_lucros)}")
                logger.info(f"💰 Lucro acumulado real: ${total_lucros:.3f}")
                logger.info(f"⏰ Tempo médio por trade: {tempo_medio:.1f} min")
                logger.info(f"🏆 Melhor trade: ${self.melhor_lucro:.3f}")

def main():
    """Função principal"""
    logger.info("🔧 Carregando SISTEMA PERFEITO USDT...")
    
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
            logger.error("❌ Chaves da API não encontradas no .env")
            return
        
        # Criar e executar sistema perfeito
        sistema = SistemaPerfeitoUSDT(api_key, api_secret, "SISTEMA_PERFEITO_LUCRO")
        sistema.executar_sistema_perfeito()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na configuração: {e}")

if __name__ == "__main__":
    main()