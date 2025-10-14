import numpy as np
from sklearn.preprocessing import StandardScaler

# Simula o mesmo shape e pré-processamento do modelo
scaler = StandardScaler()

def preprocess_input_data(data):
    data = np.array(data).astype(np.float32)
    if data.ndim == 1:
        data = np.expand_dims(data, axis=0)
    data = scaler.fit_transform(data)
    return np.expand_dims(data, axis=2)  # [batch, features, 1]
