import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel # Usar AutoModel para obter embeddings
from typing import List

from config import *

class SingleAssetProcessor(nn.Module):
    def __init__(self, num_features_per_asset, cnn_filters1, cnn_filters2, lstm_units1, lstm_units2, dropout_rate):
        super().__init__()
        self.conv1 = nn.Conv1d(num_features_per_asset, cnn_filters1, kernel_size=3, padding=1)
        self.dropout_cnn1 = nn.Dropout(dropout_rate)
        self.conv2 = nn.Conv1d(cnn_filters1, cnn_filters2, kernel_size=3, padding='same')
        self.dropout_cnn2 = nn.Dropout(dropout_rate)
        
        self.lstm1 = nn.LSTM(input_size=cnn_filters2, hidden_size=lstm_units1, num_layers=1, batch_first=True, bidirectional=True)
        self.lstm2 = nn.LSTM(input_size=lstm_units1 * 2, hidden_size=lstm_units2, num_layers=1, batch_first=True)

    def forward(self, x):
        # x: (batch, seq_len, num_features_per_asset)
        x = x.transpose(1, 2)  # (batch, num_features_per_asset, seq_len)
        x = F.relu(self.conv1(x))
        x = self.dropout_cnn1(x)
        x = F.relu(self.conv2(x))
        x = self.dropout_cnn2(x)
        x = x.transpose(1, 2)  # (batch, seq_len, cnn_filters2)
        
        lstm1_out, _ = self.lstm1(x)
        _, (h_n, _) = self.lstm2(lstm1_out)
        
        return h_n.squeeze(0)  # (batch, lstm_units2)

class DeepPortfolioAgentNetworkTorch(nn.Module):
    def __init__(self, num_assets, sequence_length, num_features_per_asset,
                 asset_cnn_filters1, asset_cnn_filters2,
                 asset_lstm_units1, asset_lstm_units2, asset_dropout,
                 mha_num_heads, mha_key_dim_divisor,
                 final_dense_units1, final_dense_units2, final_dropout,
                 output_latent_features=False, use_sentiment_analysis=False):
        super().__init__()
        self.num_assets = int(num_assets)
        self.num_features_per_asset = int(num_features_per_asset)
        self.output_latent_features = output_latent_features
        self.use_sentiment_analysis = use_sentiment_analysis

        self.asset_processor = SingleAssetProcessor(
            self.num_features_per_asset, asset_cnn_filters1, asset_cnn_filters2, 
            asset_lstm_units1, asset_lstm_units2, asset_dropout
        )
        
        self.attention = nn.MultiheadAttention(
            embed_dim=asset_lstm_units2, num_heads=mha_num_heads,
            dropout=0.1, batch_first=True
        )
        self.attention_norm = nn.LayerNorm(asset_lstm_units2)
        
        self.global_avg_pool = nn.AdaptiveAvgPool1d(1)
        
        self.dense1 = nn.Linear(asset_lstm_units2, final_dense_units1)
        self.dropout1 = nn.Dropout(final_dropout)
        self.latent_features_layer = nn.Linear(final_dense_units1, final_dense_units2) # A camada que produz as features latentes
        
        if not self.output_latent_features:
            self.output_allocation_head = nn.Linear(final_dense_units2, num_assets)

    def forward(self, observations):
        # observations: (batch, seq_len, num_assets * num_features_per_asset)
        asset_representations = []
        for i in range(self.num_assets):
            start = i * self.num_features_per_asset
            end = (i + 1) * self.num_features_per_asset
            asset_data = observations[:, :, start:end]
            asset_repr = self.asset_processor(asset_data)
            asset_representations.append(asset_repr)
        
        stacked = torch.stack(asset_representations, dim=1)
        
        attn_output, _ = self.attention(stacked, stacked, stacked)
        attn_output = self.attention_norm(stacked + attn_output) # Conexão residual + LayerNorm
        
        # Pooling sobre a dimensão dos ativos
        pooled = self.global_avg_pool(attn_output.transpose(1, 2)).squeeze(-1)
        
        # Camadas densas para features latentes
        x = F.relu(self.dense1(pooled))
        x = self.dropout1(x)
        latent_features = self.latent_features_layer(x) # Saída de features latentes

        if self.output_latent_features:
            return latent_features
        else:
            allocation_logits = self.output_allocation_head(latent_features)
            return F.softmax(allocation_logits, dim=-1)