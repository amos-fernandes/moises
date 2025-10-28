#!/usr/bin/env python3
"""
Teste de Validação do Sistema de Recuperação
Verifica se todas as funções estão funcionando antes de operar
"""

import json
import logging
import time
from estrategias_recuperacao import EstrategiasRecuperacao

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def teste_conexoes():
    """Testar conexões com todas as contas"""
    logger.info("=== TESTE DE CONEXÕES ===")
    
    recuperacao = EstrategiasRecuperacao()
    recuperacao.inicializar_traders()
    
    resultados = {}
    
    for nome, trader in recuperacao.traders.items():
        try:
            # Testar sincronização de tempo
            sync_ok = trader.sync_time()
            
            # Testar obtenção de saldo
            saldo = trader.get_saldo_usdt()
            
            # Testar análise de mercado
            oportunidade = trader.analisar_mercado_completo()
            
            resultados[nome] = {
                'conexao': 'OK',
                'sync_tempo': 'OK' if sync_ok else 'ERRO',
                'saldo': f'${saldo:.2f}',
                'analise_mercado': 'OK' if oportunidade else 'ERRO'
            }
            
            logger.info(f"[{nome.upper()}] Conexão: OK | Saldo: ${saldo:.2f}")
            
        except Exception as e:
            resultados[nome] = {
                'conexao': 'ERRO',
                'erro': str(e)
            }
            logger.error(f"[{nome.upper()}] ERRO: {e}")
    
    return resultados

def teste_analise_mercado():
    """Testar análise de mercado em vários símbolos"""
    logger.info("=== TESTE DE ANÁLISE DE MERCADO ===")
    
    recuperacao = EstrategiasRecuperacao()
    recuperacao.inicializar_traders()
    
    if not recuperacao.traders:
        logger.error("Nenhum trader disponível")
        return {}
    
    # Usar Paulo para teste
    trader = list(recuperacao.traders.values())[0]
    simbolos_teste = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOGEUSDT']
    
    resultados = {}
    
    for symbol in simbolos_teste:
        try:
            # Análise simplificada para teste
            candles = trader.get_candles_rapidos(symbol, '5m', 20)
            if candles:
                prices = [c['close'] for c in candles]
                rsi = trader.calcular_rsi_rapido(prices)
                oportunidade = {
                    'confidence': max(50, min(95, rsi + 20)),
                    'estrategia': 'teste_rapido',
                    'entry_price': candles[-1]['close'] if candles else 0
                }
            else:
                oportunidade = None
            
            if oportunidade:
                resultados[symbol] = {
                    'status': 'ANALISADO',
                    'confidence': oportunidade.get('confidence', 0),
                    'estrategia': oportunidade.get('estrategia', 'N/A'),
                    'entry_price': oportunidade.get('entry_price', 0),
                    'recomendacao': 'COMPRAR' if oportunidade.get('confidence', 0) >= 85 else 'AGUARDAR'
                }
                
                logger.info(f"[{symbol}] Confiança: {oportunidade.get('confidence', 0):.1f}% | "
                          f"Estratégia: {oportunidade.get('estrategia', 'N/A')}")
            else:
                resultados[symbol] = {
                    'status': 'SEM_OPORTUNIDADE',
                    'recomendacao': 'AGUARDAR'
                }
                logger.info(f"[{symbol}] Sem oportunidades no momento")
        
        except Exception as e:
            resultados[symbol] = {
                'status': 'ERRO',
                'erro': str(e)
            }
            logger.error(f"[{symbol}] Erro na análise: {e}")
        
        time.sleep(1)  # Pausa entre análises
    
    return resultados

def teste_calculo_tamanhos():
    """Testar cálculos de tamanho de posição"""
    logger.info("=== TESTE DE CÁLCULO DE TAMANHOS ===")
    
    recuperacao = EstrategiasRecuperacao()
    recuperacao.inicializar_traders()
    
    resultados = {}
    
    for nome, trader in recuperacao.traders.items():
        try:
            saldo_atual = trader.get_saldo_usdt()
            
            # Testar diferentes cenários
            cenarios = [
                {'confidence': 95, 'entry_price': 50000, 'stop_loss': 49000},
                {'confidence': 88, 'entry_price': 3000, 'stop_loss': 2950},
                {'confidence': 85, 'entry_price': 0.5, 'stop_loss': 0.48}
            ]
            
            tamanhos = []
            
            for cenario in cenarios:
                tamanho = trader.calcular_tamanho_agressivo(
                    saldo_atual,
                    cenario['confidence'],
                    cenario['entry_price'],
                    cenario['stop_loss']
                )
                
                tamanhos.append({
                    'confidence': cenario['confidence'],
                    'tamanho_calculado': tamanho,
                    'percentual_saldo': (tamanho / saldo_atual) * 100 if saldo_atual > 0 else 0
                })
                
                logger.info(f"[{nome.upper()}] Confiança {cenario['confidence']}%: "
                          f"${tamanho:.2f} ({(tamanho/saldo_atual)*100:.1f}% do saldo)")
            
            resultados[nome] = {
                'saldo_atual': saldo_atual,
                'tamanhos_calculados': tamanhos
            }
            
        except Exception as e:
            resultados[nome] = {
                'erro': str(e)
            }
            logger.error(f"[{nome.upper()}] Erro no cálculo: {e}")
    
    return resultados

def relatorio_completo():
    """Gerar relatório completo de validação"""
    logger.info("=== RELATÓRIO COMPLETO DE VALIDAÇÃO ===")
    
    relatorio = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'teste_conexoes': teste_conexoes(),
        'teste_analise_mercado': teste_analise_mercado(),
        'teste_calculo_tamanhos': teste_calculo_tamanhos()
    }
    
    # Salvar relatório
    nome_arquivo = f"validacao_sistema_{time.strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Relatório salvo em: {nome_arquivo}")
    
    # Resumo de validação
    conexoes_ok = sum(1 for r in relatorio['teste_conexoes'].values() if r.get('conexao') == 'OK')
    total_contas = len(relatorio['teste_conexoes'])
    
    analises_ok = sum(1 for r in relatorio['teste_analise_mercado'].values() if r.get('status') == 'ANALISADO')
    total_simbolos = len(relatorio['teste_analise_mercado'])
    
    logger.info(f"[RESUMO] Conexões: {conexoes_ok}/{total_contas} OK")
    logger.info(f"[RESUMO] Análises: {analises_ok}/{total_simbolos} OK")
    
    # Verificar se sistema está pronto
    sistema_pronto = (conexoes_ok == total_contas and analises_ok > 0)
    
    if sistema_pronto:
        logger.info("[VALIDAÇÃO] ✅ SISTEMA PRONTO PARA OPERAÇÃO!")
    else:
        logger.warning("[VALIDAÇÃO] ❌ Sistema precisa de correções antes de operar")
    
    return relatorio, sistema_pronto

def main():
    """Executar todos os testes"""
    try:
        relatorio, sistema_ok = relatorio_completo()
        
        if sistema_ok:
            resposta = input("\n✅ Sistema validado! Deseja iniciar a recuperação? (s/n): ")
            
            if resposta.lower() == 's':
                logger.info("Iniciando sistema de recuperação...")
                from estrategias_recuperacao import main as main_recuperacao
                main_recuperacao()
            else:
                logger.info("Operação cancelada pelo usuário")
        else:
            logger.error("❌ Sistema não validado. Corrija os erros antes de prosseguir.")
    
    except Exception as e:
        logger.error(f"Erro durante validação: {e}")

if __name__ == "__main__":
    main()