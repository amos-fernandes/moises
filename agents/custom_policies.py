import gymnasium as gym
import torch.nn as nn
from typing import List, Dict, Any, Optional, Union, Type

from stable_baselines3.common.policies import ActorCriticPolicy
from portfolio_features_extractor_torch import PortfolioFeaturesExtractorTorch # Seu extrator PyTorch
from config import (
    DPN_SHARED_HEAD_LATENT_DIM,
    POLICY_HEAD_NET_ARCH, 
    VALUE_HEAD_NET_ARCH,
    ACTIVATION_FN_TORCH, # Ou outra função de ativação do PyTorch
)

class CustomPortfolioPolicy(ActorCriticPolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule,
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None,
        activation_fn: Type[nn.Module] = nn.ReLU,
        features_extractor_class=PortfolioFeaturesExtractorTorch,
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        # Se net_arch não for passado pelo PPO, use o default do config
        if net_arch is None:
            net_arch = dict(pi=POLICY_HEAD_NET_ARCH, vf=VALUE_HEAD_NET_ARCH)

        # Se features_extractor_kwargs não for passado, ele será None, e o
        # construtor do PortfolioFeaturesExtractorTorch usará seus próprios defaults
        # (que devem ler do config.py também para consistência)

        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Passa a arquitetura para as cabeças da política e valor
            activation_fn=activation_fn, # Passa a classe de ativação PyTorch
            features_extractor_class=features_extractor_class, # NOSSO EXTRATOR PYTORCH
            features_extractor_kwargs=features_extractor_kwargs,
            **kwargs,
        )
        # Deixar a classe base do SB3 fazer todo o trabalho de construção (_build, _build_mlp_extractor).
        # Como extrator herda de BaseFeaturesExtractor (do torch_layers) e
        # usamos componentes PyTorch (nn.ReLU), a compatibilidade é garantida.