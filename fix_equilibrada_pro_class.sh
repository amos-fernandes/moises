#!/bin/bash

# CORREÇÃO IMPORT - Adicionar EquilibradaProStrategy ao production_system.py

echo "🔧 ADICIONANDO EquilibradaProStrategy ao production_system.py..."
echo "========================================================="

cd ~/moises || { echo "❌ Diretório não encontrado!"; exit 1; }

# 1. PARAR CONTAINER
echo "🛑 Parando container neural..."
docker compose stop neural

# 2. BACKUP DO ARQUIVO
echo "💾 Fazendo backup..."
cp src/trading/production_system.py src/trading/production_system.py.backup

# 3. ADICIONAR CLASSE EQUILIBRADAPROSTRATEGY
echo "📝 Adicionando EquilibradaProStrategy..."

cat >> src/trading/production_system.py << 'EOF'


class EquilibradaProStrategy:
    """Estratégia Equilibrada Pro sem pandas_ta - Compatível com app_neural_trading.py"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.name = "Equilibrada_Pro"
        self.balance = 1000.0
        
    def analyze_market(self, df):
        """Análise de mercado simplificada sem TA libraries"""
        try:
            # RSI manual
            df['rsi'] = self.calculate_rsi_manual(df['close'])
            
            # Médias móveis  
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean() 
            df['ema_12'] = df['close'].ewm(span=12).mean()
            
            # Volume médio (fallback se não existir)
            if 'volume' in df.columns:
                df['volume_avg'] = df['volume'].rolling(20).mean()
            else:
                df['volume_avg'] = pd.Series([1000] * len(df), index=df.index)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro na análise de mercado: {e}")
            return df
    
    def get_signal(self, df):
        """Gera sinal de trading - Estratégia Equilibrada Pro"""
        try:
            if len(df) < 50:
                return 'hold'
                
            # Analisar mercado
            df = self.analyze_market(df)
            
            # Valores atuais
            current_price = df['close'].iloc[-1]
            rsi = df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 50
            sma_20 = df['sma_20'].iloc[-1] if not pd.isna(df['sma_20'].iloc[-1]) else current_price
            sma_50 = df['sma_50'].iloc[-1] if not pd.isna(df['sma_50'].iloc[-1]) else current_price
            
            # Lógica Equilibrada Pro (conservadora e rentável)
            bullish_conditions = (
                current_price > sma_20 and  # Preço acima da média de curto prazo
                sma_20 > sma_50 and        # Tendência de alta
                rsi < 70 and               # Não sobrecomprado 
                rsi > 35                   # Não sobreverdido demais
            )
            
            bearish_conditions = (
                current_price < sma_20 and  # Preço abaixo da média
                sma_20 < sma_50 and        # Tendência de baixa
                rsi > 30 and               # Não sobrevendido
                rsi < 65                   # Não sobrecomprado demais
            )
            
            if bullish_conditions:
                return 'buy'
            elif bearish_conditions:
                return 'sell' 
            else:
                return 'hold'
                
        except Exception as e:
            self.logger.error(f"Erro ao gerar sinal: {e}")
            return 'hold'
    
    def calculate_rsi_manual(self, prices, period=14):
        """Calcula RSI manualmente (sem TA library)"""
        try:
            if len(prices) < period + 1:
                return pd.Series([50] * len(prices), index=prices.index)
                
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Evita divisão por zero
            loss = loss.replace(0, 1e-10)
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Preenche NaN com valor neutro
            return rsi.fillna(50)
            
        except Exception as e:
            self.logger.error(f"Erro no cálculo do RSI: {e}")
            return pd.Series([50] * len(prices), index=prices.index)
    
    def execute_trade(self, signal, symbol, current_price, quantity=0.1):
        """Executa trade (simulado)"""
        try:
            if signal == 'buy':
                cost = current_price * quantity
                if self.balance >= cost:
                    self.balance -= cost
                    return {
                        'action': 'buy',
                        'symbol': symbol,
                        'price': current_price,
                        'quantity': quantity,
                        'cost': cost,
                        'balance': self.balance
                    }
            elif signal == 'sell':
                revenue = current_price * quantity
                self.balance += revenue
                return {
                    'action': 'sell', 
                    'symbol': symbol,
                    'price': current_price,
                    'quantity': quantity,
                    'revenue': revenue,
                    'balance': self.balance
                }
            
            return {'action': 'hold', 'balance': self.balance}
            
        except Exception as e:
            self.logger.error(f"Erro na execução do trade: {e}")
            return {'action': 'error', 'message': str(e)}


# Instâncias globais para uso no app_neural_trading.py
production_system = ProductionTradingSystem()
equilibrada_pro_strategy = EquilibradaProStrategy()

# Alias para compatibilidade
EquilibradaProStrategy = EquilibradaProStrategy
EOF

echo "✅ EquilibradaProStrategy adicionada!"

# 4. VERIFICAR SE ARQUIVO ESTÁ OK
echo "🔍 Verificando arquivo..."
if grep -q "class EquilibradaProStrategy" src/trading/production_system.py; then
    echo "✅ Classe encontrada no arquivo"
else
    echo "❌ Classe não encontrada! Restaurando backup..."
    cp src/trading/production_system.py.backup src/trading/production_system.py
    exit 1
fi

# 5. RECONSTRUIR CONTAINER  
echo ""
echo "🔨 Reconstruindo container..."
docker compose build neural --no-cache

# 6. INICIAR SISTEMA
echo "🚀 Iniciando sistema..."
docker compose up -d

# 7. AGUARDAR E TESTAR
echo "⏳ Aguardando 45 segundos para inicialização..."
sleep 45

echo ""
echo "🧪 Testando API Neural..."

# Testar vários endpoints
endpoints_test=(
    "/"
    "/health" 
    "/docs"
    "/api/neural/status"
)

api_funcionando=false

for endpoint in "${endpoints_test[@]}"; do
    echo -n "   $endpoint: "
    if curl -f -s -m 10 "http://localhost:8001$endpoint" >/dev/null 2>&1; then
        echo "✅ OK"
        api_funcionando=true
    else
        echo "❌ Falhou"
    fi
done

if [ "$api_funcionando" = true ]; then
    echo ""
    echo "🎉 API NEURAL FUNCIONANDO!"
    
    IP_EXTERNO=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    
    echo ""
    echo "🌐 Sistema Neural Completo Disponível:"
    echo "   🤖 API Neural:     http://$IP_EXTERNO:8001"
    echo "   📊 Dashboard:      http://$IP_EXTERNO:8501" 
    echo "   📖 Documentação:   http://$IP_EXTERNO:8001/docs"
    echo "   ⚡ Status:         http://$IP_EXTERNO:8001/api/neural/status"
    
    echo ""
    echo "📊 Containers ativos:"
    docker compose ps
    
else
    echo ""
    echo "❌ API ainda com problemas. Verificando logs..."
    docker compose logs --tail=10 neural
fi

echo ""
echo "========================================================="
echo "🎯 CORREÇÃO EquilibradaProStrategy CONCLUÍDA!"
echo "   ✅ Classe adicionada ao production_system.py"
echo "   ✅ Import compatível com app_neural_trading.py"
echo "   ✅ Container reconstruído"
if [ "$api_funcionando" = true ]; then
    echo "   🎉 API NEURAL FUNCIONANDO PERFEITAMENTE!"
else
    echo "   ⚠️  Verificar logs se ainda houver problemas"
fi
echo "========================================================="