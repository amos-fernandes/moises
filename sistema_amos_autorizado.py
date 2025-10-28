#!/usr/bin/env python3
"""
SISTEMA AUTORIZADO - TRADES REAIS CONTA_3 (AMOS)
Autorização do usuário para trades reais apenas com CONTA_3
CONTA_2 (Paulo) permanece PAUSADA até segunda ordem
"""

import json
import time
import logging
import sys
from datetime import datetime

# Configurar logging sem emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'amos_autorizado_{datetime.now().strftime("%Y%m%d_%H%M")}.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AmosAutorizado:
    def __init__(self):
        """Sistema autorizado para trades reais - APENAS CONTA_3"""
        logger.info("=== SISTEMA AUTORIZADO - TRADES REAIS AMOS ===")
        logger.info("CONTA_3 (Amos): AUTORIZADA para trades reais")
        logger.info("CONTA_2 (Paulo): PAUSADA ate segunda ordem")
        
        # Carregar APENAS conta Amos (CONTA_3)
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        if 'CONTA_3' not in config:
            raise Exception("CONTA_3 (Amos) nao encontrada na configuracao")
        
        dados_amos = config['CONTA_3']
        
        from moises_estrategias_avancadas import TradingAvancado
        
        self.trader_amos = TradingAvancado(
            api_key=dados_amos['api_key'],
            api_secret=dados_amos['api_secret'],
            conta_nome="AMOS_AUTORIZADO"
        )
        
        self.saldo_inicial = self.trader_amos.get_saldo_usdt()
        self.trades_executados = []
        self.objetivo_ganho = self.saldo_inicial * 1.08  # Meta: +8% realista
        
        logger.info(f"[AMOS] Saldo inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"[AMOS] Meta de ganhos: ${self.objetivo_ganho:.2f} (+8%)")
        logger.info("[PAULO] Conta PAUSADA - nao sera operada")
    
    def encontrar_oportunidade_real(self):
        """Encontrar oportunidade real para execução"""
        # Focar em pares com maior chance de sucesso
        pares_prioritarios = [
            'ADAUSDT',   # ADA tem boa liquidez
            'DOGEUSDT',  # DOGE popular
            'BNBUSDT',   # BNB nativo da Binance
            'SOLUSDT'    # SOL tem volatilidade
        ]
        
        for symbol in pares_prioritarios:
            try:
                logger.info(f"[BUSCA] Analisando {symbol}...")
                
                # Obter dados de mercado
                candles = self.trader_amos.get_candles_rapidos(symbol, '5m', 10)
                if not candles:
                    continue
                
                preco_atual = candles[-1]['close']
                prices = [c['close'] for c in candles]
                rsi = self.trader_amos.calcular_rsi_rapido(prices)
                
                # Critério amplo para encontrar oportunidades
                if 25 <= rsi <= 75:  # RSI em zona operável
                    
                    # Calcular quantidade mínima válida
                    if symbol == 'ADAUSDT':
                        # ADA: quantidade mínima 0.1, step 0.1
                        valor_trade = 6.0  # $6
                        quantidade = max(0.1, round((valor_trade / preco_atual) / 0.1) * 0.1)
                        
                    elif symbol == 'DOGEUSDT':
                        # DOGE: quantidade mínima 1.0, step 1.0
                        valor_trade = 6.0
                        quantidade = max(1.0, round(valor_trade / preco_atual))
                        
                    elif symbol == 'BNBUSDT':
                        # BNB: quantidade mínima 0.001, step 0.001
                        valor_trade = 6.0
                        quantidade = max(0.001, round((valor_trade / preco_atual) / 0.001) * 0.001)
                        
                    elif symbol == 'SOLUSDT':
                        # SOL: quantidade mínima 0.001, step 0.001
                        valor_trade = 6.0
                        quantidade = max(0.001, round((valor_trade / preco_atual) / 0.001) * 0.001)
                    
                    valor_estimado = quantidade * preco_atual
                    
                    # Verificar se valor atende ao mínimo ($5)
                    if valor_estimado >= 5.0:
                        logger.info(f"[ENCONTRADA] {symbol}")
                        logger.info(f"  Preco: ${preco_atual:.6f}")
                        logger.info(f"  RSI: {rsi:.1f}")
                        logger.info(f"  Quantidade: {quantidade}")
                        logger.info(f"  Valor: ${valor_estimado:.2f}")
                        
                        return {
                            'symbol': symbol,
                            'preco': preco_atual,
                            'quantidade': quantidade,
                            'valor': valor_estimado,
                            'rsi': rsi
                        }
                
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro analisando {symbol}: {e}")
                continue
        
        return None
    
    def executar_trade_autorizado(self, oportunidade):
        """Executar trade real com autorização"""
        try:
            symbol = oportunidade['symbol']
            quantidade = oportunidade['quantidade']
            valor_estimado = oportunidade['valor']
            
            logger.info(f"[EXECUCAO AUTORIZADA] {symbol}")
            logger.info(f"  Quantidade: {quantidade}")
            logger.info(f"  Valor estimado: ${valor_estimado:.2f}")
            logger.info(f"  RSI: {oportunidade['rsi']:.1f}")
            
            # Preparar parâmetros para Binance
            params = {
                'symbol': symbol,
                'side': 'BUY',
                'type': 'MARKET',
                'quantity': str(quantidade)
            }
            
            logger.info(f"[PARAMETROS] {params}")
            logger.info("[ENVIANDO] Ordem para Binance API...")
            
            # EXECUTAR TRADE REAL
            resultado = self.trader_amos._request('POST', '/api/v3/order', params, signed=True)
            
            if resultado.get('error'):
                error_detail = resultado.get('detail', 'Erro desconhecido')
                logger.error(f"[ERRO API] {error_detail}")
                
                # Tentar diagnóstico adicional
                if '400' in str(error_detail):
                    logger.error("[DIAGNOSTICO] Erro 400 - possivel problema de parametros ou permissoes")
                
                return None
            
            # TRADE EXECUTADO COM SUCESSO!
            order_id = resultado.get('orderId')
            status = resultado.get('status')
            
            logger.info(f"[SUCESSO] Trade executado!")
            logger.info(f"  Order ID: {order_id}")
            logger.info(f"  Status: {status}")
            
            # Processar fills se disponíveis
            fills = resultado.get('fills', [])
            if fills:
                total_qty = 0
                total_value = 0
                
                for fill in fills:
                    qty = float(fill['qty'])
                    price = float(fill['price'])
                    total_qty += qty
                    total_value += qty * price
                
                preco_medio = total_value / total_qty if total_qty > 0 else 0
                
                logger.info(f"  Executado: {total_qty} {symbol.replace('USDT', '')}")
                logger.info(f"  Preco medio: ${preco_medio:.6f}")
                logger.info(f"  Valor total: ${total_value:.2f}")
                
                # Registrar trade
                trade_record = {
                    'timestamp': datetime.now().isoformat(),
                    'symbol': symbol,
                    'order_id': order_id,
                    'quantidade': total_qty,
                    'preco_medio': preco_medio,
                    'valor_total': total_value,
                    'rsi': oportunidade['rsi']
                }
                
                self.trades_executados.append(trade_record)
                
                # Verificar novo saldo
                time.sleep(2)  # Aguardar processamento
                novo_saldo = self.trader_amos.get_saldo_usdt()
                ganho = novo_saldo - self.saldo_inicial
                percentual = (ganho / self.saldo_inicial) * 100
                
                logger.info(f"[SALDO ATUALIZADO] ${novo_saldo:.2f}")
                logger.info(f"[GANHO TOTAL] ${ganho:+.2f} ({percentual:+.2f}%)")
                
                return trade_record
            
            return {'success': True, 'order_id': order_id}
            
        except Exception as e:
            logger.error(f"[EXCECAO] Erro durante execucao: {e}")
            return None
    
    def verificar_meta_atingida(self):
        """Verificar se a meta de ganhos foi atingida"""
        saldo_atual = self.trader_amos.get_saldo_usdt()
        
        if saldo_atual >= self.objetivo_ganho:
            ganho = saldo_atual - self.saldo_inicial
            percentual = (ganho / self.saldo_inicial) * 100
            
            logger.info(f"[META ATINGIDA] Objetivo de +8% alcancado!")
            logger.info(f"[RESULTADO] ${self.saldo_inicial:.2f} -> ${saldo_atual:.2f}")
            logger.info(f"[GANHO FINAL] ${ganho:+.2f} ({percentual:+.2f}%)")
            
            return True
        
        return False
    
    def executar_operacao_autorizada(self):
        """Executar operação com autorização do usuário"""
        logger.info("[INICIO] Operacao autorizada iniciada")
        
        tentativas = 0
        max_tentativas = 15
        
        while tentativas < max_tentativas:
            tentativas += 1
            
            logger.info(f"[TENTATIVA {tentativas}/{max_tentativas}]")
            
            # Verificar se meta já foi atingida
            if self.verificar_meta_atingida():
                logger.info("[CONCLUSAO] Meta de ganhos atingida!")
                break
            
            # Buscar oportunidade
            oportunidade = self.encontrar_oportunidade_real()
            
            if not oportunidade:
                logger.info("[AGUARDANDO] Sem oportunidades no momento")
                if tentativas < max_tentativas:
                    logger.info("Tentativa em 45 segundos...")
                    time.sleep(45)
                continue
            
            # Executar trade autorizado
            resultado = self.executar_trade_autorizado(oportunidade)
            
            if resultado:
                logger.info("[TRADE REALIZADO] Sucesso na execucao!")
                
                # Aguardar antes da próxima operação
                logger.info("Aguardando 2 minutos antes da proxima operacao...")
                time.sleep(120)
            else:
                logger.warning("[TRADE FALHOU] Tentativa nao bem-sucedida")
                if tentativas < max_tentativas:
                    logger.info("Nova tentativa em 60 segundos...")
                    time.sleep(60)
        
        # Relatório final
        self.gerar_relatorio_final()
    
    def gerar_relatorio_final(self):
        """Gerar relatório final da operação"""
        saldo_final = self.trader_amos.get_saldo_usdt()
        ganho_total = saldo_final - self.saldo_inicial
        percentual_final = (ganho_total / self.saldo_inicial) * 100
        
        logger.info("=" * 50)
        logger.info("RELATORIO FINAL - OPERACAO AUTORIZADA")
        logger.info("=" * 50)
        logger.info(f"Conta operada: CONTA_3 (Amos)")
        logger.info(f"Conta pausada: CONTA_2 (Paulo)")
        logger.info(f"Saldo inicial: ${self.saldo_inicial:.2f}")
        logger.info(f"Saldo final: ${saldo_final:.2f}")
        logger.info(f"Ganho/Perda: ${ganho_total:+.2f} ({percentual_final:+.2f}%)")
        logger.info(f"Meta objetivo: ${self.objetivo_ganho:.2f} (+8%)")
        logger.info(f"Trades executados: {len(self.trades_executados)}")
        
        if self.trades_executados:
            logger.info("Detalhes dos trades:")
            for i, trade in enumerate(self.trades_executados, 1):
                logger.info(f"  {i}. {trade['symbol']}: {trade['quantidade']:.6f} por ${trade['valor_total']:.2f}")
        
        # Salvar relatório em arquivo
        relatorio = {
            'timestamp_final': datetime.now().isoformat(),
            'conta_operada': 'CONTA_3_AMOS',
            'conta_pausada': 'CONTA_2_PAULO',
            'saldo_inicial': self.saldo_inicial,
            'saldo_final': saldo_final,
            'ganho_total': ganho_total,
            'percentual_ganho': percentual_final,
            'meta_objetivo': self.objetivo_ganho,
            'trades_executados': self.trades_executados
        }
        
        nome_arquivo = f"relatorio_amos_autorizado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Relatorio salvo: {nome_arquivo}")

def main():
    """Executar sistema autorizado"""
    try:
        print("\n" + "="*60)
        print("SISTEMA AUTORIZADO - TRADES REAIS")
        print("="*60)
        print("CONTA_3 (Amos): AUTORIZADA para trades reais")
        print("CONTA_2 (Paulo): PAUSADA ate segunda ordem")
        print("Objetivo: +8% de ganho com trades conservadores")
        print("="*60)
        
        confirmacao = input("Confirmar execucao com TRADES REAIS? (AUTORIZO): ")
        
        if confirmacao != 'AUTORIZO':
            logger.info("Operacao cancelada pelo usuario")
            return
        
        # Iniciar sistema autorizado
        sistema = AmosAutorizado()
        
        logger.info("[AUTORIZACAO CONFIRMADA] Iniciando trades reais...")
        
        sistema.executar_operacao_autorizada()
        
        logger.info("[SISTEMA FINALIZADO] Operacao autorizada concluida")
        
    except KeyboardInterrupt:
        logger.info("Sistema interrompido pelo usuario (Ctrl+C)")
    except Exception as e:
        logger.error(f"Erro critico no sistema: {e}")

if __name__ == "__main__":
    main()