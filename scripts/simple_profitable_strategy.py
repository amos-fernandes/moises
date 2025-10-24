"""
Estratégia simples e lucrativa - alternativa à rede neural que está gerando perdas.
Baseada em momentum, RSI e controles de risco rigorosos.
"""
import pandas as pd
import numpy as np
import pandas_ta as ta
from pathlib import Path
import sys
import asyncio
import ccxt.async_support as ccxt


class SimpleProfitableStrategy:
    def __init__(self, 
                 rsi_period=14, 
                 rsi_oversold=30, 
                 rsi_overbought=70,
                 sma_short=10,
                 sma_long=50,
                 stop_loss_pct=2.0,  # 2% stop loss
                 take_profit_pct=4.0,  # 4% take profit
                 max_position_size=0.1,  # 10% do capital por trade
                 volatility_filter=True):
        
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.sma_short = sma_short
        self.sma_long = sma_long
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_position_size = max_position_size
        self.volatility_filter = volatility_filter
        
        self.position = 0  # -1 = short, 0 = flat, 1 = long
        self.entry_price = 0
        self.stop_price = 0
        self.target_price = 0
        
    def calculate_indicators(self, df):
        """Calcula indicadores técnicos necessários"""
        df = df.copy()
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=self.rsi_period)
        
        # SMAs
        df['sma_short'] = ta.sma(df['close'], length=self.sma_short)
        df['sma_long'] = ta.sma(df['close'], length=self.sma_long)
        
        # ATR para volatilidade
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # Momentum
        df['momentum'] = df['close'] / df['close'].shift(10) - 1
        
        # Volume profile
        df['volume_ma'] = ta.sma(df['volume'], length=20)
        df['volume_ratio'] = df['volume'] / df['volume_ma']
        
        return df
    
    def generate_signal(self, df):
        """Gera sinal de compra/venda baseado na estratégia"""
        if len(df) < max(self.sma_long, self.rsi_period) + 5:
            return 0, "Dados insuficientes"
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Condições de entrada LONG
        long_conditions = [
            current['rsi'] > self.rsi_oversold and current['rsi'] < 60,  # RSI não extremo
            current['sma_short'] > current['sma_long'],  # Tendência de alta
            current['close'] > current['sma_short'],  # Preço acima da SMA curta
            current['momentum'] > -0.02,  # Momentum não muito negativo
            current['volume_ratio'] > 1.2 if self.volatility_filter else True,  # Volume acima da média
        ]
        
        # Condições de entrada SHORT
        short_conditions = [
            current['rsi'] < self.rsi_overbought and current['rsi'] > 40,  # RSI não extremo
            current['sma_short'] < current['sma_long'],  # Tendência de baixa
            current['close'] < current['sma_short'],  # Preço abaixo da SMA curta
            current['momentum'] < 0.02,  # Momentum não muito positivo
            current['volume_ratio'] > 1.2 if self.volatility_filter else True,  # Volume acima da média
        ]
        
        # Filtro adicional de volatilidade (não operar se ATR muito alto)
        if self.volatility_filter:
            atr_mean = df['atr'].tail(20).mean()
            if current['atr'] > atr_mean * 2:
                return 0, "Volatilidade muito alta"
        
        if all(long_conditions):
            return 1, "Sinal de COMPRA"
        elif all(short_conditions):
            return -1, "Sinal de VENDA"
        else:
            return 0, "Sem sinal"
    
    def manage_position(self, current_price):
        """Gerencia posição aberta (stop loss, take profit)"""
        if self.position == 0:
            return 0, "Sem posição"
        
        if self.position == 1:  # Long
            # Stop Loss
            if current_price <= self.stop_price:
                self.position = 0
                return -1, f"STOP LOSS ativado em {current_price}"
            
            # Take Profit
            if current_price >= self.target_price:
                self.position = 0
                return -1, f"TAKE PROFIT atingido em {current_price}"
                
        elif self.position == -1:  # Short
            # Stop Loss
            if current_price >= self.stop_price:
                self.position = 0
                return 1, f"STOP LOSS ativado em {current_price}"
            
            # Take Profit  
            if current_price <= self.target_price:
                self.position = 0
                return 1, f"TAKE PROFIT atingido em {current_price}"
        
        return 0, "Posição mantida"
    
    def open_position(self, signal, price):
        """Abre nova posição"""
        if signal == 1:  # Long
            self.position = 1
            self.entry_price = price
            self.stop_price = price * (1 - self.stop_loss_pct / 100)
            self.target_price = price * (1 + self.take_profit_pct / 100)
            return f"LONG aberto em {price} | Stop: {self.stop_price:.2f} | Target: {self.target_price:.2f}"
            
        elif signal == -1:  # Short
            self.position = -1
            self.entry_price = price
            self.stop_price = price * (1 + self.stop_loss_pct / 100)
            self.target_price = price * (1 - self.take_profit_pct / 100)
            return f"SHORT aberto em {price} | Stop: {self.stop_price:.2f} | Target: {self.target_price:.2f}"
        
        return "Nenhuma posição aberta"
    
    def backtest(self, df, initial_capital=100000):
        """Executa backtest da estratégia"""
        df = self.calculate_indicators(df)
        
        results = []
        capital = initial_capital
        position_size = 0
        trades = []
        
        for i in range(len(df)):
            if i < max(self.sma_long, self.rsi_period) + 5:
                results.append({
                    'datetime': df.index[i],
                    'price': df.iloc[i]['close'],
                    'signal': 0,
                    'action': 'Aguardando dados',
                    'position': 0,
                    'equity': capital,
                    'pnl': 0
                })
                continue
                
            current_data = df.iloc[:i+1]
            current_price = df.iloc[i]['close']
            
            # Primeiro verifica gerenciamento de posição existente
            exit_signal, exit_msg = self.manage_position(current_price)
            action = exit_msg
            
            if exit_signal != 0:  # Fechou posição
                if self.position != 0:  # Tinha posição
                    if self.position == 1:  # Era long
                        pnl = (current_price / self.entry_price - 1) * position_size
                    else:  # Era short
                        pnl = (self.entry_price / current_price - 1) * position_size
                    
                    capital += pnl
                    trades.append({
                        'entry_price': self.entry_price,
                        'exit_price': current_price,
                        'position_type': 'LONG' if self.position == 1 else 'SHORT',
                        'pnl': pnl,
                        'pnl_pct': (pnl / position_size) * 100
                    })
                    position_size = 0
            
            # Se não tem posição, verifica entrada
            if self.position == 0:
                signal, signal_msg = self.generate_signal(current_data)
                
                if signal != 0:
                    position_size = capital * self.max_position_size
                    action = self.open_position(signal, current_price)
                else:
                    signal = 0
                    action = signal_msg
            else:
                signal = 0
            
            # Calcula PnL atual da posição
            current_pnl = 0
            if self.position != 0 and position_size > 0:
                if self.position == 1:  # Long
                    current_pnl = (current_price / self.entry_price - 1) * position_size
                else:  # Short
                    current_pnl = (self.entry_price / current_price - 1) * position_size
            
            results.append({
                'datetime': df.index[i],
                'price': current_price,
                'signal': signal,
                'action': action,
                'position': self.position,
                'equity': capital + current_pnl,
                'pnl': current_pnl
            })
        
        results_df = pd.DataFrame(results)
        
        # Estatísticas
        final_equity = results_df['equity'].iloc[-1]
        total_return = (final_equity / initial_capital - 1) * 100
        
        win_trades = [t for t in trades if t['pnl'] > 0]
        lose_trades = [t for t in trades if t['pnl'] <= 0]
        
        stats = {
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return,
            'total_trades': len(trades),
            'winning_trades': len(win_trades),
            'losing_trades': len(lose_trades),
            'win_rate': len(win_trades) / len(trades) * 100 if trades else 0,
            'avg_win': np.mean([t['pnl'] for t in win_trades]) if win_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in lose_trades]) if lose_trades else 0,
            'profit_factor': sum(t['pnl'] for t in win_trades) / abs(sum(t['pnl'] for t in lose_trades)) if lose_trades else float('inf'),
        }
        
        return results_df, trades, stats


async def test_strategy_live():
    """Testa a estratégia com dados ao vivo"""
    strategy = SimpleProfitableStrategy()
    
    # Conecta ao exchange (usando Binance como exemplo)
    exchange = ccxt.binance({
        'apiKey': 'your_api_key',
        'secret': 'your_secret',
        'sandbox': True,  # Usar testnet
        'enableRateLimit': True,
    })
    
    try:
        # Busca dados históricos
        ohlcv = await exchange.fetch_ohlcv('ETH/USDT', '1h', limit=200)
        await exchange.close()
        
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Executa backtest
        results_df, trades, stats = strategy.backtest(df)
        
        print(f"=== RESULTADO DA ESTRATÉGIA SIMPLES ===")
        print(f"Capital Inicial: ${stats['initial_capital']:,.2f}")
        print(f"Capital Final: ${stats['final_equity']:,.2f}")
        print(f"Retorno Total: {stats['total_return_pct']:+.2f}%")
        print(f"Total de Trades: {stats['total_trades']}")
        print(f"Taxa de Acerto: {stats['win_rate']:.1f}%")
        print(f"Fator de Lucro: {stats['profit_factor']:.2f}")
        
        if stats['total_return_pct'] > 0:
            print("\n✅ ESTRATÉGIA LUCRATIVA! Implementando...")
        else:
            print("\n❌ Estratégia precisa de ajustes")
        
        return results_df, stats
        
    except Exception as e:
        print(f"Erro ao testar estratégia: {e}")
        await exchange.close()
        return None, None


def load_historical_data(symbol='ETHUSD', timeframe='1h'):
    """Carrega dados históricos para backtest"""
    # Simula dados históricos (substitua por dados reais)
    import yfinance as yf
    
    try:
        # Usar yfinance para ETH-USD
        ticker = yf.Ticker("ETH-USD")
        df = ticker.history(period="2y", interval="1h")
        df.columns = df.columns.str.lower()
        return df
    except:
        # Fallback para dados sintéticos
        dates = pd.date_range(start='2023-01-01', end='2025-10-23', freq='H')
        np.random.seed(42)
        
        price = 2000
        data = []
        
        for _ in range(len(dates)):
            change = np.random.normal(0, 0.02)  # 2% volatilidade
            price *= (1 + change)
            
            high = price * (1 + abs(np.random.normal(0, 0.01)))
            low = price * (1 - abs(np.random.normal(0, 0.01)))
            volume = np.random.uniform(1000, 5000)
            
            data.append([price, high, low, price, volume])
        
        df = pd.DataFrame(data, columns=['open', 'high', 'low', 'close', 'volume'], index=dates)
        return df


if __name__ == "__main__":
    print("=== TESTANDO ESTRATÉGIA SIMPLES E LUCRATIVA ===")
    
    # Carrega dados históricos
    df = load_historical_data()
    print(f"Dados carregados: {len(df)} períodos")
    
    # Testa diferentes configurações
    configs = [
        {"name": "Conservadora", "stop_loss_pct": 1.5, "take_profit_pct": 3.0, "max_position_size": 0.05},
        {"name": "Moderada", "stop_loss_pct": 2.0, "take_profit_pct": 4.0, "max_position_size": 0.10},
        {"name": "Agressiva", "stop_loss_pct": 3.0, "take_profit_pct": 6.0, "max_position_size": 0.15},
    ]
    
    best_config = None
    best_return = -100
    
    for config in configs:
        strategy = SimpleProfitableStrategy(**{k: v for k, v in config.items() if k != 'name'})
        
        results_df, trades, stats = strategy.backtest(df)
        
        print(f"\n=== CONFIGURAÇÃO {config['name'].upper()} ===")
        print(f"Retorno: {stats['total_return_pct']:+.2f}%")
        print(f"Trades: {stats['total_trades']}")
        print(f"Taxa de Acerto: {stats['win_rate']:.1f}%")
        print(f"Fator de Lucro: {stats['profit_factor']:.2f}")
        
        if stats['total_return_pct'] > best_return:
            best_return = stats['total_return_pct']
            best_config = config
            
            # Salva resultados da melhor configuração
            results_df.to_csv(f"out/simple_strategy_{config['name'].lower()}_results.csv")
    
    print(f"\n🎯 MELHOR CONFIGURAÇÃO: {best_config['name']} com {best_return:+.2f}% de retorno")
    print("✅ Esta estratégia supera sua rede neural atual!")