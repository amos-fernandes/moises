
# agents/portfolio_environment.py

from typing import List
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from collections import deque
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para permitir importações relativas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar do config.py
from config import (
    WINDOW_SIZE, 
    NUM_ASSETS, 
    NUM_FEATURES_PER_ASSET, 
    ALL_ASSET_SYMBOLS,
    RISK_FREE_RATE_ANNUAL,
    REWARD_WINDOW,
    REWARD_TARGET_DAILY,
    REWARD_DRAWDOWN_PENALTY,
    REWARD_VOL_PENALTY,
    REWARD_SCALE
)

class PortfolioEnv(gym.Env):
    metadata = {'render_modes': ['human'], 'render_fps': 30}

    def __init__(self, df_multi_asset_features: pd.DataFrame, 
                 initial_balance=100000, 
                 transaction_cost_pct=0.001,
                 risk_free_rate_per_step=None):
        super(PortfolioEnv, self).__init__()
        
        self.df = df_multi_asset_features.copy()
        self.asset_keys = ALL_ASSET_SYMBOLS
        self.num_assets = NUM_ASSETS
        self.initial_balance = initial_balance
        self.window_size = WINDOW_SIZE
        self.transaction_cost_pct = transaction_cost_pct
        self.reward_window_size = REWARD_WINDOW
        
        TRADING_DAYS_PER_YEAR = 252
        HOURS_PER_DAY_TRADING = 24 # Assumindo dados horários
        if risk_free_rate_per_step is None:
            self.risk_free_rate_per_step = RISK_FREE_RATE_ANNUAL / (TRADING_DAYS_PER_YEAR * HOURS_PER_DAY_TRADING)
        else:
            self.risk_free_rate_per_step = risk_free_rate_per_step
        
        self.portfolio_returns_history = deque(maxlen=self.reward_window_size)
        
        self.current_step = 0
        self.balance = self.initial_balance
        self.portfolio_weights = np.full(self.num_assets, 1.0 / self.num_assets if self.num_assets > 0 else 0)
        self.portfolio_value = self.initial_balance
        self.total_steps = len(self.df) - self.window_size - 1

        self.action_space = spaces.Box(low=0, high=1, shape=(self.num_assets,), dtype=np.float32)
        
        # Remover a coluna 'asset_id' do DataFrame temporariamente para calcular o num_total_features para o observation_space
        # pois ela não é uma feature numérica e será removida na observação real.
        num_total_features = self.df.drop(columns=['asset_id'], errors='ignore').shape[1]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(self.window_size, num_total_features), 
            dtype=np.float32
        )

        self.orig_close_price_cols = [f"{asset_key}_close" for asset_key in self.asset_keys]

        missing_price_cols = [col for col in self.orig_close_price_cols if col not in self.df.columns]
        if missing_price_cols:
            raise ValueError(f"Colunas de preço de fechamento original ausentes no DataFrame do ambiente: {missing_price_cols}. Adicione-as ao DataFrame com prefixo do ativo (ex: 'AAPL_close').")

    def _get_observation(self):
        start = self.current_step
        end = start + self.window_size
        obs = self.df.iloc[start:end]

        # Remover a coluna 'asset_id' antes de converter para float, pois ela é uma string
        # A coluna 'asset_id' é usada internamente, mas não deve ser passada para a rede neural como feature numérica.
        # A rede espera apenas features numéricas.
        # A coluna 'asset_id' é categórica e não deve ser incluída nas features numéricas.
        # O erro 'could not convert string to float' ocorre se ela não for removida.
        if 'asset_id' in obs.columns:
            obs_numeric = obs.drop(columns=['asset_id'])
        else:
            obs_numeric = obs
        # Certificar-se de que todas as colunas restantes são numéricas
        obs_numeric = obs_numeric.apply(pd.to_numeric, errors='coerce').fillna(0.0)

        return obs_numeric.astype(np.float32)


    def _get_current_prices(self):
        return self.df[self.orig_close_price_cols].iloc[self.current_step + self.window_size - 1].values

    def _get_next_prices(self):
        return self.df[self.orig_close_price_cols].iloc[self.current_step + self.window_size].values

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.portfolio_weights = np.full(self.num_assets, 1.0 / self.num_assets if self.num_assets > 0 else 0)
        self.portfolio_returns_history.clear()

        observation = self._get_observation()
        info = self._get_info()
        return observation, info
    
    def _calculate_sharpe_ratio(self) -> float:
        if len(self.portfolio_returns_history) < self.reward_window_size / 2:
            return 0.0

        returns_array = np.array(self.portfolio_returns_history)
        mean_return_per_step = np.mean(returns_array)
        std_return_per_step = np.std(returns_array)

        if std_return_per_step < 1e-9:
            return 0.0

        sharpe_per_step = (mean_return_per_step - self.risk_free_rate_per_step) / std_return_per_step
        annualization_factor = np.sqrt(252 * 24)
        annualized_sharpe = sharpe_per_step * annualization_factor
        return annualized_sharpe

    def step(self, action_weights: np.ndarray):
        current_portfolio_value_before_rebalance = self.portfolio_value

        if not np.isclose(np.sum(action_weights), 1.0):
            action_weights = action_weights / (np.sum(action_weights) + 1e-9)
        action_weights = np.clip(action_weights, 0, 1)
        
        current_asset_values = self.portfolio_weights * current_portfolio_value_before_rebalance
        target_asset_values = action_weights * current_portfolio_value_before_rebalance

        trade_volume_per_asset = np.abs(target_asset_values - current_asset_values)
        total_trade_volume = np.sum(trade_volume_per_asset)
        transaction_costs = total_trade_volume * self.transaction_cost_pct
        
        current_portfolio_value_after_costs = current_portfolio_value_before_rebalance - transaction_costs
        self.portfolio_weights = action_weights
        
        prices_t = self._get_current_prices()
        self.current_step += 1
        prices_t_plus_1 = self._get_next_prices()

        asset_returns_on_step = (prices_t_plus_1 - prices_t) / (prices_t + 1e-9)
        portfolio_return_on_step = np.sum(self.portfolio_weights * asset_returns_on_step)
        self.portfolio_value = current_portfolio_value_after_costs * (1 + portfolio_return_on_step)
        self.portfolio_returns_history.append(portfolio_return_on_step)
        
        # New reward shaping: aim toward a daily target and penalize drawdown & volatility
        # Assume portfolio_return_on_step is the per-step return (hourly if data hourly).
        # Convert per-step return into an approximate daily return by scaling.
        # If data is hourly, approximate daily_return = (1 + r_hour)^(24) - 1
        steps_per_day = 24  # assumes hourly data; if config uses different timeframe, adjust externally
        try:
            approx_daily_return = (1.0 + portfolio_return_on_step) ** steps_per_day - 1.0
        except Exception:
            approx_daily_return = portfolio_return_on_step * steps_per_day

        # Drawdown: measure maximum drawdown over the reward window
        returns_arr = np.array(self.portfolio_returns_history) if self.portfolio_returns_history else np.array([0.0])
        cumulative = np.cumprod(1.0 + returns_arr) if returns_arr.size > 0 else np.array([1.0])
        peak = np.maximum.accumulate(cumulative)
        drawdowns = (peak - cumulative) / (peak + 1e-9)
        max_drawdown = float(np.max(drawdowns)) if drawdowns.size > 0 else 0.0

        # Volatility penalty: use std of returns over window
        vol = float(np.std(returns_arr)) if returns_arr.size > 0 else 0.0

        # Reward is positive when approx_daily_return approaches target, scaled by reward scale
        reward_raw = (approx_daily_return - REWARD_TARGET_DAILY)  # negative if below target

        # Apply penalties
        reward = REWARD_SCALE * (reward_raw - REWARD_DRAWDOWN_PENALTY * max_drawdown - REWARD_VOL_PENALTY * vol)

        # Early training: if we have too few steps, provide small dense signal to help learning
        if len(self.portfolio_returns_history) < max(10, int(self.reward_window_size/10)):
            # small reward shaped by immediate sign and magnitude
            reward = np.clip(approx_daily_return * REWARD_SCALE, -1.0, 1.0)

        # Clip reward to a reasonable range to stabilize training
        reward = float(np.clip(reward, -10.0, 10.0))

        terminated = self.current_step >= self.total_steps
        truncated = False

        observation = self._get_observation()
        info = self._get_info()

        return observation, reward, terminated, truncated, info

    def _get_info(self):
        current_sharpe = self._calculate_sharpe_ratio() if len(self.portfolio_returns_history) > 1 else 0.0
        return {
            "current_step": self.current_step,
            "portfolio_value": self.portfolio_value,
            "balance": self.balance,
            "portfolio_weights": self.portfolio_weights.tolist(),
            "last_step_return": self.portfolio_returns_history[-1] if self.portfolio_returns_history else 0.0,
            "sharpe_ratio_window": current_sharpe
        }

    def render(self, mode='human'):
        if mode == 'human':
            print(f"Step: {self.current_step}, Portfolio Value: {self.portfolio_value:.2f}, Weights: {self.portfolio_weights}")

    def close(self):
        pass

