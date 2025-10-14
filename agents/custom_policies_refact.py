# rnn/agents/custom_policies.py

import gymnasium as gym
import torch as th # Usar 'th' é uma convenção comum
import torch.nn as nn
from typing import List, Dict, Any, Optional, Union, Type

from stable_baselines3.common.policies import ActorCriticPolicy

# Importar o seu EXTRATOR DE FEATURES PYTORCH
from portfolio_features_extractor_torch import PortfolioFeaturesExtractorTorch 

# Importar as constantes do seu config.py para os hiperparâmetros da rede
# Isso torna a configuração centralizada e fácil de ajustar.
from config import ( # Ajuste o caminho do import se necessário
    # Parâmetros para o extrator (e para a DeepPortfolioAgentNetworkTorch interna)
    # que serão passados via policy_kwargs.
    # Exemplo de como você os teria no config.py
    DPN_SHARED_HEAD_LATENT_DIM, # A dimensão da saída latente do extrator
    NUM_ASSETS,
    WINDOW_SIZE,
    NUM_FEATURES_PER_ASSET,
    ASSET_CNN_FILTERS1, ASSET_CNN_FILTERS2,
    ASSET_LSTM_UNITS1, ASSET_LSTM_UNITS2,
    FINAL_DENSE_UNITS1_EXTRACTOR, # Corresponde a final_dense_units1 na DPN_Torch
    DPN_SHARED_HEAD_DROPOUT,      # Corresponde a final_dropout na DPN_Torch
    MHA_NUM_HEADS, MHA_KEY_DIM_DIVISOR,
    
    # Parâmetros para as cabeças da política e valor (APÓS o extrator)
    POLICY_HEAD_NET_ARCH, 
    VALUE_HEAD_NET_ARCH
)

# Definir um dicionário de kwargs padrão para o seu extrator.
# Isso torna a política mais robusta se alguns parâmetros não forem passados.
DEFAULT_EXTRACTOR_KWARGS = {
    # 'features_dim' é o mais importante que a política base do SB3 usa.
    # Ele deve ser igual à dimensão da saída latente da sua DeepPortfolioAgentNetworkTorch.
    "features_dim": DPN_SHARED_HEAD_LATENT_DIM, # Ex: 64 ou 32, do config
    
    # Parâmetros para instanciar a DeepPortfolioAgentNetworkTorch dentro do extrator
    "num_assets": NUM_ASSETS,
    "sequence_length": WINDOW_SIZE,
    "num_features_per_asset": NUM_FEATURES_PER_ASSET,
    "asset_cnn_filters1": ASSET_CNN_FILTERS1, 
    "asset_cnn_filters2": ASSET_CNN_FILTERS2,
    "asset_lstm_units1": ASSET_LSTM_UNITS1, 
    "asset_lstm_units2": ASSET_LSTM_UNITS2,
    "final_dense_units1": FINAL_DENSE_UNITS1_EXTRACTOR,
    "final_dense_units2": DPN_SHARED_HEAD_LATENT_DIM, # A saída latente da DPN
    "final_dropout": DPN_SHARED_HEAD_DROPOUT,
    "mha_num_heads": MHA_NUM_HEADS, 
    "mha_key_dim_divisor": MHA_KEY_DIM_DIVISOR,
    "output_latent_features": True, # O extrator SEMPRE retorna features latentes
    "use_sentiment_analysis": False # Começar sem sentimento para simplificar
}

class CustomPortfolioPolicy(ActorCriticPolicy):
    """
    Política customizada que usa o PortfolioFeaturesExtractorTorch (com DeepPortfolioAgentNetworkTorch)
    como extrator de features. As cabeças de ator e crítico são MLPs padrão do SB3
    (construídas com PyTorch) em cima das features extraídas.
    """
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule, # Função que retorna a taxa de aprendizado
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None, # Arquitetura para as cabeças
        activation_fn: Type[nn.Module] = nn.ReLU, # Usa classe de ativação PyTorch
        features_extractor_class=PortfolioFeaturesExtractorTorch, # NOSSO EXTRATOR PYTORCH
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        # Montar os kwargs finais para o extrator de features
        current_fe_kwargs = DEFAULT_EXTRACTOR_KWARGS.copy()
        if features_extractor_kwargs is not None:
            current_fe_kwargs.update(features_extractor_kwargs)

        # O net_arch padrão do PPO para MlpPolicy é dict(pi=[64, 64], vf=[64, 64]).
        # Se você quiser um diferente para as cabeças, passe via policy_kwargs.
        # Se não for passado, ele usará o default do PPO.
        if net_arch is None:
            net_arch = dict(pi=POLICY_HEAD_NET_ARCH, vf=VALUE_HEAD_NET_ARCH) # Usa do config


        # Chamar o construtor da classe base do Stable-Baselines3
        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Passa a arquitetura para as cabeças da política e valor
            activation_fn=activation_fn, # Passa a classe de ativação PyTorch
            features_extractor_class=features_extractor_class,
            features_extractor_kwargs=current_fe_kwargs,
            **kwargs,
        )
        # A classe base `ActorCriticPolicy` cuidará de:
        # 1. Instanciar o `PortfolioFeaturesExtractorTorch` com os `features_extractor_kwargs`.
        # 2. Construir o `MlpExtractor` (que é PyTorch) com as `net_arch` e `activation_fn`
        #    para processar a saída do nosso extrator de features.
        # 3. Construir as camadas finais de ação (`action_net`) e valor (`value_net`).
        # Tudo isso é feito no método _build() da superclasse.

    # Não precisamos sobrescrever _build_mlp_extractor ou outros métodos,
    # a menos que queiramos um comportamento muito específico que o
    # `net_arch` não suporte. Deixar a classe base do SB3 fazer seu trabalho
    # é a abordagem mais robusta e menos propensa a erros quando o extrator
    # e as camadas usam o mesmo framework (PyTorch).

    def _get_constructor_parameters(self) -> Dict[str, Any]:
        # Retorna os parâmetros para salvar/carregar a política
        data = super()._get_constructor_parameters()
        # Se o seu extrator precisa de kwargs especiais que não são passados
        # automaticamente, você pode adicioná-los aqui.
        # Geralmente, features_extractor_kwargs já é salvo.
        data.update(
            dict(
                # Garante que net_arch é salvo
                net_arch=self.net_arch,
            )
        )
        return data