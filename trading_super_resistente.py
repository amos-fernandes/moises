"""
🛡️ SISTEMA SUPER-RESISTENTE - CORREÇÃO TOTAL
Resolve: Conexão + DNS + Capital + Oportunidades Perdidas
ESTRATÉGIA BLINDADA: Máxima resistência + Aproveitamento total
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
import socket
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Logging otimizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_super_resistente.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaSuperResistente:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO SUPER-RESISTENTE
        self.rsi_compra = 30              # RSI para compra (mais conservador)
        self.rsi_venda_rapida = 40        # Venda ultra-rápida
        self.rsi_venda_normal = 50        # Venda normal
        self.rsi_venda_segura = 60        # Venda segura
        self.ciclo_tempo = 8              # Ciclos mais espaçados
        
        # PARÂMETROS CORRIGIDOS
        self.config_resistente = {
            'percentual_trade': 0.15,         # 15% do capital por trade
            'reserva_usdt': 1.0,             # $1 de reserva
            'valor_minimo_trade': 4.0,       # Mínimo $4 por trade (CORRIGIDO!)
            'max_tentativas_conexao': 10,    # Máx tentativas conexão
            'timeout_conexao': 30,           # Timeout maior
            'delay_retry': 5,                # Delay entre retries
        }
        
        # ATIVOS COM VALORES CORRIGIDOS
        self.ativos_resistentes = {
            'BTCUSDT': {'min_valor': 4.0, 'peso': 0.35, 'step_size': 0.00001},
            'ETHUSDT': {'min_valor': 4.0, 'peso': 0.40, 'step_size': 0.0001}, 
            'SOLUSDT': {'min_valor': 4.0, 'peso': 0.25, 'step_size': 0.01},
        }
        
        # Controle resistente
        self.trades_ativos = {}
        self.historico_operacoes = []
        self.capital_inicial = 0
        self.lucro_consolidado = 0
        self.vendas_executadas = 0
        self.compras_executadas = 0
        self.erros_conexao = 0
        self.ultima_conexao_ok = time.time()
        
        # Configurar session com retry
        self.session = self.configurar_session_resistente()
        
        logger.info("🛡️ === SISTEMA SUPER-RESISTENTE ATIVADO ===")
        logger.info("🔧 CORREÇÕES: DNS + Timeout + Capital + Oportunidades")
        logger.info("💪 BLINDAGEM TOTAL: Máxima resistência a falhas")
        logger.info("=" * 80)
        logger.info(f"🔥 RSI: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda_rapida}")
        logger.info(f"💵 Trade: {self.config_resistente['percentual_trade']*100}% | Mín: ${self.config_resistente['valor_minimo_trade']}")
        logger.info(f"⏱️ Ciclos: {self.ciclo_tempo}s | Timeout: {self.config_resistente['timeout_conexao']}s")
        logger.info(f"🌐 Retry: {self.config_resistente['max_tentativas_conexao']}x | Delay: {self.config_resistente['delay_retry']}s")
        logger.info("=" * 80)
    
    def configurar_session_resistente(self):
        """Configurar session HTTP ultra-resistente"""
        session = requests.Session()
        
        # Configurar retry strategy
        retry_strategy = Retry(
            total=5,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=2,
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Headers otimizados
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })
        
        return session
    
    def verificar_conectividade(self):
        """Verificar se consegue conectar na Binance"""
        try:
            # Teste DNS
            socket.gethostbyname('api.binance.com')
            
            # Teste HTTP simples
            response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=10)
            if response.status_code == 200:
                self.ultima_conexao_ok = time.time()
                self.erros_conexao = 0
                return True
        except Exception as e:
            self.erros_conexao += 1
            logger.warning(f"⚠️ Problemas de conectividade: {e}")
        
        return False
    
    def get_server_time_resistente(self):
        """Timestamp ultra-resistente com múltiplos fallbacks"""
        # Tentar obter do servidor
        for tentativa in range(3):
            try:
                if self.verificar_conectividade():
                    response = self.session.get(f"{BASE_URL}/api/v3/time", timeout=15)
                    if response.status_code == 200:
                        return response.json()['serverTime']
            except Exception as e:
                logger.warning(f"Erro timestamp (tent {tentativa+1}): {e}")
                time.sleep(1)
        
        # Fallback para timestamp local
        logger.warning("⚠️ Usando timestamp local como fallback")
        return int(time.time() * 1000)
    
    def fazer_requisicao_super_resistente(self, method, endpoint, params=None, signed=False):
        """Requisição super-resistente com múltiplas estratégias"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_server_time_resistente()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Estratégia de retry super-resistente
        for tentativa in range(self.config_resistente['max_tentativas_conexao']):
            try:
                # Verificar conectividade primeiro
                if not self.verificar_conectividade():
                    logger.warning(f"⚠️ Sem conectividade (tent {tentativa+1})")
                    time.sleep(self.config_resistente['delay_retry'])
                    continue
                
                # Fazer requisição
                if method == 'GET':
                    r = self.session.get(url, params=params, headers=headers, 
                                       timeout=self.config_resistente['timeout_conexao'])
                else:
                    r = self.session.post(url, params=params, headers=headers, 
                                        timeout=self.config_resistente['timeout_conexao'])
                
                if r.status_code == 200:
                    self.erros_conexao = 0
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    logger.warning(f"Erro 400: {error_data.get('msg', r.text)}")
                    
                    # Erros que não devem repetir
                    if any(code in error_data.get('msg', '') for code in ['insufficient balance', 'MIN_NOTIONAL', '-2010']):
                        return {'error': True, 'code': error_data.get('code'), 'msg': error_data.get('msg')}
                else:
                    logger.warning(f"HTTP {r.status_code} (tent {tentativa+1}): {r.text}")
                
            except Exception as e:
                logger.error(f"Erro requisição (tent {tentativa+1}): {e}")
                self.erros_conexao += 1
            
            # Delay progressivo
            if tentativa < self.config_resistente['max_tentativas_conexao'] - 1:
                delay = self.config_resistente['delay_retry'] * (tentativa + 1)
                logger.info(f"⏳ Aguardando {delay}s antes da próxima tentativa...")
                time.sleep(delay)
        
        logger.error(f"❌ Falha total após {self.config_resistente['max_tentativas_conexao']} tentativas")
        return {'error': True, 'msg': 'Falha de conectividade total'}
    
    def get_account_info_resistente(self):
        """Info da conta super-resistente"""
        return self.fazer_requisicao_super_resistente('GET', '/api/v3/account', signed=True)
    
    def get_preco_atual_resistente(self, symbol):
        """Preço com múltiplos fallbacks"""
        for tentativa in range(3):
            try:
                r = self.session.get(f"{BASE_URL}/api/v3/ticker/price", 
                                   params={'symbol': symbol}, timeout=15)
                if r.status_code == 200:
                    return float(r.json()['price'])
            except Exception as e:
                logger.warning(f"Erro preço {symbol} (tent {tentativa+1}): {e}")
                time.sleep(2)
        
        logger.error(f"❌ Não foi possível obter preço de {symbol}")
        return 0
    
    def get_klines_resistente(self, symbol, limit=8):
        """Klines super-resistentes"""
        for tentativa in range(3):
            try:
                params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
                r = self.session.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=15)
                if r.status_code == 200:
                    return [float(k[4]) for k in r.json()]
            except Exception as e:
                logger.warning(f"Erro klines {symbol} (tent {tentativa+1}): {e}")
                time.sleep(2)
        
        logger.error(f"❌ Não foi possível obter klines de {symbol}")
        return []
    
    def calcular_rsi_otimizado(self, precos, periodo=5):
        """RSI otimizado para detecção precisa"""
        if len(precos) < periodo + 1:
            return 50
        
        deltas = np.diff(precos)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-periodo:])
        avg_loss = np.mean(losses[-periodo:])
        
        if avg_loss == 0:
            return 100
        if avg_gain == 0:
            return 0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_portfolio_detalhado_resistente(self):
        """Portfolio com verificação super-resistente"""
        conta = self.get_account_info_resistente()
        if conta.get('error'):
            logger.error(f"❌ Erro ao obter conta: {conta.get('msg')}")
            return 0, {}, 0
        
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
                    preco = self.get_preco_atual_resistente(symbol)
                    valor_usdt = total * preco
                
                if valor_usdt >= 0.01:
                    portfolio[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total,
                        'valor_usdt': valor_usdt,
                        'preco_atual': preco if asset != 'USDT' else 1.0
                    }
                    valor_total += valor_usdt
        
        return usdt_livre, portfolio, valor_total
    
    def calcular_valor_trade_corrigido(self, symbol, usdt_disponivel):
        """Cálculo CORRIGIDO do valor de trade"""
        config = self.ativos_resistentes.get(symbol, {'peso': 0.2, 'min_valor': 4.0})
        
        # CORREÇÃO: Verificar se tem USDT suficiente
        if usdt_disponivel < self.config_resistente['valor_minimo_trade']:
            logger.warning(f"⚠️ {symbol}: USDT insuficiente ${usdt_disponivel:.2f} < ${self.config_resistente['valor_minimo_trade']}")
            return 0
        
        # Valor baseado no percentual e peso
        valor_ideal = usdt_disponivel * self.config_resistente['percentual_trade'] * config['peso']
        
        # Garantir valor mínimo
        valor_minimo = max(config['min_valor'], self.config_resistente['valor_minimo_trade'])
        
        # CORREÇÃO: Verificar se pode fazer o trade
        if valor_ideal < valor_minimo:
            # Se tem USDT suficiente, usar o mínimo
            if usdt_disponivel >= valor_minimo + self.config_resistente['reserva_usdt']:
                valor_final = valor_minimo
            else:
                logger.info(f"💡 {symbol}: USDT disponível ${usdt_disponivel:.2f} insuficiente para mínimo ${valor_minimo:.2f}")
                return 0
        else:
            valor_final = valor_ideal
        
        # Verificar reserva
        if usdt_disponivel - valor_final < self.config_resistente['reserva_usdt']:
            valor_final = usdt_disponivel - self.config_resistente['reserva_usdt']
            if valor_final < valor_minimo:
                logger.info(f"💡 {symbol}: Após reserva ${self.config_resistente['reserva_usdt']}, valor insuficiente")
                return 0
        
        logger.info(f"💰 {symbol}: Valor calculado ${valor_final:.2f} (USDT: ${usdt_disponivel:.2f})")
        return valor_final
    
    def executar_compra_resistente(self, symbol, rsi, usdt_disponivel):
        """Compra super-resistente"""
        valor_trade = self.calcular_valor_trade_corrigido(symbol, usdt_disponivel)
        
        if valor_trade <= 0:
            return False
        
        logger.warning(f"🚨 COMPRA RESISTENTE: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_trade:.2f}")
        logger.warning(f"   💵 USDT disponível: ${usdt_disponivel:.2f}")
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_trade:.2f}"
        }
        
        resultado = self.fazer_requisicao_super_resistente('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra {symbol}: {resultado.get('msg')}")
            return False
        
        # Registrar trade
        self.trades_ativos[symbol] = {
            'timestamp': time.time(),
            'valor_investido': valor_trade,
            'rsi_entrada': rsi
        }
        
        self.compras_executadas += 1
        logger.info(f"✅ COMPRA EXECUTADA: ${valor_trade:.2f}")
        return True
    
    def executar_venda_resistente(self, symbol, rsi, portfolio):
        """Venda super-resistente"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            return False
        
        info_asset = portfolio[asset]
        quantidade_livre = info_asset['free']
        valor_atual = info_asset['valor_usdt']
        
        if quantidade_livre <= 0 or valor_atual < 1.0:
            return False
        
        # Calcular lucro
        trade_info = self.trades_ativos.get(symbol)
        lucro_estimado = 0
        
        if trade_info:
            lucro_estimado = valor_atual - trade_info['valor_investido']
        
        logger.warning(f"🚨 VENDA RESISTENTE: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_atual:.2f}")
        if trade_info:
            logger.warning(f"   📈 Lucro: ${lucro_estimado:.3f}")
        
        # Formatação quantidade
        if asset == 'BTC':
            qty = f"{quantidade_livre:.5f}"
        elif asset == 'ETH':
            qty = f"{quantidade_livre:.4f}"
        else:
            qty = f"{quantidade_livre:.2f}"
        
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': qty
        }
        
        resultado = self.fazer_requisicao_super_resistente('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro venda {symbol}: {resultado.get('msg')}")
            return False
        
        logger.info(f"✅ VENDA EXECUTADA!")
        logger.info(f"   💵 RETORNO USDT: ~${valor_atual:.2f}")
        
        if trade_info:
            logger.info(f"   🎉 LUCRO CONSOLIDADO: ${lucro_estimado:.3f}")
            self.lucro_consolidado += lucro_estimado
            del self.trades_ativos[symbol]
        
        self.vendas_executadas += 1
        logger.info(f"   ✅ VALOR 100% EM USDT!")
        return True
    
    def analisar_oportunidade_resistente(self, symbol, rsi, portfolio, usdt_livre):
        """Análise super-resistente de oportunidades"""
        asset = symbol.replace('USDT', '')
        
        # PRIORIDADE 1: VENDA
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor = portfolio[asset]['valor_usdt']
            
            if rsi >= self.rsi_venda_rapida:
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA_RAPIDA | ${valor:.2f}")
                return self.executar_venda_resistente(symbol, rsi, portfolio)
            elif rsi >= self.rsi_venda_normal:
                logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_NORMAL | ${valor:.2f}")
                return self.executar_venda_resistente(symbol, rsi, portfolio)
            elif rsi >= self.rsi_venda_segura:
                logger.info(f"🔒 {symbol}: RSI {rsi:.1f} | VENDA_SEGURA | ${valor:.2f}")
                return self.executar_venda_resistente(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRA
        elif rsi <= self.rsi_compra:
            valor_necessario = self.calcular_valor_trade_corrigido(symbol, usdt_livre)
            
            if valor_necessario > 0:
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_OPORTUNIDADE | ${valor_necessario:.2f}")
                return self.executar_compra_resistente(symbol, rsi, usdt_livre)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, mas capital insuficiente para trade seguro")
        
        # AGUARDAR
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDANDO")
        
        return False
    
    def ciclo_super_resistente(self):
        """Ciclo principal super-resistente"""
        # Verificar conectividade
        if not self.verificar_conectividade():
            logger.error("❌ Sem conectividade - pulando ciclo")
            return 0, 0
        
        # Obter portfolio
        usdt_livre, portfolio, valor_total = self.get_portfolio_detalhado_resistente()
        
        if valor_total == 0:
            logger.error("❌ Erro ao obter portfolio - pulando ciclo")
            return 0, 0
        
        # Status financeiro
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO: +${lucro:.3f} (+{percentual:.3f}%)")
        
        logger.info(f"💼 Capital: ${valor_total:.2f} | 💵 USDT: ${usdt_livre:.2f}")
        
        # Posições
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                logger.info(f"   📊 {asset}: ${info['valor_usdt']:.2f}")
        
        # Status conectividade
        if self.erros_conexao > 0:
            logger.warning(f"⚠️ Erros de conexão: {self.erros_conexao}")
        
        # Estatísticas
        if self.vendas_executadas > 0 or self.compras_executadas > 0:
            logger.info(f"📈 Ops: {self.compras_executadas} compras | {self.vendas_executadas} vendas")
        
        # Analisar ativos
        operacoes = 0
        
        for symbol in self.ativos_resistentes.keys():
            try:
                klines = self.get_klines_resistente(symbol)
                if len(klines) < 4:
                    logger.warning(f"⚠️ {symbol}: Dados insuficientes")
                    continue
                
                rsi = self.calcular_rsi_otimizado(klines)
                
                if self.analisar_oportunidade_resistente(symbol, rsi, portfolio, usdt_livre):
                    operacoes += 1
                    time.sleep(2)
                
            except Exception as e:
                logger.error(f"❌ Erro {symbol}: {e}")
                continue
        
        logger.info(f"🔄 Ciclo: {operacoes} operações")
        return valor_total, operacoes
    
    def executar_sistema_super_resistente(self):
        """Sistema principal super-resistente"""
        logger.info("🛡️ === SISTEMA SUPER-RESISTENTE INICIADO ===")
        logger.info("💪 MÁXIMA RESISTÊNCIA: DNS + Timeout + Capital + Oportunidades")
        logger.info("🎯 ESTRATÉGIA: Aproveitar TODAS as oportunidades!")
        logger.info("=" * 80)
        
        # Verificar conectividade inicial
        if not self.verificar_conectividade():
            logger.error("❌ Sem conectividade inicial - aguardando...")
            time.sleep(10)
        
        # Capital inicial
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_detalhado_resistente()
        self.capital_inicial = valor_inicial
        
        if valor_inicial == 0:
            logger.error("❌ Não foi possível obter capital inicial")
            return
        
        # Meta
        meta = valor_inicial * 1.02  # +2%
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +2% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO RESISTENTE {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_super_resistente()
                
                if valor_atual == 0:
                    logger.warning("⚠️ Ciclo falhou - continuando...")
                    time.sleep(self.ciclo_tempo * 2)
                    continue
                
                # Verificar meta
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro: +${lucro_final:.3f} (+{percentual:.3f}%)")
                    break
                
                logger.info(f"⏰ Próximo em {self.ciclo_tempo}s...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro crítico: {e}")
        finally:
            # Resultado final
            try:
                _, _, valor_final = self.get_portfolio_detalhado_resistente()
                
                logger.info("🏆 === RESULTADO SUPER-RESISTENTE ===")
                logger.info(f"💼 Inicial: ${self.capital_inicial:.2f}")
                logger.info(f"💼 Final: ${valor_final:.2f}")
                
                if valor_final > self.capital_inicial:
                    lucro = valor_final - self.capital_inicial
                    perc = ((valor_final / self.capital_inicial) - 1) * 100
                    logger.info(f"🎉 LUCRO: +${lucro:.3f} (+{perc:.3f}%)")
                
                logger.info(f"📊 Operações: {self.compras_executadas + self.vendas_executadas}")
                logger.info(f"🔗 Erros conexão: {self.erros_conexao}")
            except:
                logger.error("❌ Erro ao gerar relatório final")

def main():
    """Executar sistema super-resistente"""
    logger.info("🔧 Iniciando Sistema Super-Resistente...")
    
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
            logger.error("❌ Chaves API não encontradas no .env")
            return
        
        # Executar sistema super-resistente
        sistema = SistemaSuperResistente(api_key, api_secret)
        sistema.executar_sistema_super_resistente()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()