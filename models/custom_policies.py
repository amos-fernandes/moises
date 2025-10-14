# rnn/agents/custom_policies.py (NOVO ARQUIVO, ou adicione ao deep_portfolio.py)

import gymnasium as gym # Usar gymnasium
import tensorflow as tf
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor as PyTorchBaseFeaturesExtractor
# Para TensorFlow, precisamos de um extrator de features compatível ou construir a política de forma diferente.
# Stable Baselines3 tem melhor suporte nativo para PyTorch. Para TF, é um pouco mais manual.
# VAMOS USAR A ABORDAGEM DE POLÍTICA CUSTOMIZADA COM TF DIRETAMENTE.
from stable_baselines3.common.policies import ActorCriticPolicy
from typing import List, Dict, Any, Union, Type
# Importar sua rede e configs
from .deep_portfolio import DeepPortfolioAgentNetwork 
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
            output_latent_features=True # MUITO IMPORTANTE!
        )
        print("TFPortfolioFeaturesExtractor inicializado e usando DeepPortfolioAgentNetwork (output_latent_features=True).")

    def call(self, observations: tf.Tensor, training: bool = False) -> tf.Tensor:
        # A DeepPortfolioAgentNetwork já lida com o fatiamento e processamento.
        # Ela foi configurada para retornar features latentes.
        return self.network(observations, training=training)






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