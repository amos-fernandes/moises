#!/usr/bin/env python3
"""
AMOS TRADING ATIVO - Critérios Menos Restritivos
Trading real mais ativo para gerar ganhos na conta Amos
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
        logging.FileHandler(f'amos_ativo_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AmosTradingAtivo:
    def __init__(self):
        """Inicializar trading ativo para Amos"""
        logger.info("=== AMOS TRADING ATIVO - CRITÉRIOS AJUSTADOS ===")
        
        # Carregar conta Amos
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        dados_amos = config['CONTA_3']
        
        self.trader = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="AMOS_ATIVO"
        )
        
        self.saldo_inicial = self.trader.get_saldo_usdt()
        self.meta_ganho = self.saldo_inicial * 1.10  # Meta mais realista: +10%
        
        logger.info(f"[AMOS] Saldo inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"[AMOS] Meta ajustada: ${self.meta_ganho:.2f} (+10%)")
    
    def buscar_oportunidades_ativas(self):
        """Buscar oportunidades com critérios menos restritivos"""
        simbolos = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT', 'SOLUSDT']
        
        oportunidades = []
        
        for symbol in simbolos:
            try:
                logger.info(f"[AMOS] Analisando {symbol}...")
                
                candles = self.trader.get_candles_rapidos(symbol, '5m', 20)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                preco_atual = candles[-1]['close']
                rsi = self.trader.calcular_rsi_rapido(prices)
                
                # Critérios MENOS restritivos
                confidence = 60  # Base mais baixa
                razao = ""
                
                # RSI - critérios mais flexíveis
                if rsi < 40:  # Menos restritivo que 30
                    confidence += 20
                    razao += f"RSI {rsi:.1f} (favorável) "
                elif rsi > 60:  # Overbought - oportunidade de venda
                    confidence += 10
                    razao += f"RSI {rsi:.1f} (neutro) "
                
                # Volume mínimo
                volume = candles[-1]['volume']
                if volume > 50:  # Menos restritivo
                    confidence += 10
                    razao += f"Volume OK "
                
                # Volatilidade (diferença entre máximo e mínimo recente)
                max_price = max(prices[-5:])
                min_price = min(prices[-5:])
                volatilidade = (max_price - min_price) / min_price
                
                if volatilidade > 0.01:  # Mais de 1% de variação
                    confidence += 10
                    razao += f"Volatilidade {volatilidade*100:.1f}% "
                
                # Tendência das últimas 3 velas
                if prices[-1] > prices[-3]:
                    confidence += 5
                    razao += "Tendência alta "
                
                # REDUZIR limite de confiança para 75% (era 85%)
                if confidence >= 75:
                    oportunidade = {
                        'symbol': symbol,
                        'confidence': min(confidence, 95),
                        'preco_atual': preco_atual,
                        'rsi': rsi,
                        'razao': razao.strip(),
                        'volatilidade': volatilidade,
                        'entry_price': preco_atual,
                        'stop_loss': preco_atual * 0.975,  # 2.5% stop loss (menos restritivo)
                        'take_profit': preco_atual * 1.04,  # 4% take profit
                        'volume': volume
                    }
                    
                    oportunidades.append(oportunidade)
                    logger.info(f"[AMOS] Oportunidade {symbol}: {confidence:.0f}% - {razao}")
                
                time.sleep(0.5)  # Pausa menor
                
            except Exception as e:
                logger.error(f"[AMOS] Erro {symbol}: {e}")
                continue
        
        return sorted(oportunidades, key=lambda x: x['confidence'], reverse=True)
    
    def executar_trade_ativo(self, oportunidade):
        """Executar trade com critérios ativos"""
        try:
            saldo_atual = self.trader.get_saldo_usdt()
            
            if saldo_atual < 5:
                logger.warning(f"[AMOS] Saldo insuficiente: ${saldo_atual:.2f}")
                return None
            
            # Calcular valor do trade - mais agressivo
            if oportunidade['confidence'] >= 90:
                percentual = 0.25  # 25% do saldo
            elif oportunidade['confidence'] >= 80:
                percentual = 0.20  # 20% do saldo  
            else:
                percentual = 0.15  # 15% do saldo
            
            valor_trade = saldo_atual * percentual
            valor_trade = max(5.0, min(valor_trade, 8.0))  # Entre $5 e $8
            valor_trade = round(valor_trade, 2)
            
            logger.info(f"[AMOS] EXECUTANDO TRADE ATIVO:")
            logger.info(f"       {oportunidade['symbol']}: ${valor_trade:.2f}")
            logger.info(f"       Confiança: {oportunidade['confidence']:.1f}%")
            logger.info(f"       Razão: {oportunidade['razao']}")
            logger.info(f"       RSI: {oportunidade['rsi']:.1f}")
            logger.info(f"       Preço: ${oportunidade['preco_atual']:.6f}")
            
            # Tentar com quantity primeiro (método que tem mais chance de funcionar)
            quantidade = valor_trade / oportunidade['preco_atual']
            
            # Ajustar quantidade baseado nos filtros da Binance
            if oportunidade['symbol'] == 'ADAUSDT':
                quantidade = round(quantidade, 1)  # ADAUSDT usa 1 casa decimal
            elif oportunidade['symbol'] in ['BTCUSDT', 'ETHUSDT']:
                quantidade = round(quantidade, 5)  # BTC/ETH usam mais precisão
            else:
                quantidade = round(quantidade, 3)  # Padrão
            
            logger.info(f"       Quantidade calculada: {quantidade}")
            
            # EXECUTAR TRADE REAL
            params = {
                'symbol': oportunidade['symbol'],
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': f"{quantidade}"
            }
            
            logger.info(f"       Parâmetros: {params}")
            
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"[AMOS] Erro: {resultado}")
                return None
            
            # SUCCESS!
            logger.info(f"[AMOS] ✅ TRADE EXECUTADO!")
            logger.info(f"       Order ID: {resultado.get('orderId')}")
            
            fills = resultado.get('fills', [])
            if fills:
                qty_total = sum(float(f['qty']) for f in fills)
                valor_total = sum(float(f['qty']) * float(f['price']) for f in fills)
                preco_medio = valor_total / qty_total if qty_total > 0 else 0
                
                logger.info(f"       Executado: {qty_total} {oportunidade['symbol'].replace('USDT', '')}")
                logger.info(f"       Preço médio: ${preco_medio:.6f}")
                logger.info(f"       Valor total: ${valor_total:.2f}")
            
            # Verificar novo saldo
            novo_saldo = self.trader.get_saldo_usdt()
            diferenca = novo_saldo - saldo_atual
            
            logger.info(f"[AMOS] Saldo: ${saldo_atual:.2f} -> ${novo_saldo:.2f} ({diferenca:+.2f})")
            
            return {
                'success': True,
                'order_id': resultado.get('orderId'),
                'symbol': oportunidade['symbol'],
                'valor_investido': valor_total if fills else valor_trade
            }
            
        except Exception as e:
            logger.error(f"[AMOS] Erro na execução: {e}")
            return None
    
    def verificar_progresso(self):
        """Verificar progresso dos ganhos"""
        saldo_atual = self.trader.get_saldo_usdt()
        ganho = saldo_atual - self.saldo_inicial
        percentual = (ganho / self.saldo_inicial) * 100
        
        logger.info(f"[PROGRESSO] ${self.saldo_inicial:.2f} -> ${saldo_atual:.2f}")
        logger.info(f"[GANHO] ${ganho:+.2f} ({percentual:+.2f}%)")
        
        if saldo_atual >= self.meta_ganho:
            logger.info(f"[META] ✅ Atingida! +10% alcançado")
            return True
        
        return False
    
    def executar_ciclo(self):
        """Executar ciclo de trading ativo"""
        logger.info("=== CICLO ATIVO ===")
        
        # Verificar progresso
        meta_ok = self.verificar_progresso()
        if meta_ok:
            return True
        
        # Buscar oportunidades
        oportunidades = self.buscar_oportunidades_ativas()
        
        if not oportunidades:
            logger.info("[AMOS] Sem oportunidades no momento (critérios: 75%+ confiança)")
            return False
        
        # Executar melhor oportunidade
        melhor = oportunidades[0]
        resultado = self.executar_trade_ativo(melhor)
        
        if resultado and resultado.get('success'):
            logger.info("✅ Trade ativo executado com sucesso!")
            
            # Pausa após trade bem-sucedido
            logger.info("Aguardando 3 minutos após trade...")
            time.sleep(180)
            return True
        else:
            logger.warning("❌ Trade não executado")
            return False

def main():
    """Executar trading ativo para Amos"""
    try:
        trader = AmosTradingAtivo()
        
        print("\n" + "="*50)
        print("AMOS TRADING ATIVO - CRITÉRIOS AJUSTADOS")
        print("="*50)
        print(f"Saldo: ${trader.saldo_inicial:.2f}")
        print(f"Meta: ${trader.meta_ganho:.2f} (+10%)")
        print("Critério: 75%+ confiança (menos restritivo)")
        print("="*50)
        
        confirmacao = input("Iniciar trading ativo? (CONFIRMO): ")
        
        if confirmacao != 'CONFIRMO':
            logger.info("Cancelado pelo usuário")
            return
        
        logger.info("🚀 INICIANDO TRADING ATIVO!")
        
        ciclo = 1
        
        while ciclo <= 20:  # Máximo 20 ciclos
            logger.info(f"[CICLO {ciclo}/20]")
            
            meta_atingida = trader.executar_ciclo()
            
            if meta_atingida:
                logger.info("🎉 META ATINGIDA!")
                break
            
            if ciclo < 20:
                logger.info("Próximo ciclo em 2 minutos...")
                time.sleep(120)  # 2 minutos entre ciclos
            
            ciclo += 1
        
        # Relatório final
        saldo_final = trader.trader.get_saldo_usdt()
        ganho = saldo_final - trader.saldo_inicial
        percentual = (ganho / trader.saldo_inicial) * 100
        
        logger.info("=== RESULTADO FINAL ===")
        logger.info(f"Inicial: ${trader.saldo_inicial:.2f}")
        logger.info(f"Final: ${saldo_final:.2f}")
        logger.info(f"Ganho: ${ganho:+.2f} ({percentual:+.2f}%)")
        
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro: {e}")

if __name__ == "__main__":
    main()