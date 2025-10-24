"""
🔍 VERIFICAÇÃO COMPLETA DO SISTEMA - READY CHECK
Validação final antes de ativar evolução para 85%
"""

import asyncio
import requests
import json
from datetime import datetime

def check_system_status():
    """
    Verificação completa do sistema antes da evolução
    """
    
    print("🔍 VERIFICAÇÃO COMPLETA DO SISTEMA")
    print("=" * 60)
    print("🎯 Objetivo: Validar tudo antes da evolução 85%")
    print("⏰ Momento:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # Configuração da VPS (substitua pelo seu IP)
    VPS_IP = "2a02:4780:41:e6ee::1"  # Seu IP da VPS
    BASE_URL = f"http://{VPS_IP}:8001"
    
    results = {
        "vps_connection": False,
        "health_check": False,
        "neural_status": False,
        "evolution_ready": False,
        "binance_integration": False,
        "system_score": 0
    }
    
    print("🌐 1. TESTANDO CONEXÃO VPS...")
    print("-" * 40)
    
    try:
        # Teste básico de conectividade
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            results["vps_connection"] = True
            results["health_check"] = True
            
            print("✅ VPS Online e respondendo")
            print(f"   Status: {health_data.get('status', 'unknown')}")
            print(f"   System Ready: {health_data.get('system_ready', False)}")
            print(f"   Learning Active: {health_data.get('learning_active', False)}")
            
        else:
            print(f"❌ VPS respondeu com erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro conectando VPS: {e}")
        print("⚠️  Verifique se containers estão rodando")
    
    print("\n🧠 2. TESTANDO STATUS NEURAL...")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/neural/status", timeout=10)
        if response.status_code == 200:
            neural_data = response.json()
            results["neural_status"] = True
            
            learning_status = neural_data.get('learning_status', {})
            current_accuracy = learning_status.get('current_accuracy', 0)
            
            print("✅ Sistema Neural Operacional")
            print(f"   Accuracy Atual: {current_accuracy:.1%}")
            print(f"   Experiências: {learning_status.get('total_experiences', 0)}")
            print(f"   Sessões Training: {learning_status.get('training_sessions', 0)}")
            
            if current_accuracy >= 0.45:  # Base mínima
                print("✅ Accuracy base adequada para evolução")
            else:
                print("⚠️  Accuracy baixa - pode precisar treinar mais")
                
        else:
            print(f"❌ Neural status erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro neural status: {e}")
    
    print("\n🎯 3. TESTANDO SISTEMA DE EVOLUÇÃO...")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/evolution/status", timeout=10)
        if response.status_code == 200:
            evolution_data = response.json()
            results["evolution_ready"] = True
            
            evolution_status = evolution_data.get('evolution_status', {})
            
            print("✅ Sistema de Evolução Pronto")
            print(f"   Fase Atual: {evolution_status.get('current_phase', 1)}")
            print(f"   Target: {evolution_status.get('target_accuracy', 0.85):.1%}")
            print(f"   Progresso: {evolution_status.get('progress_percentage', 0):.1%}")
            
            components = evolution_status.get('components_status', {})
            for component, status in components.items():
                status_icon = "✅" if status == "active" else "⏳"
                print(f"   {status_icon} {component}: {status}")
                
        else:
            print(f"❌ Evolution status erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro evolution status: {e}")
    
    print("\n💰 4. TESTANDO INTEGRAÇÃO BINANCE...")
    print("-" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/trading/binance-status", timeout=10)
        if response.status_code == 200:
            binance_data = response.json()
            
            binance_connection = binance_data.get('binance_connection', {})
            ready_for_trading = binance_data.get('ready_for_trading', False)
            
            if ready_for_trading:
                results["binance_integration"] = True
                print("✅ Binance Integração OK")
                print(f"   Conectado: {binance_connection.get('binance_connected', False)}")
                print(f"   Score: {binance_connection.get('connectivity_score', 0):.1%}")
                print(f"   Ready Trading: {ready_for_trading}")
            else:
                print("⚠️  Binance integração pendente")
                print("   Execute teste Binance primeiro")
                
        else:
            print(f"❌ Binance status erro: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erro binance status: {e}")
    
    # Calcular score geral
    total_checks = len(results) - 1  # Excluir system_score
    passed_checks = sum(1 for k, v in results.items() if k != "system_score" and v)
    results["system_score"] = (passed_checks / total_checks) * 100
    
    print("\n" + "=" * 60)
    print("📊 RESULTADO DA VERIFICAÇÃO")
    print("=" * 60)
    
    score = results["system_score"]
    
    print(f"🎯 SCORE GERAL: {score:.0f}%")
    print()
    
    for check, status in results.items():
        if check != "system_score":
            icon = "✅" if status else "❌"
            check_name = check.replace("_", " ").title()
            print(f"{icon} {check_name}: {'OK' if status else 'FALHOU'}")
    
    print()
    
    if score >= 80:
        print("🎉 SISTEMA PRONTO PARA EVOLUÇÃO!")
        print("✅ Todos os componentes principais funcionando")
        print("🚀 Pode executar: curl -X POST http://IP:8001/api/evolution/start")
        
        evolution_command = f"curl -X POST {BASE_URL}/api/evolution/start"
        print(f"\n💡 COMANDO EXATO:")
        print(f"   {evolution_command}")
        
    elif score >= 60:
        print("⚠️  SISTEMA PARCIALMENTE PRONTO")
        print("🔧 Alguns ajustes podem ser necessários")
        print("📋 Verifique os itens que falharam acima")
        
    else:
        print("❌ SISTEMA NÃO PRONTO")
        print("🛠️  Necessário corrigir problemas antes da evolução")
        print("📞 Execute fixes dos containers e teste novamente")
    
    print(f"\n⏰ Verificação concluída: {datetime.now().strftime('%H:%M:%S')}")
    
    return results

if __name__ == "__main__":
    print("🔍 Iniciando verificação completa do sistema...")
    
    results = check_system_status()
    
    if results["system_score"] >= 80:
        print(f"\n🎯 RESULTADO: SISTEMA APROVADO!")
        print("🚀 Ready para evolução 85%!")
    else:
        print(f"\n⚠️ RESULTADO: Ajustes necessários")
        print("🔧 Score atual:", f"{results['system_score']:.0f}%")