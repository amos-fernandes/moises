# agents/rl_agent.py
from stable_baselines3 import PPO
from atcoin_env import TradingEnv  # custom env

def train_rl_model():
    env = TradingEnv()
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=50000)
    model.save("models/ppo_trading")
