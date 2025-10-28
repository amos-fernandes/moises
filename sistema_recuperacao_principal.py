#!/usr/bin/env python3
"""
RECUPERAÇÃO INTELIGENTE DE PERDAS - SISTEMA PRINCIPAL
Versão Segura para Recuperar -15.82% e Gerar Lucros Diários

CARACTERÍSTICAS:
- Validação completa antes de operar
- Estratégias específicas por conta
- Monitoramento contínuo de performance
- Paradas automáticas de segurança
- Logging detalhado de todas as operações
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta

# Adicionar diretório atual ao path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configurar logging avançado
log_filename = f"recuperacao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class SistemaRecuperacao:
    def __init__(self):
        """Inicializar sistema de recuperação completo"""
        self.inicio_operacao = datetime.now()
        self.stats = {
            'trades_executados': 0,
            'trades_vencedores': 0,
            'lucro_total': 0,
            'maior_perda': 0,
            'maior_ganho': 0
        }
        
        # Metas específicas
        self.metas = {
            'paulo': {
                'saldo_inicial': 13.88,
                'perda_atual': -15.82,
                'meta_recuperacao': 16.0,  # Recuperar e ainda ter lucro
                'risco_maximo': 0.05       # 5% por trade máximo
            },
            'amos': {
                'saldo_inicial': 4.96,
                'meta_crescimento': 6.0,   # 20% de crescimento
                'risco_maximo': 0.03       # 3% por trade máximo
            }
        }
        
        logger.info("=== SISTEMA DE RECUPERAÇÃO INTELIGENTE INICIADO ===")
        logger.info(f"Horário de início: {self.inicio_operacao}")
        logger.info(f"Meta Paulo: Recuperar ${self.metas['paulo']['meta_recuperacao']}")
        logger.info(f"Meta Amos: Crescer para ${self.metas['amos']['meta_crescimento']}")
    
    def validar_sistema(self):
        """Validação completa antes de iniciar"""
        logger.info("[ETAPA 1] Validando sistema...")
        
        try:
            # Importar e executar validação
            from teste_sistema_recuperacao import relatorio_completo
            relatorio, sistema_ok = relatorio_completo()
            
            if not sistema_ok:
                logger.error("Sistema não passou na validação!")
                return False
            
            logger.info("✅ Sistema validado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro na validação: {e}")
            return False
    
    def executar_recuperacao_controlada(self):
        """Executar recuperação com controles de segurança"""
        logger.info("[ETAPA 2] Iniciando recuperação controlada...")
        
        try:
            from estrategias_recuperacao import EstrategiasRecuperacao
            
            recuperacao = EstrategiasRecuperacao()
            recuperacao.inicializar_traders()
            
            if not recuperacao.traders:
                logger.error("Nenhum trader disponível!")
                return False
            
            # Executar ciclos com paradas de segurança
            max_ciclos = 50  # Máximo 50 ciclos por sessão
            ciclo_atual = 1
            
            while ciclo_atual <= max_ciclos:
                logger.info(f"[CICLO {ciclo_atual}/{max_ciclos}] Executando...")
                
                # Verificar condições de parada
                if self.verificar_paradas_seguranca(recuperacao):
                    logger.info("Condição de parada ativada!")
                    break
                
                # Executar ciclo
                resultado = recuperacao.executar_ciclo_recuperacao()
                
                # Atualizar estatísticas
                self.atualizar_stats(resultado)
                
                # Verificar se metas foram atingidas
                if self.verificar_metas_atingidas(resultado):
                    logger.info("🎉 METAS ATINGIDAS! Operação concluída com sucesso!")
                    break
                
                # Pausa adaptativa entre ciclos
                pausa = self.calcular_pausa_ciclo(ciclo_atual, resultado)
                logger.info(f"Próximo ciclo em {pausa}s...")
                time.sleep(pausa)
                
                ciclo_atual += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Erro durante recuperação: {e}")
            return False
    
    def verificar_paradas_seguranca(self, recuperacao):
        """Verificar condições de parada de segurança"""
        for nome, trader in recuperacao.traders.items():
            try:
                saldo_atual = trader.get_saldo_usdt()
                meta_config = self.metas.get(nome, {})
                
                # Parada por perda excessiva (mais de 20% adicional)
                if nome == 'paulo':
                    if saldo_atual < 10:  # Menos de $10 restantes
                        logger.warning(f"[PARADA] {nome}: Saldo muito baixo (${saldo_atual})")
                        return True
                
                # Parada por tempo (máximo 6 horas de operação)
                if datetime.now() - self.inicio_operacao > timedelta(hours=6):
                    logger.info("[PARADA] Tempo máximo de operação atingido (6h)")
                    return True
                    
            except Exception as e:
                logger.error(f"Erro ao verificar paradas para {nome}: {e}")
        
        return False
    
    def verificar_metas_atingidas(self, resultado):
        """Verificar se as metas foram atingidas"""
        if not resultado or 'contas' not in resultado:
            return False
        
        metas_ok = True
        
        for nome, dados in resultado['contas'].items():
            saldo = dados.get('saldo_atual', 0)
            meta_config = self.metas.get(nome, {})
            
            if nome == 'paulo':
                meta = meta_config.get('meta_recuperacao', 16)
                if saldo < meta:
                    metas_ok = False
                else:
                    logger.info(f"✅ {nome}: Meta atingida! ${saldo:.2f} >= ${meta}")
            
            elif nome == 'amos':
                meta = meta_config.get('meta_crescimento', 6)
                if saldo < meta:
                    metas_ok = False
                else:
                    logger.info(f"✅ {nome}: Meta atingida! ${saldo:.2f} >= ${meta}")
        
        return metas_ok
    
    def calcular_pausa_ciclo(self, ciclo, resultado):
        """Calcular pausa adaptativa entre ciclos"""
        # Pausa base
        pausa_base = 180  # 3 minutos
        
        # Ajustar baseado no sucesso
        if resultado and 'contas' in resultado:
            # Se houve trades bem-sucedidos, pausa menor
            total_saldo = sum(c.get('saldo_atual', 0) for c in resultado['contas'].values())
            if total_saldo > 20:  # Se saldo total cresceu
                pausa_base = 120  # 2 minutos
        
        # Pausa maior à noite (entre 22h e 6h)
        hora_atual = datetime.now().hour
        if hora_atual >= 22 or hora_atual <= 6:
            pausa_base *= 2
        
        return pausa_base
    
    def atualizar_stats(self, resultado):
        """Atualizar estatísticas da operação"""
        if not resultado or 'contas' not in resultado:
            return
        
        # Calcular progresso total
        saldo_total = sum(c.get('saldo_atual', 0) for c in resultado['contas'].values())
        
        # Atualizar stats
        self.stats['saldo_total_atual'] = saldo_total
        
        # Log de progresso
        tempo_operacao = datetime.now() - self.inicio_operacao
        logger.info(f"[STATS] Saldo Total: ${saldo_total:.2f} | Tempo: {tempo_operacao}")
    
    def gerar_relatorio_final(self):
        """Gerar relatório final da operação"""
        logger.info("=== RELATÓRIO FINAL DA OPERAÇÃO ===")
        
        tempo_total = datetime.now() - self.inicio_operacao
        
        relatorio = {
            'inicio_operacao': self.inicio_operacao.isoformat(),
            'fim_operacao': datetime.now().isoformat(),
            'duracao_total': str(tempo_total),
            'estatisticas': self.stats,
            'metas': self.metas
        }
        
        # Salvar relatório
        nome_relatorio = f"relatorio_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(nome_relatorio, 'w', encoding='utf-8') as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Relatório salvo: {nome_relatorio}")
        logger.info(f"Duração total: {tempo_total}")
        logger.info(f"Trades executados: {self.stats.get('trades_executados', 0)}")
        
        return relatorio

def main():
    """Função principal - Execução segura e controlada"""
    sistema = SistemaRecuperacao()
    
    try:
        # Etapa 1: Validação
        if not sistema.validar_sistema():
            logger.error("❌ Sistema falhou na validação. Abortando.")
            return
        
        # Confirmação do usuário
        print("\n" + "="*60)
        print("SISTEMA DE RECUPERAÇÃO PRONTO")
        print("="*60)
        print(f"Meta Paulo: Recuperar para ${sistema.metas['paulo']['meta_recuperacao']}")
        print(f"Meta Amos: Crescer para ${sistema.metas['amos']['meta_crescimento']}")
        print("="*60)
        
        confirmacao = input("Confirma início da operação? (digite 'CONFIRMO'): ")
        
        if confirmacao != 'CONFIRMO':
            logger.info("Operação cancelada pelo usuário")
            return
        
        # Etapa 2: Execução
        logger.info("🚀 INICIANDO RECUPERAÇÃO REAL...")
        sucesso = sistema.executar_recuperacao_controlada()
        
        if sucesso:
            logger.info("✅ Recuperação concluída!")
        else:
            logger.error("❌ Recuperação falhou")
    
    except KeyboardInterrupt:
        logger.info("Operação interrompida pelo usuário (Ctrl+C)")
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
    finally:
        # Sempre gerar relatório final
        sistema.gerar_relatorio_final()
        logger.info("=== SISTEMA ENCERRADO ===")

if __name__ == "__main__":
    main()