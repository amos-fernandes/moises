from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from collections import deque


from config import *


class PortfolioEnv(gym.Env): # Renomeado para seguir convenção de Gymnasium 
    metadata = {'render_modes': ['human'], 'render_fps': 30}


    def __init__(self, 
                 df_market_features: pd.DataFrame, 
                 df_news: Optional[pd.DataFrame], # Tornar notícias opcionais por enquanto
                 asset_keys_list: List[str], 
                 num_features_per_asset: int,
                 window_size: int,
                 initial_balance: float = 100000,
                 transaction_cost_pct: float = 0.001,
                 reward_window_size: int = 60,
                 risk_free_rate_annual: float = 0.02):
        super(PortfolioEnv, self).__init__()
        
        self.df_market = df_market_features.copy()
        if isinstance(df_news, pd.DataFrame) and not df_news.empty:
            self.df_news = df_news.copy()
        else:
            self.df_news = None
        #self.df_news = df_news.copy() if df_news is not None and not df_news.empty else None
        self.asset_keys = asset_keys_list
        self.num_assets = len(asset_keys_list)
        self.num_features_per_asset = num_features_per_asset
        self.window_size = window_size
        self.initial_balance = initial_balance
        self.transaction_cost_pct = transaction_cost_pct
        self.reward_window_size = reward_window_size
        self.risk_free_rate_per_step = risk_free_rate_annual / (252 * 24) # Assumindo dados horários

        self.portfolio_returns_history = deque(maxlen=self.reward_window_size)
        
        self.total_steps = len(self.df_market) - self.window_size - 2

        # --- ESPAÇO DE OBSERVAÇÃO COMO DICIONÁRIO ---
        self.observation_space = spaces.Dict({
            "market": spaces.Box(
                low=-np.inf, high=np.inf, 
                shape=(self.window_size, self.num_assets * self.num_features_per_asset), 
                dtype=np.float32
            ),
            # Para notícias, vamos passar um placeholder numérico por enquanto.
            # Um array de 1x1 é um bom placeholder. A rede neural precisará saber como interpretá-lo.
            "news": spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32) 
        })

        self.action_space = spaces.Box(low=0, high=1, shape=(self.num_assets,), dtype=np.float32)
        
        self.orig_close_price_cols = [f"{asset_prefix}_close" for asset_prefix in self.asset_keys]
        missing_price_cols = [col for col in self.orig_close_price_cols if col not in self.df_market.columns]
        if missing_price_cols:
            raise ValueError(f"Colunas de preço de fechamento original ausentes: {missing_price_cols}")

    def _get_observation(self) -> Dict[str, np.ndarray]: # <<< MUDANÇA: Retorna um Dict
        # --- Observação de Mercado ---
        start = self.current_step
        end = start + self.window_size
        market_obs = self.df_market.iloc[start:end].values.astype(np.float32)
        
        # --- Observação de Notícias (Placeholder por enquanto) ---
        # No futuro, você pegaria as notícias para o timestamp atual aqui.
        # Por agora, um placeholder que corresponda ao observation_space.
        news_obs = np.array([0.0], dtype=np.float32) # Um array 1x1 com um valor neutro

        # Retornar o dicionário completo
        return {"market": market_obs, "news": news_obs}
    

    def _get_current_prices(self):
        # Pega os preços de fechamento originais do passo atual para cálculo de retorno
        # O índice é window_size - 1 dentro da observação atual, que corresponde a self.current_step + self.window_size -1 no df original.
        # Mas para o cálculo de PnL, precisamos do preço no início do step e no final do step.
        # Preço no início do step (t)
        return self.df_market[self.orig_close_price_cols].iloc[self.current_step + self.window_size -1].values

    def _get_next_prices(self):
        # Preço no final do step (t+1)
        return self.df_market[self.orig_close_price_cols].iloc[self.current_step + self.window_size].values

    def reset(self, seed=None, options=None) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]: # Assinatura atualizada do Gymnasium
        super().reset(seed=seed) # Importante para Gymnasium
        self.current_step = 0 # Inicia do primeiro ponto onde uma janela completa pode ser formada
        self.initial_balance=10000
        self.balance = self.initial_balance
        self.portfolio_value = self.initial_balance
        self.portfolio_weights = np.full(self.num_assets, 1.0 / self.num_assets if self.num_assets > 0 else 0)
        self.portfolio_returns_history.clear()

        observation = self._get_observation()
        info = self._get_info() # Informações adicionais (opcional)
        return observation, info
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calcula o Sharpe Ratio anualizado a partir do histórico de retornos por passo."""
        if len(self.portfolio_returns_history) < self.reward_window_size / 2: # Precisa de um mínimo de dados
            return 0.0 # Ou uma pequena penalidade por não ter histórico suficiente

        returns_array = np.array(self.portfolio_returns_history)
        
        # Média dos retornos por passo
        mean_return_per_step = np.mean(returns_array)
        # Desvio padrão dos retornos por passo
        std_return_per_step = np.std(returns_array)

        #print(f"    DEBUG Sharpe: mean_ret_step={mean_return_per_step:.6f}, std_ret_step={std_return_per_step:.6f}, risk_free_step={self.risk_free_rate_per_step:.8f}")

        if std_return_per_step < 1e-9: # Evitar divisão por zero se não houver volatilidade
            print("    DEBUG Sharpe: Std dev muito baixo, retornando 0.")
            return 0.0 

        # Sharpe Ratio por passo
        sharpe_per_step = (mean_return_per_step - self.risk_free_rate_per_step) / std_return_per_step
        
        # Anualizar o Sharpe Ratio (assumindo passos horários e ~252 dias de negociação * 24 horas)
        annualization_factor = np.sqrt(252 * 24) # Ajuste se seu timeframe for diferente
        
        annualized_sharpe = sharpe_per_step * annualization_factor
        #print(f"    DEBUG Sharpe: sharpe_per_step={sharpe_per_step:.4f}, annualized_sharpe={annualized_sharpe:.4f}")


        if len(self.portfolio_returns_history) < 2: return 0.0
        returns_array = np.array(self.portfolio_returns_history)
        mean_ret = np.mean(returns_array)
        std_ret = np.std(returns_array)
        if std_ret < 1e-9: return 0.0
        sharpe_per_step = (mean_ret - self.risk_free_rate_per_step) / std_ret
        return sharpe_per_step * np.sqrt(252 * 24) # Anualizado
        


    def step(self, action_weights: np.ndarray) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict[str, Any]]:  # Ação são os pesos do portfólio
        current_portfolio_value_before_rebalance = self.portfolio_value

        # Normalizar pesos da ação se não somarem 1 (saída softmax da rede já deve fazer isso)

        if not np.isclose(np.sum(action_weights), 1.0):
            action_weights = action_weights / (np.sum(action_weights) + 1e-9)
        action_weights = np.clip(action_weights, 0, 1) # Garantir que os pesos estão entre 0 e 1 # Normaliza
        
        # Calcular custo de transação para rebalancear
        # Valor de cada ativo ANTES do rebalanceamento
        current_asset_values = self.portfolio_weights * current_portfolio_value_before_rebalance
        # Valor de cada ativo DEPOIS do rebalanceamento (com base nos novos pesos)
        target_asset_values = action_weights * current_portfolio_value_before_rebalance # Valor do portfólio ainda não mudou por preço

        # Volume negociado (absoluto) para cada ativo
        trade_volume_per_asset = np.abs(target_asset_values - current_asset_values)
        total_trade_volume = np.sum(trade_volume_per_asset)
        transaction_costs = total_trade_volume * self.transaction_cost_pct
        
        # Deduzir custos do valor do portfólio
        current_portfolio_value_after_costs = current_portfolio_value_before_rebalance - transaction_costs
        
        # Atualizar os pesos do portfólio
        self.portfolio_weights = action_weights
        
        # Pegar preços atuais (t) e próximos (t+1)
        prices_t = self._get_current_prices()
        self.current_step += 1 # Avançar para o próximo estado
        prices_t_plus_1 = self._get_next_prices()

        # Calcular retornos dos ativos
        asset_returns_on_step = (prices_t_plus_1 - prices_t) / (prices_t + 1e-9)
        
        # Calcular retorno do portfólio neste passo, APÓS custos e com os NOVOS pesos
        portfolio_return_on_step = np.sum(self.portfolio_weights * asset_returns_on_step)
        
        # Atualizar valor do portfólio
        self.portfolio_value = current_portfolio_value_after_costs * (1 + portfolio_return_on_step)
        
        # Adicionar retorno do passo ao histórico
        self.portfolio_returns_history.append(portfolio_return_on_step)
        
        # Calcular Recompensa (Sharpe Ratio)
        # Pode ser o Sharpe Ratio incremental ou o Sharpe Ratio da janela inteira
        # Para RL, uma recompensa mais frequente é geralmente melhor.
        # Usar o retorno do passo como recompensa imediata pode ser mais estável para PPO.
        # Ou podemos dar o Sharpe Ratio da janela como recompensa a cada N passos, ou no final.
        # Vamos usar o retorno do passo como recompensa principal, e o Sharpe pode ser parte do 'info'.
        # Se quisermos o Sharpe Ratio *como* recompensa, ele seria calculado aqui.
        
        # Opção A: Recompensa = Retorno do Passo (mais simples e denso)
        # ultima iteração   --  reward = portfolio_return_on_step   
        self.portfolio_returns_history.append(portfolio_return_on_step)
        #Opção B: Recompensa = Sharpe Ratio da Janela (mais complexo, pode ser esparso se calculado raramente)
        # Em PortfolioEnv.step()
# reward = portfolio_return_on_step # Recompensa atual

# NOVA RECOMPENSA (Opção B da nossa discussão anterior):
        REWARD_SCALE_FACTOR_SHARPE = 0.1  # Ou 0.01, experimente
        # if len(self.portfolio_returns_history) >= self.reward_window_size:
        #     current_sharpe = self._calculate_sharpe_ratio()
        #     reward = np.clip(current_sharpe, -5, 5) * REWARD_SCALE_FACTOR_SHARPE
        #     print(f"  Sharpe Ratio Calculado: {current_sharpe:.4f}, Recompensa (Sharpe escalado): {reward:.6f}")
        # elif len(self.portfolio_returns_history) > 1:
        #     reward = portfolio_return_on_step * 0.1
        #     print(f"  Retorno Simples como Recompensa (escalado): {reward:.6f}")
        # else:
        #     reward = 0.0

        if len(self.portfolio_returns_history) < self.reward_window_size:
            # Recompensa pequena e simples para o início do episódio
            # Isso evita os valores gigantescos, mas ainda dá um sinal de direção.
            if portfolio_return_on_step > 0:
                reward = 0.01 # Pequeno bônus por passo positivo
            elif portfolio_return_on_step < 0:
                reward = -0.01 # Pequena penalidade por passo negativo
            else:
                reward = 0.0
        else:
                # Quando a janela estiver cheia, use o Sharpe Ratio escalado
                current_sharpe = self._calculate_sharpe_ratio()
                reward = np.clip(current_sharpe, -5, 5) * REWARD_SCALE_FACTOR_SHARPE

        terminated = self.current_step >= self.total_steps 
        truncated = False 

        observation = self._get_observation()
        info = self._get_info() # Adicionar Sharpe Ratio ao info

        current_portfolio_value_before_rebalance = self.portfolio_value
        
        # Softmax na ação recebida para garantir que soma 1 (segurança extra)
        if not np.isclose(np.sum(action_weights), 1.0):
             exp_weights = np.exp(action_weights - np.max(action_weights))
             action_weights = exp_weights / np.sum(exp_weights)
        
        current_asset_values = self.portfolio_weights * current_portfolio_value_before_rebalance
        target_asset_values = action_weights * current_portfolio_value_before_rebalance
        total_trade_volume = np.sum(np.abs(target_asset_values - current_asset_values))
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
        
        # Lógica de Recompensa
        if len(self.portfolio_returns_history) < self.reward_window_size:
            if portfolio_return_on_step > 0: reward = 0.01 
            elif portfolio_return_on_step < 0: reward = -0.01
            else: reward = 0.0
        else:
            current_sharpe = self._calculate_sharpe_ratio()
            reward = np.clip(current_sharpe, -5, 5) * 0.1 # Usando REWARD_SCALE_FACTOR_SHARPE de 0.1
        
        terminated = self.current_step >= self.total_steps 
        truncated = False 
        observation = self._get_observation() # Já retorna um dicionário
        info = self._get_info()

        return observation, reward, terminated, truncated, info


    def _get_info(self) -> Dict[str, Any]: # Opcional, para retornar métricas
        current_sharpe = self._calculate_sharpe_ratio()
        return {
            "current_step": self.current_step,
            "portfolio_value": self.portfolio_value,
            "portfolio_weights": self.portfolio_weights.tolist(),
            "last_step_return": self.portfolio_returns_history[-1] if self.portfolio_returns_history else 0.0,
            "sharpe_ratio_window": current_sharpe
        }

    def render(self, mode='human'):
        if mode == 'human':
            print(f"Step: {self.current_step}, Portfolio Value: {self.portfolio_value:.2f}, Weights: {self.portfolio_weights}")

    def close(self):
        pass # Limpar recursos se necessário