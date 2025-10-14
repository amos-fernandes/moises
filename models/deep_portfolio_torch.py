import torch
import torch.nn as nn
import torch.nn.functional as F

class SingleAssetProcessor(nn.Module):
    def __init__(self, sequence_length, num_features_per_asset, cnn_filters1, cnn_filters2, lstm_units):
        super().__init__()
        self.conv1 = nn.Conv1d(num_features_per_asset, cnn_filters1, kernel_size=3, padding=1)
        self.conv2 = nn.Conv1d(cnn_filters1, cnn_filters2, kernel_size=3, padding=1)
        self.lstm = nn.LSTM(input_size=cnn_filters2, hidden_size=lstm_units, batch_first=True)

    def forward(self, x):
        # x: (batch, seq_len, num_features_per_asset)
        x = x.transpose(1, 2)  # (batch, num_features_per_asset, seq_len)
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.transpose(1, 2)  # (batch, seq_len, cnn_filters2)
        _, (h_n, _) = self.lstm(x)  # h_n: (1, batch, lstm_units)
        return h_n.squeeze(0)  # (batch, lstm_units)

class DeepPortfolioAgentNetworkTorch(nn.Module):
    def __init__(self, num_assets, sequence_length, num_features_per_asset,
                 asset_cnn_filters1=32, asset_cnn_filters2=64,
                 asset_lstm_units1=64, asset_lstm_units2=32,
                 final_dense_units1=128, final_dense_units2=32,
                 final_dropout=0.3, mha_num_heads=4, mha_key_dim_divisor=2,
                 output_latent_features=True, use_sentiment_analysis=False):
        super().__init__()
        self.num_assets = num_assets
        self.sequence_length = sequence_length
        self.num_features_per_asset = num_features_per_asset
        self.output_latent_features = output_latent_features
        self.use_sentiment_analysis = use_sentiment_analysis

        # Processador individual de ativos
        self.asset_processor = SingleAssetProcessor(
            sequence_length, num_features_per_asset,
            asset_cnn_filters1, asset_cnn_filters2, asset_lstm_units1
        )
        # Atenção multi-cabeça
        self.attention = nn.MultiheadAttention(
            embed_dim=asset_lstm_units1,
            num_heads=mha_num_heads,
            batch_first=True
        )
        # Pooling global
        self.global_avg_pool = nn.AdaptiveAvgPool1d(1)
        # Camadas densas finais
        self.dense1 = nn.Linear(asset_lstm_units1, final_dense_units1)
        self.dropout1 = nn.Dropout(final_dropout)
        self.dense2 = nn.Linear(final_dense_units1, final_dense_units2)
        self.dropout2 = nn.Dropout(final_dropout)
        self.output_allocation = nn.Linear(final_dense_units2, num_assets)

    def forward(self, x):
        # x: (batch, seq_len, num_assets * num_features_per_asset)
        batch_size = x.size(0)
        # Separar cada ativo
        asset_representations = []
        for i in range(self.num_assets):
            start = i * self.num_features_per_asset
            end = (i + 1) * self.num_features_per_asset
            asset_data = x[:, :, start:end]  # (batch, seq_len, num_features_per_asset)
            asset_repr = self.asset_processor(asset_data)  # (batch, lstm_units1)
            asset_representations.append(asset_repr)
        # Empilhar ativos: (batch, num_assets, lstm_units1)
        stacked = torch.stack(asset_representations, dim=1)
        # Atenção multi-cabeça
        attn_output, _ = self.attention(stacked, stacked, stacked)
        # Pooling global sobre ativos (num_assets)
        pooled = self.global_avg_pool(attn_output.transpose(1,2)).squeeze(-1)  # (batch, lstm_units1)
        # Camadas densas finais
        x = F.relu(self.dense1(pooled))
        x = self.dropout1(x)
        x = F.relu(self.dense2(x))
        x = self.dropout2(x)
        if self.output_latent_features:
            return x  # (batch, final_dense_units2)
        else:
            return F.softmax(self.output_allocation(x), dim=-1)  # (batch, num_assets)
