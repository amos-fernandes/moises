#!/bin/bash

# 🔍 VERIFICAÇÃO COMPLETA NA VPS
# Execute este script diretamente na sua VPS Hostinger

echo "🔍 VERIFICAÇÃO SISTEMA VPS - HOSTINGER"
echo "======================================"
echo "⏰ $(date)"
echo "======================================"

# 1. Verificar containers rodando
echo "🐳 1. VERIFICANDO CONTAINERS..."
echo "--------------------------------"

containers_running=$(docker ps --format "table {{.Names}}\t{{.Status}}" --filter "name=neural-")
if [ -n "$containers_running" ]; then
    echo "✅ Containers encontrados:"
    echo "$containers_running"
else
    echo "❌ Nenhum container neural encontrado"
    echo "🔧 Executando fix automático..."
    
    # Parar e remover containers antigos
    docker stop neural-trading-api neural-dashboard neural-redis 2>/dev/null || true
    docker rm neural-trading-api neural-dashboard neural-redis 2>/dev/null || true
    
    # Reiniciar containers
    echo "🚀 Reiniciando containers..."
    
    # Redis
    docker run -d --name neural-redis \
      -p 6379:6379 \
      --restart unless-stopped \
      redis:alpine
    
    sleep 3
    
    # API Neural
    docker run -d --name neural-trading-api \
      -p 8001:8001 \
      --link neural-redis:redis \
      --restart unless-stopped \
      --health-cmd="curl -f http://localhost:8001/health || exit 1" \
      --health-interval=30s \
      -e REDIS_URL=redis://redis:6379 \
      moises-neural-trading
    
    sleep 5
    
    echo "✅ Containers reiniciados"
fi

# 2. Verificar conectividade local
echo ""
echo "🌐 2. TESTANDO CONECTIVIDADE LOCAL..."
echo "------------------------------------"

sleep 10  # Aguardar inicialização

# Health Check
echo "📊 Health Check:"
health_response=$(curl -s http://localhost:8001/health 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Health OK"
    echo "$health_response" | python3 -m json.tool 2>/dev/null || echo "$health_response"
else
    echo "❌ Health falhou"
fi

echo ""

# Neural Status  
echo "🧠 Neural Status:"
neural_response=$(curl -s http://localhost:8001/api/neural/status 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Neural OK"
    echo "$neural_response" | python3 -m json.tool 2>/dev/null || echo "$neural_response"
else
    echo "❌ Neural falhou"
fi

echo ""

# Evolution Status
echo "🎯 Evolution Status:"
evolution_response=$(curl -s http://localhost:8001/api/evolution/status 2>/dev/null)
if [ $? -eq 0 ]; then
    echo "✅ Evolution OK"
    echo "$evolution_response" | python3 -m json.tool 2>/dev/null || echo "$evolution_response"
else
    echo "❌ Evolution falhou"
fi

# 3. Descobrir IP público
echo ""
echo "🌍 3. DESCOBRINDO IP PÚBLICO..."
echo "------------------------------"

public_ip=$(curl -s ifconfig.me 2>/dev/null || curl -s ipinfo.io/ip 2>/dev/null || echo "Não encontrado")
echo "📍 IP Público: $public_ip"

# 4. Testar acesso externo
echo ""
echo "🔗 4. TESTANDO ACESSO EXTERNO..."
echo "--------------------------------"

if [ "$public_ip" != "Não encontrado" ]; then
    echo "🧪 Testando health check externo..."
    external_health=$(curl -s http://$public_ip:8001/health 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ Acesso externo funcionando!"
        echo "🌐 URL externa: http://$public_ip:8001"
    else
        echo "❌ Acesso externo bloqueado"
        echo "🔧 Verificando firewall..."
        
        # Configurar firewall se necessário
        ufw allow 8001 2>/dev/null
        iptables -I INPUT -p tcp --dport 8001 -j ACCEPT 2>/dev/null
        
        echo "🔥 Firewall configurado para porta 8001"
    fi
fi

# 5. Resumo final
echo ""
echo "======================================"
echo "📊 RESUMO DA VERIFICAÇÃO"
echo "======================================"

if [ -n "$containers_running" ] && [ $? -eq 0 ]; then
    echo "✅ Sistema operacional na VPS"
    echo "🎯 Pronto para evolução!"
    echo ""
    echo "🚀 COMANDO DE EVOLUÇÃO:"
    echo "curl -X POST http://localhost:8001/api/evolution/start"
    echo ""
    if [ "$public_ip" != "Não encontrado" ]; then
        echo "🌐 OU EXTERNO:"
        echo "curl -X POST http://$public_ip:8001/api/evolution/start"
    fi
    echo ""
    echo "📊 MONITORAMENTO:"
    echo "curl http://localhost:8001/api/evolution/status"
    
else
    echo "❌ Sistema com problemas"
    echo "🔧 Execute novamente este script"
fi

echo ""
echo "⏰ Verificação concluída: $(date)"