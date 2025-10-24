#!/bin/bash

# 🧪 TESTE AUTOMÁTICO BINANCE COM SUAS CHAVES
# Testa conectividade real usando suas credenciais

echo "🧪 TESTE BINANCE REAL - SUAS CREDENCIAIS"
echo "========================================"

# Suas chaves Binance
API_KEY="WSKbhdmBs31cmSQSYxAkGnfbFqV8kDMiUX9me6RG5JbKn27XOcmvh7E3w0erZVSc"
SECRET_KEY="IF6rIxEqHdf7QwzOn7BYaPNmEoKhOZaQdnipd4UfPa4IkD7nlSvJ7kydIEdS8682"

echo "🔑 Testando suas credenciais..."
echo "API Key: ${API_KEY:0:20}..."
echo "Secret: ${SECRET_KEY:0:20}..."
echo ""

# 1. Teste com Testnet (mais seguro primeiro)
echo "🧪 TESTE 1: Binance Testnet (SEGURO)"
echo "------------------------------------"

curl -X POST http://localhost:8001/api/trading/test-binance \
     -H 'Content-Type: application/json' \
     -d "{
       \"api_key\": \"$API_KEY\",
       \"secret\": \"$SECRET_KEY\",
       \"use_testnet\": true
     }" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print('✅ RESULTADO TESTNET:')
    print(f\"  Status: {data.get('test_results', {}).get('connection_status', 'UNKNOWN')}\")
    print(f\"  Sistema Pronto: {data.get('system_status', 'unknown')}\")
    
    tests = data.get('test_results', {}).get('tests', {})
    if tests:
        print('📊 Testes Individuais:')
        for test_name, result in tests.items():
            if result:
                status = '✅' if result.get('status') == 'SUCCESS' else '❌'
                print(f\"  {status} {test_name}: {result.get('status', 'N/A')}\")
except:
    print('❌ Erro parsing JSON - possível falha na conexão')
"

echo ""
echo "🧪 TESTE 2: Binance Mainnet (PRODUÇÃO)"
echo "--------------------------------------"

curl -X POST http://localhost:8001/api/trading/test-binance \
     -H 'Content-Type: application/json' \
     -d "{
       \"api_key\": \"$API_KEY\",
       \"secret\": \"$SECRET_KEY\",
       \"use_testnet\": false
     }" | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    print('✅ RESULTADO MAINNET:')
    print(f\"  Status: {data.get('test_results', {}).get('connection_status', 'UNKNOWN')}\")
    print(f\"  Sistema Pronto: {data.get('system_status', 'unknown')}\")
    
    summary = data.get('connection_summary', {})
    if summary:
        print(f\"  Conectividade: {summary.get('connectivity_score', 0):.1%}\")
        print(f\"  Pronto Trading: {summary.get('ready_for_neural_trading', False)}\")
        
    tests = data.get('test_results', {}).get('tests', {})
    if tests:
        print('📊 Testes Individuais:')
        for test_name, result in tests.items():
            if result:
                status = '✅' if result.get('status') == 'SUCCESS' else '❌'
                print(f\"  {status} {test_name}: {result.get('status', 'N/A')}\")
except:
    print('❌ Erro parsing JSON - possível falha na conexão')
"

echo ""
echo "📊 VERIFICANDO STATUS CONEXÃO FINAL:"
echo "-----------------------------------"

curl -s http://localhost:8001/api/trading/binance-status | python3 -c "
import json
import sys
try:
    data = json.load(sys.stdin)
    binance = data.get('binance_connection', {})
    
    print(f\"🔗 Binance Conectado: {binance.get('binance_connected', False)}\")
    print(f\"📊 Score Conectividade: {binance.get('connectivity_score', 0):.1%}\") 
    print(f\"🚀 Pronto p/ Trading: {binance.get('ready_for_neural_trading', False)}\")
    print(f\"⏰ Último Teste: {binance.get('last_test', 'N/A')}\")
    
    if binance.get('ready_for_neural_trading'):
        print('')
        print('🎉 SISTEMA BINANCE VALIDADO!')
        print('🚀 PRONTO PARA ATIVAR EVOLUÇÃO 85%!')
        print('')
        print('Execute agora:')
        print('curl -X POST http://localhost:8001/api/evolution/start')
    else:
        print('')
        print('⚠️ Conectividade precisa de ajustes')
        print('Verifique as credenciais ou permissões da API')
        
except Exception as e:
    print(f'❌ Erro: {e}')
"

echo ""
echo "========================================"
echo "✅ Teste de conectividade completo!"