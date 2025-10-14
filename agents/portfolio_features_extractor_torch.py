# rnn/agents/portfolio_features_extractor_torch.py

from typing import Dict
import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from deep_portfolio_torch import DeepPortfolioAgentNetworkTorch

class PortfolioFeaturesExtractorTorch(BaseFeaturesExtractor):
    def __init__(self, 
                 observation_space: gym.spaces.Dict, # Recebe o espaço de dicionário
                 features_dim: int,
                 # kwargs para serem passados para DeepPortfolioAgentNetworkTorch
                 **network_kwargs):
        
        # O espaço de observação para a superclasse é o dicionário inteiro
        super().__init__(observation_space, features_dim)

        # Pegar o shape da parte 'market' para passar para a DPN
        market_obs_space = observation_space.spaces["market"]
        sequence_length = market_obs_space.shape[0] # ex: 60
        total_market_features = market_obs_space.shape[1] # ex: 104
        
        # O num_features_per_asset precisa ser passado via kwargs ou inferido
        # Se 'num_assets' e 'num_features_per_asset' estão nos kwargs, ótimo.
        if "num_features_per_asset" not in network_kwargs or "num_assets" not in network_kwargs:
            raise ValueError("`num_features_per_asset` e `num_assets` devem ser passados via policy_kwargs para o extrator.")
        
        # Garantir que a DPN interna está configurada para cuspir a 'features_dim' correta
        network_kwargs['final_dense_units2'] = features_dim
        network_kwargs['output_latent_features'] = True

        self.network = DeepPortfolioAgentNetworkTorch(**network_kwargs)
        print(f"PortfolioFeaturesExtractorTorch: Instanciada DeepPortfolioAgentNetworkTorch para extrair {features_dim} features.")
        
        # (A construção com chamada mock é boa para depuração, mas pode ser removida se estiver funcionando)
        # ...

    def forward(self, observations: Dict[str, torch.Tensor]) -> torch.Tensor:
        """
        Extrai o tensor 'market' do dicionário de observações e o passa
        para a rede neural principal.
        """
        # observations agora é um dicionário com chaves "market" e "news"
        market_data_tensor = observations["market"]
        
        # Se você fosse usar notícias, você pegaria aqui:
        # news_data_tensor = observations["news"] 
        # e passaria ambos para a rede.

        # Passar APENAS o tensor de dados de mercado para a sua rede.
        return self.network(market_data_tensor)


# rnn/agents/portfolio_features_extractor_torch.py

# import torch
# import gymnasium as gym
# from stable_baselines3.common.torch_layers import BaseFeaturesExtractor

# from deep_portfolio_torch import DeepPortfolioAgentNetworkTorch

# class PortfolioFeaturesExtractorTorch(BaseFeaturesExtractor):
#     def __init__(self, observation_space: gym.spaces.Box, 
#                  features_dim: int,
#                  # kwargs para serem passados para DeepPortfolioAgentNetworkTorch
#                  **network_kwargs):
#         super().__init__(observation_space, features_dim)

#         # Garantir que a DPN interna está configurada para cuspir a 'features_dim' correta
#         # e que output_latent_features é True.
#         network_kwargs['final_dense_units2'] = features_dim
#         network_kwargs['output_latent_features'] = True

#         self.network = DeepPortfolioAgentNetworkTorch(**network_kwargs)
#         print(f"PortfolioFeaturesExtractorTorch: Instanciada DeepPortfolioAgentNetworkTorch para extrair {features_dim} features.")

#     def forward(self, observations: torch.Tensor) -> torch.Tensor:
#         # observations já vêm como tensores PyTorch do SB3
#         return self.network(observations)