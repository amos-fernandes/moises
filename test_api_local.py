"""
🚀 TESTE LOCAL DA API CORRIGIDA
Testa a aplicação FastAPI com as correções aplicadas
"""

import os
import sys
import asyncio
import uvicorn
from multiprocessing import Process
import time
import requests
import json

# Configurar paths
sys.path.append(os.path.dirname(__file__))

def start_api_server():
    """Inicia o servidor API em processo separado"""
    os.chdir("d:/dev/moises")
    os.environ["PYTHONPATH"] = "d:/dev/moises"
    uvicorn.run(
        "app_neural_trading:app", 
        host="0.0.0.0", 
        port=8002,  # Usa porta diferente para teste
        log_level="info"
    )

def test_api_endpoints():
    """Testa os endpoints corrigidos"""
    base_url = "http://localhost:8002"
    
    print("🔍 TESTANDO ENDPOINTS CORRIGIDOS")
    print("=" * 50)
    
    # Aguarda o servidor iniciar
    print("⏳ Aguardando servidor iniciar...")
    time.sleep(10)
    
    # Testa health check
    try:
        print("\n🩺 Testando /health...")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check OK!")
            print(f"📊 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Health check falhou: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
    
    # Testa neural status
    try:
        print("\n🧠 Testando /api/neural/status...")
        response = requests.get(f"{base_url}/api/neural/status", timeout=10)
        if response.status_code == 200:
            print("✅ Neural status OK!")
            print(f"📊 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Neural status falhou: {response.status_code}")
            print(f"📄 Error: {response.text}")
    except Exception as e:
        print(f"❌ Erro no neural status: {e}")
    
    # Testa neural performance  
    try:
        print("\n🎯 Testando /api/neural/performance...")
        response = requests.get(f"{base_url}/api/neural/performance", timeout=10)
        if response.status_code == 200:
            print("✅ Neural performance OK!")
            print(f"📊 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Neural performance falhou: {response.status_code}")
            print(f"📄 Error: {response.text}")
    except Exception as e:
        print(f"❌ Erro no neural performance: {e}")

    # Testa controle save
    try:
        print("\n💾 Testando /api/neural/control (save)...")
        response = requests.post(f"{base_url}/api/neural/control?action=save", timeout=5)
        if response.status_code == 200:
            print("✅ Neural control save OK!")
            print(f"📊 Response: {json.dumps(response.json(), indent=2)}")
        else:
            print(f"❌ Neural control falhou: {response.status_code}")
            print(f"📄 Error: {response.text}")
    except Exception as e:
        print(f"❌ Erro no neural control: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 TESTE CONCLUÍDO!")

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE LOCAL DA API")
    print("📍 Porta: 8002 (teste)")
    
    try:
        # Inicia servidor em processo separado
        server_process = Process(target=start_api_server)
        server_process.start()
        
        # Testa endpoints
        test_api_endpoints()
        
        # Para servidor
        server_process.terminate()
        server_process.join()
        
        print("✅ Teste completo!")
        
    except KeyboardInterrupt:
        print("\n🛑 Teste interrompido")
        if 'server_process' in locals():
            server_process.terminate()
    except Exception as e:
        print(f"❌ Erro no teste: {e}")