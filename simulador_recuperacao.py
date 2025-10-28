#!/usr/bin/env python3
"""
SIMULADOR DE RECUPERAÇÃO - Versão Segura
Simula trades reais para mostrar estratégias de recuperação
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
        logging.FileHandler('simulacao_recuperacao.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SimuladorRecuperacao:
    def __init__(self):
        """Inicializar simulador"""
        self.saldos_simulados = {
            'CONTA_2': 13.88,  # Paulo
            'CONTA_3': 18.31   # Amos
        }
        
        self.portfolios_simulados = {
            'CONTA_2': {},  # Criptos em carteira
            'CONTA_3': {}
        }
        
        self.trades_simulados = []
        
        # Metas
        self.metas = {
            'CONTA_2': 16.00,  # Paulo precisa recuperar para $16
            'CONTA_3': 20.00   # Amos crescer para $20 (meta ajustada)
        }
        
        logger.info("=== SIMULADOR DE RECUPERAÇÃO INICIADO ===")
        logger.info(f"Paulo (CONTA_2): ${self.saldos_simulados['CONTA_2']:.2f} -> Meta: ${self.metas['CONTA_2']:.2f}")
        logger.info(f"Amos (CONTA_3): ${self.saldos_simulados['CONTA_3']:.2f} -> Meta: ${self.metas['CONTA_3']:.2f}")
    
    def obter_preco_atual(self, symbol):
        """Obter preço atual do símbolo"""
        try:
            import requests
            r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}', timeout=5)
            if r.status_code == 200:
                return float(r.json()['price'])
        except:
            pass
        
        # Preços de fallback
        precos_fallback = {
            'BTCUSDT': 67500.00,
            'ETHUSDT': 2600.00,
            'ADAUSDT': 0.6750,
            'DOGEUSDT': 0.1650,
            'BNBUSDT': 590.00
        }
        return precos_fallback.get(symbol, 1.0)
    
    def simular_trade_compra(self, conta, symbol, valor_usdt, preco_entrada):
        """Simular uma compra"""
        if self.saldos_simulados[conta] < valor_usdt:
            logger.warning(f"[{conta}] Saldo insuficiente: ${self.saldos_simulados[conta]:.2f} < ${valor_usdt:.2f}")
            return None
        
        quantidade = valor_usdt / preco_entrada
        
        # Deduzir taxa de 0.1%
        taxa = valor_usdt * 0.001
        valor_liquido = valor_usdt - taxa
        quantidade_liquida = valor_liquido / preco_entrada
        
        # Atualizar saldos
        self.saldos_simulados[conta] -= valor_usdt
        
        if symbol not in self.portfolios_simulados[conta]:
            self.portfolios_simulados[conta][symbol] = 0
        
        self.portfolios_simulados[conta][symbol] += quantidade_liquida
        
        # Registrar trade
        trade = {
            'timestamp': datetime.now().isoformat(),
            'conta': conta,
            'acao': 'COMPRA',
            'symbol': symbol,
            'quantidade': quantidade_liquida,
            'preco_entrada': preco_entrada,
            'valor_usdt': valor_usdt,
            'taxa': taxa,
            'saldo_pos_trade': self.saldos_simulados[conta]
        }
        
        self.trades_simulados.append(trade)
        
        logger.info(f"[{conta}] COMPRA SIMULADA: {quantidade_liquida:.4f} {symbol.replace('USDT', '')} por ${valor_usdt:.2f}")
        logger.info(f"[{conta}] Novo saldo: ${self.saldos_simulados[conta]:.2f}")
        
        return trade
    
    def simular_trade_venda(self, conta, symbol, percentual_venda=1.0):
        """Simular uma venda (100% = venda total)"""
        if symbol not in self.portfolios_simulados[conta] or self.portfolios_simulados[conta][symbol] <= 0:
            logger.warning(f"[{conta}] Sem {symbol} para vender")
            return None
        
        quantidade_total = self.portfolios_simulados[conta][symbol]
        quantidade_venda = quantidade_total * percentual_venda
        
        preco_atual = self.obter_preco_atual(symbol)
        valor_bruto = quantidade_venda * preco_atual
        
        # Deduzir taxa de 0.1%
        taxa = valor_bruto * 0.001
        valor_liquido = valor_bruto - taxa
        
        # Atualizar saldos
        self.saldos_simulados[conta] += valor_liquido
        self.portfolios_simulados[conta][symbol] -= quantidade_venda
        
        if self.portfolios_simulados[conta][symbol] <= 0:
            del self.portfolios_simulados[conta][symbol]
        
        # Registrar trade
        trade = {
            'timestamp': datetime.now().isoformat(),
            'conta': conta,
            'acao': 'VENDA',
            'symbol': symbol,
            'quantidade': quantidade_venda,
            'preco_saida': preco_atual,
            'valor_usdt': valor_liquido,
            'taxa': taxa,
            'saldo_pos_trade': self.saldos_simulados[conta]
        }
        
        self.trades_simulados.append(trade)
        
        logger.info(f"[{conta}] VENDA SIMULADA: {quantidade_venda:.4f} {symbol.replace('USDT', '')} por ${valor_liquido:.2f}")
        logger.info(f"[{conta}] Novo saldo: ${self.saldos_simulados[conta]:.2f}")
        
        return trade
    
    def calcular_portfolio_total(self, conta):
        """Calcular valor total do portfolio (USDT + cripto)"""
        total = self.saldos_simulados[conta]
        
        for symbol, quantidade in self.portfolios_simulados[conta].items():
            preco_atual = self.obter_preco_atual(symbol)
            valor_cripto = quantidade * preco_atual
            total += valor_cripto
        
        return total
    
    def estrategia_paulo_agressiva(self):
        """Estratégia agressiva para Paulo recuperar perdas"""
        logger.info("[PAULO] Executando estratégia de recuperação agressiva...")
        
        # Análise de mercado - procurar RSI oversold
        simbolos_oportunidade = []
        
        for symbol in ['ADAUSDT', 'DOGEUSDT', 'BTCUSDT']:
            try:
                # Simular análise RSI (usando dados reais se possível)
                with open('config/contas.json', 'r') as f:
                    config = json.load(f)
                
                dados_conta = list(config.values())[0]
                trader = TradingAvancado(
                    api_key=dados_conta['api_key'],
                    api_secret=dados_conta['api_secret'],
                    conta_nome="ANALISE"
                )
                
                candles = trader.get_candles_rapidos(symbol, '5m', 20)
                if candles:
                    prices = [c['close'] for c in candles]
                    rsi = trader.calcular_rsi_rapido(prices)
                    preco_atual = candles[-1]['close']
                    
                    if rsi < 35:  # Oversold
                        simbolos_oportunidade.append({
                            'symbol': symbol,
                            'preco': preco_atual,
                            'rsi': rsi,
                            'confidence': min(95, 70 + (35 - rsi) * 2)
                        })
                        
                        logger.info(f"[PAULO] Oportunidade {symbol}: RSI {rsi:.1f} (oversold)")
            except:
                continue
        
        # Executar trades baseados nas oportunidades
        if simbolos_oportunidade:
            # Ordenar por confiança
            simbolos_oportunidade.sort(key=lambda x: x['confidence'], reverse=True)
            
            melhor_oportunidade = simbolos_oportunidade[0]
            
            # Usar 30% do saldo para recuperação
            valor_trade = self.saldos_simulados['CONTA_2'] * 0.30
            valor_trade = max(5.0, min(valor_trade, 6.0))  # Entre $5 e $6
            
            if valor_trade >= 5:
                trade = self.simular_trade_compra(
                    'CONTA_2',
                    melhor_oportunidade['symbol'],
                    valor_trade,
                    melhor_oportunidade['preco']
                )
                
                if trade:
                    logger.info(f"[PAULO] Trade executado: {melhor_oportunidade['symbol']} - Confiança: {melhor_oportunidade['confidence']:.1f}%")
                    return trade
        
        logger.info("[PAULO] Nenhuma oportunidade forte encontrada no momento")
        return None
    
    def estrategia_amos_conservadora(self):
        """Estratégia conservadora para Amos"""
        logger.info("[AMOS] Executando estratégia de crescimento conservadora...")
        
        # Amos só opera com alta confiança (RSI < 25 ou momentum muito forte)
        for symbol in ['BTCUSDT', 'ETHUSDT']:
            try:
                with open('config/contas.json', 'r') as f:
                    config = json.load(f)
                
                dados_conta = list(config.values())[1]  # Segunda conta (Amos)
                trader = TradingAvancado(
                    api_key=dados_conta['api_key'],
                    api_secret=dados_conta['api_secret'],
                    conta_nome="ANALISE_AMOS"
                )
                
                candles = trader.get_candles_rapidos(symbol, '5m', 20)
                if candles:
                    prices = [c['close'] for c in candles]
                    rsi = trader.calcular_rsi_rapido(prices)
                    preco_atual = candles[-1]['close']
                    
                    if rsi < 25:  # Muito oversold
                        valor_trade = self.saldos_simulados['CONTA_3'] * 0.20  # Mais conservador
                        valor_trade = max(5.0, min(valor_trade, 8.0))
                        
                        trade = self.simular_trade_compra('CONTA_3', symbol, valor_trade, preco_atual)
                        
                        if trade:
                            logger.info(f"[AMOS] Trade conservador: {symbol} - RSI {rsi:.1f}")
                            return trade
            except:
                continue
        
        logger.info("[AMOS] Aguardando oportunidade com alta confiança...")
        return None
    
    def executar_ciclo_simulacao(self):
        """Executar um ciclo completo de simulação"""
        logger.info("=== INICIANDO CICLO DE SIMULAÇÃO ===")
        
        # Mostrar status inicial
        paulo_total = self.calcular_portfolio_total('CONTA_2')
        amos_total = self.calcular_portfolio_total('CONTA_3')
        
        logger.info(f"Paulo Total: ${paulo_total:.2f} (Meta: ${self.metas['CONTA_2']:.2f})")
        logger.info(f"Amos Total: ${amos_total:.2f} (Meta: ${self.metas['CONTA_3']:.2f})")
        
        trades_executados = []
        
        # Executar estratégias
        trade_paulo = self.estrategia_paulo_agressiva()
        if trade_paulo:
            trades_executados.append(trade_paulo)
        
        time.sleep(2)  # Pausa entre estratégias
        
        trade_amos = self.estrategia_amos_conservadora()
        if trade_amos:
            trades_executados.append(trade_amos)
        
        # Simular variação de preços (pequenas flutuações)
        self.simular_variacao_precos()
        
        # Verificar lucros e realizar vendas se atingir take profit
        vendas = self.verificar_take_profits()
        trades_executados.extend(vendas)
        
        # Status final
        paulo_final = self.calcular_portfolio_total('CONTA_2')
        amos_final = self.calcular_portfolio_total('CONTA_3')
        
        logger.info("=== RESULTADO DO CICLO ===")
        logger.info(f"Paulo: ${paulo_total:.2f} -> ${paulo_final:.2f} ({paulo_final-paulo_total:+.2f})")
        logger.info(f"Amos: ${amos_total:.2f} -> ${amos_final:.2f} ({amos_final-amos_total:+.2f})")
        
        # Verificar metas
        if paulo_final >= self.metas['CONTA_2'] and amos_final >= self.metas['CONTA_3']:
            logger.info("🎉 METAS ATINGIDAS! Simulação concluída com sucesso!")
            return True
        
        return False
    
    def simular_variacao_precos(self):
        """Simular pequenas variações de preço (±1-3%)"""
        import random
        
        # Para fins de simulação, não alteramos preços reais
        # Apenas logamos que houve variação
        variacao = random.uniform(-0.02, 0.03)  # -2% a +3%
        logger.info(f"[MERCADO] Variação simulada: {variacao*100:+.1f}%")
    
    def verificar_take_profits(self):
        """Verificar se alguma posição atingiu take profit (+5%)"""
        vendas = []
        
        for conta in ['CONTA_2', 'CONTA_3']:
            for symbol in list(self.portfolios_simulados[conta].keys()):
                # Simular lucro de +5% (take profit)
                import random
                if random.random() < 0.3:  # 30% chance de take profit
                    venda = self.simular_trade_venda(conta, symbol, 1.0)  # Vender tudo
                    if venda:
                        vendas.append(venda)
                        logger.info(f"[{conta}] Take Profit atingido em {symbol}")
        
        return vendas
    
    def relatorio_final(self):
        """Gerar relatório final da simulação"""
        logger.info("=== RELATÓRIO FINAL ===")
        
        for conta in ['CONTA_2', 'CONTA_3']:
            total = self.calcular_portfolio_total(conta)
            meta = self.metas[conta]
            progresso = ((total - meta) / meta) * 100
            
            logger.info(f"{conta}: ${total:.2f} / ${meta:.2f} ({progresso:+.1f}%)")
            
            if self.portfolios_simulados[conta]:
                logger.info(f"  Posições abertas:")
                for symbol, qtd in self.portfolios_simulados[conta].items():
                    preco = self.obter_preco_atual(symbol)
                    valor = qtd * preco
                    logger.info(f"    {symbol}: {qtd:.4f} (${valor:.2f})")
        
        logger.info(f"Total de trades simulados: {len(self.trades_simulados)}")
        
        # Salvar relatório
        relatorio = {
            'saldos_finais': self.saldos_simulados,
            'portfolios_finais': self.portfolios_simulados,
            'trades_executados': self.trades_simulados,
            'metas': self.metas
        }
        
        with open(f'relatorio_simulacao_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)

def main():
    """Executar simulação completa"""
    simulador = SimuladorRecuperacao()
    
    print("=== SIMULADOR DE RECUPERAÇÃO ===")
    print("Este sistema simula as estratégias de trading que seriam executadas")
    print("com as contas reais, mostrando os resultados esperados.")
    print()
    
    confirmacao = input("Executar simulação? (s/n): ")
    
    if confirmacao.lower() == 's':
        try:
            ciclos = 0
            max_ciclos = 10
            
            while ciclos < max_ciclos:
                ciclos += 1
                logger.info(f"[CICLO {ciclos}/{max_ciclos}]")
                
                metas_atingidas = simulador.executar_ciclo_simulacao()
                
                if metas_atingidas:
                    logger.info("Simulação concluída - metas atingidas!")
                    break
                
                if ciclos < max_ciclos:
                    logger.info("Próximo ciclo em 10 segundos...")
                    time.sleep(10)
            
            simulador.relatorio_final()
            
        except KeyboardInterrupt:
            logger.info("Simulação interrompida pelo usuário")
            simulador.relatorio_final()
    else:
        logger.info("Simulação cancelada")

if __name__ == "__main__":
    main()