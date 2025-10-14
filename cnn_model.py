import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv1D, MaxPooling1D, Flatten, Dense, Dropout
from tensorflow.keras.optimizers import Adam

def carregar_e_preparar_dados(caminho_csv):
    df = pd.read_csv(caminho_csv, parse_dates=["Date"], index_col="Date")
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    scaler = MinMaxScaler()
    dados_escalados = scaler.fit_transform(df)
    X, y = [], []
    for i in range(len(dados_escalados) - 60):
        X.append(dados_escalados[i:i+60])
        y.append(dados_escalados[i+60][3])
    return np.array(X), np.array(y), scaler

def criar_modelo_cnn(input_shape):
    model = Sequential([
        Conv1D(64, 3, activation='relu', input_shape=input_shape),
        MaxPooling1D(2),
        Conv1D(128, 3, activation='relu'),
        MaxPooling1D(2),
        Flatten(),
        Dense(64, activation='relu'),
        Dropout(0.2),
        Dense(1)
    ])
    model.compile(optimizer=Adam(0.001), loss='mean_squared_error')
    return model
