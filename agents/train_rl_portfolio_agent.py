# train_rl_portfolio_agent.py
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env
#from transformers import logger

# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

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


from data_handler_multi_asset import get_multi_asset_data_for_rl, MULTI_ASSET_SYMBOLS # Do seu config/data_handler
from portfolio_environment import PortfolioEnv 
from deep_portfolio import DeepPortfolioAI # Seu modelo (usado como policy)
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

env = PortfolioEnv(df_multi_asset_features=multi_asset_df, asset_symbols_list=asset_keys_list) 
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
model_ppo = PPO(
    CustomPortfolioPolicySB3, 
    env, 
    verbose=1, 
    learning_rate=learning_rate_ppo, # Pode ser uma função lr_schedule
    n_steps=n_steps_ppo,
    batch_size=batch_size_ppo,
    ent_coef=ent_coef_ppo,
    # policy_kwargs=policy_custom_kwargs, # Se tiver kwargs específicos para a política
    tensorboard_log="./ppo_deep_portfolio_tensorboard/"
)

print("Iniciando treinamento do agente PPO com rede customizada...")
model_ppo.learn(total_timesteps=1000000, progress_bar=True) # Comece com menos timesteps para teste (ex: 50k)

model_ppo.save("app/model/ppo_custom_deep_portfolio_agent")
print("Modelo RL com política customizada treinado e salvo.")

model_ppo.save("app/model/model3")
print("Modelo RL com política customizada treinado e salvo.")

model_ppo.save("app/model/model2.h5")
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