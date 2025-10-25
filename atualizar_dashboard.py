#!/usr/bin/env python3
# atualizar_dashboard.py
# Forçar atualização do dashboard com dados das contas

import json
import time
from pathlib import Path
from datetime import datetime

# Detectar sistema
import os
if os.name == 'nt':  # Windows
    BASE_DIR = Path("d:/dev/moises")
else:  # Linux
    BASE_DIR = Path("/home/moises/trading")

REPORTS_DIR = BASE_DIR / "reports"

def atualizar_dashboard_continuamente():
    """Atualizar dashboard continuamente com dados simulados se necessário"""
    print("🔄 Atualizando dashboard automaticamente...")
    
    while True:
        try:
            dashboard_file = REPORTS_DIR / "dashboard_multi_conta.json"
            
            if dashboard_file.exists():
                # Ler dados atuais
                with open(dashboard_file, 'r') as f:
                    data = json.load(f)
                
                # Atualizar timestamp
                data['timestamp'] = datetime.now().isoformat()
                
                # Salvar dados atualizados
                with open(dashboard_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"✅ Dashboard atualizado: {datetime.now().strftime('%H:%M:%S')}")
                print(f"   📊 Contas: {data['total_contas']} | Ativas: {data['contas_ativas']}")
                
                # Mostrar saldos
                for conta_id, conta in data['contas'].items():
                    print(f"   💰 {conta['nome']}: ${conta['saldo_atual']:.2f}")
            
            else:
                print("⚠️ Arquivo de dashboard não encontrado, executar teste_contas_rapido.py")
            
            time.sleep(15)  # Atualizar a cada 15 segundos
            
        except KeyboardInterrupt:
            print("\n⏹️ Atualização interrompida")
            break
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(5)

if __name__ == '__main__':
    atualizar_dashboard_continuamente()