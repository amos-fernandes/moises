import numpy as np
import tensorflow as tf
from tensorflow.keras.layers import LSTM, Dense, Conv1D, MultiHeadAttention
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification # Changed here
import gymnasium as gym
from gymnasium import spaces

class DeepPortfolioAI(tf.keras.Model):
    def __init__(self, num_assets, sequence_length=60):
        super(DeepPortfolioAI, self).__init__()
        
        # Parâmetros do modelo
        self.num_assets = num_assets
        self.sequence_length = sequence_length
        
        # CNN para análise de padrões técnicos
        self.conv1 = Conv1D(64, 3, activation='relu')
        self.conv2 = Conv1D(128, 3, activation='relu')
        
        # LSTM para análise temporal
        self.lstm1 = LSTM(128, return_sequences=True)
        self.lstm2 = LSTM(64)
        
        # Attention para correlações entre ativos
        self.attention = MultiHeadAttention(num_heads=8, key_dim=64)
        
        # Camadas densas para decisão final
        self.dense1 = Dense(256, activation='relu')
        self.dense2 = Dense(128, activation='relu')
        self.output_layer = Dense(num_assets, activation='softmax')
        
        # Inicializar tokenizer e modelo de sentimento
        self.tokenizer = AutoTokenizer.from_pretrained('ProsusAI/finbert')
        self.sentiment_model = TFAutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert') # Changed here

    def call(self, inputs):
        market_data, news_data = inputs
        
        # Análise técnica com CNN
        x_technical = self.conv1(market_data)
        x_technical = self.conv2(x_technical)
        
        # Análise temporal com LSTM
        x_temporal = self.lstm1(x_technical)
        x_temporal = self.lstm2(x_temporal)
        
        # Attention para correlações
        x_attention = self.attention(x_temporal, x_temporal, x_temporal)
        
        # Combinar com análise de sentimento
        sentiment_embeddings = self._process_news(news_data)
        x_combined = tf.concat([x_attention, sentiment_embeddings], axis=-1)
        
        # Camadas densas finais
        x = self.dense1(x_combined)
        x = self.dense2(x)
        return self.output_layer(x)
    
    def _process_news(self, news_data):
        inputs = self.tokenizer(news_data, return_tensors="pt", padding=True, truncation=True)
        sentiment_scores = self.sentiment_model(**inputs).logits
        return tf.convert_to_tensor(sentiment_scores.detach().numpy())

class PortfolioEnvironment(gym.Env):
    def __init__(self, data, initial_balance=100000):
        super(PortfolioEnvironment, self).__init__()
        
        self.data = data
        self.initial_balance = initial_balance
        self.current_step = 0
        
        # Define espaços de ação e observação
        self.action_space = spaces.Box(
            low=0, high=1, shape=(len(data.columns),), dtype=np.float32)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(60, len(data.columns)), dtype=np.float32)
        
    def reset(self):
        self.current_step = 0
        self.balance = self.initial_balance
        self.portfolio = np.zeros(len(self.data.columns))
        return self._get_observation()
    
    def step(self, action):
        # Implementar lógica de negociação
        current_prices = self.data.iloc[self.current_step]
        next_prices = self.data.iloc[self.current_step + 1]
        
        # Calcular retorno
        returns = (next_prices - current_prices) / current_prices
        reward = np.sum(action * returns)
        
        # Atualizar portfolio
        self.portfolio = action
        self.balance *= (1 + reward)
        
        # Incrementar step
        self.current_step += 1
        done = self.current_step >= len(self.data) - 1
        
        return self._get_observation(), reward, done, {}
    
    def _get_observation(self):
        return self.data.iloc[self.current_step-60:self.current_step].values