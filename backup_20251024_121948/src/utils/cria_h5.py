# 
import tensorflow as tf
placeholder_model = tf.keras.Sequential([tf.keras.layers.Dense(1, input_shape=(10,))]) # Ajuste input_shape
placeholder_model.compile(optimizer='adam', loss='mse')
placeholder_model.save("app/model/model.h5") 