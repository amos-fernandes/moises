#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 VALIDAÇÃO DE PRODUÇÃO - MOISES
===============================
"""

import os
from pathlib import Path

def validate_production():
    """Valida se está tudo pronto"""
    print("🔍 VALIDANDO PRODUÇÃO - MOISES")
    print("=" * 35)
    
    issues = []
    
    # Verificar .env
    env_file = Path("d:/dev/moises/.env")
    if env_file.exists():
        content = env_file.read_text(encoding='utf-8')
        if 'SUA_API_KEY_AQUI' in content:
            issues.append("❌ API Keys não configuradas")
        else:
            print("✅ API Keys configuradas")
    else:
        issues.append("❌ Arquivo .env ausente")
    
    # Verificar estrutura
    dirs = ["config", "logs", "reports"]
    for dir_name in dirs:
        dir_path = Path(f"d:/dev/moises/{dir_name}")
        if dir_path.exists():
            print(f"✅ Diretório {dir_name}")
        else:
            issues.append(f"❌ Diretório {dir_name} ausente")
    
    # Status final
    print("\n" + "="*40)
    if not issues:
        print("🎉 PRODUÇÃO VALIDADA! 🎉")
        print("💝 MOISES pronto para ajudar crianças!")
    else:
        print("⚠️ PENDÊNCIAS:")
        for issue in issues:
            print(f"  {issue}")
    print("="*40)

if __name__ == "__main__":
    validate_production()
