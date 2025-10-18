from typing import Dict
import torch
import torch.nn as nn
import gymnasium as gym
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from deep_portfolio_torch import DeepPortfolioAgentNetworkTorch

class PortfolioFeaturesExtractorTorch(BaseFeaturesExtractor):
    def __init__(self, 
                 observation_space: gym.spaces.Box, 
                 features_dim: int,
                 **network_kwargs):
        
        super().__init__(observation_space, features_dim)

        # O observation_space agora é um Box, então pegamos o shape diretamente
        sequence_length = observation_space.shape[0] # ex: 60
        total_market_features = observation_space.shape[1] # ex: 104
        
        # num_assets e num_features_per_asset devem ser passados via network_kwargs
        if "num_features_per_asset" not in network_kwargs or "num_assets" not in network_kwargs:
            raise ValueError("`num_features_per_asset` e `num_assets` devem ser passados via policy_kwargs para o extrator.")
        
        # Garantir que a DPN interna está configurada para cuspir a 'features_dim' correta
        network_kwargs["final_dense_units2"] = features_dim
        network_kwargs["output_latent_features"] = True

        self.network = DeepPortfolioAgentNetworkTorch(**network_kwargs)
        print(f"PortfolioFeaturesExtractorTorch: Instanciada DeepPortfolioAgentNetworkTorch para extrair {features_dim} features.")
        
    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """
        Recebe o tensor de observações diretamente e o passa para a rede neural principal.
        """
        # observations já vêm como tensores PyTorch do SB3
        return self.network(observations)

