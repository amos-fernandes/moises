"""
SISTEMA SCALPING ADAPTATIVO - APROVEITA CAPITAL EXISTENTE
Usa posições existentes + USDT disponível de forma inteligente
Foco em lucros pequenos e consistentes
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

# Configuracao de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_scalping_adaptativo.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingScalpingAdaptativo:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        
        # PARAMETROS SCALPING ADAPTATIVO
        self.lucro_target_pequeno = 0.8   # Target pequeno: 0.8%
        self.lucro_target_medio = 1.5     # Target médio: 1.5% 
        self.stop_loss = 0.5              # Stop loss: 0.5%
        self.confianca_minima = 65        # Confiança mínima baixa
        self.rsi_oversold = 50            # RSI menos restritivo
        self.rsi_overbought = 50          # RSI menos restritivo
        
        # Controle de trades e performance
        self.trades_executados = []
        self.lucro_total = 0
        self.trades_sucessos = 0
        self.trades_perdas = 0
        
        logger.info(f"🚀 Sistema Scalping Adaptativo - {conta_nome}")
        logger.info("=" * 60)
        logger.info("💡 ESTRATÉGIA ADAPTATIVA:")
        logger.info("   🎯 Aproveita posições BTC existentes")
        logger.info("   📊 Vende em alta para ter USDT")
        logger.info("   💰 Compra em baixa para acumular")
        logger.info(f"   🎯 Target pequeno: {self.lucro_target_pequeno}%")
        logger.info(f"   🎯 Target médio: {self.lucro_target_medio}%")
        logger.info(f"   🛡️ Stop loss: {self.stop_loss}%")
        logger.info("=" * 60)
    
    def _request(self, method, path, params, signed: bool):
        """Requisição da Binance"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            try:
                r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                if r.status_code == 200:
                    params['timestamp'] = r.json()['serverTime']
                else:
                    params['timestamp'] = int(datetime.now().timestamp() * 1000)
            except:
                params['timestamp'] = int(datetime.now().timestamp() * 1000)
                
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                r = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=10)
            
            if r.status_code != 200:
                logger.error(f"Erro HTTP {r.status_code}: {r.text}")
                return {'error': True, 'detail': f"{r.status_code}: {r.text}"}
            
            return r.json()
        except Exception as e:
            logger.error(f"Erro na requisição: {str(e)}")
            return {'error': True, 'detail': str(e)}
    
    def get_account_info(self):
        """Obter informações da conta"""
        return self._request('GET', '/api/v3/account', {}, signed=True)
    
    def get_portfolio_completo(self):
        """Obter portfolio completo com detalhes"""
        account = self.get_account_info()
        if account.get('error'):
            return 0, {}
        
        total_value = 0
        portfolio = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total_balance = free + locked
            
            if total_balance > 0:
                if asset == 'USDT':
                    value_usdt = total_balance
                    price = 1.0
                else:
                    try:
                        ticker_symbol = f"{asset}USDT"
                        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={ticker_symbol}", timeout=5)
                        if r.status_code == 200:
                            price = float(r.json()['price'])
                            value_usdt = total_balance * price
                        else:
                            price = 0
                            value_usdt = 0
                    except:
                        price = 0
                        value_usdt = 0
                
                if value_usdt > 0.01:
                    total_value += value_usdt
                    portfolio[asset] = {
                        'quantidade': total_balance,
                        'free': free,
                        'locked': locked,
                        'preco_atual': price,
                        'valor_usdt': value_usdt
                    }
        
        return total_value, portfolio
    
    def get_price(self, symbol):
        """Obter preço atual"""
        try:
            r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={symbol}", timeout=5)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            pass
        return None
    
    def get_candles(self, symbol: str, limit: int = 20):
        """Obter candles"""
        try:
            params = {
                'symbol': symbol,
                'interval': '1m',
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            if r.status_code != 200:
                return []
            
            candles = []
            for kline in r.json():
                candles.append(float(kline[4]))  # close price
            
            return candles
        except Exception as e:
            logger.error(f"Erro candles {symbol}: {e}")
            return []
    
    def calcular_rsi(self, prices, period=14):
        """Calcular RSI"""
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
    
    def analisar_oportunidade(self, symbol, portfolio_info):
        """Análise de oportunidade adaptativa"""
        candles = self.get_candles(symbol, 30)
        if len(candles) < 20:
            return None
        
        rsi = self.calcular_rsi(candles)
        preco_atual = candles[-1]
        
        # Tendência recente
        sma_5 = np.mean(candles[-5:])
        sma_10 = np.mean(candles[-10:])
        
        # Análise adaptativa
        decisao = {
            'symbol': symbol,
            'preco': preco_atual,
            'rsi': rsi,
            'tendencia': 'ALTA' if sma_5 > sma_10 else 'BAIXA',
            'acao': 'AGUARDAR',
            'confianca': 50,
            'motivo': 'neutro'
        }
        
        # Se tem a cripto no portfolio
        if symbol.replace('USDT', '') in portfolio_info:
            crypto = symbol.replace('USDT', '')
            quantidade = portfolio_info[crypto]['free']
            valor_atual = portfolio_info[crypto]['valor_usdt']
            
            # RSI alto = hora de vender (tomar lucro)
            if rsi >= 60:
                decisao.update({
                    'acao': 'VENDER',
                    'confianca': 60 + (rsi - 60) * 2,
                    'motivo': f'RSI_alto_{rsi:.1f}_tomar_lucro',
                    'quantidade_vender': quantidade * 0.5  # Vender metade
                })
            # RSI muito baixo = aguardar mais queda para comprar mais
            elif rsi <= 35:
                decisao.update({
                    'acao': 'AGUARDAR_MAIS_QUEDA',
                    'confianca': 70 + (35 - rsi) * 2,
                    'motivo': f'RSI_baixo_{rsi:.1f}_aguardar_mais_queda'
                })
        else:
            # Não tem a cripto - só compra se RSI muito baixo
            if rsi <= 40:
                decisao.update({
                    'acao': 'COMPRAR',
                    'confianca': 60 + (40 - rsi) * 2,
                    'motivo': f'RSI_baixo_{rsi:.1f}_entrada'
                })
        
        # Limitar confiança
        decisao['confianca'] = min(95, max(30, decisao['confianca']))
        
        return decisao
    
    def executar_venda_parcial(self, symbol, quantidade):
        """Vender parte da posição para ter USDT"""
        try:
            # Formatação correta
            quantidade_str = f"{quantidade:.8f}".rstrip('0').rstrip('.')
            
            logger.info(f"💸 VENDA PARCIAL: {symbol}")
            logger.info(f"   📊 Quantidade: {quantidade_str}")
            
            params = {
                'symbol': symbol,
                'side': 'SELL',
                'type': 'MARKET',
                'quantity': quantidade_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro venda: {resultado.get('detail')}")
                return None
            
            preco_venda = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            valor_recebido = quantidade * preco_venda
            
            logger.info(f"✅ VENDA EXECUTADA!")
            logger.info(f"   💰 Preço: ${preco_venda:.6f}")
            logger.info(f"   💵 Valor recebido: ~${valor_recebido:.2f}")
            
            # Registrar trade
            self.trades_executados.append({
                'tipo': 'VENDA_PARCIAL',
                'symbol': symbol,
                'quantidade': quantidade,
                'preco': preco_venda,
                'valor': valor_recebido,
                'timestamp': datetime.now()
            })
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro venda: {e}")
            return None
    
    def executar_compra_adaptativa(self, symbol, valor_usdt):
        """Compra adaptativa com o USDT disponível"""
        try:
            # Usar valor mínimo ou disponível
            valor_final = max(5.0, min(valor_usdt, 10.0))
            
            if valor_usdt < 5.0:
                logger.warning(f"💸 {symbol}: USDT ${valor_usdt:.2f} < mínimo Binance ($5)")
                return None
            
            valor_str = f"{valor_final:.2f}"
            
            logger.info(f"💰 COMPRA ADAPTATIVA: {symbol}")
            logger.info(f"   💵 Valor: ${valor_str}")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': valor_str
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro compra: {resultado.get('detail')}")
                return None
            
            quantidade = float(resultado.get('executedQty', 0))
            preco_compra = float(resultado.get('fills', [{}])[0].get('price', 0)) if resultado.get('fills') else 0
            
            logger.info(f"✅ COMPRA EXECUTADA!")
            logger.info(f"   📊 Quantidade: {quantidade:.8f}")
            logger.info(f"   💰 Preço: ${preco_compra:.6f}")
            
            # Registrar trade
            self.trades_executados.append({
                'tipo': 'COMPRA',
                'symbol': symbol,
                'quantidade': quantidade,
                'preco': preco_compra,
                'valor': float(valor_str),
                'timestamp': datetime.now()
            })
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro compra: {e}")
            return None
    
    def ciclo_adaptativo(self, ciclo):
        """Ciclo adaptativo focado em lucros pequenos"""
        logger.info(f"🔄 === CICLO ADAPTATIVO {ciclo} ===")
        
        # Obter portfolio completo
        valor_total, portfolio = self.get_portfolio_completo()
        
        logger.info(f"💼 Portfolio total: ${valor_total:.2f}")
        
        # Log do portfolio
        for asset, info in portfolio.items():
            if info['valor_usdt'] > 1.0:  # Só mostrar valores relevantes
                logger.info(f"   {asset}: {info['quantidade']:.8f} = ${info['valor_usdt']:.2f}")
        
        usdt_disponivel = portfolio.get('USDT', {}).get('free', 0)
        logger.info(f"💵 USDT livre: ${usdt_disponivel:.2f}")
        
        # Símbolos para análise (focar nos que temos posições)
        simbolos_analise = []
        
        # Adicionar símbolos que temos no portfolio
        for asset in portfolio.keys():
            if asset != 'USDT':
                simbolos_analise.append(f"{asset}USDT")
        
        # Adicionar alguns principais se não temos posições
        simbolos_principais = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT']
        for symbol in simbolos_principais:
            if symbol not in simbolos_analise:
                simbolos_analise.append(symbol)
        
        acoes_executadas = 0
        
        # Analisar cada símbolo
        for symbol in simbolos_analise[:5]:  # Máximo 5 símbolos
            analise = self.analisar_oportunidade(symbol, portfolio)
            if not analise:
                continue
            
            acao = analise['acao']
            confianca = analise['confianca']
            rsi = analise['rsi']
            
            # Emoji para clareza
            if acao == 'VENDER':
                emoji = "💸"
            elif acao == 'COMPRAR':
                emoji = "💰"
            else:
                emoji = "⏳"
            
            logger.info(f"{emoji} {symbol}: RSI {rsi:.1f} | {acao} | Conf: {confianca:.1f}%")
            logger.info(f"   💡 Motivo: {analise['motivo']}")
            
            # Executar ação se confiança suficiente
            if confianca >= self.confianca_minima:
                if acao == 'VENDER' and 'quantidade_vender' in analise:
                    quantidade = analise['quantidade_vender']
                    if quantidade > 0:
                        resultado = self.executar_venda_parcial(symbol, quantidade)
                        if resultado:
                            acoes_executadas += 1
                
                elif acao == 'COMPRAR' and usdt_disponivel >= 5.0:
                    # Usar parte do USDT disponível
                    valor_compra = min(usdt_disponivel * 0.6, 8.0)
                    resultado = self.executar_compra_adaptativa(symbol, valor_compra)
                    if resultado:
                        acoes_executadas += 1
                        usdt_disponivel -= valor_compra
        
        if acoes_executadas == 0:
            logger.info("📊 Nenhuma ação executada neste ciclo")
            if usdt_disponivel < 5.0:
                logger.info("💡 Aguardando mais USDT ou oportunidades de venda")
        else:
            logger.info(f"✅ {acoes_executadas} ação(ões) executada(s)")
        
        return True
    
    def relatorio_trades(self):
        """Relatório dos trades executados"""
        if len(self.trades_executados) == 0:
            return
        
        logger.info("\n" + "=" * 50)
        logger.info("📊 RELATÓRIO DE TRADES")
        logger.info("=" * 50)
        
        total_compras = sum(1 for t in self.trades_executados if t['tipo'] == 'COMPRA')
        total_vendas = sum(1 for t in self.trades_executados if t['tipo'] == 'VENDA_PARCIAL')
        
        logger.info(f"🛒 Compras executadas: {total_compras}")
        logger.info(f"💸 Vendas executadas: {total_vendas}")
        logger.info(f"📈 Total de trades: {len(self.trades_executados)}")
        
        # Últimos 3 trades
        if len(self.trades_executados) >= 3:
            logger.info("\n🔄 ÚLTIMOS 3 TRADES:")
            for trade in self.trades_executados[-3:]:
                logger.info(f"   {trade['tipo']}: {trade['symbol']} - ${trade['valor']:.2f}")
        
        logger.info("=" * 50 + "\n")
    
    def run_adaptativo(self, max_ciclos=30):
        """Executar sistema adaptativo"""
        logger.info("🚀 === SISTEMA SCALPING ADAPTATIVO ===")
        logger.info("💡 Estratégia: Aproveitar posições existentes + USDT")
        logger.info("🎯 Objetivo: Lucros pequenos e frequentes")
        logger.info("=" * 60)
        
        valor_inicial, _ = self.get_portfolio_completo()
        logger.info(f"💼 Portfolio inicial: ${valor_inicial:.2f}")
        
        for ciclo in range(1, max_ciclos + 1):
            try:
                self.ciclo_adaptativo(ciclo)
                
                # Relatório a cada 5 ciclos
                if ciclo % 5 == 0:
                    valor_atual, _ = self.get_portfolio_completo()
                    progresso = valor_atual - valor_inicial
                    
                    logger.info(f"\n📊 === PROGRESSO CICLO {ciclo} ===")
                    logger.info(f"💼 Portfolio: ${valor_inicial:.2f} → ${valor_atual:.2f}")
                    logger.info(f"📈 Variação: ${progresso:+.2f} ({(progresso/valor_inicial)*100:+.2f}%)")
                    
                    self.relatorio_trades()
                
                # Aguardar próximo ciclo (2 minutos para adaptativo)
                if ciclo < max_ciclos:
                    logger.info("⏰ Próximo ciclo em 2 minutos...")
                    time.sleep(120)
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema interrompido")
                break
            except Exception as e:
                logger.error(f"❌ Erro no ciclo {ciclo}: {e}")
                time.sleep(60)
        
        # Relatório final
        valor_final, _ = self.get_portfolio_completo()
        resultado_total = valor_final - valor_inicial
        
        logger.info("🏆 === RELATÓRIO FINAL ===")
        logger.info(f"💼 Portfolio inicial: ${valor_inicial:.2f}")
        logger.info(f"💼 Portfolio final: ${valor_final:.2f}")
        logger.info(f"📈 Resultado: ${resultado_total:+.2f}")
        
        self.relatorio_trades()

def main():
    """Função principal"""
    try:
        logger.info("🔧 Carregando configuração...")
        
        with open('config/contas.json', 'r') as f:
            contas = json.load(f)
        
        conta = contas['CONTA_3']
        
        trader = TradingScalpingAdaptativo(
            api_key=conta['api_key'],
            api_secret=conta['api_secret'],
            conta_nome="AMOS_ADAPTATIVO"
        )
        
        logger.info("✅ Sistema adaptativo configurado")
        trader.run_adaptativo(max_ciclos=30)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()