import tensorflow as tf
import numpy as np
from tf_agents.environments import tf_py_environment, wrappers, gym_wrapper
from tf_agents.agents.ppo import ppo_agent
from tf_agents.networks import actor_distribution_network, value_network
from tf_agents.trajectories import trajectory
from tf_agents.drivers.dynamic_step_driver import DynamicStepDriver
from tf_agents.replay_buffers.tf_uniform_replay_buffer import TFUniformReplayBuffer
from tf_agents.utils import common
from tf_agents.metrics import tf_metrics
from tensorflow.keras.optimizers import Adam

# Seus módulos
from portfolio_environment import PortfolioEnv  # Adaptado do seu código
from DeepPortfolioAgent import DeepPortfolioAgentNetwork

# --- CONFIGS ---
NUM_ASSETS = 4
WINDOW_SIZE = 60
FEATURES_PER_ASSET = 26
TOTAL_FEATURES = NUM_ASSETS * FEATURES_PER_ASSET
BATCH_SIZE = 64
REPLAY_BUFFER_CAPACITY = 1000
LEARNING_RATE = 3e-4
NUM_ITERATIONS = 200

import pandas as pd

# Mock: gera dados aleatórios para teste
num_steps = 500
symbols = ["ETH-USD","BTC-USD","ADA-USD","SOL-USD"]
features = ["open", "high", "low", "close", "volume"]
df_data = {}

for symbol in symbols:
    for feat in features:
        df_data[f"{symbol}_{feat}"] = np.random.rand(num_steps)

df_mock = pd.DataFrame(df_data)


# --- ENV SETUP ---
py_env = PortfolioEnv(df_mock, asset_symbols_list=symbols)
train_env = tf_py_environment.TFPyEnvironment(gym_wrapper.GymWrapper(py_env))

# --- FEATURE EXTRACTOR WRAPPER ---
class FeatureProjector(tf.keras.Model):
    def __init__(self):
        super().__init__()
        self.extractor = DeepPortfolioAgentNetwork(
            num_assets=NUM_ASSETS,
            sequence_length=WINDOW_SIZE,
            num_features_per_asset=FEATURES_PER_ASSET,
            asset_cnn_filters1=32,
            asset_cnn_filters2=64,
            asset_lstm_units1=64,
            asset_lstm_units2=32,
            mha_num_heads=4,
            mha_key_dim_divisor=4,
            final_dense_units1=64,
            final_dense_units2=32,
            final_dropout=0.2,
            use_sentiment_analysis=False
        )

    def call(self, observation, training=False):
        return self.extractor(observation, training=training)

# --- NETWORKS ---
feature_combiner = FeatureProjector()

actor_net = actor_distribution_network.ActorDistributionNetwork(
    input_tensor_spec=train_env.observation_spec(),
    output_tensor_spec=train_env.action_spec(),
    preprocessing_combiner=feature_combiner,
    fc_layer_params=()
)

value_net = value_network.ValueNetwork(
    input_tensor_spec=train_env.observation_spec(),
    preprocessing_combiner=feature_combiner,
    fc_layer_params=()
)

# --- AGENT ---
optimizer = Adam(learning_rate=LEARNING_RATE)
train_step = tf.Variable(0)
agent = ppo_agent.PPOAgent(
    train_env.time_step_spec(),
    train_env.action_spec(),
    actor_net=actor_net,
    value_net=value_net,
    optimizer=optimizer,
    num_epochs=5,
    train_step_counter=train_step
)
agent.initialize()

# --- REPLAY BUFFER ---
replay_buffer = TFUniformReplayBuffer(
    data_spec=agent.collect_data_spec,
    batch_size=train_env.batch_size,
    max_length=REPLAY_BUFFER_CAPACITY
)

# --- DRIVER ---
observer = replay_buffer.add_batch
driver = DynamicStepDriver(
    env=train_env,
    policy=agent.collect_policy,
    observers=[observer],
    num_steps=1
)

# --- METRICS (opcional) ---
avg_return = tf_metrics.AverageReturnMetric()

# --- TREINAMENTO ---
print("🚦 Iniciando ciclo de treino PPO com TFAgents e DeepPortfolioAgentNetwork...")
for i in range(NUM_ITERATIONS):
    driver.run()
    experience = replay_buffer.gather_all()
    train_loss = agent.train(experience)
    replay_buffer.clear()
    print(f"Iteração {i+1}/{NUM_ITERATIONS} - Loss: {train_loss.loss:.5f}")

print("✅ Treinamento finalizado com sucesso!")
