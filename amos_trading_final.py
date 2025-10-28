#!/usr/bin/env python3
"""
AMOS TRADING FINAL - Versão Corrigida
Resolve problemas de API, Unicode e quantidade mínima
"""

import json
import time
import logging
import sys
from datetime import datetime

# Configurar logging SEM emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amos_final_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AmosTradingFinal:
    def __init__(self):
        """Sistema final corrigido para Amos"""
        logger.info("=== AMOS TRADING FINAL - VERSAO CORRIGIDA ===")
        
        # Carregar configuração
        try:
            with open('config/contas.json', 'r') as f:
                config = json.load(f)
            
            dados_amos = config['CONTA_3']
            
            # Importar classe corrigida
            from moises_estrategias_avancadas import TradingAvancado
            
            self.trader = TradingAvancado(
                api_key=dados_amos['api_key'],
                api_secret=dados_amos['api_secret'],
                conta_nome="AMOS_FINAL"
            )
            
            self.saldo_inicial = self.trader.get_saldo_usdt()
            logger.info(f"[AMOS] Saldo atual: ${self.saldo_inicial:.2f}")
            
        except Exception as e:
            logger.error(f"Erro na inicializacao: {e}")
            raise
    
    def verificar_requisitos_minimos(self, symbol):
        """Verificar requisitos mínimos da Binance para cada símbolo"""
        requisitos = {
            'BTCUSDT': {'min_qty': 0.00001, 'step_size': 0.00001, 'min_notional': 5.0},
            'ETHUSDT': {'min_qty': 0.0001, 'step_size': 0.0001, 'min_notional': 5.0},
            'BNBUSDT': {'min_qty': 0.001, 'step_size': 0.001, 'min_notional': 5.0},
            'ADAUSDT': {'min_qty': 0.1, 'step_size': 0.1, 'min_notional': 5.0},
            'DOGEUSDT': {'min_qty': 1.0, 'step_size': 1.0, 'min_notional': 5.0},
            'SOLUSDT': {'min_qty': 0.001, 'step_size': 0.001, 'min_notional': 5.0}
        }
        
        return requisitos.get(symbol, {'min_qty': 0.001, 'step_size': 0.001, 'min_notional': 5.0})
    
    def calcular_quantidade_valida(self, symbol, valor_usdt, preco):
        """Calcular quantidade válida respeitando os filtros da Binance"""
        requisitos = self.verificar_requisitos_minimos(symbol)
        
        # Calcular quantidade básica
        quantidade_base = valor_usdt / preco
        
        # Ajustar para step_size
        step_size = requisitos['step_size']
        quantidade_ajustada = round(quantidade_base / step_size) * step_size
        
        # Garantir quantidade mínima
        min_qty = requisitos['min_qty']
        quantidade_final = max(quantidade_ajustada, min_qty)
        
        # Verificar notional mínimo
        valor_notional = quantidade_final * preco
        min_notional = requisitos['min_notional']
        
        if valor_notional < min_notional:
            # Aumentar quantidade para atingir notional mínimo
            quantidade_final = (min_notional / preco)
            quantidade_final = round(quantidade_final / step_size) * step_size
        
        return quantidade_final
    
    def buscar_oportunidade_simples(self):
        """Buscar uma oportunidade simples e executável"""
        simbolos_prioritarios = ['ADAUSDT', 'DOGEUSDT', 'SOLUSDT']  # Altcoins com maior volatilidade
        
        for symbol in simbolos_prioritarios:
            try:
                logger.info(f"[ANALISE] Verificando {symbol}...")
                
                # Obter dados básicos
                candles = self.trader.get_candles_rapidos(symbol, '5m', 15)
                if not candles:
                    continue
                
                preco_atual = candles[-1]['close']
                prices = [c['close'] for c in candles]
                
                # RSI simples
                rsi = self.trader.calcular_rsi_rapido(prices)
                
                # Critério MUITO simples: RSI entre 30-70 (zona tradeable)
                if 30 <= rsi <= 70:
                    # Verificar se conseguimos calcular quantidade válida
                    quantidade = self.calcular_quantidade_valida(symbol, 6.0, preco_atual)
                    valor_estimado = quantidade * preco_atual
                    
                    if valor_estimado >= 5.0:  # Valor mínimo
                        oportunidade = {
                            'symbol': symbol,
                            'preco': preco_atual,
                            'quantidade': quantidade,
                            'valor_estimado': valor_estimado,
                            'rsi': rsi,
                            'razao': f"RSI {rsi:.1f} (zona tradeable)"
                        }
                        
                        logger.info(f"[OPORTUNIDADE] {symbol}")
                        logger.info(f"  Preco: ${preco_atual:.6f}")
                        logger.info(f"  Quantidade: {quantidade}")
                        logger.info(f"  Valor: ${valor_estimado:.2f}")
                        logger.info(f"  RSI: {rsi:.1f}")
                        
                        return oportunidade
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        return None
    
    def executar_trade_simples(self, oportunidade):
        """Executar trade com máxima simplicidade"""
        try:
            symbol = oportunidade['symbol']
            quantidade = oportunidade['quantidade']
            
            logger.info(f"[EXECUCAO] Preparando trade {symbol}")
            logger.info(f"  Quantidade: {quantidade}")
            logger.info(f"  Valor estimado: ${oportunidade['valor_estimado']:.2f}")
            
            # Parâmetros simplificados
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': f"{quantidade}"
            }
            
            logger.info(f"[PARAMS] {params}")
            
            # Executar trade real
            logger.info("[EXECUCAO] Enviando ordem para Binance...")
            resultado = self.trader._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                logger.error(f"[ERRO] Falha na execucao: {resultado}")
                
                # Tentar versão de teste para debug
                logger.info("[DEBUG] Testando com endpoint de teste...")
                resultado_teste = self.trader._request('POST', '/api/v3/order/test', params, signed=True)
                
                if resultado_teste.get('error'):
                    logger.error(f"[DEBUG] Teste tambem falhou: {resultado_teste}")
                else:
                    logger.info("[DEBUG] Teste passou - problema na execucao real")
                
                return None
            
            # SUCESSO!
            logger.info(f"[SUCESSO] Trade executado!")
            logger.info(f"  Order ID: {resultado.get('orderId')}")
            
            # Processar fills
            fills = resultado.get('fills', [])
            if fills:
                total_qty = sum(float(f['qty']) for f in fills)
                total_value = sum(float(f['qty']) * float(f['price']) for f in fills)
                avg_price = total_value / total_qty if total_qty > 0 else 0
                
                logger.info(f"  Executado: {total_qty} {symbol.replace('USDT', '')}")
                logger.info(f"  Preco medio: ${avg_price:.6f}")
                logger.info(f"  Valor total: ${total_value:.2f}")
            
            # Verificar novo saldo
            novo_saldo = self.trader.get_saldo_usdt()
            logger.info(f"[SALDO] Novo saldo: ${novo_saldo:.2f}")
            
            return {
                'success': True,
                'order_id': resultado.get('orderId'),
                'symbol': symbol,
                'valor': total_value if fills else oportunidade['valor_estimado']
            }
            
        except Exception as e:
            logger.error(f"[ERRO] Excecao na execucao: {e}")
            return None
    
    def executar_tentativa(self):
        """Executar uma tentativa completa"""
        logger.info("=== NOVA TENTATIVA ===")
        
        # Verificar saldo atual
        saldo_atual = self.trader.get_saldo_usdt()
        ganho = saldo_atual - self.saldo_inicial
        percentual = (ganho / self.saldo_inicial) * 100 if self.saldo_inicial > 0 else 0
        
        logger.info(f"[STATUS] Saldo: ${saldo_atual:.2f}")
        logger.info(f"[STATUS] Ganho: ${ganho:+.2f} ({percentual:+.2f}%)")
        
        if saldo_atual < 5:
            logger.warning("[PARADA] Saldo insuficiente")
            return False
        
        # Buscar oportunidade
        oportunidade = self.buscar_oportunidade_simples()
        
        if not oportunidade:
            logger.info("[INFO] Nenhuma oportunidade encontrada")
            return False
        
        # Executar trade
        resultado = self.executar_trade_simples(oportunidade)
        
        if resultado and resultado.get('success'):
            logger.info("[SUCESSO] Trade realizado com sucesso!")
            return True
        else:
            logger.warning("[FALHA] Trade nao executado")
            return False

def main():
    """Executar sistema final"""
    try:
        trader = AmosTradingFinal()
        
        print("\n" + "="*50)
        print("SISTEMA FINAL AMOS - VERSAO CORRIGIDA")
        print("="*50)
        print(f"Saldo atual: ${trader.saldo_inicial:.2f}")
        print("Objetivo: Executar pelo menos 1 trade real")
        print("Criterios: RSI 30-70, quantidade valida")
        print("="*50)
        
        confirmacao = input("Executar sistema final? (SIM): ")
        
        if confirmacao != 'SIM':
            logger.info("Sistema cancelado")
            return
        
        logger.info("[INICIO] Sistema final iniciado")
        
        tentativas = 0
        max_tentativas = 10
        sucesso = False
        
        while tentativas < max_tentativas and not sucesso:
            tentativas += 1
            logger.info(f"[TENTATIVA {tentativas}/{max_tentativas}]")
            
            sucesso = trader.executar_tentativa()
            
            if sucesso:
                logger.info("[CONCLUSAO] Trade executado com sucesso!")
                break
            
            if tentativas < max_tentativas:
                logger.info(f"Proxima tentativa em 30 segundos...")
                time.sleep(30)
        
        if not sucesso:
            logger.warning("[CONCLUSAO] Nenhum trade executado apos todas as tentativas")
        
        # Status final
        saldo_final = trader.trader.get_saldo_usdt()
        ganho_final = saldo_final - trader.saldo_inicial
        percentual_final = (ganho_final / trader.saldo_inicial) * 100
        
        logger.info("=== RELATORIO FINAL ===")
        logger.info(f"Saldo inicial: ${trader.saldo_inicial:.2f}")
        logger.info(f"Saldo final: ${saldo_final:.2f}")
        logger.info(f"Variacao: ${ganho_final:+.2f} ({percentual_final:+.2f}%)")
        logger.info(f"Tentativas: {tentativas}")
        logger.info(f"Status: {'SUCESSO' if sucesso else 'SEM EXECUCAO'}")
        
    except KeyboardInterrupt:
        logger.info("Sistema interrompido pelo usuario")
    except Exception as e:
        logger.error(f"Erro critico: {e}")

if __name__ == "__main__":
    main()