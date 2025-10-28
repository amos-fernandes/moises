#!/usr/bin/env python3
"""
Teste Simples de Conexão e Saldos
"""

import json
import logging
from moises_estrategias_avancadas import TradingAvancado

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def teste_conexao_simples():
    """Teste básico de conexão"""
    print("=== TESTE DE CONEXÃO SIMPLES ===")
    
    try:
        # Carregar config
        with open('config/contas.json', 'r') as f:
            config = json.load(f)
        
        resultados = {}
        
        for nome, dados in config.items():
            print(f"\n[{nome.upper()}]")
            
            try:
                # Criar trader
                trader = TradingAvancado(
                    api_key=dados['api_key'],
                    api_secret=dados['api_secret'],
                    conta_nome=nome
                )
                
                # Testar sincronização
                sync_ok = trader.sync_time()
                print(f"  Sincronização: {'✅ OK' if sync_ok else '❌ ERRO'}")
                
                # Testar saldo
                try:
                    saldo = trader.get_saldo_usdt()
                    print(f"  Saldo USDT: ${saldo:.2f}")
                    
                    resultados[nome] = {
                        'status': 'OK',
                        'saldo': saldo,
                        'sync': sync_ok
                    }
                    
                except Exception as e:
                    print(f"  Erro no saldo: {e}")
                    resultados[nome] = {
                        'status': 'ERRO_SALDO',
                        'erro': str(e)
                    }
                
            except Exception as e:
                print(f"  Erro geral: {e}")
                resultados[nome] = {
                    'status': 'ERRO_CONEXAO',
                    'erro': str(e)
                }
        
        # Resumo
        print(f"\n=== RESUMO ===")
        total_saldo = 0
        contas_ok = 0
        
        for nome, resultado in resultados.items():
            if resultado['status'] == 'OK':
                saldo = resultado['saldo']
                total_saldo += saldo
                contas_ok += 1
                print(f"{nome}: ✅ ${saldo:.2f}")
            else:
                print(f"{nome}: ❌ {resultado['status']}")
        
        print(f"\nContas funcionando: {contas_ok}/{len(config)}")
        print(f"Saldo total: ${total_saldo:.2f}")
        
        if contas_ok > 0:
            print("\n✅ Sistema pronto para operar!")
            return True
        else:
            print("\n❌ Nenhuma conta funcionando!")
            return False
    
    except Exception as e:
        print(f"Erro crítico: {e}")
        return False

if __name__ == "__main__":
    teste_conexao_simples()