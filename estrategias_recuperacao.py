#!/usr/bin/env python3
"""
Estratégias Específicas de Recuperação de Perdas
Sistema focado em reverter -15.82% de perdas com segurança
"""

import json
import time
import logging
from datetime import datetime, timedelta
from moises_estrategias_avancadas import TradingAvancado

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s',
                   handlers=[
                       logging.FileHandler('recuperacao.log', encoding='utf-8'),
                       logging.StreamHandler()
                   ])
logger = logging.getLogger(__name__)

class EstrategiasRecuperacao:
    def __init__(self):
        """Inicializar sistema de recuperação"""
        self.config = self.carregar_config()
        self.traders = {}
        self.meta_diaria = {
            'paulo': 0.05,   # 5% ao dia para recuperar rapidamente
            'amos': 0.04     # 4% ao dia para segurança
        }
        self.perdas_iniciais = {
            'paulo': -15.82,  # Perdas reportadas
            'amos': 0         # Assumindo estável
        }
        
    def carregar_config(self):
        """Carregar configuração das contas"""
        try:
            with open('config/contas.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar config: {e}")
            return {}
    
    def inicializar_traders(self):
        """Inicializar traders para cada conta"""
        for nome_conta, dados in self.config.items():
            try:
                trader = TradingAvancado(
                    api_key=dados['api_key'],
                    api_secret=dados['api_secret'],
                    conta_nome=nome_conta
                )
                self.traders[nome_conta] = trader
                logger.info(f"[SUCESSO] Trader {nome_conta} inicializado")
                
            except Exception as e:
                logger.error(f"[ERRO] Falha ao inicializar {nome_conta}: {e}")
    
    def estrategia_paulo_recuperacao(self):
        """Estratégia específica para recuperar Paulo (-15.82%)"""
        trader = self.traders.get('paulo')
        if not trader:
            return
        
        logger.info(f"[PAULO] Iniciando recuperação agressiva (-15.82%)")
        
        # Símbolos com boa volatilidade para recuperação rápida
        simbolos_alvo = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOGEUSDT']
        
        for symbol in simbolos_alvo:
            try:
                # Análise rápida para oportunidades
                mercado = trader.analisar_mercado_completo()
                oportunidade = mercado.get(symbol) if mercado else None
                
                if oportunidade and oportunidade.get('confidence', 0) >= 88:
                    logger.info(f"[PAULO] Oportunidade encontrada em {symbol}: {oportunidade['confidence']:.1f}%")
                    
                    # Executar com tamanho calculado para recuperação
                    resultado = trader.executar_trade_inteligente(oportunidade, symbol)
                    
                    if resultado:
                        logger.info(f"[PAULO] Trade executado: {resultado}")
                        time.sleep(5)  # Pausa entre trades
                    else:
                        logger.warning(f"[PAULO] Trade falhou para {symbol}")
                
                time.sleep(2)  # Pausa entre análises
                
            except Exception as e:
                logger.error(f"[PAULO] Erro em {symbol}: {e}")
                continue
    
    def estrategia_amos_crescimento(self):
        """Estratégia conservadora para Amos gerar lucro"""
        trader = self.traders.get('amos')
        if not trader:
            return
        
        logger.info(f"[AMOS] Estratégia de crescimento conservadora")
        
        # Símbolos mais estáveis para crescimento seguro
        simbolos_seguros = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        for symbol in simbolos_seguros:
            try:
                mercado = trader.analisar_mercado_completo()
                oportunidade = mercado.get(symbol) if mercado else None
                
                # Critério mais rigoroso para Amos (mais conservador)
                if oportunidade and oportunidade.get('confidence', 0) >= 92:
                    logger.info(f"[AMOS] Oportunidade alta confiança {symbol}: {oportunidade['confidence']:.1f}%")
                    
                    resultado = trader.executar_trade_inteligente(oportunidade, symbol)
                    
                    if resultado:
                        logger.info(f"[AMOS] Trade conservador executado: {resultado}")
                        time.sleep(10)  # Pausa maior entre trades
                
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"[AMOS] Erro em {symbol}: {e}")
                continue
    
    def monitorar_progresso(self):
        """Monitorar progresso da recuperação"""
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'contas': {}
        }
        
        for nome, trader in self.traders.items():
            try:
                saldo_atual = trader.get_saldo_usdt()
                
                # Calcular progresso
                perda_inicial = self.perdas_iniciais.get(nome, 0)
                progresso = ((saldo_atual - perda_inicial) / abs(perda_inicial)) * 100 if perda_inicial != 0 else 0
                
                relatorio['contas'][nome] = {
                    'saldo_atual': saldo_atual,
                    'perda_inicial': perda_inicial,
                    'progresso_recuperacao': progresso,
                    'meta_diaria': self.meta_diaria.get(nome, 0) * 100
                }
                
                logger.info(f"[{nome.upper()}] Saldo: ${saldo_atual:.2f} | Progresso: {progresso:.2f}%")
                
            except Exception as e:
                logger.error(f"Erro ao monitorar {nome}: {e}")
        
        # Salvar relatório
        with open(f"relatorio_recuperacao_{datetime.now().strftime('%Y%m%d_%H%M')}.json", 'w') as f:
            json.dump(relatorio, f, indent=2)
        
        return relatorio
    
    def executar_ciclo_recuperacao(self):
        """Executar um ciclo completo de recuperação"""
        logger.info("=== INICIANDO CICLO DE RECUPERAÇÃO ===")
        
        # Monitorar estado inicial
        self.monitorar_progresso()
        
        # Executar estratégias simultaneamente
        try:
            # Paulo - Recuperação agressiva
            self.estrategia_paulo_recuperacao()
            
            # Pausa entre contas
            time.sleep(10)
            
            # Amos - Crescimento conservador
            self.estrategia_amos_crescimento()
            
        except Exception as e:
            logger.error(f"Erro durante ciclo: {e}")
        
        # Monitorar resultado
        relatorio_final = self.monitorar_progresso()
        
        logger.info("=== CICLO DE RECUPERAÇÃO CONCLUÍDO ===")
        return relatorio_final

def main():
    """Função principal - execução contínua"""
    recuperacao = EstrategiasRecuperacao()
    
    # Inicializar traders
    recuperacao.inicializar_traders()
    
    if not recuperacao.traders:
        logger.error("Nenhum trader inicializado. Abortando.")
        return
    
    # Executar ciclos de recuperação
    ciclo = 1
    
    while True:
        try:
            logger.info(f"[CICLO {ciclo}] Iniciando recuperação...")
            
            resultado = recuperacao.executar_ciclo_recuperacao()
            
            # Verificar se atingiu metas
            paulo_saldo = resultado['contas'].get('paulo', {}).get('saldo_atual', 0)
            amos_saldo = resultado['contas'].get('amos', {}).get('saldo_atual', 0)
            
            # Se Paulo recuperou e Amos cresceu, reduzir frequência
            if paulo_saldo > 15 and amos_saldo > 6:
                logger.info("[SUCESSO] Metas parciais atingidas! Reduzindo frequência...")
                time.sleep(600)  # 10 minutos entre ciclos
            else:
                logger.info("[CONTINUANDO] Executando próximo ciclo em 3 minutos...")
                time.sleep(180)  # 3 minutos entre ciclos
            
            ciclo += 1
            
        except KeyboardInterrupt:
            logger.info("Recuperação interrompida pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no ciclo {ciclo}: {e}")
            time.sleep(300)  # 5 minutos em caso de erro
            ciclo += 1

if __name__ == "__main__":
    main()