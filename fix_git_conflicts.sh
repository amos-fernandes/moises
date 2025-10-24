#!/bin/bash

# CORREÇÃO GIT - Remove conflitos e força pull

echo "🔧 RESOLVENDO CONFLITOS GIT NA VPS..."
echo "====================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. MOSTRAR SITUAÇÃO ATUAL
echo "📋 Situação atual do Git:"
git status --porcelain

# 2. FAZER BACKUP DOS ARQUIVOS CONFLITANTES
echo ""
echo "💾 Fazendo backup dos arquivos conflitantes..."
mkdir -p backup_scripts_$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_scripts_$(date +%Y%m%d_%H%M%S)"

# Mover arquivos conflitantes
for file in fix_docker_build.sh fix_pandas_ta_final.sh fix_requirements_force.sh force_rebuild.sh; do
    if [ -f "$file" ]; then
        echo "📁 Movendo $file para $BACKUP_DIR/"
        mv "$file" "$BACKUP_DIR/"
    fi
done

# 3. LIMPAR ARQUIVOS NÃO RASTREADOS
echo ""
echo "🧹 Limpando arquivos não rastreados..."
git clean -fd

# 4. DESCARTAR MUDANÇAS LOCAIS
echo "🔄 Descartando mudanças locais..."
git reset --hard HEAD

# 5. PULL FORÇADO
echo "📥 Pull forçado do GitHub..."
git pull origin main

# 6. VERIFICAR SUCESSO
if [ $? -eq 0 ]; then
    echo "✅ Pull realizado com sucesso!"
    
    echo ""
    echo "📋 Arquivos disponíveis agora:"
    ls -la *.sh 2>/dev/null || echo "Nenhum script .sh encontrado"
    
    # Verificar requirements.txt
    echo ""
    echo "🔍 Verificando requirements.txt:"
    if [ -f "requirements.txt" ]; then
        if grep -q "pandas_ta==0.3.14b0" requirements.txt; then
            echo "✅ Requirements.txt correto (pandas_ta==0.3.14b0)"
        elif grep -q "pandas-ta==0.4.71b0\|pandas_ta==0.4.71b0" requirements.txt; then
            echo "❌ Requirements.txt ainda com versão errada!"
            echo "🔧 Corrigindo..."
            
            # Sobrescrever com versão correta
            cat > requirements.txt << 'EOF'
# Sistema Neural Trading - Python 3.11 Compatível
fastapi==0.119.0
uvicorn[standard]==0.30.6
pydantic==2.5.2
python-multipart==0.0.6
pandas==2.1.4
numpy==1.26.4
pandas_ta==0.3.14b0
ta==0.10.2
yfinance==0.2.28
tensorflow==2.15.0
scikit-learn==1.3.2
keras==3.11.3
ccxt==4.1.64
requests==2.31.0
streamlit==1.29.0
plotly==5.18.0
matplotlib==3.7.1
seaborn==0.13.0
schedule==1.2.0
python-dotenv==1.0.0
redis==5.0.1
aiofiles==23.2.1
joblib==1.3.2
websockets==12.0
EOF
            echo "✅ Requirements.txt corrigido!"
        fi
        
        # Mostrar versão pandas_ta
        echo "📦 Versão pandas_ta final:"
        grep pandas_ta requirements.txt
    else
        echo "❌ requirements.txt não encontrado!"
    fi
    
    echo ""
    echo "🚀 Agora execute para continuar:"
    echo "   docker-compose down"
    echo "   docker system prune -af" 
    echo "   docker-compose build --no-cache"
    echo "   docker-compose up -d"
    
else
    echo "❌ Falha no pull!"
    echo "Tentando reset mais agressivo..."
    
    # Reset mais agressivo
    git fetch origin
    git reset --hard origin/main
    
    if [ $? -eq 0 ]; then
        echo "✅ Reset agressivo funcionou!"
    else
        echo "❌ Problema sério no Git. Execute manualmente:"
        echo "  rm -rf .git"
        echo "  git init"
        echo "  git remote add origin https://github.com/amos-fernandes/moises.git"
        echo "  git pull origin main"
    fi
fi

echo ""
echo "====================================="
echo "🎯 CONFLITOS GIT RESOLVIDOS!"
echo "====================================="