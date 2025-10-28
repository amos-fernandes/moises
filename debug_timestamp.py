#!/usr/bin/env python3
"""
Teste de Timestamp para debug
"""

import time
import requests

print("=== DEBUG TIMESTAMP ===")

# Timestamp atual
timestamp_atual = int(time.time() * 1000)
print(f"Timestamp local: {timestamp_atual}")

# Converter para data legível
import datetime
dt = datetime.datetime.fromtimestamp(timestamp_atual / 1000)
print(f"Data local: {dt}")

# Obter timestamp da Binance
try:
    r = requests.get('https://api.binance.com/api/v3/time', timeout=5)
    if r.status_code == 200:
        server_time = r.json()['serverTime']
        print(f"Timestamp Binance: {server_time}")
        
        dt_server = datetime.datetime.fromtimestamp(server_time / 1000)
        print(f"Data Binance: {dt_server}")
        
        diff = server_time - timestamp_atual
        print(f"Diferença: {diff}ms")
        
    else:
        print(f"Erro ao obter tempo da Binance: {r.status_code}")
        
except Exception as e:
    print(f"Erro: {e}")