#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔐 CONFIGURAÇÃO DE API KEYS - MOISES TRADING REAL
==============================================
Sistema seguro para configurar conexão com Binance
Data: 24/10/2025 - Aniversário do MOISES
"""

import os
import sys
from pathlib import Path
from binance.client import Client
from binance.exceptions import BinanceAPIException
import json
from datetime import datetime

class BinanceSetup:
    def __init__(self):
        self.env_file = Path("d:/dev/moises/.env")
        self.config_file = Path("d:/dev/moises/config/binance_config.json")
        
    def create_env_template(self):
        """Cria template do arquivo .env"""
        env_template = '''# 🔐 CONFIGURAÇÃO BINANCE - MOISES TRADING
# ========================================
# ⚠️ NUNCA compartilhe essas informações!
# ⚠️ Mantenha este arquivo seguro e privado!

# API Keys da Binance (obtidas em https://www.binance.com/en/my/settings/api-management)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_key_here

# Configurações de Trading
TRADING_MODE=testnet  # testnet ou live
MAX_DAILY_TRADES=10
PROFIT_TARGET=0.01    # 1% por trade
HUMANITARIAN_ALLOCATION=0.20  # 20% para famílias

# Configurações de Segurança
ENABLE_WHITELIST=true
MAX_POSITION_SIZE=0.1  # 10% do capital por posição
STOP_LOSS_PERCENT=0.005  # 0.5% stop loss

# Notificações
TELEGRAM_BOT_TOKEN=optional_telegram_bot_token
TELEGRAM_CHAT_ID=optional_telegram_chat_id
'''
        
        if not self.env_file.exists():
            self.env_file.write_text(env_template, encoding='utf-8')
            print(f"✅ Template .env criado: {self.env_file}")
        else:
            print(f"⚠️ Arquivo .env já existe: {self.env_file}")
    
    def validate_api_keys(self, api_key, api_secret, testnet=True):
        """Valida as API keys com a Binance"""
        try:
            client = Client(api_key, api_secret, testnet=testnet)
            
            # Teste básico de conexão
            status = client.get_system_status()
            print(f"✅ Status do sistema: {status}")
            
            # Teste de permissões da conta
            account_info = client.get_account()
            print(f"✅ Tipo da conta: {account_info['accountType']}")
            print(f"✅ Permissões: {', '.join(account_info['permissions'])}")
            
            # Verificar saldos
            balances = [
                {
                    'asset': balance['asset'],
                    'free': float(balance['free']),
                    'locked': float(balance['locked'])
                }
                for balance in account_info['balances']
                if float(balance['free']) > 0 or float(balance['locked']) > 0
            ]
            
            print(f"\n💰 SALDOS DISPONÍVEIS:")
            print("-" * 30)
            for balance in balances[:10]:  # Mostrar apenas os 10 primeiros
                if balance['free'] > 0:
                    print(f"{balance['asset']}: {balance['free']:.8f}")
            
            return True, client, balances
            
        except BinanceAPIException as e:
            print(f"❌ Erro na API Binance: {e}")
            return False, None, None
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return False, None, None
    
    def interactive_setup(self):
        """Setup interativo das API keys"""
        print("🔐 CONFIGURAÇÃO INTERATIVA DAS API KEYS")
        print("=" * 45)
        
        # Instruções
        print("\n📋 INSTRUÇÕES:")
        print("1. Acesse: https://www.binance.com/en/my/settings/api-management")
        print("2. Crie uma nova API Key")
        print("3. Ative as permissões: 'Enable Spot & Margin Trading'")
        print("4. Configure whitelist de IPs (recomendado)")
        print("5. Cole as keys abaixo:\n")
        
        # Entrada das keys
        api_key = input("🔑 Cole sua BINANCE_API_KEY: ").strip()
        if not api_key or api_key == "your_api_key_here":
            print("❌ API Key inválida!")
            return False
        
        api_secret = input("🔐 Cole sua BINANCE_API_SECRET: ").strip()
        if not api_secret or api_secret == "your_secret_key_here":
            print("❌ API Secret inválida!")
            return False
        
        # Escolher modo
        print("\n🎯 MODO DE TRADING:")
        print("1. TESTNET (Recomendado para começar)")
        print("2. LIVE (Trading real)")
        
        mode_choice = input("Escolha (1 ou 2): ").strip()
        testnet_mode = mode_choice == "1"
        
        print(f"\n🔍 Validando API Keys ({'TESTNET' if testnet_mode else 'LIVE'})...")
        
        # Validar conexão
        is_valid, client, balances = self.validate_api_keys(api_key, api_secret, testnet_mode)
        
        if is_valid:
            # Salvar configuração
            self.save_configuration(api_key, api_secret, testnet_mode, balances)
            print("\n✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
            return True
        else:
            print("\n❌ CONFIGURAÇÃO FALHOU!")
            return False
    
    def save_configuration(self, api_key, api_secret, testnet_mode, balances):
        """Salva configuração de forma segura"""
        
        # Criar diretório config se não existir
        config_dir = Path("d:/dev/moises/config")
        config_dir.mkdir(exist_ok=True)
        
        # Atualizar arquivo .env
        env_content = f'''# 🔐 CONFIGURAÇÃO BINANCE - MOISES TRADING
# Data de configuração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
BINANCE_API_KEY={api_key}
BINANCE_API_SECRET={api_secret}
TRADING_MODE={'testnet' if testnet_mode else 'live'}
MAX_DAILY_TRADES=10
PROFIT_TARGET=0.01
HUMANITARIAN_ALLOCATION=0.20
ENABLE_WHITELIST=true
MAX_POSITION_SIZE=0.1
STOP_LOSS_PERCENT=0.005
'''
        
        self.env_file.write_text(env_content, encoding='utf-8')
        
        # Salvar configuração em JSON
        config = {
            "setup_date": datetime.now().isoformat(),
            "trading_mode": "testnet" if testnet_mode else "live",
            "account_validated": True,
            "initial_balances": balances,
            "moises_phase": "BEBÊ",
            "humanitarian_allocation": 20,
            "daily_trades_target": 2,
            "profit_per_trade_target": 1.0
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Configuração salva em: {self.config_file}")
        print(f"✅ Variáveis de ambiente em: {self.env_file}")
    
    def test_connection(self):
        """Testa conexão com configuração existente"""
        try:
            # Carregar variáveis do .env
            if not self.env_file.exists():
                print("❌ Arquivo .env não encontrado!")
                return False
            
            # Simular carregamento do .env (para demonstração)
            env_content = self.env_file.read_text(encoding='utf-8')
            
            if 'your_api_key_here' in env_content:
                print("⚠️ API Keys ainda não foram configuradas!")
                return False
            
            print("✅ Configuração encontrada!")
            print("🔍 Para testar a conexão, execute o trading real...")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao testar configuração: {e}")
            return False

def show_security_tips():
    """Mostra dicas de segurança importantes"""
    print("\n🛡️ DICAS DE SEGURANÇA IMPORTANTES:")
    print("=" * 40)
    print("✅ SEMPRE use whitelist de IPs")
    print("✅ NUNCA compartilhe suas API keys")
    print("✅ Use 2FA na sua conta Binance")
    print("✅ Monitore regularmente sua conta")
    print("✅ Comece sempre no TESTNET")
    print("✅ Use apenas capital que pode perder")
    print("⚠️ REVOGUE keys antigas periodicamente")
    print("⚠️ NUNCA faça commit das keys no Git")

def main():
    """Função principal de configuração"""
    print("🎂🔐 CONFIGURAÇÃO BINANCE - ANIVERSÁRIO DO MOISES 🔐🎂")
    print("=" * 55)
    print("🎯 Objetivo: Ativar trading real com $18.18 USDT")
    print("💝 Missão: 95% precisão + 20% impacto humanitário")
    print("=" * 55)
    
    setup = BinanceSetup()
    
    print("\n🚀 OPÇÕES DE CONFIGURAÇÃO:")
    print("1. 🔧 Configuração interativa (Recomendado)")
    print("2. 📝 Criar template .env")
    print("3. 🔍 Testar configuração existente")
    print("4. 🛡️ Dicas de segurança")
    
    choice = input("\nEscolha uma opção (1-4): ").strip()
    
    if choice == "1":
        setup.create_env_template()
        success = setup.interactive_setup()
        if success:
            show_security_tips()
            print("\n🎊 MOISES ESTÁ PRONTO PARA TRADING REAL!")
        
    elif choice == "2":
        setup.create_env_template()
        print("\n📝 Template criado! Edite o arquivo .env com suas keys.")
        
    elif choice == "3":
        setup.test_connection()
        
    elif choice == "4":
        show_security_tips()
        
    else:
        print("❌ Opção inválida!")

if __name__ == "__main__":
    main()