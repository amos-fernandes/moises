import numpy as np
from tensorflow.keras import regularizers
import tensorflow as tf
from tensorflow.keras.layers import (
    Input, Conv1D, LSTM, Dense, Dropout, 
    MultiHeadAttention, Reshape, Concatenate,
    TimeDistributed, GlobalAveragePooling1D, LayerNormalization
)
from tensorflow.keras.models import Model
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para permitir importações relativas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar do config.py
from config import (
    WINDOW_SIZE, NUM_ASSETS, NUM_FEATURES_PER_ASSET, L2_REG,
    ASSET_CNN_FILTERS1, ASSET_CNN_FILTERS2, ASSET_LSTM_UNITS1, ASSET_LSTM_UNITS2,
    ASSET_DROPOUT, MHA_NUM_HEADS, MHA_KEY_DIM_DIVISOR, FINAL_DENSE_UNITS1,
    FINAL_DENSE_UNITS2, FINAL_DROPOUT, USE_SENTIMENT_ANALYSIS
)

class AssetProcessor(tf.keras.Model):
    def __init__(self, sequence_length, num_features, cnn_filters1=ASSET_CNN_FILTERS1, cnn_filters2=ASSET_CNN_FILTERS2, lstm_units1=ASSET_LSTM_UNITS1, lstm_units2=ASSET_LSTM_UNITS2, dropout_rate=ASSET_DROPOUT, name="single_asset_processor_module", **kwargs):
        super(AssetProcessor, self).__init__(name=name, **kwargs)
        self.sequence_length = sequence_length
        self.num_features = num_features
        self.cnn_filters1 = cnn_filters1
        self.cnn_filters2 = cnn_filters2
        self.lstm_units1 = lstm_units1
        self.lstm_units2 = lstm_units2
        self.dropout_rate = dropout_rate
        
        self.conv1 = Conv1D(filters=cnn_filters1, kernel_size=3, activation='relu', padding='same', name="asset_cnn1")
        self.dropout_cnn1 = Dropout(dropout_rate, name="asset_cnn1_dropout")
        self.conv2 = Conv1D(filters=cnn_filters2, kernel_size=3, activation='relu', padding='same', name="asset_cnn2")
        self.dropout_cnn2 = Dropout(dropout_rate, name="asset_cnn2_dropout")
        self.lstm1 = LSTM(lstm_units1, return_sequences=True, name="asset_lstm1")
        self.dropout_lstm1 = Dropout(dropout_rate, name="asset_lstm1_dropout")
        self.lstm2 = LSTM(lstm_units2, return_sequences=False, name="asset_lstm2_final")
        self.dropout_lstm2 = Dropout(dropout_rate, name="asset_lstm2_dropout")

    def call(self, inputs, training=False):
        x = self.conv1(inputs)
        x = self.dropout_cnn1(x, training=training)
        x = self.conv2(x)
        x = self.dropout_cnn2(x, training=training)
        x = self.lstm1(x, training=training)
        x = self.dropout_lstm1(x, training=training)
        x = self.lstm2(x, training=training)
        x_processed_asset = self.dropout_lstm2(x, training=training)
        x_processed_asset = LayerNormalization(epsilon=1e-6)(x_processed_asset) # Normalize output
        return x_processed_asset

    def get_config(self):
        config = super().get_config()
        config.update({
            "sequence_length": self.sequence_length,
            "num_features": self.num_features,
            "cnn_filters1": self.cnn_filters1,
            "cnn_filters2": self.cnn_filters2,
            "lstm_units1": self.lstm_units1,
            "lstm_units2": self.lstm_units2,
            "dropout_rate": self.dropout_rate,
        })
        return config

class DeepPortfolioAgentNetwork(tf.keras.Model):
    def __init__(self, 
                 num_assets=NUM_ASSETS, 
                 sequence_length=WINDOW_SIZE, 
                 num_features_per_asset=NUM_FEATURES_PER_ASSET,
                 asset_cnn_filters1=ASSET_CNN_FILTERS1, asset_cnn_filters2=ASSET_CNN_FILTERS2, 
                 asset_lstm_units1=ASSET_LSTM_UNITS1, asset_lstm_units2=ASSET_LSTM_UNITS2, asset_dropout=ASSET_DROPOUT,
                 mha_num_heads=MHA_NUM_HEADS, mha_key_dim_divisor=MHA_KEY_DIM_DIVISOR,
                 final_dense_units1=FINAL_DENSE_UNITS1, final_dense_units2=FINAL_DENSE_UNITS2, final_dropout=FINAL_DROPOUT,
                 use_sentiment_analysis=USE_SENTIMENT_ANALYSIS, 
                 output_latent_features=False, **kwargs):
        super(DeepPortfolioAgentNetwork, self).__init__(name="deep_portfolio_agent_network", **kwargs)
        
        self.num_assets = num_assets
        self.sequence_length = sequence_length
        self.num_features_per_asset = num_features_per_asset
        self.asset_lstm_output_dim = asset_lstm_units2

        self.asset_processor = AssetProcessor(
            sequence_length=self.sequence_length, num_features=self.num_features_per_asset,
            cnn_filters1=asset_cnn_filters1, cnn_filters2=asset_cnn_filters2,
            lstm_units1=asset_lstm_units1, lstm_units2=asset_lstm_units2,
            dropout_rate=asset_dropout
        )
        
        calculated_key_dim = self.asset_lstm_output_dim // mha_key_dim_divisor 
        if calculated_key_dim == 0:
            calculated_key_dim = self.asset_lstm_output_dim
            print(f"AVISO: asset_lstm_output_dim ({self.asset_lstm_output_dim}) muito pequeno para mha_key_dim_divisor ({mha_key_dim_divisor}). Usando key_dim = {calculated_key_dim}")

        self.attention = MultiHeadAttention(num_heads=mha_num_heads, key_dim=calculated_key_dim, dropout=0.1, name="multi_asset_attention")
        self.attention_norm = LayerNormalization(epsilon=1e-6, name="attention_layernorm")
        self.global_avg_pool_attention = GlobalAveragePooling1D(name="gap_after_attention")

        self.use_sentiment = use_sentiment_analysis
        self.sentiment_embedding_size = 3 
        if self.use_sentiment:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained('ProsusAI/finbert')
                self.sentiment_model = TFAutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert', from_pt=True)
                print("Modelo FinBERT carregado para análise de sentimento.")
            except Exception as e:
                print(f"AVISO: Falha ao carregar FinBERT: {e}. Análise de sentimento será desabilitada.")
                self.use_sentiment = False

        self.output_latent_features = output_latent_features
        
        self.dense1 = Dense(final_dense_units1, activation='relu', kernel_regularizer=regularizers.l2(L2_REG), name="final_dense1")
        self.dropout1 = Dropout(final_dropout, name="final_dropout1")
        self.dense2 = Dense(final_dense_units2, activation='relu', kernel_regularizer=regularizers.l2(L2_REG), name="final_dense2")
        self.dropout2 = Dropout(final_dropout, name="final_dropout2")
        self.output_allocation = Dense(self.num_assets, activation='softmax', name="portfolio_allocation_output")

    def call(self, inputs, training=False):
        # inputs shape: (batch_size, sequence_length, num_assets * num_features_per_asset)
        market_data_flat = inputs 
        
        asset_representations_list = []
        for i in range(self.num_assets):
            start_idx = i * self.num_features_per_asset
            end_idx = (i + 1) * self.num_features_per_asset
            current_asset_data = market_data_flat[:, :, start_idx:end_idx]
            # current_asset_data = tf.debugging.check_numerics(current_asset_data, message=f"NaN/Inf found in current_asset_data for asset {i}") # Desabilitado para produção
            processed_asset_representation = self.asset_processor(current_asset_data, training=training)
            # processed_asset_representation = tf.debugging.check_numerics(processed_asset_representation, message=f"NaN/Inf found in processed_asset_representation for asset {i}") # Desabilitado para produção
            asset_representations_list.append(processed_asset_representation)
            
        stacked_asset_features = tf.stack(asset_representations_list, axis=1)
        
        attention_output = self.attention(
            query=stacked_asset_features, value=stacked_asset_features, key=stacked_asset_features,
            training=training
        )
        attention_output = self.attention_norm(stacked_asset_features + attention_output) 
        
        context_vector_from_attention = self.global_avg_pool_attention(attention_output)
        
        current_features_for_dense = context_vector_from_attention

        if self.output_latent_features:
            return current_features_for_dense

        x = self.dense1(current_features_for_dense)
        x = self.dropout1(x, training=training)
        x = self.dense2(x)
        x = self.dropout2(x, training=training)
        
        portfolio_weights = self.output_allocation(x)
        return portfolio_weights

    def get_config(self):
        config = super().get_config()
        config.update({
            "num_assets": self.num_assets,
            "sequence_length": self.sequence_length,
            "num_features_per_asset": self.num_features_per_asset,
            "asset_cnn_filters1": ASSET_CNN_FILTERS1,
            "asset_cnn_filters2": ASSET_CNN_FILTERS2,
            "asset_lstm_units1": ASSET_LSTM_UNITS1,
            "asset_lstm_units2": ASSET_LSTM_UNITS2,
            "asset_dropout": ASSET_DROPOUT,
            "mha_num_heads": MHA_NUM_HEADS,
            "mha_key_dim_divisor": MHA_KEY_DIM_DIVISOR,
            "final_dense_units1": FINAL_DENSE_UNITS1,
            "final_dense_units2": FINAL_DENSE_UNITS2,
            "final_dropout": FINAL_DROPOUT,
            "use_sentiment_analysis": USE_SENTIMENT_ANALYSIS,
            "output_latent_features": self.output_latent_features,
        })
        return config


if __name__ == '__main__':
    print("Testando o Forward Pass do DeepPortfolioAgentNetwork...")

    # 1. Definir Parâmetros para o Teste (devem corresponder ao config.py)
    batch_size_test = 2
    seq_len_test = WINDOW_SIZE
    num_assets_test = NUM_ASSETS
    num_features_per_asset_test = NUM_FEATURES_PER_ASSET
    total_features_flat = num_assets_test * num_features_per_asset_test

    print(f"Configuração do Teste:")
    print(f"  Batch Size: {batch_size_test}")
    print(f"  Sequence Length (Window): {seq_len_test}")
    print(f"  Number of Assets: {num_assets_test}")
    print(f"  Features per Asset: {num_features_per_asset_test}")
    print(f"  Total Flat Features per Timestep: {total_features_flat}")

    # 2. Criar Tensor de Input Mockado
    mock_market_data_flat = tf.random.normal(
        shape=(batch_size_test, seq_len_test, total_features_flat)
    )
    print(f"Shape do Input Mockado (market_data_flat): {mock_market_data_flat.shape}")

    # 3. Instanciar o Modelo
    print("\nInstanciando DeepPortfolioAgentNetwork...")
    agent_network = DeepPortfolioAgentNetwork(
        num_assets=num_assets_test,
        sequence_length=seq_len_test,
        num_features_per_asset=num_features_per_asset_test,
        use_sentiment_analysis=False # Para teste, desabilitar sentimento se não tiver o modelo
    )

    print("\nConstruindo o modelo com input mockado (primeira chamada)...")
    try:
        output_weights = agent_network(mock_market_data_flat, training=False)
        print(f"Shape da Saída (Pesos do Portfólio): {output_weights.shape}")
        print(f"Soma dos Pesos (deve ser ~1.0): {tf.reduce_sum(output_weights, axis=1).numpy()}")
        assert output_weights.shape == (batch_size_test, num_assets_test)
        print("Teste de forward pass bem-sucedido!")

        # Testar output_latent_features
        print("\nTestando DeepPortfolioAgentNetwork com output_latent_features=True...")
        agent_network_latent = DeepPortfolioAgentNetwork(
            num_assets=num_assets_test,
            sequence_length=seq_len_test,
            num_features_per_asset=num_features_per_asset_test,
            output_latent_features=True,
            use_sentiment_analysis=False
        )
        latent_features = agent_network_latent(mock_market_data_flat, training=False)
        print(f"Shape das Features Latentes: {latent_features.shape}")
        assert latent_features.shape == (batch_size_test, FINAL_DENSE_UNITS2)
        print("Teste de features latentes bem-sucedido!")

    except Exception as e:
        print(f"ERRO durante o teste do forward pass: {e}")



