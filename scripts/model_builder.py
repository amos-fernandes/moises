# model_builder.py

import tensorflow as tf
from tensorflow.keras import regularizers # Boa prática manter o import aqui também

# Importa as constantes do config.py
from config import LSTM_UNITS, DENSE_UNITS, DROPOUT_RATE, LEARNING_RATE, L2_REG

def build_lstm_model(input_shape): # LEARNING_RATE é pega do config.py agora
    """Constrói o modelo LSTM com regularização L2."""
    
    model = tf.keras.Sequential() 
    
    # Camadas LSTM
    for i, units in enumerate(LSTM_UNITS):
        return_sequences = True if i < len(LSTM_UNITS) - 1 else False
        layer_name_lstm = f'lstm_{i}' # Adicionar nomes às camadas é uma boa prática
        if i == 0:
            model.add(tf.keras.layers.LSTM(units, 
                                           return_sequences=return_sequences, 
                                           input_shape=input_shape,
                                           kernel_regularizer=regularizers.l2(L2_REG),
                                           name=layer_name_lstm
                                           ))
        else:
            model.add(tf.keras.layers.LSTM(units, 
                                           return_sequences=return_sequences,
                                           kernel_regularizer=regularizers.l2(L2_REG),
                                           name=layer_name_lstm 
                                           ))
        model.add(tf.keras.layers.Dropout(DROPOUT_RATE, name=f'dropout_lstm_{i}'))
        
    # Camada Densa
    model.add(tf.keras.layers.Dense(DENSE_UNITS, 
                                    activation='relu', 
                                    kernel_regularizer=regularizers.l2(L2_REG),
                                    name='dense_main'
                                    ))
    model.add(tf.keras.layers.Dropout(DROPOUT_RATE, name='dropout_dense'))
    
    # Camada de Saída
    model.add(tf.keras.layers.Dense(1, activation='sigmoid', name='output')) # CORRIGIDO: aspas simples
    
    # O LEARNING_RATE é pego do config.py
    optimizer = tf.keras.optimizers.Adam(learning_rate=LEARNING_RATE, amsgrad=True, clipvalue=1.0) # clipvalue é bom para RNNs
    model.compile(optimizer=optimizer, loss='binary_crossentropy', metrics=['accuracy']) # CORRIGIDO: aspas
    model.summary()
    return model