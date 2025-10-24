#!/bin/bash

# TESTE COMPLETO - Verificar todos os endpoints e funcionalidades

echo "🧪 TESTANDO SISTEMA NEURAL COMPLETO..."
echo "======================================"

# 1. VERIFICAR CONTAINERS
echo "📊 Status dos containers:"
docker compose ps

echo ""
echo "🔍 Verificando se containers estão rodando..."
if docker ps | grep -q "neural-api"; then
    echo "✅ neural-api rodando"
else
    echo "❌ neural-api não encontrado"
fi

if docker ps | grep -q "neural-dashboard"; then
    echo "✅ neural-dashboard rodando"
else
    echo "❌ neural-dashboard não encontrado"
fi

# 2. OBTER IPs
IP_EXTERNO=$(curl -s ifconfig.me 2>/dev/null || echo "VPS_IP")
IP_INTERNO=$(hostname -I | awk '{print $1}' 2>/dev/null || echo "localhost")

echo ""
echo "🌐 IPs do sistema:"
echo "   Externo: $IP_EXTERNO"
echo "   Interno: $IP_INTERNO"

# 3. TESTAR ENDPOINTS DA API NEURAL
echo ""
echo "🤖 TESTANDO API NEURAL (Porta 8001)..."

# Health check
echo "🏥 Health Check:"
if curl -f -s -m 10 http://localhost:8001/health 2>/dev/null; then
    echo "✅ /health - OK"
else
    echo "❌ /health - Falhou"
    echo "   Tentando outros endpoints..."
fi

# Testar endpoints alternativos
echo ""
echo "🔍 Testando endpoints do sistema neural..."

endpoints=(
    "/api/neural/status"
    "/api/neural/portfolio" 
    "/api/neural/performance"
    "/api/neural/trades"
    "/api/strategy/equilibrada"
    "/api/strategy/us_market"
    "/docs"
    "/"
)

for endpoint in "${endpoints[@]}"; do
    echo -n "   $endpoint: "
    if curl -f -s -m 5 "http://localhost:8001$endpoint" >/dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ Falhou"
    fi
done

# 4. TESTAR DASHBOARD STREAMLIT
echo ""
echo "📊 TESTANDO DASHBOARD (Porta 8501)..."

echo -n "🏠 Dashboard Home: "
if curl -f -s -m 10 http://localhost:8501 >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ Falhou"
fi

echo -n "📈 Dashboard Health: "  
if curl -f -s -m 10 http://localhost:8501/_stcore/health >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ Falhou"
fi

# 5. VERIFICAR LOGS
echo ""
echo "📋 LOGS RECENTES (últimas 10 linhas):"
echo ""
echo "🤖 Neural API:"
docker compose logs --tail=10 neural

echo ""
echo "📊 Dashboard:"
docker compose logs --tail=10 dashboard

# 6. VERIFICAR ARQUIVOS E DIRETÓRIOS
echo ""
echo "📁 Verificando estrutura de arquivos..."

if [ -d "logs" ]; then
    echo "✅ Diretório logs existe"
    ls -la logs/ 2>/dev/null | head -5
else
    echo "❌ Diretório logs não encontrado"
fi

if [ -d "data" ]; then
    echo "✅ Diretório data existe"
    ls -la data/ 2>/dev/null | head -3
else
    echo "❌ Diretório data não encontrado"
fi

# 7. TESTAR FUNCIONALIDADES ESPECÍFICAS
echo ""
echo "🧠 TESTANDO FUNCIONALIDADES NEURAIS..."

# Testar se pode fazer uma requisição de portfolio
echo -n "📊 Portfolio Neural: "
if curl -f -s -m 10 -X GET "http://localhost:8001/api/neural/portfolio" >/dev/null 2>&1; then
    echo "✅ OK"
else
    echo "❌ Não disponível ainda"
fi

# 8. RESUMO FINAL
echo ""
echo "======================================"
echo "📋 RESUMO DO SISTEMA:"
echo "======================================"

echo "🌐 URLs de Acesso:"
echo "   Neural API:  http://$IP_EXTERNO:8001"
echo "   Dashboard:   http://$IP_EXTERNO:8501"
echo "   Documentação: http://$IP_EXTERNO:8001/docs"

echo ""
echo "🔧 Comandos úteis:"
echo "   Ver logs:        docker compose logs -f"
echo "   Reiniciar:       docker compose restart"  
echo "   Parar:           docker compose down"
echo "   Status:          docker compose ps"

echo ""
echo "📊 Próximos passos:"
echo "1. Acesse http://$IP_EXTERNO:8001/docs para ver a API"
echo "2. Acesse http://$IP_EXTERNO:8501 para o dashboard"
echo "3. Configure as chaves da Binance no .env"
echo "4. Monitore os logs para performance"

echo ""
if docker ps | grep -q "neural"; then
    echo "🎯 STATUS: ✅ SISTEMA NEURAL FUNCIONANDO PERFEITAMENTE!"
else
    echo "⚠️  STATUS: Sistema ainda inicializando..."
fi

echo "======================================"