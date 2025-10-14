# rnn/agents/deep_portfolio.py (ou onde você tem DeepPortfolioAI)

import tensorflow as tf
from tensorflow.keras.layers import Input, Conv1D, LSTM, Dense, Dropout, MultiHeadAttention, Reshape, Concatenate, TimeDistributed, GlobalAveragePooling1D
from tensorflow.keras.models import Model # Usar a API Funcional do Keras é mais flexível aqui
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification
 
# Importar do config.py
# from ..config import WINDOW_SIZE, NUM_FEATURES_PER_ASSET, NUM_ASSETS 
# (Você precisará adicionar NUM_FEATURES_PER_ASSET e NUM_ASSETS ao config.py)

# VALORES DE EXEMPLO (PEGUE DO CONFIG.PY)
WINDOW_SIZE_CONF = 60
NUM_ASSETS_CONF = 4 # Ex: BTC, ETH, ADA, SOL
NUM_FEATURES_PER_ASSET_CONF = 26 # O número de features que você calcula para UM ativo
                                 # (ex: open, high, ..., sma_10_div_atr, adx_14, etc.)
                                 # Se o input achatado é 104, e são 4 ativos, então 104/4 = 26.

class DeepPortfolioAgentNetwork(tf.keras.Model): # Renomeado para clareza, já que é a rede do agente
    def __init__(self, num_assets, sequence_length, num_features_per_asset, lstm_units_asset=64, cnn_filters_asset=32):
        super(DeepPortfolioAgentNetwork, self).__init__()
        
        self.num_assets = num_assets
        self.sequence_length = sequence_length
        self.num_features_per_asset = num_features_per_asset
        
        # --- Camadas para Processamento Individual de Ativos ---
        # Usaremos TimeDistributed para aplicar as mesmas camadas CNN/LSTM a cada ativo
        # A entrada esperada por TimeDistributed(Layer) é (batch_size, num_time_distributed_items, ...)
        # No nosso caso, num_time_distributed_items será num_assets.
        # O input para o modelo será (batch_size, sequence_length, num_assets * num_features_per_asset)
        # Precisaremos de um Reshape para (batch_size, num_assets, sequence_length, num_features_per_asset)
        # e depois talvez um Permute para aplicar TimeDistributed na dimensão de ativos.
        # OU, uma abordagem mais simples é criar um "sub-modelo" para processar um ativo
        # e depois aplicar esse sub-modelo a cada fatia de ativo.

        # Abordagem com sub-modelo para processamento de ativo individual
        asset_input_shape = (self.sequence_length, self.num_features_per_asset)
        asset_processing_input = Input(shape=asset_input_shape, name="asset_input_features")
        
        # CNN para cada ativo
        cnn_layer1 = Conv1D(filters=cnn_filters_asset, kernel_size=3, activation='relu', padding='same', name="asset_cnn1")(asset_processing_input)
        # cnn_layer1_dropout = Dropout(0.2)(cnn_layer1) # Opcional
        cnn_layer2 = Conv1D(filters=cnn_filters_asset*2, kernel_size=3, activation='relu', padding='same', name="asset_cnn2")(cnn_layer1) # ou cnn_layer1_dropout
        # cnn_layer2_pool = MaxPooling1D(pool_size=2)(cnn_layer2) # Opcional

        # LSTM para cada ativo
        # Se usou pooling na CNN, ajuste a entrada do LSTM
        # lstm_output_asset = LSTM(lstm_units_asset, return_sequences=False, name="asset_lstm_final")(cnn_layer2_pool ou cnn_layer2)
        lstm_output_asset = LSTM(lstm_units_asset, return_sequences=False, name="asset_lstm_final")(cnn_layer2) # Saída (None, lstm_units_asset)
        
        # Criar o sub-modelo de processamento de ativo
        self.asset_processor = Model(inputs=asset_processing_input, outputs=lstm_output_asset, name="single_asset_processor")
        self.asset_processor.summary() # Ver a estrutura do processador de ativo

        # --- Camadas para Combinação e Decisão ---
        # MultiHeadAttention para correlações entre as representações dos ativos
        # A entrada para MHA será (batch_size, num_assets, lstm_units_asset)
        self.attention = MultiHeadAttention(num_heads=4, key_dim=lstm_units_asset, dropout=0.1, name="multi_asset_attention") # key_dim pode ser lstm_units_asset
        
        # Camadas densas para decisão final
        # O tamanho da entrada para self.dense1 dependerá da saída da atenção e do sentimento
        # Saída da Atenção pode ser (batch_size, num_assets, lstm_units_asset). Podemos achatá-la ou usar GlobalAveragePooling.
        self.global_avg_pool = GlobalAveragePooling1D(name="gap_after_attention") # Reduz a dimensão dos ativos

        # Assumindo que o sentimento será um vetor por passo de tempo/batch
        # self.sentiment_dense = Dense(32, activation='relu', name="sentiment_processor_dense") # Opcional, para processar embedding de sentimento

        self.concat_layer = Concatenate(axis=-1, name="concat_attention_sentiment")
        
        self.dense1 = Dense(128, activation='relu', name="final_dense1")
        self.dropout1 = Dropout(0.3, name="final_dropout1")
        self.dense2 = Dense(64, activation='relu', name="final_dense2")
        self.dropout2 = Dropout(0.3, name="final_dropout2")
        self.output_allocation = Dense(self.num_assets, activation='softmax', name="portfolio_allocation_output")
        
        # Inicializar tokenizer e modelo de sentimento (se for usar)
        self.use_sentiment = False # Defina como True se for usar
        if self.use_sentiment:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained('ProsusAI/finbert')
                self.sentiment_model = TFAutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert', from_pt=True)
                print("Modelo FinBERT carregado para análise de sentimento.")
            except Exception as e:
                print(f"AVISO: Falha ao carregar FinBERT: {e}. Análise de sentimento será desabilitada.")
                self.use_sentiment = False

    def call(self, inputs, training=False): # Adicionado `training` para Dropout e outras camadas
        # `inputs` pode ser um tensor único (market_data_flat) ou uma tupla/dicionário
        # se você tiver news_data separado.
        # Vamos assumir que a API de RL (Stable-Baselines3) passará um único tensor de observação.
        # Se news_data for parte da observação, precisaremos separá-la.
        # Por agora, vamos focar no market_data.
        
        market_data_flat = inputs # Shape: (batch_size, sequence_length, num_assets * num_features_per_asset)
        
        # 1. Reshape e Processamento Individual de Ativos
        # Reshape para (batch_size, num_assets, sequence_length, num_features_per_asset)
        # Isso pode ser complexo. Uma forma é fatiar e processar.
        
        reshaped_market_data = tf.reshape(market_data_flat, 
                                         [-1, self.sequence_length, self.num_assets, self.num_features_per_asset])
        # Transpor para (batch_size, num_assets, sequence_length, num_features_per_asset)
        # (Assume que o input original já está como (batch, seq, assets*features) )
        # Se o input é (batch_size, seq_len, total_features), e total_features = num_assets * num_features_asset
        # precisamos de (batch_size, num_assets, seq_len, num_features_asset) para TimeDistributed(asset_processor)
        # Isso requer cuidado no reshape e transpose.
        
        # Alternativa: Processar cada ativo sequencialmente (mais fácil de implementar, pode ser mais lento)
        asset_representations = []
        for i in range(self.num_assets):
            # Fatiar os dados para o ativo 'i'
            # start_idx = i * self.num_features_per_asset
            # end_idx = (i + 1) * self.num_features_per_asset
            # current_asset_data = market_data_flat[:, :, start_idx:end_idx] # Shape (batch, seq_len, num_feat_per_asset)
            
            # A forma correta de fatiar se market_data_flat é (batch, seq_len, num_assets * num_features_per_asset)
            # e as features estão agrupadas por ativo (ex: ativo1_feat1, ativo1_feat2, ..., ativo2_feat1, ...)
            slices = []
            for asset_idx in range(self.num_assets):
                asset_slice_features = market_data_flat[
                    :, :, asset_idx*self.num_features_per_asset : (asset_idx+1)*self.num_features_per_asset
                ]
                slices.append(asset_slice_features)
            
            # `slices` é uma lista de tensores, cada um (batch, seq_len, num_features_per_asset)
            # Agora processar cada um
            processed_asset_slices = [self.asset_processor(s, training=training) for s in slices]
            # `processed_asset_slices` é uma lista de tensores, cada um (batch, lstm_units_asset)

        # Empilhar as representações dos ativos para a camada de Atenção
        # Resultado: (batch_size, num_assets, lstm_units_asset)
        stacked_asset_representations = tf.stack(processed_asset_slices, axis=1)

        # 2. Camada de Atenção entre Ativos
        # Input: (batch_size, num_assets, lstm_units_asset)
        # Output: (batch_size, num_assets, lstm_units_asset) - o output da MHA geralmente tem a mesma dimensão do value
        attention_output = self.attention(
            query=stacked_asset_representations, 
            value=stacked_asset_representations, 
            key=stacked_asset_representations,
            training=training
        )
        
        # Reduzir a dimensão dos ativos (ex: com GlobalAveragePooling1D na dimensão num_assets)
        # Input para GAP1D: (batch_size, steps, features) -> aqui (batch_size, num_assets, lstm_units_asset)
        context_vector_from_attention = self.global_avg_pool(attention_output) # Shape (batch_size, lstm_units_asset)

        # 3. Análise de Sentimento (Placeholder - requer `news_data` como input)
        # Se você tiver `news_data` como parte do `inputs`
        # sentiment_features = tf.zeros_like(context_vector_from_attention[:, :16]) # Placeholder
        # if self.use_sentiment and news_data is not None:
        #     # ... (lógica para _process_news(news_data)) ...
        #     # sentiment_features = self.sentiment_dense(processed_news_embeddings)
        #     pass # Implementar

        # 4. Combinar e Camadas Densas Finais
        # Por agora, apenas usando a saída da atenção
        combined_features = context_vector_from_attention
        # if self.use_sentiment:
        #     combined_features = self.concat_layer([context_vector_from_attention, sentiment_features])
            
        x = self.dense1(combined_features)
        x = self.dropout1(x, training=training)
        x = self.dense2(x)
        x = self.dropout2(x, training=training)
        
        portfolio_weights = self.output_allocation(x) # Softmax output
        return portfolio_weights

    # _process_news como você definiu (com return_tensors="tf" e ajuste para output TF)
    def _process_news(self, news_data_batch: List[str]): # Espera um batch de strings
        if not self.use_sentiment or not news_data_batch:
            # Retornar um tensor de zeros com o shape esperado se não houver notícias ou o modelo de sentimento não for usado
            # O shape precisa ser (batch_size, num_sentiment_output_features)
            # Se batch_size é inferido, e num_sentiment_output_features é, digamos, 32 (após self.sentiment_dense)
            # Isso é complicado de determinar aqui sem o batch_size.
            # Uma solução é retornar um placeholder que será tratado no 'call'.
            # Alternativamente, se a política RL sempre espera um input combinado, 
            # o ambiente precisa fornecer um placeholder para news_data.
            return tf.zeros((tf.shape(news_data_batch)[0] if isinstance(news_data_batch, tf.Tensor) else len(news_data_batch), 32)) # Exemplo

        inputs = self.tokenizer(news_data_batch, return_tensors="tf", padding=True, truncation=True, max_length=128) # max_length menor para eficiência
        outputs = self.sentiment_model(inputs, training=False) # `training=False` para inferência do FinBERT
        sentiment_logits = outputs.logits # Shape (batch_size, 3) para FinBERT (pos, neg, neu)
        
        # Você pode querer processar esses logits mais (ex: passar por uma Dense)
        # ou usar diretamente. Se usar diretamente, a concatenação precisa ser compatível.
        # Exemplo: usar uma camada densa para reduzir/expandir para um tamanho fixo de embedding de sentimento.
        # processed_sentiment = self.sentiment_dense(sentiment_logits)
        # return processed_sentiment
        return sentiment_logits # Retornando logits (batch_size, 3) por enquanto