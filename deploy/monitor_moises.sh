#!/bin/bash
# monitor_moises.sh - Script de monitoramento do MOISES

echo "🎂💰 MOISES - PAINEL DE MONITORAMENTO 💰🎂"
echo "=============================================="

while true; do
    clear
    echo "🎂💰 MOISES - PAINEL DE MONITORAMENTO 💰🎂"
    echo "=============================================="
    echo "⏰ $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # Status do serviço
    echo "🔧 STATUS DO SERVIÇO:"
    if systemctl is-active --quiet moises; then
        echo "   ✅ MOISES: ATIVO"
        echo "   ⏱️ Uptime: $(systemctl show moises --property=ActiveEnterTimestamp --value | cut -d' ' -f2-)"
    else
        echo "   ❌ MOISES: INATIVO"
    fi
    echo ""
    
    # Últimos logs
    echo "📋 ÚLTIMAS ATIVIDADES:"
    journalctl -u moises -n 5 --no-pager -o short-iso
    echo ""
    
    # Recursos do sistema
    echo "💻 RECURSOS DO SISTEMA:"
    echo "   📊 CPU: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
    echo "   🧠 RAM: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
    echo "   💽 Disco: $(df -h / | awk 'NR==2{print $5}')"
    echo ""
    
    # Verificar saldo (se possível)
    if [ -f "/home/moises/trading/logs/moises_continuo.log" ]; then
        echo "💰 ÚLTIMA ATIVIDADE FINANCEIRA:"
        tail -n 3 /home/moises/trading/logs/moises_continuo.log | grep -E "(Saldo|TRADE|✅)" | tail -n 1
        echo ""
    fi
    
    echo "🔄 Atualizando em 30 segundos... (Ctrl+C para sair)"
    sleep 30
done