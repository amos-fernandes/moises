#!/usr/bin/env python3
"""
AMOS DAY TRADING COMPLETO - COMPRA E VENDA
Sistema completo: Compra em baixa + Venda em alta = Lucro em USDT
"""

import json
import time
import logging
import sys
from datetime import datetime
from moises_estrategias_avancadas import TradingAvancado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amos_daytrading_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AmosDayTrading:
    def __init__(self):
        """Sistema completo de Day Trading para Amos"""
        logger.info("=== AMOS DAY TRADING COMPLETO - COMPRA E VENDA ===")
        
        # Carregar conta Amos
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        dados_amos = config['CONTA_3']
        
        self.trader = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="AMOS_DAYTRADING"
        )
        
        self.saldo_inicial_usdt = self.trader.get_saldo_usdt()
        logger.info(f"[AMOS] Saldo USDT: ${self.saldo_inicial_usdt:.2f}")
        
        # Verificar moedas já compradas
        self.verificar_portfolio_atual()
    
    def verificar_portfolio_atual(self):
        """Verificar todas as moedas que já temos na carteira"""
        try:
            # Obter informações da conta
            account = self.trader._request('GET', '/api/v3/account', {}, signed=True)
            
            if account.get('error'):
                logger.error(f"Erro ao obter conta: {account}")
                return {}
            
            portfolio = {}
            total_valor_criptos = 0
            
            logger.info("[PORTFOLIO] Verificando moedas na carteira...")
            
            for balance in account.get('balances', []):
                asset = balance['asset']
                free_qty = float(balance['free'])
                locked_qty = float(balance['locked'])
                total_qty = free_qty + locked_qty
                
                # Ignorar USDT e moedas com quantidade zero
                if asset != 'USDT' and total_qty > 0:
                    # Obter preço atual
                    try:
                        import requests
                        r = requests.get(f'https://api.binance.com/api/v3/ticker/price?symbol={asset}USDT', timeout=5)
                        if r.status_code == 200:
                            preco_atual = float(r.json()['price'])
                            valor_usdt = total_qty * preco_atual
                            
                            portfolio[asset] = {
                                'quantidade': total_qty,
                                'quantidade_livre': free_qty,
                                'preco_atual': preco_atual,
                                'valor_usdt': valor_usdt
                            }
                            
                            total_valor_criptos += valor_usdt
                            
                            logger.info(f"[{asset}] {total_qty:.6f} = ${valor_usdt:.2f} (${preco_atual:.6f})")
                        
                    except Exception as e:
                        logger.warning(f"Erro ao obter preço {asset}: {e}")
            
            logger.info(f"[PORTFOLIO] Total em criptos: ${total_valor_criptos:.2f}")
            logger.info(f"[PORTFOLIO] Total USDT: ${self.saldo_inicial_usdt:.2f}")
            logger.info(f"[PORTFOLIO] Patrimônio total: ${self.saldo_inicial_usdt + total_valor_criptos:.2f}")
            
            self.portfolio = portfolio
            return portfolio
            
        except Exception as e:
            logger.error(f"Erro ao verificar portfolio: {e}")
            return {}
    
    def analisar_oportunidade_venda(self, asset):
        """Analisar se uma moeda está em alta para venda"""
        try:
            symbol = f"{asset}USDT"
            
            # Obter candles para análise
            candles = self.trader.get_candles_rapidos(symbol, '5m', 20)
            if not candles:
                return None
            
            prices = [c['close'] for c in candles]
            preco_atual = candles[-1]['close']
            
            # Calcular RSI
            rsi = self.trader.calcular_rsi_rapido(prices)
            
            # Calcular variação percentual recente
            preco_5min_atras = prices[-2] if len(prices) > 1 else preco_atual
            variacao_5min = ((preco_atual - preco_5min_atras) / preco_5min_atras) * 100
            
            # Verificar média móvel
            ma_5 = sum(prices[-5:]) / 5
            ma_10 = sum(prices[-10:]) / 10
            
            # CRITÉRIOS PARA VENDA (oportunidade de lucro)
            venda_score = 0
            razoes = []
            
            # RSI alto (overbought - bom momento para vender)
            if rsi > 65:
                venda_score += 30
                razoes.append(f"RSI {rsi:.1f} (overbought)")
            elif rsi > 55:
                venda_score += 15
                razoes.append(f"RSI {rsi:.1f} (alta)")
            
            # Variação positiva recente
            if variacao_5min > 1:
                venda_score += 25
                razoes.append(f"Alta +{variacao_5min:.1f}%")
            elif variacao_5min > 0.5:
                venda_score += 15
                razoes.append(f"Subindo +{variacao_5min:.1f}%")
            
            # Média móvel favorável
            if ma_5 > ma_10:
                venda_score += 10
                razoes.append("Tendência alta")
            
            # Preço atual acima da média
            if preco_atual > ma_10:
                venda_score += 10
                razoes.append("Acima média")
            
            logger.info(f"[ANALISE VENDA {asset}] Score: {venda_score}/85")
            logger.info(f"  Preço: ${preco_atual:.6f}")
            logger.info(f"  RSI: {rsi:.1f}")
            logger.info(f"  Variação 5min: {variacao_5min:+.2f}%")
            logger.info(f"  Razões: {', '.join(razoes)}")
            
            if venda_score >= 50:  # Critério para venda
                return {
                    'asset': asset,
                    'symbol': symbol,
                    'preco_atual': preco_atual,
                    'venda_score': venda_score,
                    'rsi': rsi,
                    'variacao_5min': variacao_5min,
                    'razoes': razoes
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro analisando venda {asset}: {e}")
            return None
    
    def executar_venda_lucro(self, asset_data):
        """Executar venda para realizar lucro"""
        try:
            asset = asset_data['asset']
            symbol = asset_data['symbol']
            
            if asset not in self.portfolio:
                logger.warning(f"[VENDA] {asset} não encontrado no portfolio")
                return None
            
            quantidade_disponivel = self.portfolio[asset]['quantidade_livre']
            preco_atual = asset_data['preco_atual']
            valor_estimado = quantidade_disponivel * preco_atual
            
            logger.info(f"[VENDA EM ALTA] {asset}")
            logger.info(f"  Quantidade: {quantidade_disponivel:.6f}")
            logger.info(f"  Preço atual: ${preco_atual:.6f}")
            logger.info(f"  Valor estimado: ${valor_estimado:.2f}")
            logger.info(f"  Score venda: {asset_data['venda_score']}/85")
            logger.info(f"  Razões: {', '.join(asset_data['razoes'])}")
            
            if valor_estimado < 5:  # Valor muito pequeno
                logger.warning(f"[VENDA] Valor muito pequeno: ${valor_estimado:.2f}")
                return None
            
            # Ajustar quantidade para filtros da Binance
            if asset == 'SOL':
                quantidade_venda = round(quantidade_disponivel, 3)
            elif asset == 'ADA':
                quantidade_venda = round(quantidade_disponivel, 1)
            elif asset in ['BTC', 'ETH']:
                quantidade_venda = round(quantidade_disponivel, 5)
            else:
                quantidade_venda = round(quantidade_disponivel, 4)
            
            # Parâmetros de venda
            params = {
                'symbol': symbol,
                'side': 'SELL',  # VENDA
                'type': 'MARKET',
                'quantity': f"{quantidade_venda}"
            }
            
            logger.info(f"[EXECUTANDO VENDA] {params}")
            
            # Executar venda real
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"[ERRO VENDA] {resultado}")
                return None
            
            # VENDA REALIZADA COM SUCESSO!
            logger.info(f"[SUCESSO VENDA] {asset} vendido!")
            logger.info(f"  Order ID: {resultado.get('orderId')}")
            
            # Processar resultado
            fills = resultado.get('fills', [])
            if fills:
                qty_vendida = sum(float(f['qty']) for f in fills)
                valor_recebido = sum(float(f['qty']) * float(f['price']) for f in fills)
                preco_medio_venda = valor_recebido / qty_vendida if qty_vendida > 0 else 0
                
                logger.info(f"  Vendido: {qty_vendida:.6f} {asset}")
                logger.info(f"  Preço médio venda: ${preco_medio_venda:.6f}")
                logger.info(f"  USDT recebido: ${valor_recebido:.2f}")
                
                # Atualizar saldo
                novo_saldo_usdt = self.trader.get_saldo_usdt()
                logger.info(f"[SALDO ATUALIZADO] ${novo_saldo_usdt:.2f}")
                
                return {
                    'success': True,
                    'asset': asset,
                    'quantidade_vendida': qty_vendida,
                    'valor_recebido': valor_recebido,
                    'preco_medio_venda': preco_medio_venda,
                    'novo_saldo': novo_saldo_usdt
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro na venda {asset}: {e}")
            return None
    
    def buscar_oportunidade_compra(self):
        """Buscar oportunidades de compra (RSI baixo)"""
        simbolos = ['ADAUSDT', 'DOGEUSDT', 'SOLUSDT', 'BNBUSDT']
        
        for symbol in simbolos:
            try:
                candles = self.trader.get_candles_rapidos(symbol, '5m', 15)
                if not candles:
                    continue
                
                prices = [c['close'] for c in candles]
                preco_atual = candles[-1]['close']
                rsi = self.trader.calcular_rsi_rapido(prices)
                
                # Critério de compra: RSI baixo (oversold)
                if rsi < 35:
                    asset = symbol.replace('USDT', '')
                    
                    # Calcular quantidade
                    saldo_usdt = self.trader.get_saldo_usdt()
                    valor_compra = min(6.0, saldo_usdt * 0.3)  # Máximo $6 ou 30% do saldo
                    
                    if valor_compra >= 5 and saldo_usdt >= 5:
                        # Ajustar quantidade baseada nos filtros
                        if asset == 'ADA':
                            quantidade = round(valor_compra / preco_atual, 1)
                        elif asset == 'DOGE':
                            quantidade = round(valor_compra / preco_atual)
                        elif asset == 'SOL':
                            quantidade = round(valor_compra / preco_atual, 3)
                        else:
                            quantidade = round(valor_compra / preco_atual, 4)
                        
                        valor_real = quantidade * preco_atual
                        
                        if valor_real >= 5:
                            return {
                                'symbol': symbol,
                                'asset': asset,
                                'preco': preco_atual,
                                'quantidade': quantidade,
                                'valor': valor_real,
                                'rsi': rsi
                            }
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Erro analisando compra {symbol}: {e}")
                continue
        
        return None
    
    def executar_compra_baixa(self, oportunidade):
        """Executar compra em baixa"""
        try:
            symbol = oportunidade['symbol']
            quantidade = oportunidade['quantidade']
            
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': f"{quantidade}"
            }
            
            logger.info(f"[COMPRA EM BAIXA] {symbol}")
            logger.info(f"  Quantidade: {quantidade}")
            logger.info(f"  Valor: ${oportunidade['valor']:.2f}")
            logger.info(f"  RSI: {oportunidade['rsi']:.1f}")
            logger.info(f"  Parâmetros: {params}")
            
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"[ERRO COMPRA] {resultado}")
                return None
            
            logger.info(f"[SUCESSO COMPRA] {oportunidade['asset']} comprado!")
            logger.info(f"  Order ID: {resultado.get('orderId')}")
            
            return {'success': True, 'asset': oportunidade['asset']}
            
        except Exception as e:
            logger.error(f"Erro na compra: {e}")
            return None
    
    def executar_ciclo_daytrading(self):
        """Executar ciclo completo: verificar vendas + buscar compras"""
        logger.info("=== CICLO DAY TRADING ===")
        
        # 1. VERIFICAR VENDAS (realizar lucros)
        self.verificar_portfolio_atual()
        
        vendas_realizadas = 0
        
        for asset in list(self.portfolio.keys()):
            if asset == 'USDT':
                continue
                
            oportunidade_venda = self.analisar_oportunidade_venda(asset)
            
            if oportunidade_venda:
                logger.info(f"[OPORTUNIDADE VENDA] {asset} em alta!")
                
                resultado_venda = self.executar_venda_lucro(oportunidade_venda)
                
                if resultado_venda and resultado_venda.get('success'):
                    logger.info(f"[LUCRO REALIZADO] {asset} -> USDT: ${resultado_venda['valor_recebido']:.2f}")
                    vendas_realizadas += 1
                    time.sleep(5)  # Pausa após venda
        
        # 2. BUSCAR COMPRAS (em baixa)
        if vendas_realizadas == 0:  # Só comprar se não vendeu nada
            saldo_atual = self.trader.get_saldo_usdt()
            
            if saldo_atual >= 5:
                oportunidade_compra = self.buscar_oportunidade_compra()
                
                if oportunidade_compra:
                    logger.info(f"[OPORTUNIDADE COMPRA] {oportunidade_compra['asset']} em baixa (RSI {oportunidade_compra['rsi']:.1f})")
                    
                    resultado_compra = self.executar_compra_baixa(oportunidade_compra)
                    
                    if resultado_compra and resultado_compra.get('success'):
                        logger.info(f"[COMPRA REALIZADA] {resultado_compra['asset']} comprado em baixa")
                else:
                    logger.info("[INFO] Nenhuma oportunidade de compra (aguardando RSI < 35)")
            else:
                logger.warning(f"[SALDO BAIXO] ${saldo_atual:.2f} - aguardando vendas")
        
        # Status final do ciclo
        saldo_final = self.trader.get_saldo_usdt()
        self.verificar_portfolio_atual()
        
        total_patrimonio = saldo_final + sum(p['valor_usdt'] for p in self.portfolio.values())
        
        logger.info(f"[STATUS] USDT: ${saldo_final:.2f}")
        logger.info(f"[STATUS] Patrimônio total: ${total_patrimonio:.2f}")
        
        return vendas_realizadas > 0 or saldo_final > self.saldo_inicial_usdt

def main():
    """Executar Day Trading completo"""
    try:
        daytrader = AmosDayTrading()
        
        print("\n" + "="*60)
        print("AMOS DAY TRADING COMPLETO - COMPRA EM BAIXA E VENDA EM ALTA")
        print("="*60)
        print(f"Saldo USDT: ${daytrader.saldo_inicial_usdt:.2f}")
        print("Estratégia: Vender moedas em alta + Comprar em baixa")
        print("Objetivo: Realizar lucros convertendo para USDT")
        print("="*60)
        
        confirmacao = input("Executar Day Trading completo? (AUTORIZO): ")
        
        if confirmacao != 'AUTORIZO':
            logger.info("Day Trading cancelado")
            return
        
        logger.info("[AUTORIZADO] Day Trading iniciado!")
        
        ciclo = 1
        
        while ciclo <= 20:
            logger.info(f"[CICLO {ciclo}/20] Day Trading")
            
            sucesso = daytrader.executar_ciclo_daytrading()
            
            if ciclo < 20:
                tempo_pausa = 120 if sucesso else 180  # 2min se houve ação, 3min se não
                logger.info(f"Próximo ciclo em {tempo_pausa//60} minutos...")
                time.sleep(tempo_pausa)
            
            ciclo += 1
        
        # Relatório final
        saldo_final = daytrader.trader.get_saldo_usdt()
        daytrader.verificar_portfolio_atual()
        
        total_final = saldo_final + sum(p['valor_usdt'] for p in daytrader.portfolio.values())
        lucro_total = total_final - daytrader.saldo_inicial_usdt
        percentual = (lucro_total / daytrader.saldo_inicial_usdt) * 100
        
        logger.info("=== RELATORIO FINAL DAY TRADING ===")
        logger.info(f"Saldo inicial: ${daytrader.saldo_inicial_usdt:.2f}")
        logger.info(f"Saldo final USDT: ${saldo_final:.2f}")
        logger.info(f"Patrimônio total: ${total_final:.2f}")
        logger.info(f"Lucro/Perda: ${lucro_total:+.2f} ({percentual:+.2f}%)")
        
    except KeyboardInterrupt:
        logger.info("Day Trading interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no Day Trading: {e}")

if __name__ == "__main__":
    main()