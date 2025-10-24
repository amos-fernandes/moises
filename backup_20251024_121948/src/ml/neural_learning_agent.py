"""
Sistema de Aprendizado Contínuo para Rede Neural
Integra estratégias Equilibrada_Pro e US Market System com RL
A rede neural aprende e melhora continuamente baseada nos resultados
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timezone
from dataclasses import dataclass
import pickle
import json
from collections import deque
import asyncio

# Imports do sistema existente
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.trading.production_system import EquilibradaProStrategy
from src.trading.us_market_system import USMarketAnalyzer, USMarketSignal
from src.config.multi_asset_config import OPTIMIZED_ASSET_CONFIGS

logger = logging.getLogger(__name__)

@dataclass
class TradingExperience:
    """Armazena experiência de trading para aprendizado"""
    symbol: str
    state: np.ndarray  # Estado do mercado (features)
    action: int  # 0=Hold, 1=Buy, 2=Sell
    reward: float  # Resultado da ação
    next_state: np.ndarray  # Próximo estado
    done: bool  # Episódio terminou
    confidence: float  # Confiança da decisão original
    strategy_used: str  # 'equilibrada_pro' ou 'us_market'
    timestamp: datetime
    market_conditions: str  # 'bull', 'bear', 'sideways'

class NeuralTradingAgent:
    """
    Agente de RL que aprende continuamente das estratégias existentes
    Combina Deep Q-Learning com imitation learning
    """
    
    def __init__(self, 
                 state_size: int = 50,  # Tamanho do estado (features)
                 action_size: int = 3,  # Hold, Buy, Sell
                 learning_rate: float = 0.001,
                 gamma: float = 0.95,  # Discount factor
                 epsilon: float = 1.0,  # Exploration rate
                 epsilon_min: float = 0.01,
                 epsilon_decay: float = 0.995):
        
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        
        # Memory para experiências
        self.memory = deque(maxlen=10000)
        self.training_memory = deque(maxlen=50000)  # Memória de longo prazo
        
        # Redes neurais
        self.q_network = self._build_network()
        self.target_network = self._build_network()
        self.update_target_network()
        
        # Métricas de performance
        self.performance_history = []
        self.accuracy_history = []
        self.reward_history = []
        
        # Integração com estratégias existentes
        self.equilibrada_pro = EquilibradaProStrategy()
        self.us_analyzer = USMarketAnalyzer()
        
        logger.info("🧠 Neural Trading Agent inicializado")
        logger.info(f"📊 State size: {state_size}, Action size: {action_size}")
        logger.info(f"🎯 Learning rate: {learning_rate}, Gamma: {gamma}")
    
    def _build_network(self) -> keras.Model:
        """Constrói a rede neural Q-Network"""
        model = keras.Sequential([
            keras.layers.Dense(128, activation='relu', input_shape=(self.state_size,)),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.3),
            
            keras.layers.Dense(256, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.3),
            
            keras.layers.Dense(128, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.2),
            
            keras.layers.Dense(64, activation='relu'),
            keras.layers.Dropout(0.2),
            
            # Output: Q-values para cada ação + confiança
            keras.layers.Dense(self.action_size + 1, activation='linear')  # +1 para confiança
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['accuracy']
        )
        
        return model
    
    def preprocess_market_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Preprocessa dados de mercado para estado da rede neural
        Combina indicadores técnicos em vetor de features
        """
        try:
            # Calcula indicadores técnicos
            df = df.copy()
            
            # Preços normalizados
            df['price_norm'] = df['close'] / df['close'].rolling(20).mean()
            df['volume_norm'] = df['volume'] / df['volume'].rolling(20).mean()
            
            # Indicadores técnicos
            df['rsi'] = self._calculate_rsi(df['close'])
            df['macd'] = self._calculate_macd(df['close'])
            df['bb_position'] = self._calculate_bb_position(df['close'])
            df['sma_5'] = df['close'].rolling(5).mean()
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            
            # Momentum
            df['momentum_1'] = df['close'].pct_change(1)
            df['momentum_5'] = df['close'].pct_change(5)
            df['momentum_10'] = df['close'].pct_change(10)
            
            # Volatilidade
            df['volatility'] = df['close'].rolling(20).std()
            df['atr'] = self._calculate_atr(df)
            
            # Features finais (últimos valores)
            features = [
                df['price_norm'].iloc[-1] if not pd.isna(df['price_norm'].iloc[-1]) else 1.0,
                df['volume_norm'].iloc[-1] if not pd.isna(df['volume_norm'].iloc[-1]) else 1.0,
                df['rsi'].iloc[-1] if not pd.isna(df['rsi'].iloc[-1]) else 50.0,
                df['macd'].iloc[-1] if not pd.isna(df['macd'].iloc[-1]) else 0.0,
                df['bb_position'].iloc[-1] if not pd.isna(df['bb_position'].iloc[-1]) else 0.5,
                (df['sma_5'].iloc[-1] / df['sma_20'].iloc[-1]) if not pd.isna(df['sma_5'].iloc[-1]) and not pd.isna(df['sma_20'].iloc[-1]) else 1.0,
                (df['sma_20'].iloc[-1] / df['sma_50'].iloc[-1]) if not pd.isna(df['sma_20'].iloc[-1]) and not pd.isna(df['sma_50'].iloc[-1]) else 1.0,
                df['momentum_1'].iloc[-1] if not pd.isna(df['momentum_1'].iloc[-1]) else 0.0,
                df['momentum_5'].iloc[-1] if not pd.isna(df['momentum_5'].iloc[-1]) else 0.0,
                df['momentum_10'].iloc[-1] if not pd.isna(df['momentum_10'].iloc[-1]) else 0.0,
                df['volatility'].iloc[-1] if not pd.isna(df['volatility'].iloc[-1]) else 0.0,
                df['atr'].iloc[-1] if not pd.isna(df['atr'].iloc[-1]) else 0.0,
            ]
            
            # Preenche até state_size com zeros se necessário
            while len(features) < self.state_size:
                features.append(0.0)
            
            # Trunca se muito longo
            features = features[:self.state_size]
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"Erro no preprocessamento: {e}")
            return np.zeros(self.state_size, dtype=np.float32)
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: pd.Series) -> pd.Series:
        """Calcula MACD"""
        ema_12 = prices.ewm(span=12).mean()
        ema_26 = prices.ewm(span=26).mean()
        return ema_12 - ema_26
    
    def _calculate_bb_position(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """Calcula posição nas Bollinger Bands (0-1)"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return (prices - lower) / (upper - lower)
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula ATR (Average True Range)"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = np.maximum(high_low, np.maximum(high_close, low_close))
        return true_range.rolling(period).mean()
    
    def get_expert_action(self, symbol: str, df: pd.DataFrame) -> Tuple[int, float, str]:
        """
        Obtém ação de especialistas (Equilibrada_Pro + US Market)
        Retorna: (ação, confiança, estratégia_usada)
        """
        try:
            # Verifica se é ação americana
            us_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA']
            
            if symbol in us_stocks:
                # Usa US Market Analyzer
                signal = self.us_analyzer.analyze_us_stock(symbol, df)
                
                if signal.signal == 'BUY' and signal.confidence >= 0.65:
                    return 1, signal.confidence, 'us_market'
                elif signal.signal == 'SELL' and signal.confidence >= 0.65:
                    return 2, signal.confidence, 'us_market'
                else:
                    return 0, signal.confidence, 'us_market'
            else:
                # Usa Equilibrada_Pro
                result = self.equilibrada_pro.analyze_market_data(df)
                
                if result and 'signal' in result:
                    if result['signal'] > 0.65:
                        return 1, result['signal'], 'equilibrada_pro'
                    elif result['signal'] < 0.35:
                        return 2, 1 - result['signal'], 'equilibrada_pro'
                    else:
                        return 0, 0.5, 'equilibrada_pro'
                else:
                    return 0, 0.5, 'equilibrada_pro'
                    
        except Exception as e:
            logger.error(f"Erro obtendo ação expert para {symbol}: {e}")
            return 0, 0.5, 'error'
    
    def act(self, state: np.ndarray, use_expert: bool = False, symbol: str = None, df: pd.DataFrame = None) -> Tuple[int, float]:
        """
        Escolhe ação: exploration vs exploitation vs expert guidance
        Retorna: (ação, confiança)
        """
        # Fase inicial: aprende dos experts
        if use_expert and symbol and df is not None:
            expert_action, expert_confidence, _ = self.get_expert_action(symbol, df)
            
            # Adiciona ruído para exploration durante aprendizado
            if np.random.random() < 0.1:  # 10% exploration
                return np.random.choice(self.action_size), 0.3
            else:
                return expert_action, expert_confidence
        
        # Exploration vs Exploitation
        if np.random.random() <= self.epsilon:
            action = np.random.choice(self.action_size)
            confidence = 0.3  # Baixa confiança em ações aleatórias
            return action, confidence
        
        # Predição da rede neural
        q_values = self.q_network.predict(state.reshape(1, -1), verbose=0)[0]
        action = np.argmax(q_values[:self.action_size])
        confidence = min(abs(q_values[self.action_size]), 1.0)  # Último neurônio = confiança
        
        return action, confidence
    
    def remember(self, experience: TradingExperience):
        """Armazena experiência na memória"""
        self.memory.append(experience)
        self.training_memory.append(experience)
    
    def replay_training(self, batch_size: int = 32):
        """
        Treinamento com replay de experiências
        Implementa Double DQN para estabilidade
        """
        if len(self.memory) < batch_size:
            return
        
        # Sample batch
        batch_indices = np.random.choice(len(self.memory), batch_size, replace=False)
        batch = [self.memory[i] for i in batch_indices]
        
        # Prepara dados para treinamento
        states = np.array([exp.state for exp in batch])
        actions = np.array([exp.action for exp in batch])
        rewards = np.array([exp.reward for exp in batch])
        next_states = np.array([exp.next_state for exp in batch])
        dones = np.array([exp.done for exp in batch])
        
        # Calcula Q-targets usando Double DQN
        current_q_values = self.q_network.predict(states, verbose=0)
        next_q_values = self.q_network.predict(next_states, verbose=0)
        target_q_values = self.target_network.predict(next_states, verbose=0)
        
        for i in range(batch_size):
            if dones[i]:
                target = rewards[i]
            else:
                # Double DQN: usa main network para seleção, target para avaliação
                next_action = np.argmax(next_q_values[i][:self.action_size])
                target = rewards[i] + self.gamma * target_q_values[i][next_action]
            
            current_q_values[i][actions[i]] = target
        
        # Treina a rede
        history = self.q_network.fit(states, current_q_values, epochs=1, verbose=0)
        
        # Decay exploration
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return history.history['loss'][0]
    
    def imitation_learning(self, batch_size: int = 64):
        """
        Aprendizado por imitação das estratégias existentes
        Treina a rede para imitar decisões dos experts
        """
        if len(self.training_memory) < batch_size:
            return
        
        # Filtra experiências de experts com alta confiança
        expert_experiences = [
            exp for exp in self.training_memory 
            if exp.confidence >= 0.65 and exp.strategy_used in ['equilibrada_pro', 'us_market']
        ]
        
        if len(expert_experiences) < batch_size:
            expert_experiences = list(self.training_memory)[-batch_size:]
        
        batch_indices = np.random.choice(len(expert_experiences), 
                                       min(batch_size, len(expert_experiences)), 
                                       replace=False)
        batch = [expert_experiences[i] for i in batch_indices]
        
        states = np.array([exp.state for exp in batch])
        actions = np.array([exp.action for exp in batch])
        confidences = np.array([exp.confidence for exp in batch])
        
        # Cria targets: Q-values altos para ações dos experts
        targets = np.zeros((len(batch), self.action_size + 1))
        
        for i, (action, confidence) in enumerate(zip(actions, confidences)):
            # Q-value alto para ação do expert
            targets[i][action] = confidence * 2  # Amplifica recompensa
            # Outros actions com valores menores
            for j in range(self.action_size):
                if j != action:
                    targets[i][j] = -0.1
            # Confiança
            targets[i][self.action_size] = confidence
        
        # Treina
        history = self.q_network.fit(states, targets, epochs=1, verbose=0)
        
        return history.history['loss'][0]
    
    def update_target_network(self):
        """Atualiza target network"""
        self.target_network.set_weights(self.q_network.get_weights())
    
    def calculate_reward(self, action: int, price_change: float, confidence: float) -> float:
        """
        Calcula recompensa baseada na ação e resultado
        Incorpora confidence e magnitude do movimento
        """
        base_reward = 0
        
        if action == 0:  # Hold
            # Pequena penalidade por não agir em movimentos grandes
            if abs(price_change) > 0.02:  # 2%
                base_reward = -0.1
            else:
                base_reward = 0.1  # Recompensa por evitar ruído
        
        elif action == 1:  # Buy
            if price_change > 0:
                # Recompensa proporcional ao ganho
                base_reward = price_change * 10
            else:
                # Penalidade proporcional à perda
                base_reward = price_change * 15  # Penalidade maior que recompensa
        
        elif action == 2:  # Sell
            if price_change < 0:
                # Recompensa por vender antes da queda
                base_reward = abs(price_change) * 10
            else:
                # Penalidade por vender antes da alta
                base_reward = -price_change * 15
        
        # Ajusta pela confiança
        confidence_multiplier = 0.5 + confidence * 1.5  # 0.5 a 2.0
        final_reward = base_reward * confidence_multiplier
        
        return np.clip(final_reward, -2.0, 2.0)  # Limita recompensas
    
    def evaluate_performance(self) -> Dict:
        """Avalia performance atual da rede neural"""
        recent_experiences = list(self.training_memory)[-100:]  # Últimas 100
        
        if len(recent_experiences) < 10:
            return {"insufficient_data": True}
        
        total_reward = sum(exp.reward for exp in recent_experiences)
        avg_reward = total_reward / len(recent_experiences)
        
        # Calcula accuracy (ações corretas)
        correct_actions = 0
        for exp in recent_experiences:
            if exp.reward > 0:
                correct_actions += 1
        
        accuracy = correct_actions / len(recent_experiences)
        
        # Profit factor
        positive_rewards = [exp.reward for exp in recent_experiences if exp.reward > 0]
        negative_rewards = [exp.reward for exp in recent_experiences if exp.reward < 0]
        
        profit_factor = 0
        if negative_rewards:
            total_profit = sum(positive_rewards) if positive_rewards else 0
            total_loss = abs(sum(negative_rewards))
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        performance = {
            "total_experiences": len(recent_experiences),
            "avg_reward": avg_reward,
            "accuracy": accuracy,
            "profit_factor": profit_factor,
            "exploration_rate": self.epsilon,
            "total_profit": sum(positive_rewards) if positive_rewards else 0,
            "total_loss": sum(negative_rewards) if negative_rewards else 0,
        }
        
        # Armazena histórico
        self.performance_history.append(performance)
        self.accuracy_history.append(accuracy)
        self.reward_history.append(avg_reward)
        
        return performance
    
    def save_model(self, filepath: str = "neural_trading_agent.h5"):
        """Salva modelo treinado"""
        try:
            self.q_network.save(filepath)
            
            # Salva metadados
            metadata = {
                "state_size": self.state_size,
                "action_size": self.action_size,
                "epsilon": self.epsilon,
                "performance_history": self.performance_history[-50:],  # Últimos 50
                "accuracy_history": self.accuracy_history[-50:],
                "reward_history": self.reward_history[-50:],
            }
            
            with open(filepath.replace('.h5', '_metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"✅ Modelo salvo em {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Erro salvando modelo: {e}")
    
    def load_model(self, filepath: str = "neural_trading_agent.h5"):
        """Carrega modelo salvo"""
        try:
            if os.path.exists(filepath):
                self.q_network = keras.models.load_model(filepath)
                self.target_network = keras.models.load_model(filepath)
                
                # Carrega metadados
                metadata_path = filepath.replace('.h5', '_metadata.json')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    self.epsilon = metadata.get('epsilon', self.epsilon)
                    self.performance_history = metadata.get('performance_history', [])
                    self.accuracy_history = metadata.get('accuracy_history', [])
                    self.reward_history = metadata.get('reward_history', [])
                
                logger.info(f"✅ Modelo carregado de {filepath}")
                logger.info(f"📊 Epsilon atual: {self.epsilon:.3f}")
                
                return True
                
        except Exception as e:
            logger.error(f"❌ Erro carregando modelo: {e}")
            
        return False

# Exemplo de uso
if __name__ == "__main__":
    print("🧠 Sistema de Aprendizado Contínuo para Rede Neural")
    print("🎯 Integra Equilibrada_Pro + US Market System com RL")
    print("📈 A rede neural aprende e melhora continuamente")
    
    # Inicializa agente
    agent = NeuralTradingAgent(
        state_size=50,
        action_size=3,
        learning_rate=0.001
    )
    
    print(f"✅ Agente inicializado")
    print(f"🧠 State size: {agent.state_size}")
    print(f"🎯 Action size: {agent.action_size}")
    print(f"📊 Exploration rate: {agent.epsilon:.3f}")
    
    # Testa com dados simulados
    dates = pd.date_range(start='2024-01-01', periods=100, freq='H')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.01)
    
    test_df = pd.DataFrame({
        'open': prices * 0.999,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)
    
    # Processa estado
    state = agent.preprocess_market_data(test_df)
    print(f"📊 Estado processado: {state.shape}")
    
    # Obtém ação expert
    action, confidence, strategy = agent.get_expert_action('AAPL', test_df)
    print(f"🎯 Ação expert: {action} (conf: {confidence:.2f}, strategy: {strategy})")
    
    print("\n🚀 Sistema pronto para aprendizado contínuo!")