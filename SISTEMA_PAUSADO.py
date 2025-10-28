#!/usr/bin/env python3
"""
SISTEMA PAUSADO - NÃO OPERAR

Por instrução do usuário:
- Não continuar trabalhando com ganhos na conta Amos
- Paralisar operações com a conta Paulo  
- Não fazer simulações

Este arquivo marca que o sistema está PAUSADO.
Data: 27/10/2025
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("="*60)
    logger.info("SISTEMA DE TRADING PAUSADO POR INSTRUÇÃO DO USUÁRIO")
    logger.info("="*60)
    logger.info("- Operações com conta Paulo: PARALISADAS")
    logger.info("- Operações com conta Amos: PARALISADAS") 
    logger.info("- Simulações: DESABILITADAS")
    logger.info("="*60)
    logger.info("Status: TODOS OS SISTEMAS PAUSADOS")
    logger.info("Data: 27/10/2025")
    logger.info("="*60)
    
    print("\n🚫 SISTEMA PAUSADO - NENHUMA OPERAÇÃO SERÁ EXECUTADA")
    return False

if __name__ == "__main__":
    main()