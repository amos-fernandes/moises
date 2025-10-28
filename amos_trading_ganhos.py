#!/usr/bin/env python3
"""
SISTEMA REATIVADO - APENAS CONTA AMOS
Trading real para gerar ganhos na conta Amos
Conta Paulo permanece pausada
"""

import json
import time
import logging
from datetime import datetime
from moises_estrategias_avancadas import TradingAvancado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amos_trading_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AmosTrading:
    def __init__(self):
        """Inicializar trading apenas para Amos"""
        logger.info("=== SISTEMA REATIVADO - APENAS AMOS ===")
        
        # Carregar apenas conta Amos
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        # Conta Amos (CONTA_3)
        dados_amos = config['CONTA_3']
        
        self.trader_amos = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="AMOS_GANHOS"
        )
        
        self.saldo_inicial = self.trader_amos.get_saldo_usdt()
        self.meta_ganho = self.saldo_inicial * 1.15  # Meta: +15% de ganho
        
        logger.info(f"[AMOS] Saldo inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"[AMOS] Meta de ganhos: ${self.meta_ganho:.2f} (+15%)")
        logger.info("[PAULO] Conta PAUSADA - não operará")
    
    def analisar_oportunidades_amos(self):
        """Buscar oportunidades conservadoras para Amos"""
        simbolos_conservadores = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']  # Criptos mais estáveis
        
        melhores_oportunidades = []
        
        for symbol in simbolos_conservadores:
            try:
                logger.info(f"[AMOS] Analisando {symbol}...")
                
                # Obter dados de mercado
                candles = self.trader_amos.get_candles_rapidos(symbol, '5m', 30)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                preco_atual = candles[-1]['close']
                volume = candles[-1]['volume']
                
                # Calcular RSI
                rsi = self.trader_amos.calcular_rsi_rapido(prices)
                
                # Calcular médias móveis
                ma_5 = sum(prices[-5:]) / 5
                ma_15 = sum(prices[-15:]) / 15
                
                # Critérios conservadores para Amos
                confidence = 50  # Base
                
                # RSI oversold (oportunidade de compra)
                if rsi < 30:
                    confidence += 25
                elif rsi < 35:
                    confidence += 15
                
                # Tendência de alta (MA5 > MA15)
                if ma_5 > ma_15:
                    confidence += 10
                
                # Volume adequado
                if volume > 100:
                    confidence += 5
                
                # Só considerar oportunidades com alta confiança para Amos
                if confidence >= 85:
                    oportunidade = {
                        'symbol': symbol,
                        'confidence': min(confidence, 98),
                        'preco_atual': preco_atual,
                        'rsi': rsi,
                        'ma_trend': 'ALTA' if ma_5 > ma_15 else 'BAIXA',
                        'entry_price': preco_atual,
                        'stop_loss': preco_atual * 0.97,  # 3% stop loss
                        'take_profit': preco_atual * 1.06,  # 6% take profit
                        'volume': volume
                    }
                    
                    melhores_oportunidades.append(oportunidade)
                    
                    logger.info(f"[AMOS] Oportunidade {symbol}: {confidence:.0f}% confiança")
                    logger.info(f"       RSI: {rsi:.1f} | Preço: ${preco_atual:.4f} | Trend: {oportunidade['ma_trend']}")
                
                time.sleep(1)  # Pausa entre análises
                
            except Exception as e:
                logger.error(f"[AMOS] Erro analisando {symbol}: {e}")
                continue
        
        # Ordenar por confiança
        melhores_oportunidades.sort(key=lambda x: x['confidence'], reverse=True)
        
        return melhores_oportunidades
    
    def executar_trade_conservador_amos(self, oportunidade):
        """Executar trade conservador para Amos"""
        try:
            saldo_atual = self.trader_amos.get_saldo_usdt()
            
            if saldo_atual < 5:
                logger.warning(f"[AMOS] Saldo insuficiente: ${saldo_atual:.2f}")
                return None
            
            # Calcular tamanho conservador (máximo 20% do saldo)
            percentual_conservador = 0.20  # 20% do saldo
            valor_maximo = saldo_atual * percentual_conservador
            
            # Baseado na confiança, ajustar o valor
            if oportunidade['confidence'] >= 95:
                valor_trade = min(valor_maximo, saldo_atual * 0.25)  # 25% se muito confiante
            elif oportunidade['confidence'] >= 90:
                valor_trade = valor_maximo  # 20% padrão
            else:
                valor_trade = min(valor_maximo, saldo_atual * 0.15)  # 15% se menos confiante
            
            # Garantir valor mínimo
            valor_trade = max(5.0, round(valor_trade, 2))
            
            logger.info(f"[AMOS] Executando trade conservador:")
            logger.info(f"       Símbolo: {oportunidade['symbol']}")
            logger.info(f"       Confiança: {oportunidade['confidence']:.1f}%")
            logger.info(f"       Valor: ${valor_trade:.2f} ({(valor_trade/saldo_atual)*100:.1f}% do saldo)")
            logger.info(f"       Preço entrada: ${oportunidade['entry_price']:.4f}")
            logger.info(f"       Stop Loss: ${oportunidade['stop_loss']:.4f}")
            logger.info(f"       Take Profit: ${oportunidade['take_profit']:.4f}")
            
            # Executar trade real
            params = {
                'symbol': oportunidade['symbol'],
                'side': 'BUY',
                'type': 'MARKET',
                'quoteOrderQty': f"{valor_trade:.2f}"
            }
            
            resultado = self.trader_amos._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"[AMOS] Erro no trade: {resultado}")
                
                # Tentar com quantity em vez de quoteOrderQty
                logger.info("[AMOS] Tentando com quantity...")
                quantidade = valor_trade / oportunidade['entry_price']
                quantidade = round(quantidade, 4)
                
                params_qty = {
                    'symbol': oportunidade['symbol'],
                    'side': 'BUY', 
                    'type': 'MARKET',
                    'quantity': f"{quantidade:.4f}"
                }
                
                resultado = self.trader_amos._request('POST', '/api/v3/order', params_qty, signed=True)
                
                if resultado.get('error'):
                    logger.error(f"[AMOS] Erro também com quantity: {resultado}")
                    return None
            
            # Trade executado com sucesso
            if not resultado.get('error'):
                logger.info(f"[AMOS] ✅ TRADE EXECUTADO COM SUCESSO!")
                logger.info(f"       Order ID: {resultado.get('orderId')}")
                
                fills = resultado.get('fills', [])
                if fills:
                    quantidade_total = sum(float(fill['qty']) for fill in fills)
                    valor_total = sum(float(fill['qty']) * float(fill['price']) for fill in fills)
                    preco_medio = valor_total / quantidade_total if quantidade_total > 0 else 0
                    
                    logger.info(f"       Quantidade: {quantidade_total:.6f}")
                    logger.info(f"       Preço médio: ${preco_medio:.4f}")
                    logger.info(f"       Valor investido: ${valor_total:.2f}")
                
                # Verificar novo saldo
                novo_saldo = self.trader_amos.get_saldo_usdt()
                logger.info(f"[AMOS] Novo saldo USDT: ${novo_saldo:.2f}")
                
                return {
                    'success': True,
                    'order_id': resultado.get('orderId'),
                    'symbol': oportunidade['symbol'],
                    'valor_investido': valor_total if fills else valor_trade,
                    'quantidade': quantidade_total if fills else 0,
                    'preco_medio': preco_medio if fills else oportunidade['entry_price']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"[AMOS] Erro na execução: {e}")
            return None
    
    def verificar_progresso_amos(self):
        """Verificar progresso dos ganhos de Amos"""
        saldo_atual = self.trader_amos.get_saldo_usdt()
        ganho_percentual = ((saldo_atual - self.saldo_inicial) / self.saldo_inicial) * 100
        
        logger.info(f"[AMOS] Progresso: ${self.saldo_inicial:.2f} -> ${saldo_atual:.2f}")
        logger.info(f"[AMOS] Ganho: {ganho_percentual:+.2f}% (Meta: +15%)")
        
        if saldo_atual >= self.meta_ganho:
            logger.info(f"[AMOS] 🎉 META ATINGIDA! Ganho de +15% alcançado!")
            return True
        
        return False
    
    def executar_ciclo_amos(self):
        """Executar um ciclo de trading para Amos"""
        logger.info("[AMOS] === INICIANDO CICLO DE GANHOS ===")
        
        # Verificar progresso atual
        meta_atingida = self.verificar_progresso_amos()
        if meta_atingida:
            return True
        
        # Buscar oportunidades
        oportunidades = self.analisar_oportunidades_amos()
        
        if not oportunidades:
            logger.info("[AMOS] Nenhuma oportunidade conservadora encontrada no momento")
            return False
        
        # Executar trade com a melhor oportunidade
        melhor_oportunidade = oportunidades[0]
        
        logger.info(f"[AMOS] Melhor oportunidade: {melhor_oportunidade['symbol']} ({melhor_oportunidade['confidence']:.1f}%)")
        
        resultado = self.executar_trade_conservador_amos(melhor_oportunidade)
        
        if resultado and resultado.get('success'):
            logger.info("[AMOS] Trade executado com sucesso!")
            return True
        else:
            logger.warning("[AMOS] Trade não executado")
            return False

def main():
    """Executar sistema de ganhos para Amos"""
    try:
        amos_trader = AmosTrading()
        
        print("\n" + "="*60)
        print("SISTEMA REATIVADO - TRADES REAIS APENAS PARA AMOS")
        print("="*60)
        print(f"Saldo inicial Amos: ${amos_trader.saldo_inicial:.2f}")
        print(f"Meta de ganhos: ${amos_trader.meta_ganho:.2f} (+15%)")
        print("Conta Paulo: PAUSADA")
        print("="*60)
        
        confirmacao = input("Confirmar início do trading real para Amos? (digite 'CONFIRMO'): ")
        
        if confirmacao != 'CONFIRMO':
            logger.info("Trading cancelado pelo usuário")
            return
        
        logger.info("[AMOS] 🚀 INICIANDO TRADING REAL PARA GANHOS!")
        
        ciclo = 1
        max_ciclos = 30
        
        while ciclo <= max_ciclos:
            logger.info(f"[CICLO {ciclo}/{max_ciclos}]")
            
            meta_atingida = amos_trader.executar_ciclo_amos()
            
            if meta_atingida:
                logger.info("🎉 Meta de ganhos atingida! Sistema concluído.")
                break
            
            if ciclo < max_ciclos:
                logger.info(f"Próximo ciclo em 5 minutos...")
                time.sleep(300)  # 5 minutos entre ciclos
            
            ciclo += 1
        
        # Relatório final
        saldo_final = amos_trader.trader_amos.get_saldo_usdt()
        ganho_total = saldo_final - amos_trader.saldo_inicial
        ganho_percent = (ganho_total / amos_trader.saldo_inicial) * 100
        
        logger.info("=== RELATÓRIO FINAL ===")
        logger.info(f"Saldo inicial: ${amos_trader.saldo_inicial:.2f}")
        logger.info(f"Saldo final: ${saldo_final:.2f}")
        logger.info(f"Ganho total: ${ganho_total:+.2f} ({ganho_percent:+.2f}%)")
        
    except KeyboardInterrupt:
        logger.info("Sistema interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        logger.error(f"Erro no sistema: {e}")

if __name__ == "__main__":
    main()