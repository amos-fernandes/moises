
# rnn/agents/deep_portfolio.py (ou onde você tem DeepPortfolioAI / DeepPortfolioAgentNetwork)
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
# Comente as importações do transformers se não for testar o sentimento agora para simplificar
# from transformers import AutoTokenizer, TFAutoModelForSequenceClassification

# --- DEFINIÇÕES DE CONFIGURAÇÃO (COPIE OU IMPORTE DO SEU CONFIG.PY) ---
# Se você não importar do config.py, defina-as aqui para o teste
WINDOW_SIZE_CONF = 60
NUM_ASSETS_CONF = 4  # Ex: ETH, BTC, ADA, SOL
NUM_FEATURES_PER_ASSET_CONF = 26 # Número de features calculadas para CADA ativo
                                 # (open_div_atr, ..., buy_condition_v1, etc.)
L2_REG = 0.0001 # Exemplo, use o valor do seu config

# (Cole as classes AssetProcessor e DeepPortfolioAgentNetwork aqui se estiver em um novo script)
# Ou, se estiver no mesmo arquivo, elas já estarão definidas.

# ... (Definição das classes AssetProcessor e DeepPortfolioAgentNetwork como na resposta anterior) ...
# Certifique-se que a classe DeepPortfolioAgentNetwork está usando estas constantes:
# num_assets=NUM_ASSETS_CONF, 
# sequence_length=WINDOW_SIZE_CONF, 
# num_features_per_asset=NUM_FEATURES_PER_ASSET_CONF

class AssetProcessor(tf.keras.Model):
    def __init__(self, sequence_length, num_features, cnn_filters1=32, cnn_filters2=64, lstm_units1=64, lstm_units2=32, dropout_rate=0.2, name="single_asset_processor_module", **kwargs): # Adicionado **kwargs
        super(AssetProcessor, self).__init__(name=name, **kwargs) # Adicionado **kwargs
        self.sequence_length = sequence_length
        self.num_features = num_features
        self.cnn_filters1 = cnn_filters1 # Salvar para get_config
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
                 num_assets=int(NUM_ASSETS_CONF), 
                 sequence_length=int(WINDOW_SIZE_CONF), 
                 num_features_per_asset=int(NUM_FEATURES_PER_ASSET_CONF),
                 asset_cnn_filters1=32, asset_cnn_filters2=64, 
                 asset_lstm_units1=64, asset_lstm_units2=32, asset_dropout=0.2,
                 mha_num_heads=4, mha_key_dim_divisor=2, # key_dim será asset_lstm_units2 // mha_key_dim_divisor
                 final_dense_units1=128, final_dense_units2=64, final_dropout=0.3,
                 use_sentiment_analysis=True, 
                 output_latent_features=False, **kwargs): # Adicionado **kwargs
        super(DeepPortfolioAgentNetwork, self).__init__(name="deep_portfolio_agent_network", **kwargs) # Adicionado **kwargs
        

        print(f"DPN __init__ > num_assets ENTRADA: {num_assets}, tipo: {type(num_assets)}")

        # Tentar extrair o valor escalar se for um tensor/variável ou TrackedDict
        def get_int_value(param_name, val):
            if isinstance(val, (tf.Tensor, tf.Variable)):
                if val.shape == tf.TensorShape([]): # Escalar
                    print(f"DPN __init__: Convertendo {param_name} (Tensor/Variable escalar) para int.")
                    return int(val.numpy())
                else:
                    raise ValueError(f"{param_name} é um Tensor/Variable mas não é escalar. Shape: {val.shape}")
            elif isinstance(val, dict): # Pode ser um TrackedDict
                # TrackedDict pode se comportar como um dict. Se o valor real está "escondido",
                # precisamos descobrir como acessá-lo.
                # Por agora, vamos tentar a conversão direta, e se falhar, o erro será mais claro.
                # Se for um dict simples com uma chave específica, você precisaria dessa chave.
                # O erro 'KeyError: value' sugere que ['value'] não é a forma correta.
                # Geralmente, para hiperparâmetros, o TrackedDict deve conter o valor diretamente
                # se o SB3 o passou corretamente.
                print(f"DPN __init__: Tentando converter {param_name} (dict-like) para int.")
                try:
                    return int(val) # Tentar conversão direta
                except TypeError:
                     # Se TrackedDict se comporta como um tensor quando usado em ops TF,
                     # tf.get_static_value pode funcionar, ou apenas o uso direto
                     # em operações TF (mas range() não é uma op TF).
                     # Se for um tensor TF "disfarçado", .numpy() pode funcionar.
                     # Se for um dict com uma chave específica, essa chave seria necessária.
                     # O erro mostra que ['value'] não funcionou.
                     print(f"DPN __init__: Conversão direta de {param_name} (dict-like) para int falhou. Investigar TrackedDict.")
                     # Para depuração, você pode tentar imprimir os itens do dict:
                     # if isinstance(val, collections.abc.Mapping): # Checa se é um dict-like
                     #    for k, v_item in val.items():
                     #        print(f"   {param_name} item: {k} -> {v_item}")
                     raise TypeError(f"{param_name} é {type(val)} e não pôde ser convertido para int diretamente. Valor: {val}")
            else: # Tenta conversão direta para outros tipos
                return int(val)

        try:
            self.num_assets = get_int_value("num_assets", num_assets)
            self.sequence_length = get_int_value("sequence_length", sequence_length)
            self.num_features_per_asset = get_int_value("num_features_per_asset", num_features_per_asset)
            self.asset_lstm_output_dim = get_int_value("asset_lstm_units2", asset_lstm_units2) # Do kwargs
            
            # Faça o mesmo para TODOS os outros parâmetros que devem ser inteiros e são passados
            # para construtores de camadas Keras (cnn_filters, lstm_units, mha_num_heads, etc.)
            # Exemplo:
            # self.asset_cnn_filters1_val = get_int_value("asset_cnn_filters1", kwargs.get("asset_cnn_filters1"))

        except Exception as e_conv:
            print(f"ERRO CRÍTICO DE CONVERSÃO DE TIPO no __init__ da DeepPortfolioAgentNetwork: {e_conv}")
            raise

        print(f"DPN __init__ > self.num_assets APÓS conversão: {self.num_assets}, tipo: {type(self.num_assets)}")
        





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
        
        # Ajustar key_dim para ser compatível com a dimensão de entrada e num_heads
        # key_dim * num_heads deve ser idealmente igual a asset_lstm_output_dim se for auto-atenção direta,
        # ou o MHA projeta internamente. Para simplificar, vamos fazer key_dim ser divisível.
        # Se asset_lstm_output_dim não for divisível por num_heads, key_dim pode ser diferente.
        # Vamos definir key_dim explicitamente. Se asset_lstm_output_dim = 32 e num_heads = 4, key_dim pode ser 8.
        # Ou deixar o MHA lidar com a projeção se key_dim for diferente.
        # Para maior clareza, calculamos uma key_dim sensata.
        calculated_key_dim = self.asset_lstm_output_dim // mha_key_dim_divisor 
        if calculated_key_dim == 0: # Evitar key_dim zero
            calculated_key_dim = self.asset_lstm_output_dim # Fallback se for muito pequeno
            print(f"AVISO: asset_lstm_output_dim ({self.asset_lstm_output_dim}) muito pequeno para mha_key_dim_divisor ({mha_key_dim_divisor}). Usando key_dim = {calculated_key_dim}")

        self.attention = MultiHeadAttention(num_heads=mha_num_heads, key_dim=calculated_key_dim, dropout=0.1, name="multi_asset_attention")
        self.attention_norm = LayerNormalization(epsilon=1e-6, name="attention_layernorm")
        self.global_avg_pool_attention = GlobalAveragePooling1D(name="gap_after_attention")

        self.use_sentiment = use_sentiment_analysis # Desabilitado por padrão para este teste
        self.sentiment_embedding_size = 3 
        if self.use_sentiment:
            try:
                self.tokenizer = AutoTokenizer.from_pretrained('ProsusAI/finbert')
                self.sentiment_model = TFAutoModelForSequenceClassification.from_pretrained('ProsusAI/finbert', from_pt=True)
                print("Modelo FinBERT carregado para análise de sentimento.")
            except Exception as e:
                print(f"AVISO: Falha ao carregar FinBERT: {e}. Análise de sentimento será desabilitada.")
                self.use_sentiment = False

        
        dense_input_dim = self.use_sentiment
        #if self.use_sentiment: dense_input_dim += self.sentiment_embedding_size
        
        self.dense1 = Dense(final_dense_units1, activation='relu', kernel_regularizer=regularizers.l2(L2_REG), name="final_dense1")
        self.dropout1 = Dropout(final_dropout, name="final_dropout1")
        self.dense2 = Dense(final_dense_units2, activation='relu', kernel_regularizer=regularizers.l2(L2_REG), name="final_dense2")
        self.dropout2 = Dropout(final_dropout, name="final_dropout2")
        self.output_allocation = Dense(self.num_assets, activation='softmax', name="portfolio_allocation_output")

    def call(self, inputs, training=False):
        market_data_flat = inputs 
        
        print(type(self.num_assets))
        asset_representations_list = []
        for i in range(self.num_assets):
            start_idx = i * self.num_features_per_asset
            end_idx = (i + 1) * self.num_features_per_asset
            current_asset_data = market_data_flat[:, :, start_idx:end_idx]
            processed_asset_representation = self.asset_processor(current_asset_data, training=training)
            asset_representations_list.append(processed_asset_representation)
            
        stacked_asset_features = tf.stack(asset_representations_list, axis=1)
        
        # Para MHA, query, value, key são (batch_size, Tq, dim), (batch_size, Tv, dim)
        # Aqui, T = num_assets, dim = asset_lstm_output_dim
        attention_output = self.attention(
            query=stacked_asset_features, value=stacked_asset_features, key=stacked_asset_features,
            training=training
        )
        attention_output = self.attention_norm(stacked_asset_features + attention_output) 
        
        context_vector_from_attention = self.global_avg_pool_attention(attention_output)
        
        current_features_for_dense = context_vector_from_attention
        # if self.use_sentiment: ... (lógica de concatenação)

        x = self.dense1(current_features_for_dense)
        x = self.dropout1(x, training=training)
        x = self.dense2(x)
        x = self.dropout2(x, training=training)
        
        portfolio_weights = self.output_allocation(x)
        return portfolio_weights

    def get_config(self): # Necessário se você quiser salvar/carregar o modelo que usa este sub-modelo
        config = super().get_config()
        config.update({
            "num_assets": self.num_assets,
            "sequence_length": self.sequence_length,
            "num_features_per_asset": self.num_features_per_asset,
            # Adicione outros args do __init__ aqui para todas as camadas e sub-modelos
            "asset_lstm_output_dim": self.asset_lstm_output_dim,
            # ... e os parâmetros passados para AssetProcessor e MHA, etc.
        })
        return config
    
    # @classmethod
    # def from_config(cls, config): # Necessário para carregar com sub-modelo customizado
    #    # Extrair config do AssetProcessor se necessário
    #    return cls(**config)


if __name__ == '__main__':
    print("Testando o Forward Pass do DeepPortfolioAgentNetwork...")

    # 1. Definir Parâmetros para o Teste (devem corresponder ao config.py)
    batch_size_test = 2 # Um batch pequeno para teste
    seq_len_test = WINDOW_SIZE_CONF
    num_assets_test = NUM_ASSETS_CONF
    num_features_per_asset_test = NUM_FEATURES_PER_ASSET_CONF
    total_features_flat = num_assets_test * num_features_per_asset_test

    print(f"Configuração do Teste:")
    print(f"  Batch Size: {batch_size_test}")
    print(f"  Sequence Length (Window): {seq_len_test}")
    print(f"  Number of Assets: {num_assets_test}")
    print(f"  Features per Asset: {num_features_per_asset_test}")
    print(f"  Total Flat Features per Timestep: {total_features_flat}")

    # 2. Criar Tensor de Input Mockado
    # Shape: (batch_size, sequence_length, num_assets * num_features_per_asset)
    mock_market_data_flat = tf.random.normal(
        shape=(batch_size_test, seq_len_test, total_features_flat)
    )
    print(f"Shape do Input Mockado (market_data_flat): {mock_market_data_flat.shape}")

    # 3. Instanciar o Modelo
    # Use os mesmos hiperparâmetros que você definiria no config.py para a rede
    print("\nInstanciando DeepPortfolioAgentNetwork...")
    agent_network = DeepPortfolioAgentNetwork(
        num_assets=num_assets_test,
        sequence_length=seq_len_test,
        num_features_per_asset=num_features_per_asset_test,
        # Você pode variar os próximos parâmetros para testar diferentes configs
        asset_cnn_filters1=32, asset_cnn_filters2=64,
        asset_lstm_units1=64, asset_lstm_units2=32, # asset_lstm_units2 define asset_lstm_output_dim
        asset_dropout=0.1,
        mha_num_heads=4, mha_key_dim_divisor=4, # Ex: 32 // 4 = 8 para key_dim
        final_dense_units1=64, final_dense_units2=32, final_dropout=0.2,
        use_sentiment_analysis=False # Testar sem sentimento primeiro
    )

    # Para construir o modelo e ver o summary, você pode chamar com o input mockado
    # ou explicitamente chamar model.build() se souber o input shape completo
    # Chamar com input mockado é mais fácil para construir.
    print("\nConstruindo o modelo com input mockado (primeira chamada)...")
    try:
        # É uma boa prática fazer a primeira chamada dentro de um tf.function para otimizar
        # ou apenas chamar diretamente para teste.
        _ = agent_network(mock_market_data_flat) # Chamada para construir as camadas
        print("\n--- Summary da Rede Principal (DeepPortfolioAgentNetwork) ---")
        agent_network.summary()
        
        # O summary do asset_processor já foi impresso no __init__ do DeepPortfolioAgentNetwork
        # se você descomentar as linhas de build/summary lá.
        # Ou você pode imprimir aqui:
        print("\n--- Summary do AssetProcessor (Sub-Modelo) ---")
        agent_network.asset_processor.summary()


    except Exception as e:
        print(f"Erro ao construir a rede principal: {e}", exc_info=True)
        exit()

    # 4. Chamar model(mock_input) para o Forward Pass
    print("\nExecutando Forward Pass...")
    try:
        predictions = agent_network(mock_market_data_flat, training=False) # Passar training=False para inferência
        print("Forward Pass concluído com sucesso!")
    except Exception as e:
        print(f"Erro durante o Forward Pass: {e}", exc_info=True)
        exit()

    # 5. Verificar o Shape da Saída
    print(f"\nShape da Saída (predictions): {predictions.shape}")
    expected_output_shape = (batch_size_test, num_assets_test)
    if predictions.shape == expected_output_shape:
        print(f"Shape da Saída está CORRETO! Esperado: {expected_output_shape}")
    else:
        print(f"ERRO: Shape da Saída INCORRETO. Esperado: {expected_output_shape}, Obtido: {predictions.shape}")

    # Verificar se a saída é uma distribuição de probabilidade (softmax)
    if hasattr(predictions, 'numpy'): # Se for um EagerTensor
        output_sum = tf.reduce_sum(predictions, axis=-1).numpy()
        print(f"Soma das probabilidades de saída por amostra no batch (deve ser próximo de 1): {output_sum}")
        if np.allclose(output_sum, 1.0):
            print("Saída Softmax parece CORRETA (soma 1).")
        else:
            print("AVISO: Saída Softmax pode NÃO estar correta (soma diferente de 1).")
    
    print("\nExemplo das primeiras predições (pesos do portfólio):")
    print(predictions.numpy()[:min(5, batch_size_test)]) # Imprime até 5 predições do batch

    # Teste com sentimento (se implementado e FinBERT carregado)
    # agent_network.use_sentiment = True # Ativar para teste
    # if agent_network.use_sentiment and hasattr(agent_network, 'tokenizer'):
    #     print("\nTestando Forward Pass COM SENTIMENTO...")
    #     mock_news_batch = ["positive news for asset 1", "market is very volatile today"] # Exemplo
    #     # A forma como você passa 'news' para o call() precisa ser definida.
    #     # Se for um dicionário:
    #     # mock_inputs_with_news = {"market_data": mock_market_data_flat, "news_data": mock_news_batch}
    #     # predictions_with_sentiment = agent_network(mock_inputs_with_news, training=False)
    #     # print(f"Shape da Saída com Sentimento: {predictions_with_sentiment.shape}")
    # else:
    #     print("\nTeste com sentimento pulado (use_sentiment=False ou FinBERT não carregado).")

    print("\nTeste do Forward Pass Concluído!")





