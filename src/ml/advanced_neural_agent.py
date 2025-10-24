"""
🚀 NEURAL AGENT COMPLETO - ATIVAÇÃO AVANÇADA
Evolução do modo mínimo para sistema neural completo com Deep Q-Learning
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from collections import deque
import random
from typing import Dict, List, Tuple, Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class AdvancedNeuralAgent:
    """
    Neural Agent completo com Deep Q-Learning avançado
    Substitui o modo mínimo por sistema neural full-featured
    """
    
    def __init__(self, 
                 state_size: int = 50,
                 action_size: int = 3,  # BUY, SELL, HOLD
                 learning_rate: float = 0.001):
        
        self.state_size = state_size
        self.action_size = action_size
        self.learning_rate = learning_rate
        
        # Parâmetros de aprendizado otimizados para trading
        self.epsilon = 0.95  # Exploration rate inicial alta
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.gamma = 0.95  # Discount factor
        self.batch_size = 64
        
        # Memory systems
        self.memory = deque(maxlen=10000)
        self.training_memory = deque(maxlen=5000)
        self.priority_memory = deque(maxlen=1000)  # Para experiences importantes
        
        # Performance tracking
        self.total_trades = 0
        self.successful_trades = 0
        self.total_profit = 0.0
        self.performance_history = []
        
        # Neural Networks
        self.q_network = self._build_advanced_network()
        self.target_network = self._build_advanced_network()
        self._update_target_network()
        
        # Trading específico
        self.confidence_threshold = 0.65
        self.market_regime_detector = MarketRegimeDetector()
        
        logger.info("🚀 AdvancedNeuralAgent inicializado - Deep Q-Learning ativo")
    
    def _build_advanced_network(self) -> keras.Model:
        """
        Constrói rede neural avançada para trading
        """
        model = keras.Sequential([
            # Input layer
            keras.layers.Input(shape=(self.state_size,)),
            
            # Feature extraction layers
            keras.layers.Dense(256, activation='relu', name='feature_1'),
            keras.layers.Dropout(0.2),
            
            keras.layers.Dense(128, activation='relu', name='feature_2'),
            keras.layers.Dropout(0.2),
            
            keras.layers.Dense(64, activation='relu', name='feature_3'),
            keras.layers.BatchNormalization(),
            
            # Decision layers
            keras.layers.Dense(32, activation='relu', name='decision_1'),
            keras.layers.Dense(16, activation='relu', name='decision_2'),
            
            # Output layer - Q-values para cada ação
            keras.layers.Dense(self.action_size, activation='linear', name='q_values')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def preprocess_market_data(self, df: pd.DataFrame) -> np.ndarray:
        """
        Preprocessa dados de mercado em estado para a rede neural
        """
        if len(df) < self.state_size:
            # Padding se dados insuficientes
            padding_size = self.state_size - len(df)
            df_padded = pd.concat([df.iloc[:1].reindex(range(padding_size)), df])
            df = df_padded
        
        # Features técnicas
        features = []
        
        # Preços normalizados
        close_prices = df['close'].tail(20).pct_change().fillna(0)
        features.extend(close_prices.tolist())
        
        # Indicadores técnicos
        if len(df) >= 14:
            # RSI
            rsi = self._calculate_rsi(df['close'], 14)
            features.append(rsi / 100.0)  # Normalizado 0-1
            
            # MACD
            macd, signal = self._calculate_macd(df['close'])
            features.extend([macd, signal])
        else:
            features.extend([0.5, 0.0, 0.0])  # Valores neutros
        
        # Volume normalizado
        if 'volume' in df.columns:
            volume_norm = (df['volume'].iloc[-1] / df['volume'].tail(20).mean() - 1)
            features.append(volume_norm)
        else:
            features.append(0.0)
        
        # Market regime
        regime = self.market_regime_detector.detect_regime(df)
        regime_encoded = [1.0 if regime == 'bullish' else -1.0 if regime == 'bearish' else 0.0]
        features.extend(regime_encoded)
        
        # Volatility
        volatility = df['close'].tail(10).std() / df['close'].tail(10).mean()
        features.append(volatility)
        
        # Padding para atingir state_size
        while len(features) < self.state_size:
            features.append(0.0)
        
        # Truncate se necessário
        features = features[:self.state_size]
        
        return np.array(features).reshape(1, -1)
    
    def act(self, state: np.ndarray, market_context: Dict = None) -> Tuple[int, float]:
        """
        Decide ação baseada no estado atual do mercado
        """
        # Exploration vs Exploitation
        if np.random.random() <= self.epsilon:
            action = random.choice(range(self.action_size))
            confidence = 0.5  # Confidence baixa para exploration
        else:
            # Predição da rede neural
            q_values = self.q_network.predict(state, verbose=0)[0]
            action = np.argmax(q_values)
            
            # Calcula confidence baseada na diferença entre melhor e segunda melhor ação
            sorted_q = np.sort(q_values)
            confidence = (sorted_q[-1] - sorted_q[-2]) / (np.max(q_values) - np.min(q_values) + 1e-8)
            confidence = np.clip(confidence, 0.0, 1.0)
        
        # Ajusta confidence baseado em market context
        if market_context:
            regime_multiplier = self._get_regime_confidence_multiplier(market_context.get('regime', 'neutral'))
            confidence *= regime_multiplier
        
        return action, confidence
    
    def _get_regime_confidence_multiplier(self, regime: str) -> float:
        """Ajusta confidence baseado no regime de mercado"""
        multipliers = {
            'bullish': 1.2,    # Mais confiante em mercado de alta
            'bearish': 0.8,    # Menos confiante em mercado de baixa
            'neutral': 1.0,    # Confidence normal
            'volatile': 0.7    # Menos confiante em alta volatilidade
        }
        return multipliers.get(regime, 1.0)
    
    def remember(self, state, action, reward, next_state, done, priority_level=1):
        """
        Armazena experience em memory com sistema de prioridade
        """
        experience = (state, action, reward, next_state, done)
        
        # Memory principal
        self.memory.append(experience)
        
        # Training memory para experiências recentes
        self.training_memory.append(experience)
        
        # Priority memory para experiências importantes
        if priority_level > 1 or abs(reward) > 0.02:  # Trades significativos
            self.priority_memory.append(experience)
    
    def replay_training(self) -> Dict:
        """
        Treinamento por replay com priorização
        """
        if len(self.memory) < self.batch_size:
            return {"training": False, "reason": "Insufficient memory"}
        
        # Sampling estratégico
        priority_samples = min(len(self.priority_memory), self.batch_size // 4)
        regular_samples = self.batch_size - priority_samples
        
        batch = []
        
        # Samples prioritários
        if priority_samples > 0:
            batch.extend(random.sample(list(self.priority_memory), priority_samples))
        
        # Samples regulares
        if regular_samples > 0:
            batch.extend(random.sample(list(self.memory), regular_samples))
        
        # Preparar training data
        states = np.array([e[0][0] for e in batch])
        actions = np.array([e[1] for e in batch])
        rewards = np.array([e[2] for e in batch])
        next_states = np.array([e[3][0] for e in batch])
        dones = np.array([e[4] for e in batch])
        
        # Current Q-values
        current_q_values = self.q_network.predict(states, verbose=0)
        
        # Target Q-values
        next_q_values = self.target_network.predict(next_states, verbose=0)
        
        # Update Q-values
        for i in range(len(batch)):
            if dones[i]:
                current_q_values[i][actions[i]] = rewards[i]
            else:
                current_q_values[i][actions[i]] = rewards[i] + self.gamma * np.max(next_q_values[i])
        
        # Train network
        history = self.q_network.fit(
            states, current_q_values,
            batch_size=self.batch_size,
            epochs=1,
            verbose=0
        )
        
        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
        
        return {
            "training": True,
            "loss": history.history['loss'][0],
            "epsilon": self.epsilon,
            "batch_size": len(batch),
            "priority_samples": priority_samples
        }
    
    def _update_target_network(self):
        """Atualiza target network"""
        self.target_network.set_weights(self.q_network.get_weights())
    
    def update_target_network_soft(self, tau=0.01):
        """Soft update do target network"""
        target_weights = self.target_network.get_weights()
        main_weights = self.q_network.get_weights()
        
        for i in range(len(target_weights)):
            target_weights[i] = tau * main_weights[i] + (1 - tau) * target_weights[i]
        
        self.target_network.set_weights(target_weights)
    
    def evaluate_performance(self) -> Dict:
        """
        Avalia performance detalhada do neural agent
        """
        if self.total_trades == 0:
            return {
                "accuracy": 0.5,
                "total_trades": 0,
                "profit": 0.0,
                "status": "No trades yet"
            }
        
        accuracy = self.successful_trades / self.total_trades
        avg_profit_per_trade = self.total_profit / self.total_trades
        
        # Métricas avançadas
        recent_performance = self.performance_history[-100:] if self.performance_history else []
        recent_accuracy = sum(recent_performance) / len(recent_performance) if recent_performance else 0.5
        
        return {
            "accuracy": accuracy,
            "recent_accuracy": recent_accuracy,
            "total_trades": self.total_trades,
            "successful_trades": self.successful_trades,
            "total_profit": self.total_profit,
            "avg_profit_per_trade": avg_profit_per_trade,
            "epsilon": self.epsilon,
            "memory_size": len(self.memory),
            "training_readiness": len(self.memory) >= self.batch_size,
            "confidence_threshold": self.confidence_threshold,
            "network_complexity": self.q_network.count_params()
        }
    
    def save_model(self, filepath: str = "models/advanced_neural_agent"):
        """Salva modelo treinado"""
        self.q_network.save(f"{filepath}_main.h5")
        self.target_network.save(f"{filepath}_target.h5")
        logger.info(f"💾 Modelo salvo: {filepath}")
    
    def load_model(self, filepath: str = "models/advanced_neural_agent"):
        """Carrega modelo salvo"""
        try:
            self.q_network = keras.models.load_model(f"{filepath}_main.h5")
            self.target_network = keras.models.load_model(f"{filepath}_target.h5")
            logger.info(f"📥 Modelo carregado: {filepath}")
        except Exception as e:
            logger.warning(f"⚠️ Erro ao carregar modelo: {e}")
    
    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> float:
        """Calcula RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50.0
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[float, float]:
        """Calcula MACD"""
        exp1 = prices.ewm(span=12).mean()
        exp2 = prices.ewm(span=26).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9).mean()
        
        return macd.iloc[-1], signal.iloc[-1]


class MarketRegimeDetector:
    """
    Detector de regime de mercado para ajuste adaptativo
    """
    
    def __init__(self):
        self.regimes = ['bullish', 'bearish', 'neutral', 'volatile']
    
    def detect_regime(self, df: pd.DataFrame) -> str:
        """
        Detecta regime atual do mercado
        """
        if len(df) < 20:
            return 'neutral'
        
        # Análise de tendência
        short_ma = df['close'].tail(10).mean()
        long_ma = df['close'].tail(20).mean()
        trend_strength = (short_ma - long_ma) / long_ma
        
        # Análise de volatilidade
        volatility = df['close'].tail(10).std() / df['close'].tail(10).mean()
        
        # Determinação do regime
        if volatility > 0.05:  # Alta volatilidade
            return 'volatile'
        elif trend_strength > 0.02:  # Tendência de alta
            return 'bullish'
        elif trend_strength < -0.02:  # Tendência de baixa
            return 'bearish'
        else:
            return 'neutral'