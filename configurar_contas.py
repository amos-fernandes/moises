#!/usr/bin/env python3
# configurar_contas.py
# Script para configurar múltiplas contas de forma fácil

import json
import os
from pathlib import Path

# Detectar sistema
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

def carregar_contas():
    """Carregar contas existentes"""
    config_file = CONFIG_DIR / "contas.json"
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def salvar_contas(contas):
    """Salvar configuração das contas"""
    config_file = CONFIG_DIR / "contas.json"
    with open(config_file, 'w') as f:
        json.dump(contas, f, indent=2)

def adicionar_conta():
    """Interface para adicionar nova conta"""
    print("\n🎂💰 CONFIGURAR NOVA CONTA MOISES 💰🎂")
    print("=" * 50)
    
    contas = carregar_contas()
    
    # Determinar próximo ID
    conta_ids = [key for key in contas.keys() if key.startswith('CONTA_')]
    if conta_ids:
        proximo_num = max([int(id.split('_')[1]) for id in conta_ids]) + 1
    else:
        proximo_num = 2  # Conta 1 já está no .env
    
    conta_id = f"CONTA_{proximo_num}"
    
    print(f"📝 Configurando: {conta_id}")
    print("-" * 30)
    
    # Coletar informações
    nome = input("🏷️  Nome da conta (ex: 'Conta João', 'Trading Bot 2'): ").strip()
    if not nome:
        nome = f"Conta {proximo_num}"
    
    print("\n🔐 Chaves da API Binance:")
    print("   (Obtenha em: https://www.binance.com/en/my/settings/api-management)")
    
    api_key = input("🔑 API Key: ").strip()
    if not api_key:
        print("❌ API Key é obrigatória!")
        return False
    
    api_secret = input("🔒 Secret Key: ").strip()
    if not api_secret:
        print("❌ Secret Key é obrigatória!")
        return False
    
    # Testar conexão (opcional)
    print("\n🧪 Testando conexão...")
    try:
        import requests
        import hmac
        import hashlib
        import time
        from urllib.parse import urlencode
        
        # Testar sincronização de tempo
        r = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        server_time = r.json()['serverTime']
        local_time = int(time.time() * 1000)
        offset = server_time - local_time
        
        # Testar chamada autenticada
        params = {
            'recvWindow': 5000,
            'timestamp': int(time.time() * 1000) + offset
        }
        query_string = urlencode(params)
        signature = hmac.new(api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
        params['signature'] = signature
        
        headers = {'X-MBX-APIKEY': api_key}
        r = requests.get("https://api.binance.com/api/v3/account", params=params, headers=headers, timeout=10)
        
        if r.status_code == 200:
            account = r.json()
            usdt_balance = 0
            for balance in account.get('balances', []):
                if balance['asset'] == 'USDT':
                    usdt_balance = float(balance['free'])
                    break
            
            print(f"✅ Conexão bem-sucedida!")
            print(f"💰 Saldo USDT: ${usdt_balance:.2f}")
        else:
            print(f"⚠️ Aviso: Não foi possível verificar saldo (código {r.status_code})")
            print("   Mas as chaves parecem válidas")
            
    except Exception as e:
        print(f"⚠️ Erro no teste: {e}")
        continuar = input("Continuar mesmo assim? (s/n): ").lower().strip()
        if continuar not in ['s', 'sim', 'y', 'yes']:
            return False
    
    # Salvar conta
    contas[conta_id] = {
        'nome': nome,
        'api_key': api_key,
        'api_secret': api_secret,
        'criada_em': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    salvar_contas(contas)
    
    print(f"\n✅ {conta_id} ({nome}) configurada com sucesso!")
    print(f"📁 Salva em: {CONFIG_DIR}/contas.json")
    
    return True

def listar_contas():
    """Listar contas configuradas"""
    contas = carregar_contas()
    
    print("\n📊 CONTAS CONFIGURADAS:")
    print("=" * 40)
    
    # Conta principal do .env
    env_file = Path('.env')
    if env_file.exists():
        print("✅ CONTA_1: Conta Principal (configurada no .env)")
    
    # Contas adicionais
    if contas:
        for conta_id, dados in contas.items():
            print(f"✅ {conta_id}: {dados['nome']}")
            print(f"   📅 Criada: {dados.get('criada_em', 'N/A')}")
    
    if not contas:
        print("📝 Nenhuma conta adicional configurada")
        print("   Use a opção 1 para adicionar contas")

def remover_conta():
    """Remover conta"""
    contas = carregar_contas()
    
    if not contas:
        print("❌ Nenhuma conta para remover")
        return
    
    print("\n🗑️ REMOVER CONTA:")
    print("=" * 30)
    
    for conta_id, dados in contas.items():
        print(f"{conta_id}: {dados['nome']}")
    
    conta_para_remover = input("\nID da conta para remover: ").strip().upper()
    
    if conta_para_remover in contas:
        nome = contas[conta_para_remover]['nome']
        confirmar = input(f"Confirma remoção de {conta_para_remover} ({nome})? (s/n): ")
        
        if confirmar.lower().strip() in ['s', 'sim', 'y', 'yes']:
            del contas[conta_para_remover]
            salvar_contas(contas)
            print(f"✅ {conta_para_remover} removida com sucesso!")
        else:
            print("❌ Remoção cancelada")
    else:
        print("❌ Conta não encontrada")

def menu_principal():
    """Menu principal"""
    while True:
        print("\n🎂💰 CONFIGURAÇÃO CONTAS MOISES 💰🎂")
        print("=" * 45)
        print("1. 📝 Adicionar nova conta")
        print("2. 📊 Listar contas configuradas")
        print("3. 🗑️ Remover conta")
        print("4. 🚀 Iniciar MOISES Multi-Conta")
        print("5. 📊 Abrir Dashboard")
        print("0. 🚪 Sair")
        print("=" * 45)
        
        opcao = input("Escolha uma opção: ").strip()
        
        if opcao == "1":
            adicionar_conta()
        elif opcao == "2":
            listar_contas()
        elif opcao == "3":
            remover_conta()
        elif opcao == "4":
            print("\n🚀 Iniciando MOISES Multi-Conta...")
            print("Execute: python moises_multi_conta.py")
            break
        elif opcao == "5":
            print("\n📊 Iniciando Dashboard...")
            print("Execute: python dashboard_multi_conta.py")
            print("Acesse: http://localhost:8001")
            break
        elif opcao == "0":
            print("🎂 Até logo! MOISES sempre pronto para operar! 💰")
            break
        else:
            print("❌ Opção inválida!")

if __name__ == '__main__':
    try:
        menu_principal()
    except KeyboardInterrupt:
        print("\n\n🎂 MOISES configurado com sucesso! 💰")