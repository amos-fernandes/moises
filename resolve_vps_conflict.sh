#!/bin/bash

# Resolver conflito Git e baixar atualizações - VPS ~/moises

echo "🔧 Resolvendo conflito Git no VPS..."
echo "===================================="

# 1. Fazer stash das alterações locais
echo "💾 Salvando alterações locais..."
git stash push -m "VPS local changes backup $(date)" || true

# 2. Fazer pull das atualizações
echo "📥 Baixando atualizações..."
git pull origin main

# 3. Verificar se arquivos foram baixados
echo "✅ Verificando arquivos baixados..."
files=(
    "update_moises_vps.sh"
    "app_neural_trading.py"
    "neural_monitor_dashboard.py"
    "COMANDOS_VPS_CORRETOS.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file - OK"
    else
        echo "❌ $file - FALTANDO!"
    fi
done

# 4. Dar permissões aos scripts
echo "🔧 Configurando permissões..."
chmod +x *.sh 2>/dev/null || true

# 5. Executar script de atualização (se existir)
if [ -f "update_moises_vps.sh" ]; then
    echo "🚀 Executando atualização do sistema neural..."
    ./update_moises_vps.sh
else
    echo "⚠️ update_moises_vps.sh não encontrado"
    
    # Alternativa: executar comandos básicos
    echo "📦 Executando comandos básicos de setup..."
    
    # Criar diretórios
    mkdir -p {logs,data,models,backups}
    
    # Instalar dependências se pip3 estiver disponível
    if command -v pip3 &> /dev/null; then
        echo "📦 Instalando dependências Python..."
        pip3 install --user --upgrade pandas numpy tensorflow streamlit requests 2>/dev/null || true
    fi
    
    # Tentar iniciar sistema diretamente
    if [ -f "app_neural_trading.py" ]; then
        echo "🧠 Iniciando sistema neural..."
        echo "Para iniciar manualmente:"
        echo "  python3 app_neural_trading.py &"
        echo "  streamlit run neural_monitor_dashboard.py --server.port=8501 &"
    fi
fi

echo ""
echo "===================================="
echo "✅ Resolução de conflito concluída!"
echo "===================================="