"""
SISTEMA DAY TRADING - VERSÃO MELHORADA COM SUGESTÕES
Implementando melhorias específicas sugeridas:
1. Reduzir limiar de confiança (75% → 65%)
2. Ampliar RSI oversold (< 35 → < 40) 
3. Estratégias mais agressivas
4. Melhor lógica de seleção de trades
5. Reduzir oportunidades perdidas

Baseado no sistema original que funciona sem erros
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

# Configuracao de logging simples
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_melhorado_sugestoes.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://api.binance.com"

class TradingMelhoradoSugestoes:
    def __init__(self, api_key: str, api_secret: str, conta_nome: str = "Conta Principal"):
        self.api_key = api_key
        self.api_secret = api_secret.encode('utf-8')
        self.conta_nome = conta_nome
        self.recv_window = 5000
        self.server_time_offset = 0
        
        # Parametros melhorados baseados nas sugestões
        self.confianca_minima = 65  # Reduzido de 75% para 65%
        self.rsi_oversold = 40      # Ampliado de 35 para 40
        self.rsi_overbought = 60    # Reduzido de 65 para 60
        self.valor_trade_min = 1.0  # Ajustado para situações de baixo capital
        self.valor_trade_binance_min = 5.0  # Mínimo oficial da Binance
        self.max_trades_por_ciclo = 2  # Múltiplos trades por ciclo
        
        # Sistema de monitoramento avancado
        self.trades_executados = []
        self.oportunidades_perdidas = []
        self.oportunidades_aproveitadas = []
        self.performance_historico = []
        self.melhor_rsi_encontrado = {'buy': 100, 'sell': 0}
        self.ciclos_sem_trade = 0
        self.total_lucro = 0
        
        logger.info(f"Trading Melhorado iniciado - {conta_nome}")
        logger.info("=== PARAMETROS MELHORADOS ===")
        logger.info(f"Confiança mínima: {self.confianca_minima}% (antes: 75%)")
        logger.info(f"RSI oversold: < {self.rsi_oversold} (antes: < 35)")
        logger.info(f"RSI overbought: > {self.rsi_overbought} (antes: > 65)")
        logger.info(f"Max trades por ciclo: {self.max_trades_por_ciclo}")
        logger.info("Estratégia mais agressiva ativada")
    
    def _request(self, method, path, params, signed: bool):
        """Requisicao original que funcionava sem erros de timestamp"""
        url = BASE_URL + path
        params = dict(params)
        headers = {}
        
        if signed:
            params['recvWindow'] = self.recv_window
            # Obter timestamp da Binance para garantir precisao - METODO ORIGINAL
            try:
                r = requests.get('https://api.binance.com/api/v3/time', timeout=3)
                if r.status_code == 200:
                    params['timestamp'] = r.json()['serverTime']
                else:
                    import datetime
                    params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
            except:
                import datetime
                params['timestamp'] = int(datetime.datetime.now().timestamp() * 1000)
                
            query_string = urlencode(params)
            signature = hmac.new(self.api_secret, query_string.encode('utf-8'), hashlib.sha256).hexdigest()
            params['signature'] = signature
            headers['X-MBX-APIKEY'] = self.api_key
        
        try:
            if method == 'GET':
                r = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                r = requests.post(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {'error': True, 'detail': str(e)}
    
    def get_saldo_usdt(self):
        """Obter saldo USDT disponivel"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            logger.error(f"Erro obtendo saldo: {account}")
            return 0
        
        for balance in account.get('balances', []):
            if balance['asset'] == 'USDT':
                return float(balance['free'])
        return 0
    
    def get_portfolio_total(self):
        """Obter valor total do portfolio (USDT + outras criptos)"""
        account = self._request('GET', '/api/v3/account', {}, signed=True)
        if account.get('error'):
            logger.error(f"Erro obtendo portfolio: {account}")
            return 0
        
        total_value = 0
        portfolio_details = {}
        
        for balance in account.get('balances', []):
            asset = balance['asset']
            free = float(balance['free'])
            locked = float(balance['locked'])
            total = free + locked
            
            if total > 0:
                if asset == 'USDT':
                    value_usdt = total
                else:
                    try:
                        ticker_symbol = f"{asset}USDT"
                        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol={ticker_symbol}", timeout=5)
                        if r.status_code == 200:
                            price = float(r.json()['price'])
                            value_usdt = total * price
                        else:
                            value_usdt = 0
                    except:
                        value_usdt = 0
                
                if value_usdt > 0.01:
                    total_value += value_usdt
                    portfolio_details[asset] = {
                        'quantidade': total,
                        'valor_usdt': value_usdt,
                        'free': free,
                        'locked': locked
                    }
        
        # Log do portfolio detalhado
        logger.info(f"Portfolio total: ${total_value:.2f}")
        for asset, details in portfolio_details.items():
            logger.info(f"  {asset}: {details['quantidade']:.6f} = ${details['valor_usdt']:.2f}")
        
        return total_value
    
    def get_candles_rapidos(self, symbol: str, interval: str, limit: int = 50):
        """Obter candles para analise rapida"""
        try:
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            
            r = requests.get(BASE_URL + '/api/v3/klines', params=params, timeout=5)
            r.raise_for_status()
            
            candles = []
            for kline in r.json():
                candles.append({
                    'timestamp': int(kline[0]),
                    'open': float(kline[1]),
                    'high': float(kline[2]),
                    'low': float(kline[3]),
                    'close': float(kline[4]),
                    'volume': float(kline[5])
                })
            
            return candles
            
        except Exception as e:
            logger.error(f"Erro ao obter candles {symbol}: {e}")
            return []
    
    def calcular_rsi_rapido(self, prices, period=14):
        """RSI otimizado para trading rapido"""
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
    
    def calcular_score_oportunidade(self, analise):
        """Novo sistema de pontuacao para priorizar oportunidades"""
        score = 0
        rsi = analise['rsi']
        confianca = analise['confianca']
        
        # Score base por RSI extremo (mais agressivo)
        if analise['sinal'] == 'COMPRA':
            if rsi <= 25:
                score += 100  # RSI muito extremo
            elif rsi <= 30:
                score += 80   # RSI extremo
            elif rsi <= 35:
                score += 60   # RSI bom
            elif rsi <= 40:
                score += 40   # RSI aceitável
            else:
                score += 20   # RSI neutro
        
        # Bonus por confiança
        score += confianca * 0.8
        
        # Bonus por volume (se disponível)
        if 'volume_score' in analise:
            score += analise['volume_score']
        
        return score
    
    def analisar_simbolo(self, symbol):
        """Analise mais agressiva de um simbolo"""
        candles = self.get_candles_rapidos(symbol, '5m', 30)
        if len(candles) < 20:
            return None
        
        closes = [c['close'] for c in candles]
        volumes = [c['volume'] for c in candles]
        preco_atual = closes[-1]
        rsi = self.calcular_rsi_rapido(closes)
        
        # Medias moveis
        sma_10 = np.mean(closes[-10:])
        sma_20 = np.mean(closes[-20:])
        
        # Volume médio (para detectar movimento)
        volume_medio = np.mean(volumes[-10:])
        volume_atual = volumes[-1]
        volume_score = min(20, (volume_atual / volume_medio) * 10) if volume_medio > 0 else 0
        
        # Logica MAIS AGRESSIVA baseada nas sugestões
        sinal = None
        confianca = 0
        
        if rsi < self.rsi_oversold:  # < 40 (ampliado de 35)
            sinal = 'COMPRA'
            # Formula melhorada de confiança
            base_conf = 60 + (self.rsi_oversold - rsi) * 2
            
            # Bonus por tendência de baixa (preço abaixo das médias)
            if preco_atual < sma_10:
                base_conf += 10
            if preco_atual < sma_20:
                base_conf += 5
            
            # Bonus por volume elevado
            if volume_atual > volume_medio * 1.2:
                base_conf += 10
            
            confianca = base_conf
            
        elif rsi > self.rsi_overbought:  # > 60 (reduzido de 65)
            sinal = 'VENDA'
            base_conf = 60 + (rsi - self.rsi_overbought) * 2
            
            if preco_atual > sma_10:
                base_conf += 10
            if preco_atual > sma_20:
                base_conf += 5
                
            if volume_atual > volume_medio * 1.2:
                base_conf += 10
            
            confianca = base_conf
        else:
            sinal = 'NEUTRO'
            confianca = 45 + (abs(50 - rsi) * 0.2)  # Ligeiramente menor confiança para neutro
        
        confianca = min(95, max(30, confianca))  # Entre 30% e 95%
        
        # Registrar RSI extremos para monitoramento
        if rsi < self.melhor_rsi_encontrado['buy'] and sinal == 'COMPRA':
            self.melhor_rsi_encontrado['buy'] = rsi
            logger.info(f"🚀 NOVO RSI MÍNIMO: {rsi:.1f} em {symbol} (Conf: {confianca:.1f}%)")
        
        if rsi > self.melhor_rsi_encontrado['sell'] and sinal == 'VENDA':
            self.melhor_rsi_encontrado['sell'] = rsi
            logger.info(f"📈 NOVO RSI MÁXIMO: {rsi:.1f} em {symbol} (Conf: {confianca:.1f}%)")
        
        resultado = {
            'symbol': symbol,
            'preco': preco_atual,
            'rsi': rsi,
            'sma_10': sma_10,
            'sma_20': sma_20,
            'volume_score': volume_score,
            'sinal': sinal,
            'confianca': confianca
        }
        
        # Calcular score para ranking
        resultado['score'] = self.calcular_score_oportunidade(resultado)
        
        return resultado
    
    def executar_compra(self, symbol, valor_usdt):
        """Executar compra usando o metodo original"""
        try:
            logger.info(f"💰 EXECUTANDO COMPRA: {symbol} - ${valor_usdt:.2f}")
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_usdt:.2f}"
            }
            
            resultado = self._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"❌ Erro na compra: {resultado}")
                return None
            
            logger.info(f"✅ COMPRA EXECUTADA: Order ID {resultado.get('orderId')}")
            logger.info(f"📊 Quantidade: {resultado.get('executedQty')}")
            
            # Registrar trade para monitoramento
            trade_info = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'order_id': resultado.get('orderId'),
                'valor_usdt': valor_usdt,
                'quantidade': resultado.get('executedQty'),
                'tipo': 'COMPRA'
            }
            self.trades_executados.append(trade_info)
            
            return resultado
            
        except Exception as e:
            logger.error(f"❌ Erro executando compra: {e}")
            return None
    
    def calcular_valor_trade_inteligente(self, saldo_usdt, confianca, rsi):
        """Calcular valor do trade baseado na confiança e RSI - VERSÃO ADAPTATIVA"""
        
        # Estratégia adaptativa para baixo capital
        if saldo_usdt < 5.0:
            # Para capital muito baixo, usar todo disponível se for uma ótima oportunidade
            if confianca >= 85 and rsi <= 30:
                return max(1.0, saldo_usdt * 0.9)  # 90% do disponível para oportunidades excepcionais
            elif confianca >= 75:
                return max(1.0, saldo_usdt * 0.7)  # 70% para boas oportunidades
            else:
                return max(1.0, saldo_usdt * 0.5)  # 50% para oportunidades normais
        
        # Valor base para capital maior
        if saldo_usdt < 10:
            valor_base = min(saldo_usdt * 0.4, 5.0)
        elif saldo_usdt < 20:
            valor_base = min(saldo_usdt * 0.3, 8.0)
        else:
            valor_base = min(saldo_usdt * 0.25, 10.0)
        
        # Multiplicador por confiança elevada
        if confianca >= 90:
            valor_base *= 1.5
        elif confianca >= 80:
            valor_base *= 1.3
        elif confianca >= 70:
            valor_base *= 1.1
        
        # Multiplicador por RSI extremo
        if rsi <= 25:
            valor_base *= 1.4  # RSI muito extremo
        elif rsi <= 30:
            valor_base *= 1.2  # RSI extremo
        
        # Garantir limites adaptativos
        valor_final = max(self.valor_trade_min, min(valor_base, saldo_usdt * 0.8))
        
        return valor_final
    
    def ciclo_trading(self, ciclo):
        """Um ciclo completo de trading MELHORADO"""
        logger.info(f"🔄 === CICLO {ciclo} === (VERSÃO MELHORADA)")
        
        # Verificar portfolio total
        portfolio_total = self.get_portfolio_total()
        saldo_usdt = self.get_saldo_usdt()
        
        logger.info(f"💼 Portfolio total: ${portfolio_total:.2f}")
        logger.info(f"💵 USDT disponível: ${saldo_usdt:.2f}")
        
        if saldo_usdt < self.valor_trade_min:
            logger.warning(f"⚠️ USDT muito baixo (${saldo_usdt:.2f}), mas continuando monitoramento...")
            # Ainda continuar para detectar oportunidades excepcionais
        
        # Analisar simbolos principais
        simbolos = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']
        
        oportunidades = []
        
        for symbol in simbolos:
            analise = self.analisar_simbolo(symbol)
            
            if analise:
                # Log melhorado com emojis para clareza
                emoji_sinal = "🟢" if analise['sinal'] == 'COMPRA' else "🔴" if analise['sinal'] == 'VENDA' else "⚪"
                logger.info(f"{emoji_sinal} {symbol}: RSI {analise['rsi']:.1f} | {analise['sinal']} | Conf: {analise['confianca']:.1f}% | Score: {analise['score']:.0f}")
                
                # Coletar oportunidades com confiança reduzida (65% em vez de 75%)
                if analise['sinal'] == 'COMPRA' and analise['confianca'] >= self.confianca_minima:
                    oportunidades.append(analise)
        
        # Ordenar por score (melhor sistema de priorização)
        oportunidades.sort(key=lambda x: x['score'], reverse=True)
        
        trades_executados_ciclo = 0
        
        # Executar até 2 trades por ciclo (mais agressivo)
        for i, oportunidade in enumerate(oportunidades):
            if trades_executados_ciclo >= self.max_trades_por_ciclo:
                # Registrar oportunidades restantes como perdidas
                for op_perdida in oportunidades[i:]:
                    self.oportunidades_perdidas.append({
                        'ciclo': ciclo,
                        'symbol': op_perdida['symbol'],
                        'rsi': op_perdida['rsi'],
                        'confianca': op_perdida['confianca'],
                        'score': op_perdida['score'],
                        'motivo': 'limite_trades_por_ciclo'
                    })
                break
            
            symbol = oportunidade['symbol']
            confianca = oportunidade['confianca']
            rsi = oportunidade['rsi']
            
            # Calcular valor inteligente do trade
            valor_trade = self.calcular_valor_trade_inteligente(saldo_usdt, confianca, rsi)
            
            # Verificar se vale a pena tentar o trade
            pode_executar = False
            
            if valor_trade <= saldo_usdt:
                # Se o valor calculado está dentro do disponível
                if valor_trade >= self.valor_trade_binance_min:
                    # Trade normal da Binance
                    pode_executar = True
                elif valor_trade >= 1.0 and confianca >= 80 and rsi <= 30:
                    # Trade de emergência para oportunidades excepcionais
                    logger.warning(f"⚡ TRADE ESPECIAL: Valor ${valor_trade:.2f} < mínimo Binance (${self.valor_trade_binance_min})")
                    logger.warning(f"   Mas RSI muito baixo ({rsi:.1f}) e alta confiança ({confianca:.1f}%)")
                    pode_executar = True
            
            if pode_executar:
                logger.info(f"🎯 MELHOR OPORTUNIDADE #{i+1}: {symbol}")
                logger.info(f"   RSI: {rsi:.1f} | Confiança: {confianca:.1f}% | Score: {oportunidade['score']:.0f}")
                logger.info(f"   Valor calculado: ${valor_trade:.2f}")
                
                resultado = self.executar_compra(symbol, valor_trade)
                if resultado:
                    saldo_usdt -= valor_trade  # Atualizar saldo para próximo trade
                    trades_executados_ciclo += 1
                    self.oportunidades_aproveitadas.append(oportunidade)
                    self.ciclos_sem_trade = 0
                else:
                    # Se falhou, registrar como perdida
                    self.oportunidades_perdidas.append({
                        'ciclo': ciclo,
                        'symbol': symbol,
                        'rsi': rsi,
                        'confianca': confianca,
                        'score': oportunidade['score'],
                        'motivo': 'erro_execucao'
                    })
            else:
                # Registrar como perdida por capital insuficiente
                motivo_detalhado = f'capital_insuf_${valor_trade:.2f}_disp_${saldo_usdt:.2f}'
                if valor_trade < self.valor_trade_binance_min:
                    motivo_detalhado += f'_abaixo_min_binance'
                    
                self.oportunidades_perdidas.append({
                    'ciclo': ciclo,
                    'symbol': symbol,
                    'rsi': rsi,
                    'confianca': confianca,
                    'score': oportunidade['score'],
                    'motivo': motivo_detalhado
                })
        
        if trades_executados_ciclo == 0:
            if len(oportunidades) == 0:
                logger.info("📊 Nenhuma oportunidade encontrada com os critérios atuais")
            else:
                logger.info(f"⏳ {len(oportunidades)} oportunidades encontradas, mas não executadas")
            self.ciclos_sem_trade += 1
        else:
            logger.info(f"✅ {trades_executados_ciclo} trade(s) executado(s) neste ciclo")
        
        # Alert melhorado para ciclos sem trade
        if self.ciclos_sem_trade >= 3:
            logger.warning(f"🚨 ATENÇÃO: {self.ciclos_sem_trade} ciclos consecutivos sem trades!")
            if self.ciclos_sem_trade >= 5:
                logger.warning("🔧 Sugestão: Sistema pode estar muito conservador")
                logger.warning(f"   - Confiança atual: {self.confianca_minima}% (considerar reduzir para 60%)")
                logger.warning(f"   - RSI oversold: < {self.rsi_oversold} (considerar aumentar para 45)")
        
        return True
    
    def run(self, max_ciclos=50):
        """Executar sistema de trading melhorado"""
        logger.info("🚀 === SISTEMA DAY TRADING - VERSÃO MELHORADA ===")
        logger.info("📈 Implementando sugestões de melhoria:")
        logger.info(f"   ✓ Confiança mínima reduzida: {self.confianca_minima}%")
        logger.info(f"   ✓ RSI oversold ampliado: < {self.rsi_oversold}")
        logger.info(f"   ✓ Estratégia mais agressiva ativada")
        logger.info(f"   ✓ Múltiplos trades por ciclo: {self.max_trades_por_ciclo}")
        logger.info(f"   ✓ Sistema de pontuação melhorado")
        logger.info("=" * 60)
        
        portfolio_inicial = self.get_portfolio_total()
        saldo_usdt_inicial = self.get_saldo_usdt()
        
        logger.info(f"💼 Portfolio inicial: ${portfolio_inicial:.2f}")
        logger.info(f"💵 USDT inicial: ${saldo_usdt_inicial:.2f}")
        
        if portfolio_inicial < 1.0:
            logger.error("❌ Portfolio insuficiente para operar")
            return
        
        for ciclo in range(1, max_ciclos + 1):
            try:
                sucesso = self.ciclo_trading(ciclo)
                
                if not sucesso:
                    logger.info("🛑 Parando sistema")
                    break
                
                # Relatorio de progresso melhorado a cada 3 ciclos
                if ciclo % 3 == 0:
                    portfolio_atual = self.get_portfolio_total()
                    progresso = portfolio_atual - portfolio_inicial
                    taxa_sucesso = len(self.oportunidades_aproveitadas) / max(1, len(self.oportunidades_aproveitadas) + len(self.oportunidades_perdidas)) * 100
                    
                    logger.info(f"\n📊 === RELATÓRIO PROGRESSO CICLO {ciclo} ===")
                    logger.info(f"💼 Portfolio: ${portfolio_inicial:.2f} → ${portfolio_atual:.2f}")
                    logger.info(f"📈 Progresso: ${progresso:+.2f} ({(progresso/portfolio_inicial)*100:+.2f}%)")
                    logger.info(f"✅ Trades executados: {len(self.trades_executados)}")
                    logger.info(f"📊 Taxa de sucesso: {taxa_sucesso:.1f}%")
                    logger.info(f"⏳ Ciclos sem trade: {self.ciclos_sem_trade}")
                    logger.info(f"❌ Oportunidades perdidas: {len(self.oportunidades_perdidas)}")
                    logger.info(f"🎯 Aproveitadas: {len(self.oportunidades_aproveitadas)}")
                    
                    if len(self.oportunidades_perdidas) > 0:
                        motivos = {}
                        for op in self.oportunidades_perdidas:
                            motivo = op['motivo']
                            motivos[motivo] = motivos.get(motivo, 0) + 1
                        logger.info("🔍 Principais motivos de perdas:")
                        for motivo, count in motivos.items():
                            logger.info(f"   • {motivo}: {count}x")
                    
                    logger.info("=" * 50 + "\n")
                
                if ciclo < max_ciclos:
                    logger.info("⏰ Aguardando próximo ciclo (3 min)...")
                    time.sleep(180)  # 3 minutos
                
            except KeyboardInterrupt:
                logger.info("⏹️ Sistema interrompido pelo usuário")
                break
            except Exception as e:
                logger.error(f"❌ Erro no ciclo {ciclo}: {e}")
                time.sleep(60)
        
        # Relatório final melhorado
        portfolio_final = self.get_portfolio_total()
        saldo_usdt_final = self.get_saldo_usdt()
        
        lucro_total = portfolio_final - portfolio_inicial
        lucro_usdt = saldo_usdt_final - saldo_usdt_inicial
        percentual_total = (lucro_total / portfolio_inicial) * 100 if portfolio_inicial > 0 else 0
        
        logger.info("=" * 60)
        logger.info("🏆 RELATÓRIO FINAL - VERSÃO MELHORADA")
        logger.info("=" * 60)
        
        logger.info("💰 PERFORMANCE FINANCEIRA:")
        logger.info(f"   Portfolio inicial: ${portfolio_inicial:.2f}")
        logger.info(f"   Portfolio final: ${portfolio_final:.2f}")
        logger.info(f"   Resultado: ${lucro_total:+.2f} ({percentual_total:+.2f}%)")
        logger.info(f"   USDT: ${saldo_usdt_inicial:.2f} → ${saldo_usdt_final:.2f} ({lucro_usdt:+.2f})")
        
        logger.info("\n📊 ESTATÍSTICAS DE TRADING:")
        logger.info(f"   ✅ Trades executados: {len(self.trades_executados)}")
        logger.info(f"   🎯 Oportunidades aproveitadas: {len(self.oportunidades_aproveitadas)}")
        logger.info(f"   ❌ Oportunidades perdidas: {len(self.oportunidades_perdidas)}")
        
        if len(self.oportunidades_aproveitadas) + len(self.oportunidades_perdidas) > 0:
            taxa_aproveitamento = len(self.oportunidades_aproveitadas) / (len(self.oportunidades_aproveitadas) + len(self.oportunidades_perdidas)) * 100
            logger.info(f"   📈 Taxa de aproveitamento: {taxa_aproveitamento:.1f}%")
        
        logger.info(f"   🔄 Ciclos executados: {ciclo}")
        logger.info(f"   ⏳ Ciclos sem trades: {self.ciclos_sem_trade}")
        logger.info(f"   🎯 RSI mínimo encontrado: {self.melhor_rsi_encontrado['buy']:.1f}")
        logger.info(f"   📈 RSI máximo encontrado: {self.melhor_rsi_encontrado['sell']:.1f}")
        
        if len(self.trades_executados) > 0:
            valor_medio_trade = np.mean([t['valor_usdt'] for t in self.trades_executados])
            logger.info(f"   💵 Valor médio por trade: ${valor_medio_trade:.2f}")
        
        logger.info("\n🔍 ANÁLISE DE MELHORIAS IMPLEMENTADAS:")
        logger.info(f"   ✓ Confiança mínima: 75% → {self.confianca_minima}% ({'✅ Melhorou' if len(self.trades_executados) > 0 else '⚠️ Ainda conservador'})")
        logger.info(f"   ✓ RSI oversold: < 35 → < {self.rsi_oversold} ({'✅ Mais oportunidades' if len(self.oportunidades_aproveitadas) > 0 else '⚠️ Poucos sinais'})")
        logger.info(f"   ✓ Múltiplos trades: até {self.max_trades_por_ciclo} por ciclo")
        logger.info(f"   ✓ Sistema de pontuação implementado")
        
        if len(self.oportunidades_perdidas) > 0:
            logger.info("\n🎯 TOP 5 OPORTUNIDADES PERDIDAS:")
            oportunidades_ordenadas = sorted(self.oportunidades_perdidas, key=lambda x: x.get('score', 0), reverse=True)
            for i, op in enumerate(oportunidades_ordenadas[:5], 1):
                logger.info(f"   {i}. {op['symbol']}: RSI {op['rsi']:.1f}, Conf {op['confianca']:.1f}%, Score {op.get('score', 0):.0f}")
                logger.info(f"      Motivo: {op['motivo']}")
        
        logger.info("\n💡 PRÓXIMAS MELHORIAS SUGERIDAS:")
        
        if len(self.trades_executados) == 0:
            logger.info("   🔧 Considerar reduzir confiança para 60%")
            logger.info("   🔧 Considerar aumentar RSI oversold para 45")
            
        if self.ciclos_sem_trade > 5:
            logger.info("   🔧 Sistema ainda muito conservador")
            logger.info("   🔧 Considerar incluir mais símbolos")
            
        if len(self.oportunidades_perdidas) > len(self.oportunidades_aproveitadas) * 2:
            logger.info("   🔧 Muitas oportunidades perdidas por falta de capital")
            logger.info("   🔧 Considerar reduzir valor mínimo de trade")
            logger.info("   🔧 Implementar gestão fracionária de posições")
        
        logger.info("=" * 60)

def main():
    """Funcao principal"""
    try:
        logger.info("🔧 Carregando configuração...")
        
        with open('config/contas.json', 'r') as f:
            contas = json.load(f)
        
        conta = contas['CONTA_3']  # Amos
        
        trader = TradingMelhoradoSugestoes(
            api_key=conta['api_key'],
            api_secret=conta['api_secret'],
            conta_nome="AMOS_MELHORADO"
        )
        
        logger.info("✅ Sistema configurado - versão melhorada")
        trader.run(max_ciclos=50)
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()