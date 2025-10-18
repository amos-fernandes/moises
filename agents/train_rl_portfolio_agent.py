# train_rl_portfolio_agent.py
import sys
from pathlib import Path
# Ensure repo root is on sys.path so relative imports work when script is run directly
repo_root = str(Path(__file__).resolve().parents[1])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
import gymnasium as gym
import tensorflow as tf
import pandas as pd
# Ensure MlpExtractor and torch.nn are available for the custom extractor defined below
from stable_baselines3.common.torch_layers import MlpExtractor
import torch.nn as nn
#from transformers import logger

# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

class CustomMlpExtractor(MlpExtractor):
    def __init__(self, input_dim, net_arch, activation_fn, device):
        super().__init__(input_dim, net_arch, activation_fn, device)

    def forward(self, features):
        for layer in self.policy_net:
            if isinstance(layer, nn.ReLU):
                features = layer(features)  # Passando 'features' como argumento
            else:
                features = layer(features)
        return features
# Para TensorFlow, precisamos de um extrator de features compatível ou construir a política de forma diferente.
# Stable Baselines3 tem melhor suporte nativo para PyTorch. Para TF, é um pouco mais manual.
# VAMOS USAR A ABORDAGEM DE POLÍTICA CUSTOMIZADA COM TF DIRETAMENTE.
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import List, Dict, Any, Optional, Union, Type
# Importar sua rede e configs
#import agents.DeepPortfolioAgent as DeepPortfolioAgent
from DeepPortfolioAgent import DeepPortfolioAgentNetwork 
from agents.feature_scaler_adapter import fit_and_create_scaled
import os
# from ..config import (NUM_ASSETS, WINDOW_SIZE, NUM_FEATURES_PER_ASSET, ...) # Importe do seu config real
# VALORES DE EXEMPLO (PEGUE DO SEU CONFIG.PY REAL)
NUM_ASSETS_POLICY = 4
WINDOW_SIZE_POLICY = 60
NUM_FEATURES_PER_ASSET_POLICY = 26
# Hiperparâmetros para DeepPortfolioAgentNetwork quando usada como extrator
ASSET_CNN_FILTERS1_POLICY = 32
ASSET_CNN_FILTERS2_POLICY = 64
ASSET_LSTM_UNITS1_POLICY = 64
ASSET_LSTM_UNITS2_POLICY = 32 # Esta será a dimensão das features latentes para ator/crítico
ASSET_DROPOUT_POLICY = 0.2
MHA_NUM_HEADS_POLICY = 4
MHA_KEY_DIM_DIVISOR_POLICY = 2 # Para key_dim = 32 // 2 = 16
FINAL_DENSE_UNITS1_POLICY = 128
FINAL_DENSE_UNITS2_POLICY = ASSET_LSTM_UNITS2_POLICY # A saída da dense2 SÃO as features latentes
FINAL_DROPOUT_POLICY = 0.3


class TFPortfolioFeaturesExtractor(tf.keras.layers.Layer): # Herda de tf.keras.layers.Layer
    """
    Extrator de features customizado para SB3 que usa DeepPortfolioAgentNetwork.
    A observação do ambiente é (batch, window, num_assets * num_features_per_asset).
    A saída são as features latentes (batch, latent_dim).
    """
    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = ASSET_LSTM_UNITS2_POLICY):
        super(TFPortfolioFeaturesExtractor, self).__init__()
        self.features_dim = features_dim # SB3 usa isso para saber o tamanho da saída

        # Instanciar a rede base para extrair features
        # Ela deve retornar as ativações ANTES da camada softmax de alocação.
        self.network = DeepPortfolioAgentNetwork(
            num_assets=NUM_ASSETS_POLICY,
            sequence_length=WINDOW_SIZE_POLICY,
            num_features_per_asset=NUM_FEATURES_PER_ASSET_POLICY,
            asset_cnn_filters1=ASSET_CNN_FILTERS1_POLICY, 
            asset_cnn_filters2=ASSET_CNN_FILTERS2_POLICY,
            asset_lstm_units1=ASSET_LSTM_UNITS1_POLICY, 
            asset_lstm_units2=ASSET_LSTM_UNITS2_POLICY, # Define a saída do asset_processor
            asset_dropout=ASSET_DROPOUT_POLICY,
            mha_num_heads=MHA_NUM_HEADS_POLICY, 
            mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR_POLICY,
            final_dense_units1=FINAL_DENSE_UNITS1_POLICY, 
            final_dense_units2=self.features_dim, # A saída da dense2 é a nossa feature latente
            final_dropout=FINAL_DROPOUT_POLICY,
            output_latent_features=True,
            use_sentiment_analysis=True # MUITO IMPORTANTE!
        )
        print("TFPortfolioFeaturesExtractor inicializado e usando DeepPortfolioAgentNetwork (output_latent_features=True).")

    def call(self, observations: tf.Tensor, training: bool = False) -> tf.Tensor:
        # A DeepPortfolioAgentNetwork já lida com o fatiamento e processamento.
        # Ela foi configurada para retornar features latentes.
        return self.network(observations, training=training)


class CustomPolicy(ActorCriticPolicy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mlp_extractor = CustomMlpExtractor(
            input_dim=self.observation_space.shape[0],
            net_arch=[64, 64],  # Exemplo de arquitetura
            activation_fn=nn.ReLU,
            device=self.device
        )



class CustomPortfolioPolicySB3(ActorCriticPolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule, # Função que retorna a taxa de aprendizado
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None, # Arquitetura para MLPs pós-extrator
        activation_fn: Type[tf.Module] = tf.nn.relu, # Usar tf.nn.relu para TF
        # Adicionar quaisquer outros parâmetros específicos que o extrator precise
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        if features_extractor_kwargs is None:
            features_extractor_kwargs = {}
        
        # A dimensão das features que o nosso extrator PortfolioFeatureExtractor vai cuspir.
        # Deve ser igual a ASSET_LSTM_UNITS2_POLICY (ou final_dense_units2 do extrator)
        # Se não for passado, o construtor do ActorCriticPolicy pode tentar inferir.
        # Vamos passar explicitamente para garantir.
        features_extractor_kwargs.setdefault("features_dim", ASSET_LSTM_UNITS2_POLICY) # Ou o valor que você definiu

        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Para camadas Dense APÓS o extrator de features
            activation_fn=activation_fn,
            features_extractor_class=TFPortfolioFeaturesExtractor,
            features_extractor_kwargs=features_extractor_kwargs,
            **kwargs,
        )
        # Otimizador é criado na classe base.
        # As redes de ator e crítico são construídas no método _build da classe base,
        # usando o self.features_extractor e depois o self.mlp_extractor (que é
        # construído com base no net_arch).

    # Não precisamos sobrescrever _build_mlp_extractor se o features_extractor
    # já fizer o trabalho pesado e o net_arch padrão para as cabeças for suficiente.
    # Se quisermos MLPs customizados para ator e crítico APÓS o extrator:
    # def _build_mlp_extractor(self) -> None:
    #     # self.mlp_extractor é uma instância de MlpExtractor (ou similar)
    #     # A entrada para ele é self.features_extractor.features_dim
    #     # Aqui, net_arch definiria a estrutura do mlp_extractor
    #     self.mlp_extractor = MlpExtractor(
    #         feature_dim=self.features_extractor.features_dim,
    #         net_arch=self.net_arch, # net_arch é uma lista de ints para camadas da política e valor
    #         activation_fn=self.activation_fn,
    #         device=self.device,
    #     )
    # As redes de ação e valor (action_net, value_net) são então criadas
    # no _build da classe ActorCriticPolicy, no topo do mlp_extractor.# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

import gymnasium as gym # Usar gymnasium
import tensorflow as tf
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor as PyTorchBaseFeaturesExtractor

from stable_baselines3.common.torch_layers import MlpExtractor
import torch.nn as nn

class CustomMlpExtractor(MlpExtractor):
    def __init__(self, input_dim, net_arch, activation_fn, device):
        super().__init__(input_dim, net_arch, activation_fn, device)

    def forward(self, features):
        for layer in self.policy_net:
            if isinstance(layer, nn.ReLU):
                features = layer(features)  # Passando 'features' como argumento
            else:
                features = layer(features)
        return features
# Para TensorFlow, precisamos de um extrator de features compatível ou construir a política de forma diferente.
# Stable Baselines3 tem melhor suporte nativo para PyTorch. Para TF, é um pouco mais manual.
# VAMOS USAR A ABORDAGEM DE POLÍTICA CUSTOMIZADA COM TF DIRETAMENTE.
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import List, Dict, Any, Optional, Union, Type
# Importar sua rede e configs
#import agents.DeepPortfolioAgent as DeepPortfolioAgent
from DeepPortfolioAgent import DeepPortfolioAgentNetwork 
# from ..config import (NUM_ASSETS, WINDOW_SIZE, NUM_FEATURES_PER_ASSET, ...) # Importe do seu config real
# VALORES DE EXEMPLO (PEGUE DO SEU CONFIG.PY REAL)
NUM_ASSETS_POLICY = 4
WINDOW_SIZE_POLICY = 60
NUM_FEATURES_PER_ASSET_POLICY = 26
# Hiperparâmetros para DeepPortfolioAgentNetwork quando usada como extrator
ASSET_CNN_FILTERS1_POLICY = 32
ASSET_CNN_FILTERS2_POLICY = 64
ASSET_LSTM_UNITS1_POLICY = 64
ASSET_LSTM_UNITS2_POLICY = 32 # Esta será a dimensão das features latentes para ator/crítico
ASSET_DROPOUT_POLICY = 0.2
MHA_NUM_HEADS_POLICY = 4
MHA_KEY_DIM_DIVISOR_POLICY = 2 # Para key_dim = 32 // 2 = 16
FINAL_DENSE_UNITS1_POLICY = 128
FINAL_DENSE_UNITS2_POLICY = ASSET_LSTM_UNITS2_POLICY # A saída da dense2 SÃO as features latentes
FINAL_DROPOUT_POLICY = 0.3


class TFPortfolioFeaturesExtractor(tf.keras.layers.Layer): # Herda de tf.keras.layers.Layer
    """
    Extrator de features customizado para SB3 que usa DeepPortfolioAgentNetwork.
    A observação do ambiente é (batch, window, num_assets * num_features_per_asset).
    A saída são as features latentes (batch, latent_dim).
    """
    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = ASSET_LSTM_UNITS2_POLICY):
        super(TFPortfolioFeaturesExtractor, self).__init__()
        self.features_dim = features_dim # SB3 usa isso para saber o tamanho da saída

        # Instanciar a rede base para extrair features
        # Ela deve retornar as ativações ANTES da camada softmax de alocação.
        self.network = DeepPortfolioAgentNetwork(
            num_assets=NUM_ASSETS_POLICY,
            sequence_length=WINDOW_SIZE_POLICY,
            num_features_per_asset=NUM_FEATURES_PER_ASSET_POLICY,
            asset_cnn_filters1=ASSET_CNN_FILTERS1_POLICY, 
            asset_cnn_filters2=ASSET_CNN_FILTERS2_POLICY,
            asset_lstm_units1=ASSET_LSTM_UNITS1_POLICY, 
            asset_lstm_units2=ASSET_LSTM_UNITS2_POLICY, # Define a saída do asset_processor
            asset_dropout=ASSET_DROPOUT_POLICY,
            mha_num_heads=MHA_NUM_HEADS_POLICY, 
            mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR_POLICY,
            final_dense_units1=FINAL_DENSE_UNITS1_POLICY, 
            final_dense_units2=self.features_dim, # A saída da dense2 é a nossa feature latente
            final_dropout=FINAL_DROPOUT_POLICY,
            output_latent_features=True,
            use_sentiment_analysis=True # MUITO IMPORTANTE!
        )
        print("TFPortfolioFeaturesExtractor inicializado e usando DeepPortfolioAgentNetwork (output_latent_features=True).")

    def call(self, observations: tf.Tensor, training: bool = False) -> tf.Tensor:
        # A DeepPortfolioAgentNetwork já lida com o fatiamento e processamento.
        # Ela foi configurada para retornar features latentes.
        return self.network(observations, training=training)


class CustomPolicy(ActorCriticPolicy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mlp_extractor = CustomMlpExtractor(
            input_dim=self.observation_space.shape[0],
            net_arch=[64, 64],  # Exemplo de arquitetura
            activation_fn=nn.ReLU,
            device=self.device
        )



class CustomPortfolioPolicySB3(ActorCriticPolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule, # Função que retorna a taxa de aprendizado
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None, # Arquitetura para MLPs pós-extrator
        activation_fn: Type[tf.Module] = tf.nn.relu, # Usar tf.nn.relu para TF
        # Adicionar quaisquer outros parâmetros específicos que o extrator precise
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        if features_extractor_kwargs is None:
            features_extractor_kwargs = {}
        
        # A dimensão das features que o nosso extrator PortfolioFeatureExtractor vai cuspir.
        # Deve ser igual a ASSET_LSTM_UNITS2_POLICY (ou final_dense_units2 do extrator)
        # Se não for passado, o construtor do ActorCriticPolicy pode tentar inferir.
        # Vamos passar explicitamente para garantir.
        features_extractor_kwargs.setdefault("features_dim", ASSET_LSTM_UNITS2_POLICY) # Ou o valor que você definiu

        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Para camadas Dense APÓS o extrator de features
            activation_fn=activation_fn,
            features_extractor_class=TFPortfolioFeaturesExtractor,
            features_extractor_kwargs=features_extractor_kwargs,
            **kwargs,
        )
        # Otimizador é criado na classe base.
        # As redes de ator e crítico são construídas no método _build da classe base,
        # usando o self.features_extractor e depois o self.mlp_extractor (que é
        # construído com base no net_arch).

    # Não precisamos sobrescrever _build_mlp_extractor se o features_extractor
    # já fizer o trabalho pesado e o net_arch padrão para as cabeças for suficiente.
    # Se quisermos MLPs customizados para ator e crítico APÓS o extrator:
    # def _build_mlp_extractor(self) -> None:
    #     # self.mlp_extractor é uma instância de MlpExtractor (ou similar)
    #     # A entrada para ele é self.features_extractor.features_dim
    #     # Aqui, net_arch definiria a estrutura do mlp_extractor
    #     self.mlp_extractor = MlpExtractor(
    #         feature_dim=self.features_extractor.features_dim,
    #         net_arch=self.net_arch, # net_arch é uma lista de ints para camadas da política e valor
    #         activation_fn=self.activation_fn,
    #         device=self.device,
    #     )
    # As redes de ação e valor (action_net, value_net) são então criadas
    # no _build da classe ActorCriticPolicy, no topo do mlp_extractor.# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

import gymnasium as gym # Usar gymnasium
import tensorflow as tf
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor as PyTorchBaseFeaturesExtractor

from stable_baselines3.common.torch_layers import MlpExtractor
import torch.nn as nn

class CustomMlpExtractor(MlpExtractor):
    def __init__(self, input_dim, net_arch, activation_fn, device):
        super().__init__(input_dim, net_arch, activation_fn, device)

    def forward(self, features):
        for layer in self.policy_net:
            if isinstance(layer, nn.ReLU):
                features = layer(features)  # Passando 'features' como argumento
            else:
                features = layer(features)
        return features
# Para TensorFlow, precisamos de um extrator de features compatível ou construir a política de forma diferente.
# Stable Baselines3 tem melhor suporte nativo para PyTorch. Para TF, é um pouco mais manual.
# VAMOS USAR A ABORDAGEM DE POLÍTICA CUSTOMIZADA COM TF DIRETAMENTE.
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import List, Dict, Any, Optional, Union, Type
# Importar sua rede e configs
#import agents.DeepPortfolioAgent as DeepPortfolioAgent
from DeepPortfolioAgent import DeepPortfolioAgentNetwork 
# from ..config import (NUM_ASSETS, WINDOW_SIZE, NUM_FEATURES_PER_ASSET, ...) # Importe do seu config real
# VALORES DE EXEMPLO (PEGUE DO SEU CONFIG.PY REAL)
NUM_ASSETS_POLICY = 4
WINDOW_SIZE_POLICY = 60
NUM_FEATURES_PER_ASSET_POLICY = 26
# Hiperparâmetros para DeepPortfolioAgentNetwork quando usada como extrator
ASSET_CNN_FILTERS1_POLICY = 32
ASSET_CNN_FILTERS2_POLICY = 64
ASSET_LSTM_UNITS1_POLICY = 64
ASSET_LSTM_UNITS2_POLICY = 32 # Esta será a dimensão das features latentes para ator/crítico
ASSET_DROPOUT_POLICY = 0.2
MHA_NUM_HEADS_POLICY = 4
MHA_KEY_DIM_DIVISOR_POLICY = 2 # Para key_dim = 32 // 2 = 16
FINAL_DENSE_UNITS1_POLICY = 128
FINAL_DENSE_UNITS2_POLICY = ASSET_LSTM_UNITS2_POLICY # A saída da dense2 SÃO as features latentes
FINAL_DROPOUT_POLICY = 0.3


class TFPortfolioFeaturesExtractor(tf.keras.layers.Layer): # Herda de tf.keras.layers.Layer
    """
    Extrator de features customizado para SB3 que usa DeepPortfolioAgentNetwork.
    A observação do ambiente é (batch, window, num_assets * num_features_per_asset).
    A saída são as features latentes (batch, latent_dim).
    """
    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = ASSET_LSTM_UNITS2_POLICY):
        super(TFPortfolioFeaturesExtractor, self).__init__()
        self.features_dim = features_dim # SB3 usa isso para saber o tamanho da saída

        # Instanciar a rede base para extrair features
        # Ela deve retornar as ativações ANTES da camada softmax de alocação.
        self.network = DeepPortfolioAgentNetwork(
            num_assets=NUM_ASSETS_POLICY,
            sequence_length=WINDOW_SIZE_POLICY,
            num_features_per_asset=NUM_FEATURES_PER_ASSET_POLICY,
            asset_cnn_filters1=ASSET_CNN_FILTERS1_POLICY, 
            asset_cnn_filters2=ASSET_CNN_FILTERS2_POLICY,
            asset_lstm_units1=ASSET_LSTM_UNITS1_POLICY, 
            asset_lstm_units2=ASSET_LSTM_UNITS2_POLICY, # Define a saída do asset_processor
            asset_dropout=ASSET_DROPOUT_POLICY,
            mha_num_heads=MHA_NUM_HEADS_POLICY, 
            mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR_POLICY,
            final_dense_units1=FINAL_DENSE_UNITS1_POLICY, 
            final_dense_units2=self.features_dim, # A saída da dense2 é a nossa feature latente
            final_dropout=FINAL_DROPOUT_POLICY,
            output_latent_features=True,
            use_sentiment_analysis=True # MUITO IMPORTANTE!
        )
        print("TFPortfolioFeaturesExtractor inicializado e usando DeepPortfolioAgentNetwork (output_latent_features=True).")

    def call(self, observations: tf.Tensor, training: bool = False) -> tf.Tensor:
        # A DeepPortfolioAgentNetwork já lida com o fatiamento e processamento.
        # Ela foi configurada para retornar features latentes.
        return self.network(observations, training=training)


class CustomPolicy(ActorCriticPolicy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mlp_extractor = CustomMlpExtractor(
            input_dim=self.observation_space.shape[0],
            net_arch=[64, 64],  # Exemplo de arquitetura
            activation_fn=nn.ReLU,
            device=self.device
        )



class CustomPortfolioPolicySB3(ActorCriticPolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule, # Função que retorna a taxa de aprendizado
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None, # Arquitetura para MLPs pós-extrator
        activation_fn: Type[tf.Module] = tf.nn.relu, # Usar tf.nn.relu para TF
        # Adicionar quaisquer outros parâmetros específicos que o extrator precise
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        if features_extractor_kwargs is None:
            features_extractor_kwargs = {}
        
        # A dimensão das features que o nosso extrator PortfolioFeatureExtractor vai cuspir.
        # Deve ser igual a ASSET_LSTM_UNITS2_POLICY (ou final_dense_units2 do extrator)
        # Se não for passado, o construtor do ActorCriticPolicy pode tentar inferir.
        # Vamos passar explicitamente para garantir.
        features_extractor_kwargs.setdefault("features_dim", ASSET_LSTM_UNITS2_POLICY) # Ou o valor que você definiu

        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Para camadas Dense APÓS o extrator de features
            activation_fn=activation_fn,
            features_extractor_class=TFPortfolioFeaturesExtractor,
            features_extractor_kwargs=features_extractor_kwargs,
            **kwargs,
        )
        # Otimizador é criado na classe base.
        # As redes de ator e crítico são construídas no método _build da classe base,
        # usando o self.features_extractor e depois o self.mlp_extractor (que é
        # construído com base no net_arch).

    # Não precisamos sobrescrever _build_mlp_extractor se o features_extractor
    # já fizer o trabalho pesado e o net_arch padrão para as cabeças for suficiente.
    # Se quisermos MLPs customizados para ator e crítico APÓS o extrator:
    # def _build_mlp_extractor(self) -> None:
    #     # self.mlp_extractor é uma instância de MlpExtractor (ou similar)
    #     # A entrada para ele é self.features_extractor.features_dim
    #     # Aqui, net_arch definiria a estrutura do mlp_extractor
    #     self.mlp_extractor = MlpExtractor(
    #         feature_dim=self.features_extractor.features_dim,
    #         net_arch=self.net_arch, # net_arch é uma lista de ints para camadas da política e valor
    #         activation_fn=self.activation_fn,
    #         device=self.device,
    #     )
    # As redes de ação e valor (action_net, value_net) são então criadas
    # no _build da classe ActorCriticPolicy, no topo do mlp_extractor.# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

import gymnasium as gym # Usar gymnasium
import tensorflow as tf
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor as PyTorchBaseFeaturesExtractor

from stable_baselines3.common.torch_layers import MlpExtractor
import torch.nn as nn

class CustomMlpExtractor(MlpExtractor):
    def __init__(self, input_dim, net_arch, activation_fn, device):
        super().__init__(input_dim, net_arch, activation_fn, device)

    def forward(self, features):
        for layer in self.policy_net:
            if isinstance(layer, nn.ReLU):
                features = layer(features)  # Passando 'features' como argumento
            else:
                features = layer(features)
        return features
# Para TensorFlow, precisamos de um extrator de features compatível ou construir a política de forma diferente.
# Stable Baselines3 tem melhor suporte nativo para PyTorch. Para TF, é um pouco mais manual.
# VAMOS USAR A ABORDAGEM DE POLÍTICA CUSTOMIZADA COM TF DIRETAMENTE.
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import List, Dict, Any, Optional, Union, Type
# Importar sua rede e configs
#import agents.DeepPortfolioAgent as DeepPortfolioAgent
from DeepPortfolioAgent import DeepPortfolioAgentNetwork 
# from ..config import (NUM_ASSETS, WINDOW_SIZE, NUM_FEATURES_PER_ASSET, ...) # Importe do seu config real
# VALORES DE EXEMPLO (PEGUE DO SEU CONFIG.PY REAL)
NUM_ASSETS_POLICY = 4
WINDOW_SIZE_POLICY = 60
NUM_FEATURES_PER_ASSET_POLICY = 26
# Hiperparâmetros para DeepPortfolioAgentNetwork quando usada como extrator
ASSET_CNN_FILTERS1_POLICY = 32
ASSET_CNN_FILTERS2_POLICY = 64
ASSET_LSTM_UNITS1_POLICY = 64
ASSET_LSTM_UNITS2_POLICY = 32 # Esta será a dimensão das features latentes para ator/crítico
ASSET_DROPOUT_POLICY = 0.2
MHA_NUM_HEADS_POLICY = 4
MHA_KEY_DIM_DIVISOR_POLICY = 2 # Para key_dim = 32 // 2 = 16
FINAL_DENSE_UNITS1_POLICY = 128
FINAL_DENSE_UNITS2_POLICY = ASSET_LSTM_UNITS2_POLICY # A saída da dense2 SÃO as features latentes
FINAL_DROPOUT_POLICY = 0.3


class TFPortfolioFeaturesExtractor(tf.keras.layers.Layer): # Herda de tf.keras.layers.Layer
    """
    Extrator de features customizado para SB3 que usa DeepPortfolioAgentNetwork.
    A observação do ambiente é (batch, window, num_assets * num_features_per_asset).
    A saída são as features latentes (batch, latent_dim).
    """
    def __init__(self, observation_space: gym.spaces.Box, features_dim: int = ASSET_LSTM_UNITS2_POLICY):
        super(TFPortfolioFeaturesExtractor, self).__init__()
        self.features_dim = features_dim # SB3 usa isso para saber o tamanho da saída

        # Instanciar a rede base para extrair features
        # Ela deve retornar as ativações ANTES da camada softmax de alocação.
        self.network = DeepPortfolioAgentNetwork(
            num_assets=NUM_ASSETS_POLICY,
            sequence_length=WINDOW_SIZE_POLICY,
            num_features_per_asset=NUM_FEATURES_PER_ASSET_POLICY,
            asset_cnn_filters1=ASSET_CNN_FILTERS1_POLICY, 
            asset_cnn_filters2=ASSET_CNN_FILTERS2_POLICY,
            asset_lstm_units1=ASSET_LSTM_UNITS1_POLICY, 
            asset_lstm_units2=ASSET_LSTM_UNITS2_POLICY, # Define a saída do asset_processor
            asset_dropout=ASSET_DROPOUT_POLICY,
            mha_num_heads=MHA_NUM_HEADS_POLICY, 
            mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR_POLICY,
            final_dense_units1=FINAL_DENSE_UNITS1_POLICY, 
            final_dense_units2=self.features_dim, # A saída da dense2 é a nossa feature latente
            final_dropout=FINAL_DROPOUT_POLICY,
            output_latent_features=True,
            use_sentiment_analysis=True # MUITO IMPORTANTE!
        )
        print("TFPortfolioFeaturesExtractor inicializado e usando DeepPortfolioAgentNetwork (output_latent_features=True).")

    def call(self, observations: tf.Tensor, training: bool = False) -> tf.Tensor:
        # A DeepPortfolioAgentNetwork já lida com o fatiamento e processamento.
        # Ela foi configurada para retornar features latentes.
        return self.network(observations, training=training)


class CustomPolicy(ActorCriticPolicy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mlp_extractor = CustomMlpExtractor(
            input_dim=self.observation_space.shape[0],
            net_arch=[64, 64],  # Exemplo de arquitetura
            activation_fn=nn.ReLU,
            device=self.device
        )



class CustomPortfolioPolicySB3(ActorCriticPolicy):
    def __init__(
        self,
        observation_space: gym.spaces.Space,
        action_space: gym.spaces.Space,
        lr_schedule, # Função que retorna a taxa de aprendizado
        net_arch: Optional[List[Union[int, Dict[str, List[int]]]]] = None, # Arquitetura para MLPs pós-extrator
        activation_fn: Type[tf.Module] = tf.nn.relu, # Usar tf.nn.relu para TF
        # Adicionar quaisquer outros parâmetros específicos que o extrator precise
        features_extractor_kwargs: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        if features_extractor_kwargs is None:
            features_extractor_kwargs = {}
        
        # A dimensão das features que o nosso extrator PortfolioFeatureExtractor vai cuspir.
        # Deve ser igual a ASSET_LSTM_UNITS2_POLICY (ou final_dense_units2 do extrator)
        # Se não for passado, o construtor do ActorCriticPolicy pode tentar inferir.
        # Vamos passar explicitamente para garantir.
        features_extractor_kwargs.setdefault("features_dim", ASSET_LSTM_UNITS2_POLICY) # Ou o valor que você definiu

        super().__init__(
            observation_space,
            action_space,
            lr_schedule,
            net_arch=net_arch, # Para camadas Dense APÓS o extrator de features
            activation_fn=activation_fn,
            features_extractor_class=TFPortfolioFeaturesExtractor,
            features_extractor_kwargs=features_extractor_kwargs,
            **kwargs,
        )
        # Otimizador é criado na classe base.
        # As redes de ator e crítico são construídas no método _build da classe base,
        # usando o self.features_extractor e depois o self.mlp_extractor (que é
        # construído com base no net_arch).

    # Não precisamos sobrescrever _build_mlp_extractor se o features_extractor
    # já fizer o trabalho pesado e o net_arch padrão para as cabeças for suficiente.
    # Se quisermos MLPs customizados para ator e crítico APÓS o extrator:
    # def _build_mlp_extractor(self) -> None:
    #     # self.mlp_extractor é uma instância de MlpExtractor (ou similar)
    #     # A entrada para ele é self.features_extractor.features_dim
    #     # Aqui, net_arch definiria a estrutura do mlp_extractor
    #     self.mlp_extractor = MlpExtractor(
    #         feature_dim=self.features_extractor.features_dim,
    #         net_arch=self.net_arch, # net_arch é uma lista de ints para camadas da política e valor
    #         activation_fn=self.activation_fn,
    #         device=self.device,
    #     )
    # As redes de ação e valor (action_net, value_net) são então criadas
    # no _build da classe ActorCriticPolicy, no topo do mlp_extractor.

from custom_policies import CustomPortfolioPolicy # Importar a política customizada
#from .deep_portfolio import NUM_ASSETS_CONF, WINDOW_SIZE_CONF, NUM_FEATURES_PER_ASSET_CONF # Se precisar para policy_kwargs
# (Importe as configs do config.py)
#from ..config import LEARNING_RATE as PPO_LEARNING_RATE 
PPO_LEARNING_RATE = 0.0005


try:
    from data_handler_multi_asset import get_multi_asset_data_for_rl, MULTI_ASSET_SYMBOLS # Do seu config/data_handler
    from portfolio_environment import PortfolioEnv 
    from deep_portfolio import DeepPortfolioAI # Seu modelo (usado como policy)
except Exception:
    # Fallback: if agents/data_handler_multi_asset cannot be imported (pandas_ta missing, etc.),
    # build a small synthetic multi-asset dataframe using the new-rede-a data handler.
    print('Aviso: agents.data_handler_multi_asset import failed, using synthetic multi-asset fallback for smoke run.')
    from new_rede_a_portable_import import load_portable
    portable = load_portable()
    # Inject lightweight dummy modules to satisfy optional external libs used by the data handler
    import types, sys as _sys
    if 'alpha_vantage' not in _sys.modules:
        alpha_mod = types.ModuleType('alpha_vantage')
        ts_mod = types.ModuleType('alpha_vantage.timeseries')
        fx_mod = types.ModuleType('alpha_vantage.foreignexchange')
        cc_mod = types.ModuleType('alpha_vantage.cryptocurrencies')
        class TimeSeries:
            def __init__(self, *a, **k): pass
        class ForeignExchange:
            def __init__(self, *a, **k): pass
        class CryptoCurrencies:
            def __init__(self, *a, **k): pass
        ts_mod.TimeSeries = TimeSeries
        fx_mod.ForeignExchange = ForeignExchange
        cc_mod.CryptoCurrencies = CryptoCurrencies
        _sys.modules['alpha_vantage'] = alpha_mod
        _sys.modules['alpha_vantage.timeseries'] = ts_mod
        _sys.modules['alpha_vantage.foreignexchange'] = fx_mod
        _sys.modules['alpha_vantage.cryptocurrencies'] = cc_mod
    if 'twelvedata' not in _sys.modules:
        td_mod = types.ModuleType('twelvedata')
        class TDClient:
            def __init__(self, *a, **k): pass
        td_mod.TDClient = TDClient
        _sys.modules['twelvedata'] = td_mod
    newdh = portable.load_module('new-rede-a.data_handler_multi_asset')
    PortfolioEnv = getattr(portable.load_module('new-rede-a.portfolio_environment'), 'PortfolioEnv')
    DeepPortfolioAI = None
    # Build synthetic multi-asset features
    MULTI_ASSET_SYMBOLS = {'asset_a': 'A', 'asset_b': 'B', 'asset_c': 'C'}
    def get_multi_asset_data_for_rl(asset_symbols_map, timeframe_yf, days_to_fetch, logger_instance=None):
        import pandas as _pd
        import numpy as _np
        dfs = []
        for key in asset_symbols_map.keys():
            idx = _pd.date_range('2023-01-01', periods=600, freq='H')
            df_ohlcv = _pd.DataFrame({
                'open': _np.linspace(100, 120, len(idx)) + _np.random.randn(len(idx)) * 0.5,
                'high': _np.linspace(100.5, 120.5, len(idx)) + _np.random.randn(len(idx)) * 0.6,
                'low': _np.linspace(99.5, 119.5, len(idx)) + _np.random.randn(len(idx)) * 0.6,
                'close': _np.linspace(100, 120, len(idx)) + _np.random.randn(len(idx)) * 0.55,
                'volume': (_np.random.randint(100, 1000, size=len(idx))).astype(float)
            }, index=idx)
            feats = newdh.calculate_all_features_for_single_asset(df_ohlcv)
            if feats is None:
                continue
            feats = feats.add_prefix(f"{key}_")
            # add original close
            feats[f"{key}_close"] = df_ohlcv['close'].values[:len(feats)]
            dfs.append(feats)
        if not dfs:
            return _pd.DataFrame()
        # Outer join on index-like by concatenation; align by position
        combined = _pd.concat(dfs, axis=1, join='outer')
        combined.fillna(method='ffill', inplace=True)
        combined.dropna(inplace=True)
        return combined
# from config import ... # Outras configs

RISK_FREE_RATE_ANNUAL = 0.2
REWARD_WINDOW = 252
frisk_free_per_step = 0.0 

# Janela de recompensa para Sharpe (ex: últimos 60 passos/horas)
# Deve ser menor ou igual ao ep_len_mean ou um valor razoável
reward_calc_window = 60

# 1. Carregar e preparar dados multi-ativos
# (MULTI_ASSET_SYMBOLS viria do config.py)
asset_keys_list = list(MULTI_ASSET_SYMBOLS.keys()) # ['crypto_eth', 'crypto_ada', ...]

multi_asset_df = get_multi_asset_data_for_rl(
    MULTI_ASSET_SYMBOLS, 
    timeframe_yf='1h', # Ou TIMEFRAME_YFINANCE do config
    days_to_fetch=365*2,
    logger_instance=any
    # Ou DAYS_TO_FETCH do config
)

print("Imprimindo retorno para df_combined passado para train_rl_portifolio")
print(multi_asset_df)


#-------------------

if multi_asset_df is None or multi_asset_df.empty:
    print("Falha ao carregar dados multi-ativos. Encerrando treinamento RL.")
    exit()
# Fit and save RL scalers (price/volume and indicator scalers) using the adapter
try:
    print("Fitting RL scalers on multi-asset features (this may take a moment)...")
    multi_asset_df, scaler_info = fit_and_create_scaled(multi_asset_df, save_scalers=True)
    print("Scalers fit and saved:", scaler_info)
except Exception as e:
    print("Aviso: falha ao ajustar/salvar scalers RL:", e)

# Ensure the dataframe contains the '<symbol>_close' columns the env expects.
required_symbols = None
# If portable loader is available (fallback path), prefer its config
if 'portable' in globals():
    try:
        cfgm = portable.load_module('new-rede-a.config')
        required_symbols = getattr(cfgm, 'ALL_ASSET_SYMBOLS', None)
    except Exception:
        required_symbols = None
if required_symbols is None:
    required_symbols = asset_keys_list

expected_close_cols = [f"{k}_close" for k in required_symbols]
existing_close_cols = [c for c in multi_asset_df.columns if str(c).endswith('_close')]
if existing_close_cols:
    for i, col in enumerate(expected_close_cols):
        if col not in multi_asset_df.columns:
            src = existing_close_cols[i % len(existing_close_cols)]
            multi_asset_df[col] = multi_asset_df[src].values
else:
    # fallback: create close columns from numeric cols or constants
    numeric_cols = [c for c in multi_asset_df.columns if pd.api.types.is_numeric_dtype(multi_asset_df[c])]
    for i, col in enumerate(expected_close_cols):
        src = numeric_cols[i % len(numeric_cols)] if numeric_cols else None
        if src:
            multi_asset_df[col] = multi_asset_df[src].values
        else:
            multi_asset_df[col] = 1.0

# Instantiate the environment using the scaled feature dataframe
try:
    env = PortfolioEnv(df_multi_asset_features=multi_asset_df, initial_balance=100000)
except TypeError:
    env = PortfolioEnv(multi_asset_df)
print("Ambiente de Portfólio Criado.")

# --- Usar a Política Customizada ---
# Hiperparâmetros para o PPO
learning_rate_ppo = PPO_LEARNING_RATE # Ex: 3e-4 ou 1e-4 (do config.py)
n_steps_ppo = 2048 
batch_size_ppo = 64
ent_coef_ppo = 0.0 

# policy_kwargs para passar para o __init__ da CustomPortfolioPolicySB3, se necessário
# (além dos que já são passados para o features_extractor_kwargs)
# Exemplo: Se você adicionou mais args ao __init__ de CustomPortfolioPolicySB3
# policy_custom_kwargs = dict(
#    meu_parametro_customizado=valor,
#    # features_extractor_kwargs já é tratado pela classe base se você passar features_extractor_class
# )

print("Instanciando PPO com Política Customizada (DeepPortfolioAgentNetwork)...")
# Prefer PyTorch-based extractor when available (new-rede-a provides a PyTorch extractor)
try:
    # Build policy_kwargs to pass to SB3 so it uses the PyTorch extractor
    from new_rede_a_portable_import import load_portable
    portable_local = load_portable()
    # Try to import the torch-based extractor
    PortfolioFeaturesExtractorTorch = getattr(portable_local.load_module('new-rede-a.portfolio_features_extractor_torch'), 'PortfolioFeaturesExtractorTorch')
    # Network kwargs: match the DeepPortfolioAgentNetworkTorch constructor signature
    policy_kwargs = dict(
        features_extractor_class=PortfolioFeaturesExtractorTorch,
        features_extractor_kwargs=dict(
            features_dim=32, # latent dim, adapt if needed
            num_assets=len(asset_keys_list),
            num_features_per_asset=NUM_FEATURES_PER_ASSET_POLICY,
            sequence_length=WINDOW_SIZE_POLICY,
            asset_cnn_filters1=ASSET_CNN_FILTERS1_POLICY,
            asset_cnn_filters2=ASSET_CNN_FILTERS2_POLICY,
            asset_lstm_units1=ASSET_LSTM_UNITS1_POLICY,
            asset_lstm_units2=ASSET_LSTM_UNITS2_POLICY,
            asset_dropout=ASSET_DROPOUT_POLICY,
            mha_num_heads=MHA_NUM_HEADS_POLICY,
            mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR_POLICY,
            final_dense_units1=FINAL_DENSE_UNITS1_POLICY,
            final_dense_units2=FINAL_DENSE_UNITS2_POLICY,
            final_dropout=FINAL_DROPOUT_POLICY,
        ),
    )

    model_ppo = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=learning_rate_ppo,
        n_steps=n_steps_ppo,
        batch_size=batch_size_ppo,
        ent_coef=ent_coef_ppo,
        policy_kwargs=policy_kwargs,
        tensorboard_log="./ppo_deep_portfolio_tensorboard/",
    )
    print("Usando extractor PyTorch (PortfolioFeaturesExtractorTorch) como features_extractor_class.")
except Exception as e:
    print("Aviso: não foi possível usar o extractor PyTorch — usando fallback MlpPolicy. Erro:", e)
    model_ppo = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=learning_rate_ppo,
        n_steps=n_steps_ppo,
        batch_size=batch_size_ppo,
        ent_coef=ent_coef_ppo,
        tensorboard_log="./ppo_deep_portfolio_tensorboard/",
    )

print("Iniciando treinamento do agente PPO com rede customizada...")
# For smoke tests, allow overriding with SMOKE_TIMESTEPS env var. Default to 5000 timesteps.
smoke_env_ts = int(os.getenv('SMOKE_TIMESTEPS', '5000'))
try:
    configured_total = int(os.getenv('PPO_TOTAL_TIMESTEPS', 1000000))
except Exception:
    configured_total = 1000000
total_timesteps_to_run = min(smoke_env_ts, configured_total)
print(f"Starting PPO.learn for {total_timesteps_to_run} timesteps (smoke run)")
model_ppo.learn(total_timesteps=total_timesteps_to_run, progress_bar=True)
# Save model and any VecNormalize stats to the configured model directory
try:
    import agents.config as aconf
except Exception:
    aconf = None
try:
    import scripts.config as sconf
except Exception:
    sconf = None

model_root = None
if aconf is not None and hasattr(aconf, 'MODEL_ROOT_DIR'):
    model_root = Path(aconf.MODEL_ROOT_DIR)
elif sconf is not None and hasattr(sconf, 'MODEL_SAVE_DIR'):
    model_root = Path(sconf.MODEL_SAVE_DIR)
else:
    model_root = Path('app/model')

model_root.mkdir(parents=True, exist_ok=True)

model_path = model_root / (getattr(aconf, 'RL_AGENT_MODEL_NAME', 'ppo_custom_deep_portfolio_agent'))
try:
    model_ppo.save(str(model_path))
    print(f"Modelo RL salvo em: {model_path}")
except Exception as e:
    print("Aviso: falha ao salvar modelo RL no model_root, salvando localmente.", e)
    model_ppo.save("app/model/ppo_custom_deep_portfolio_agent")

# If VecNormalize wrapper used, try to save its stats
try:
    from stable_baselines3.common.vec_env import VecNormalize
    if isinstance(env, VecNormalize):
        stats_path = model_root / getattr(aconf, 'VEC_NORMALIZE_STATS_FILENAME', 'vec_normalize_stats.pkl')
        env.save(str(stats_path))
        print(f"VecNormalize stats salvos em: {stats_path}")
except Exception:
    pass

print("Modelo RL com política customizada treinado e salvo.")



#----------




# if multi_asset_df is None or multi_asset_df.empty:
#     print("Falha ao carregar dados multi-ativos. Encerrando treinamento RL.")
#     exit()

# # 2. Criar o Ambiente
# # O multi_asset_df já deve ter as features para observação E as colunas de preço de close original
# env = PortfolioEnv(df_multi_asset_features=multi_asset_df, asset_symbols_list=asset_keys_list)


# risk_free_per_step = 0.0 

# # Janela de recompensa para Sharpe (ex: últimos 60 passos/horas)
# # Deve ser menor ou igual ao ep_len_mean ou um valor razoável
# reward_calc_window = 60

# env = PortfolioEnv(
#     df_multi_asset_features=multi_asset_df, 
#     asset_symbols_list=asset_keys_list,
#     initial_balance=100000, # Do config
#     window_size=60, # Do config
#     transaction_cost_pct=0.001, # Do config ou defina aqui
#     reward_window_size=reward_calc_window,
#     risk_free_rate_per_step=risk_free_per_step
# )

# # Opcional: Verificar se o ambiente está em conformidade com a API do Gymnasium
# # check_env(env) # Pode dar avisos/erros se algo estiver errado
# print("Ambiente de Portfólio Criado.")
# print(f"Observation Space: {env.observation_space.shape}")
# print(f"Action Space: {env.action_space.shape}")




# # 3. Definir a Política de Rede Neural
# # Stable-Baselines3 permite que você defina uma arquitetura customizada.
# # Precisamos de uma forma de passar sua arquitetura DeepPortfolioAI para o PPO.
# # Uma maneira é criar uma classe de política customizada.
# # Por agora, vamos usar a política padrão "MlpPolicy" e depois vemos como integrar a sua.
# # Ou, se DeepPortfolioAI for uma tf.keras.Model, podemos tentar usá-la em policy_kwargs.

# # Para usar sua DeepPortfolioAI, você precisaria de uma FeatureExtractor customizada
# # ou uma política que a incorpore, o que é mais avançado com Stable-Baselines3.
# # Vamos começar com MlpPolicy para testar o ambiente.

# # policy_kwargs = dict(
# #     features_extractor_class=YourCustomFeatureExtractor, # Se a entrada precisar de tratamento especial
# #     features_extractor_kwargs=dict(features_dim=128),
# #     net_arch=[dict(pi=[256, 128], vf=[256, 128])] # Exemplo de arquitetura para policy e value networks
# # )
# # Ou, se o DeepPortfolioAI puder ser adaptado para ser a policy_network:
# policy_kwargs = dict(
#    net_arch=dict(
#        pi=[{'model': DeepPortfolioAI(num_assets=env.num_assets)}], # Não é direto assim
#        vf=[] # Value function pode ser separada ou compartilhada
#    )
# )

# # Para começar e testar o ambiente, use a MlpPolicy padrão.
# # O input da MlpPolicy será a observação achatada (WINDOW_SIZE * num_total_features).
# # Isso pode não ser ideal para dados sequenciais. "MlpLstmPolicy" é melhor.

# model_ppo = PPO("MlpPolicy", env, verbose=1, ent_coef=0.01, tensorboard_log="./ppo_portfolio_tensorboard/")
# # Se "MlpLstmPolicy" não funcionar bem com o shape da observação (janela, features_totais),
# # você pode precisar de um FeatureExtractor que achate a janela, ou uma política customizada.

# # 4. Treinar o Agente
# print("Iniciando treinamento do agente PPO...")
# model_ppo.learn(total_timesteps=int("1000000"), progress_bar=True) # Aumente timesteps para treino real

# # 5. Salvar o Modelo Treinado
# model_ppo.save("rl_models/ppo_deep_portfolio_agent")
# print("Modelo RL treinado salvo.")


# # (Opcional) Testar o agente treinado
# obs, _ = env.reset()
# for _ in range(200):
#     action, _states = model_ppo.predict(obs, deterministic=True)
#     obs, rewards, terminated, truncated, info = env.step(action)
#     env.render()
#     if terminated or truncated:
#         obs, _ = env.reset()
# env.close()