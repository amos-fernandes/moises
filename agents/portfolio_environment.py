# agents/portfolio_environment.py (ou atcoin_env.py)

from typing import List
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces
from collections import deque

# Importar do config.py
# from ..config import WINDOW_SIZE # Ajuste o import
WINDOW_SIZE_ENV = 60 # Exemplo, pegue do config
NUM_ASSETS=4
WINDOW_SIZE=60

NUM_FEATURES_PER_ASSET=26






class PortfolioEnv(gym.Env): # Renomeado para seguir convenção de Gymnasium (Opcional)
    metadata = {'render_modes': ['human'], 'render_fps': 30}

    def __init__(self, df_multi_asset_features: pd.DataFrame, 
                 asset_symbols_list: List[str], # Lista de chaves dos ativos ex: ['crypto_eth', 'stock_aapl']
                 initial_balance=100000, 
                 window_size=WINDOW_SIZE_ENV,
                 transaction_cost_pct=0.001,
                 reward_window_size=240, # Janela para cálculo do Sharpe Ratio (ex: 60 passos/horas)
                 risk_free_rate_per_step=None): # Custo de transação de 0.1%
        super(PortfolioEnv, self).__init__()
        
        self.df = df_multi_asset_features.copy() # DataFrame ACHATADO com todas as features de todos os ativos
        self.asset_keys = asset_symbols_list # Usado para identificar colunas de preço de fechamento
        self.num_assets = len(asset_symbols_list)
        self.initial_balance = initial_balance
        self.window_size = window_size
        self.transaction_cost_pct = transaction_cost_pct
        self.reward_window_size = reward_window_size
        # Cálculo automático da taxa livre de risco por passo se não for passada
        RISK_FREE_RATE_ANNUAL = 0.02 # 2% ao ano
        TRADING_DAYS_PER_YEAR = 252
        HOURS_PER_DAY_TRADING = 24
        if risk_free_rate_per_step is None:
            self.risk_free_rate_per_step = RISK_FREE_RATE_ANNUAL / (TRADING_DAYS_PER_YEAR * HOURS_PER_DAY_TRADING)
        else:
            self.risk_free_rate_per_step = risk_free_rate_per_step
        self.portfolio_returns_history = deque(maxlen=self.reward_window_size) # Armazena retorenos do portifólio por passos
        
        self.current_step = 0
        self.balance = self.initial_balance
        self.portfolio_weights = np.full(self.num_assets, 1.0 / self.num_assets if self.num_assets > 0 else 0) # Pesos iniciais iguais
        self.portfolio_value = self.initial_balance
        self.total_steps = len(self.df) - self.window_size -2 # -1 para ter um next_prices

        # Espaço de Ação: pesos do portfólio para cada ativo (devem somar 1, via Softmax da rede)
        # A rede neural vai outputar pesos que somam 1 (softmax).
        self.action_space = spaces.Box(low=0, high=1, shape=(NUM_ASSETS,), dtype=np.float32)
        
        # Espaço de Observação: janela de N features para M ativos (achatado)
        # O número de colunas no df é num_assets * num_features_per_asset
        num_total_features = self.df.shape[1]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(WINDOW_SIZE, NUM_ASSETS * NUM_FEATURES_PER_ASSET), 
            dtype=np.float32
        )


        
        
        self.current_prices_cols = [f"{key}_close" for key in self.asset_keys] # Assumindo que 'close' é uma das features base
        # Se você usa 'close_div_atr', então seria f"{key}_close_div_atr"
        # É importante ter uma coluna de preço de fechamento *original* (não escalada, não normalizada por ATR)
        # para calcular os retornos reais do portfólio. Se não estiver no df, precisará ser adicionada/mantida.
        # Por agora, vamos assumir que o df passado já tem as colunas de preço de fechamento originais,
        # ou você precisará de um df separado só com os preços para o cálculo de retorno.
        # VOU ASSUMIR QUE VOCÊ ADICIONA COLUNAS DE PREÇO DE FECHAMENTO ORIGINAIS AO `df_multi_asset_features`
        # com nomes como `eth_orig_close`, `ada_orig_close` etc.
        self.orig_close_price_cols = [f"{asset_prefix}_close" for asset_prefix in self.asset_keys] # Ex: 'crypto_eth_close'

        # Verificar se as colunas de preço de fechamento original existem
        missing_price_cols = [col for col in self.orig_close_price_cols if col not in self.df.columns]
        if missing_price_cols:
            raise ValueError(f"Colunas de preço de fechamento original ausentes no DataFrame do ambiente: {missing_price_cols}. "
                             "Adicione-as ao DataFrame com prefixo do ativo (ex: 'crypto_eth_close').")


    def _get_observation(self):
        # Pega as features da janela atual
        # O DataFrame self.df já deve estar achatado e conter TODAS as features de TODOS os ativos
        start = self.current_step
        end = start + self.window_size
        obs = self.df.iloc[start:end].values
        return obs.astype(np.float32)

    def _get_current_prices(self):
        # Pega os preços de fechamento originais do passo atual para cálculo de retorno
        # O índice é window_size - 1 dentro da observação atual, que corresponde a self.current_step + self.window_size -1 no df original.
        # Mas para o cálculo de PnL, precisamos do preço no início do step e no final do step.
        # Preço no início do step (t)
        return self.df[self.orig_close_price_cols].iloc[self.current_step + self.window_size -1].values

    def _get_next_prices(self):
        # Preço no final do step (t+1)
        return self.df[self.orig_close_price_cols].iloc[self.current_step + self.window_size].values

    def reset(self, seed=None, options=None): # Assinatura atualizada do Gymnasium
        super().reset(seed=seed) # Importante para Gymnasium
        self.current_step = 0 # Inicia do primeiro ponto onde uma janela completa pode ser formada
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

        print(f"    DEBUG Sharpe: mean_ret_step={mean_return_per_step:.6f}, std_ret_step={std_return_per_step:.6f}, risk_free_step={self.risk_free_rate_per_step:.8f}")

        if std_return_per_step < 1e-9: # Evitar divisão por zero se não houver volatilidade
            print("    DEBUG Sharpe: Std dev muito baixo, retornando 0.")
            return 0.0 

        # Sharpe Ratio por passo
        sharpe_per_step = (mean_return_per_step - self.risk_free_rate_per_step) / std_return_per_step
        
        # Anualizar o Sharpe Ratio (assumindo passos horários e ~252 dias de negociação * 24 horas)
        annualization_factor = np.sqrt(252 * 24) # Ajuste se seu timeframe for diferente
        
        annualized_sharpe = sharpe_per_step * annualization_factor
        print(f"    DEBUG Sharpe: sharpe_per_step={sharpe_per_step:.4f}, annualized_sharpe={annualized_sharpe:.4f}")
        return annualized_sharpe


    def step(self, action_weights: np.ndarray): # Ação são os pesos do portfólio
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
        # Ou, podemos dar o Sharpe Ratio da janela como recompensa a cada N passos, ou no final.
        # Por agora, vamos usar o retorno do passo como recompensa principal, e o Sharpe pode ser parte do 'info'.
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

        return observation, reward, terminated, truncated, info


    def _get_info(self): # Opcional, para retornar métricas
        current_sharpe = self._calculate_sharpe_ratio() if len(self.portfolio_returns_history) > 1 else 0.0
        return {
            "current_step": self.current_step,
            "portfolio_value": self.portfolio_value,
            "balance": self.balance, # Se você rastrear cash separadamente
            "portfolio_weights": self.portfolio_weights.tolist(),
            "last_step_return": self.portfolio_returns_history[-1] if self.portfolio_returns_history else 0.0,
            "sharpe_ratio_window": current_sharpe
        }

    def render(self, mode='human'):
        if mode == 'human':
            print(f"Step: {self.current_step}, Portfolio Value: {self.portfolio_value:.2f}, Weights: {self.portfolio_weights}")

    def close(self):
        pass # Limpar recursos se necessário