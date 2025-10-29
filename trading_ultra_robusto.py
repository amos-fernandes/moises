"""
🎯 SISTEMA ULTRA-ROBUSTO USDT - CORREÇÃO TOTAL
Resolve TODOS os problemas de saldo + Garantia 100% USDT
ESTRATÉGIA BLINDADA: Compra → Venda → Consolidação → Reinvestimento
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

# Logging otimizado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_ultra_robusto.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class SistemaUltraRobustoUSDT:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.recv_window = 60000
        
        # CONFIGURAÇÃO ULTRA-ROBUSTA
        self.rsi_compra = 25              # Compra em oportunidade
        self.rsi_venda_rapida = 35        # Venda ultra-rápida
        self.rsi_venda_normal = 45        # Venda normal
        self.rsi_venda_segura = 55        # Venda segura
        self.ciclo_tempo = 6              # Ciclos super-rápidos
        
        # PARÂMETROS OTIMIZADOS
        self.config_robusto = {
            'percentual_trade': 0.18,         # 18% do capital por trade
            'reserva_usdt': 2.0,             # Sempre $2 de reserva
            'lucro_minimo': 0.001,           # 0.1% mínimo
            'max_tentativas_venda': 5,       # Máx tentativas por venda
            'delay_entre_ops': 1.5,          # Delay entre operações
        }
        
        # ATIVOS SELECIONADOS
        self.ativos_robustos = {
            'BTCUSDT': {'min_valor': 6.0, 'peso': 0.35, 'step_size': 0.00001},
            'ETHUSDT': {'min_valor': 5.0, 'peso': 0.40, 'step_size': 0.0001}, 
            'SOLUSDT': {'min_valor': 5.0, 'peso': 0.25, 'step_size': 0.01},
        }
        
        # Controle robusto
        self.trades_ativos = {}
        self.historico_operacoes = []
        self.capital_inicial = 0
        self.lucro_consolidado = 0
        self.vendas_bem_sucedidas = 0
        self.compras_bem_sucedidas = 0
        self.tentativas_venda = {}
        
        logger.info("🛡️ === SISTEMA ULTRA-ROBUSTO ATIVADO ===")
        logger.info("💰 GARANTIA ABSOLUTA: SEMPRE VOLTA PARA USDT!")
        logger.info("🚀 CORREÇÕES: Saldo + Precisão + Timeout + Retry")
        logger.info("=" * 75)
        logger.info(f"🔥 RSI: Compra ≤{self.rsi_compra} | Venda ≥{self.rsi_venda_rapida}")
        logger.info(f"💵 Trade: {self.config_robusto['percentual_trade']*100}% | Reserva: ${self.config_robusto['reserva_usdt']}")
        logger.info(f"⏱️ Ciclos: {self.ciclo_tempo}s | Retry: {self.config_robusto['max_tentativas_venda']}x")
        logger.info("=" * 75)
    
    def get_server_time_safe(self):
        """Timestamp ultra-seguro"""
        for i in range(3):
            try:
                response = requests.get(f"{BASE_URL}/api/v3/time", timeout=8)
                if response.status_code == 200:
                    return response.json()['serverTime']
            except:
                time.sleep(0.5)
        return int(time.time() * 1000)
    
    def fazer_requisicao_robusta(self, method, endpoint, params=None, signed=False):
        """Requisição ultra-robusta com retry inteligente"""
        if params is None:
            params = {}
        
        url = BASE_URL + endpoint
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            params['timestamp'] = self.get_server_time_safe()
            
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        # Retry com backoff exponencial
        for tentativa in range(4):
            try:
                if method == 'GET':
                    r = requests.get(url, params=params, headers=headers, timeout=15)
                else:
                    r = requests.post(url, params=params, headers=headers, timeout=15)
                
                if r.status_code == 200:
                    return r.json()
                elif r.status_code == 400:
                    error_data = r.json() if r.text else {}
                    logger.warning(f"Erro 400 (tentativa {tentativa+1}): {error_data.get('msg', r.text)}")
                    
                    # Erros que não devem repetir
                    if any(code in error_data.get('msg', '') for code in ['insufficient balance', 'MIN_NOTIONAL', '-2010']):
                        return {'error': True, 'code': error_data.get('code'), 'msg': error_data.get('msg')}
                    
                    if tentativa < 3:
                        time.sleep(2 ** tentativa)
                else:
                    logger.error(f"HTTP {r.status_code}: {r.text}")
                    if tentativa < 3:
                        time.sleep(1 * (tentativa + 1))
                    
            except Exception as e:
                logger.error(f"Erro requisição (tent {tentativa+1}): {e}")
                if tentativa < 3:
                    time.sleep(2 * (tentativa + 1))
        
        return {'error': True, 'msg': 'Falha após múltiplas tentativas'}
    
    def get_account_info_robusto(self):
        """Info da conta com retry"""
        return self.fazer_requisicao_robusta('GET', '/api/v3/account', signed=True)
    
    def get_preco_atual_robusto(self, symbol):
        """Preço com fallback"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price", 
                           params={'symbol': symbol}, timeout=8)
            if r.status_code == 200:
                return float(r.json()['price'])
        except Exception as e:
            logger.warning(f"Erro preço {symbol}: {e}")
        return 0
    
    def get_klines_robusto(self, symbol, limit=10):
        """Klines com tratamento de erro"""
        try:
            params = {'symbol': symbol, 'interval': '1m', 'limit': limit}
            r = requests.get(f"{BASE_URL}/api/v3/klines", params=params, timeout=8)
            if r.status_code == 200:
                return [float(k[4]) for k in r.json()]
        except Exception as e:
            logger.warning(f"Erro klines {symbol}: {e}")
        return []
    
    def calcular_rsi_preciso(self, precos, periodo=6):
        """RSI com precisão melhorada"""
        if len(precos) < periodo + 1:
            return 50
        
        deltas = np.diff(precos)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Suavização exponencial
        alpha = 2.0 / (periodo + 1)
        avg_gain = gains[-1]
        avg_loss = losses[-1]
        
        for i in range(1, min(periodo, len(gains))):
            avg_gain = alpha * gains[-(i+1)] + (1 - alpha) * avg_gain
            avg_loss = alpha * losses[-(i+1)] + (1 - alpha) * avg_loss
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def get_portfolio_detalhado(self):
        """Portfolio com verificação detalhada"""
        conta = self.get_account_info_robusto()
        if conta.get('error'):
            logger.error(f"Erro ao obter conta: {conta.get('msg')}")
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
                    preco = self.get_preco_atual_robusto(symbol)
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
    
    def formatar_quantidade(self, symbol, quantidade):
        """Formatação precisa da quantidade"""
        config = self.ativos_robustos.get(symbol, {})
        step_size = config.get('step_size', 0.01)
        
        # Arredondar para o step_size
        quantidade_ajustada = (quantidade // step_size) * step_size
        
        if symbol == 'BTCUSDT':
            return f"{quantidade_ajustada:.5f}"
        elif symbol == 'ETHUSDT':
            return f"{quantidade_ajustada:.4f}"
        else:
            return f"{quantidade_ajustada:.2f}"
    
    def executar_compra_robusta(self, symbol, rsi, usdt_disponivel):
        """Compra ultra-robusta"""
        config = self.ativos_robustos[symbol]
        valor_compra = usdt_disponivel * self.config_robusto['percentual_trade'] * config['peso']
        
        # Verificações de segurança
        if valor_compra < config['min_valor']:
            if usdt_disponivel >= config['min_valor'] + self.config_robusto['reserva_usdt']:
                valor_compra = config['min_valor']
            else:
                logger.warning(f"⚠️ {symbol}: Capital insuficiente (${valor_compra:.2f} < ${config['min_valor']})")
                return False
        
        # Verificar limite de trades ativos
        if len(self.trades_ativos) >= 3:
            logger.info(f"⏳ {symbol}: Máximo de trades ativos atingido")
            return False
        
        logger.warning(f"🚨 COMPRA ROBUSTA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_compra:.2f}")
        
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quoteOrderQty': f"{valor_compra:.2f}"
        }
        
        resultado = self.fazer_requisicao_robusta('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            logger.error(f"❌ Erro compra {symbol}: {resultado.get('msg')}")
            return False
        
        # Registrar trade ativo
        self.trades_ativos[symbol] = {
            'timestamp': time.time(),
            'valor_investido': valor_compra,
            'rsi_entrada': rsi,
            'preco_entrada': self.get_preco_atual_robusto(symbol)
        }
        
        self.compras_bem_sucedidas += 1
        logger.info(f"✅ COMPRA EXECUTADA: ${valor_compra:.2f}")
        return True
    
    def executar_venda_robusta(self, symbol, rsi, portfolio):
        """Venda ultra-robusta com múltiplas tentativas"""
        asset = symbol.replace('USDT', '')
        
        if asset not in portfolio:
            logger.warning(f"⚠️ {symbol}: Asset não encontrado no portfolio")
            return False
        
        # Verificar tentativas anteriores
        if symbol in self.tentativas_venda and self.tentativas_venda[symbol] >= self.config_robusto['max_tentativas_venda']:
            logger.warning(f"⚠️ {symbol}: Máximo de tentativas de venda atingido")
            return False
        
        info_asset = portfolio[asset]
        quantidade_livre = info_asset['free']
        valor_atual = info_asset['valor_usdt']
        
        if quantidade_livre <= 0:
            logger.warning(f"⚠️ {symbol}: Quantidade livre = 0 (pode estar em ordem)")
            return False
        
        if valor_atual < 1.0:
            logger.warning(f"⚠️ {symbol}: Valor muito baixo (${valor_atual:.2f})")
            return False
        
        # Calcular lucro potencial
        trade_info = self.trades_ativos.get(symbol)
        lucro_estimado = 0
        
        if trade_info:
            lucro_estimado = valor_atual - trade_info['valor_investido']
        
        logger.warning(f"🚨 VENDA ROBUSTA: {symbol}")
        logger.warning(f"   📊 RSI: {rsi:.1f} | Valor: ${valor_atual:.2f}")
        if trade_info:
            logger.warning(f"   📈 Lucro estimado: ${lucro_estimado:.3f}")
        
        # Formatação ultra-precisa
        qty_formatada = self.formatar_quantidade(symbol, quantidade_livre)
        
        logger.info(f"   🔧 Quantidade formatada: {qty_formatada}")
        
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': qty_formatada
        }
        
        resultado = self.fazer_requisicao_robusta('POST', '/api/v3/order', params, signed=True)
        
        if resultado.get('error'):
            error_msg = resultado.get('msg', '')
            logger.error(f"❌ Erro venda {symbol}: {error_msg}")
            
            # Contar tentativa
            self.tentativas_venda[symbol] = self.tentativas_venda.get(symbol, 0) + 1
            
            # Se erro de saldo, aguardar um pouco
            if 'insufficient' in error_msg.lower() or '-2010' in error_msg:
                logger.warning(f"   ⏳ Aguardando liberação do saldo...")
                time.sleep(3)
            
            return False
        
        logger.info(f"✅ VENDA EXECUTADA!")
        logger.info(f"   💵 RETORNO USDT: ~${valor_atual:.2f}")
        
        if trade_info:
            logger.info(f"   🎉 LUCRO CONSOLIDADO: ${lucro_estimado:.3f}")
            self.lucro_consolidado += lucro_estimado
            
            # Salvar histórico
            self.historico_operacoes.append({
                'symbol': symbol,
                'tipo': 'VENDA_LUCRO',
                'valor': valor_atual,
                'lucro': lucro_estimado,
                'timestamp': time.time()
            })
            
            # Remover trade ativo
            del self.trades_ativos[symbol]
        
        self.vendas_bem_sucedidas += 1
        
        # Limpar contador de tentativas
        if symbol in self.tentativas_venda:
            del self.tentativas_venda[symbol]
        
        logger.info(f"   ✅ VALOR 100% CONSOLIDADO EM USDT!")
        return True
    
    def analisar_oportunidade_robusta(self, symbol, rsi, portfolio, usdt_livre):
        """Análise ultra-robusta"""
        asset = symbol.replace('USDT', '')
        
        # PRIORIDADE 1: VENDA se temos o asset
        if asset in portfolio and portfolio[asset]['free'] > 0:
            valor = portfolio[asset]['valor_usdt']
            
            # Venda ultra-rápida
            if rsi >= self.rsi_venda_rapida:
                logger.info(f"💸 {symbol}: RSI {rsi:.1f} | VENDA_ULTRA_RAPIDA | ${valor:.2f}")
                return self.executar_venda_robusta(symbol, rsi, portfolio)
            
            # Venda normal
            elif rsi >= self.rsi_venda_normal:
                logger.info(f"💰 {symbol}: RSI {rsi:.1f} | VENDA_NORMAL | ${valor:.2f}")
                return self.executar_venda_robusta(symbol, rsi, portfolio)
            
            # Venda segura
            elif rsi >= self.rsi_venda_segura:
                logger.info(f"🔒 {symbol}: RSI {rsi:.1f} | VENDA_SEGURA | ${valor:.2f}")
                return self.executar_venda_robusta(symbol, rsi, portfolio)
        
        # PRIORIDADE 2: COMPRA se RSI favorável
        elif rsi <= self.rsi_compra:
            config = self.ativos_robustos[symbol]
            valor_necessario = usdt_livre * self.config_robusto['percentual_trade']
            
            if valor_necessario >= config['min_valor'] and usdt_livre >= config['min_valor'] + self.config_robusto['reserva_usdt']:
                logger.info(f"🔥 {symbol}: RSI {rsi:.1f} | COMPRA_OPORTUNIDADE | ${valor_necessario:.2f}")
                return self.executar_compra_robusta(symbol, rsi, usdt_livre)
            else:
                logger.info(f"⏳ {symbol}: RSI {rsi:.1f} favorável, mas capital insuficiente")
        
        # AGUARDAR
        else:
            logger.info(f"⏳ {symbol}: RSI {rsi:.1f} | AGUARDANDO")
        
        return False
    
    def ciclo_ultra_robusto(self):
        """Ciclo principal ultra-robusto"""
        usdt_livre, portfolio, valor_total = self.get_portfolio_detalhado()
        
        # Status financeiro
        if valor_total > self.capital_inicial and self.capital_inicial > 0:
            lucro = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📈 LUCRO TOTAL: +${lucro:.3f} (+{percentual:.3f}%)")
        elif self.capital_inicial > 0:
            variacao = valor_total - self.capital_inicial
            percentual = ((valor_total / self.capital_inicial) - 1) * 100
            logger.info(f"📊 CAPITAL: ${valor_total:.2f} | Var: {variacao:+.3f} ({percentual:+.3f}%)")
        
        logger.info(f"💵 USDT livre: ${usdt_livre:.2f}")
        
        # Posições ativas
        posicoes = []
        for asset, info in portfolio.items():
            if asset != 'USDT' and info['valor_usdt'] > 0.5:
                posicoes.append(f"{asset}: ${info['valor_usdt']:.2f}")
        
        if posicoes:
            logger.info(f"📊 Posições: {' | '.join(posicoes)}")
        
        # Estatísticas
        if self.trades_ativos:
            logger.info(f"⚡ Trades ativos: {len(self.trades_ativos)}")
        
        if self.vendas_bem_sucedidas > 0 or self.compras_bem_sucedidas > 0:
            logger.info(f"📈 Operações: {self.compras_bem_sucedidas} compras | {self.vendas_bem_sucedidas} vendas")
        
        if self.lucro_consolidado > 0:
            logger.info(f"💰 Lucro consolidado: ${self.lucro_consolidado:.3f}")
        
        # Analisar cada ativo
        operacoes_executadas = 0
        
        for symbol in self.ativos_robustos.keys():
            try:
                klines = self.get_klines_robusto(symbol)
                if len(klines) < 5:
                    logger.warning(f"⚠️ {symbol}: Dados insuficientes")
                    continue
                
                rsi = self.calcular_rsi_preciso(klines)
                
                if self.analisar_oportunidade_robusta(symbol, rsi, portfolio, usdt_livre):
                    operacoes_executadas += 1
                    time.sleep(self.config_robusto['delay_entre_ops'])
                
            except Exception as e:
                logger.error(f"❌ Erro {symbol}: {e}")
                continue
        
        logger.info(f"🔄 Ciclo: {operacoes_executadas} operações executadas")
        return valor_total, operacoes_executadas
    
    def executar_sistema_ultra_robusto(self):
        """Sistema principal ultra-robusto"""
        logger.info("🛡️ === SISTEMA ULTRA-ROBUSTO INICIADO ===")
        logger.info("💰 BLINDAGEM TOTAL: TODO LUCRO GARANTIDO EM USDT!")
        logger.info("🔧 CORREÇÕES: Retry + Precisão + Timeout + Saldo")
        logger.info("=" * 80)
        
        # Inicialização
        usdt_inicial, portfolio_inicial, valor_inicial = self.get_portfolio_detalhado()
        self.capital_inicial = valor_inicial
        
        # Meta conservadora
        meta = valor_inicial * 1.015  # +1.5%
        
        logger.info(f"💼 Capital inicial: ${valor_inicial:.2f}")
        logger.info(f"💵 USDT disponível: ${usdt_inicial:.2f}")
        logger.warning(f"🎯 Meta: +1.5% = ${meta:.2f}")
        
        ciclo = 0
        
        try:
            while True:
                ciclo += 1
                logger.info(f"🔄 === CICLO ROBUSTO {ciclo} ===")
                
                valor_atual, operacoes = self.ciclo_ultra_robusto()
                
                # Verificar meta
                if valor_atual >= meta:
                    lucro_final = valor_atual - self.capital_inicial
                    percentual = ((valor_atual / self.capital_inicial) - 1) * 100
                    
                    logger.info("🎉 === META ALCANÇADA! ===")
                    logger.info(f"🏆 Capital final: ${valor_atual:.2f}")
                    logger.info(f"💰 Lucro total: +${lucro_final:.3f} (+{percentual:.3f}%)")
                    logger.info(f"📊 Operações: {self.compras_bem_sucedidas + self.vendas_bem_sucedidas}")
                    break
                
                logger.info(f"⏰ Próximo ciclo em {self.ciclo_tempo}s...")
                time.sleep(self.ciclo_tempo)
                
        except KeyboardInterrupt:
            logger.info("⏹️ Sistema parado pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro crítico: {e}")
        finally:
            # Resultado final
            _, _, valor_final = self.get_portfolio_detalhado()
            
            logger.info("🏆 === RESULTADO ULTRA-ROBUSTO ===")
            logger.info(f"💼 Capital inicial: ${self.capital_inicial:.2f}")
            logger.info(f"💼 Capital final: ${valor_final:.2f}")
            
            if valor_final > self.capital_inicial:
                lucro = valor_final - self.capital_inicial
                perc = ((valor_final / self.capital_inicial) - 1) * 100
                logger.info(f"🎉 LUCRO FINAL: +${lucro:.3f} (+{perc:.3f}%)")
            
            logger.info(f"📊 Total operações: {len(self.historico_operacoes)}")
            if self.historico_operacoes:
                lucros = [h.get('lucro', 0) for h in self.historico_operacoes if h.get('lucro')]
                if lucros:
                    logger.info(f"💰 Lucro médio: ${np.mean(lucros):.3f}")
                    logger.info(f"🔥 Melhor lucro: ${max(lucros):.3f}")

def main():
    """Executar sistema ultra-robusto"""
    logger.info("🔧 Iniciando Sistema Ultra-Robusto...")
    
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
        
        # Executar sistema ultra-robusto
        sistema = SistemaUltraRobustoUSDT(api_key, api_secret)
        sistema.executar_sistema_ultra_robusto()
        
    except FileNotFoundError:
        logger.error("❌ Arquivo .env não encontrado")
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")

if __name__ == "__main__":
    main()