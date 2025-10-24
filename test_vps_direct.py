"""
🔍 TESTE DIRETO VPS - VERIFICAÇÃO ENDPOINTS
Testa diretamente os endpoints da VPS com IP correto
"""

import requests
import json
from datetime import datetime

def test_vps_directly():
    """
    Teste direto dos endpoints da VPS
    """
    
    print("🔍 TESTE DIRETO VPS - VERIFICAÇÃO SISTEMA")
    print("=" * 60)
    
    # IPs possíveis da sua VPS Hostinger
    possible_ips = [
        "localhost",  # Se estiver na VPS
        "127.0.0.1", 
        # Adicione seu IP da VPS aqui quando souber
    ]
    
    port = 8001
    
    # Endpoints para testar
    endpoints = [
        "/health",
        "/api/neural/status", 
        "/api/evolution/status",
        "/api/trading/binance-status"
    ]
    
    print("🎯 Testando endpoints essenciais...")
    print("=" * 40)
    
    working_ip = None
    
    # Testar cada IP possível
    for ip in possible_ips:
        print(f"\n🔗 Testando IP: {ip}")
        
        try:
            base_url = f"http://{ip}:{port}"
            response = requests.get(f"{base_url}/health", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ CONEXÃO OK com {ip}!")
                working_ip = ip
                break
            else:
                print(f"❌ {ip} - Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ {ip} - Erro: {str(e)[:50]}...")
    
    if not working_ip:
        print("\n❌ NENHUM IP FUNCIONANDO")
        print("🔧 POSSÍVEIS SOLUÇÕES:")
        print("1. Verificar se containers estão rodando:")
        print("   docker ps")
        print("2. Verificar logs dos containers:")
        print("   docker logs neural-trading-api")
        print("3. Reiniciar containers se necessário:")
        print("   ./fix_containers_binance.sh")
        return False
    
    # Testar todos os endpoints com IP funcionando
    base_url = f"http://{working_ip}:{port}"
    
    print(f"\n🧪 TESTANDO ENDPOINTS EM {base_url}")
    print("=" * 40)
    
    results = {}
    
    for endpoint in endpoints:
        print(f"\n📡 {endpoint}")
        
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint] = {"status": "OK", "data": data}
                
                print("   ✅ OK")
                
                # Mostrar info relevante
                if endpoint == "/health":
                    print(f"   Status: {data.get('status', 'N/A')}")
                    print(f"   System Ready: {data.get('system_ready', False)}")
                    
                elif endpoint == "/api/neural/status":
                    learning = data.get('learning_status', {})
                    accuracy = learning.get('current_accuracy', 0)
                    print(f"   Accuracy: {accuracy:.1%}")
                    
                elif endpoint == "/api/evolution/status":
                    evolution = data.get('evolution_status', {})
                    phase = evolution.get('current_phase', 1)
                    target = evolution.get('target_accuracy', 0.85)
                    print(f"   Fase: {phase}, Target: {target:.1%}")
                    
                elif endpoint == "/api/trading/binance-status":
                    ready = data.get('ready_for_trading', False)
                    print(f"   Trading Ready: {ready}")
                    
            else:
                results[endpoint] = {"status": "ERROR", "code": response.status_code}
                print(f"   ❌ Erro {response.status_code}")
                
        except Exception as e:
            results[endpoint] = {"status": "FAILED", "error": str(e)}
            print(f"   ❌ Falha: {str(e)[:50]}...")
    
    # Resumo final
    print("\n" + "=" * 60)
    print("📊 RESUMO DO TESTE")
    print("=" * 60)
    
    working_endpoints = sum(1 for r in results.values() if r["status"] == "OK")
    total_endpoints = len(results)
    score = (working_endpoints / total_endpoints) * 100 if total_endpoints > 0 else 0
    
    print(f"🎯 SCORE: {working_endpoints}/{total_endpoints} ({score:.0f}%)")
    print(f"🌐 IP Funcional: {working_ip}")
    
    if score >= 75:
        print("\n🎉 SISTEMA PRONTO!")
        print("✅ Pode ativar evolução")
        
        evolution_command = f"curl -X POST {base_url}/api/evolution/start"
        print(f"\n🚀 COMANDO:")
        print(f"   {evolution_command}")
        
        return True
        
    else:
        print(f"\n⚠️ SISTEMA PARCIAL ({score:.0f}%)")
        print("🔧 Alguns endpoints precisam de atenção")
        
        return False

if __name__ == "__main__":
    success = test_vps_directly()
    
    if success:
        print(f"\n✅ VERIFICAÇÃO: APROVADO!")
    else:
        print(f"\n❌ VERIFICAÇÃO: Ajustes necessários")