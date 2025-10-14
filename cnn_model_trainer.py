import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Conv1D, MaxPooling1D, Flatten, Dropout
import matplotlib.pyplot as plt

# 1. Carregar os dados
df = pd.read_csv("sp500_ratios.csv")

# 2. Pré-processar os dados
df = df.drop(columns=["Date", "Ticker"])  # Colunas não numéricas
df = df.dropna()  # Remove linhas com valores ausentes

# 3. Separar recursos e alvo (vamos usar "ROE - Return On Equity" como alvo de previsão)
target_column = "ROE - Return On Equity"
X = df.drop(columns=[target_column]).values
y = df[target_column].values

# 4. Normalizar
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# 5. Redimensionar para CNN (samples, time_steps, features)
X_scaled = X_scaled.reshape((X_scaled.shape[0], X_scaled.shape[1], 1))  # 1D CNN

# 6. Divisão treino/teste
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# 7. Modelo CNN
model = Sequential([
    Conv1D(32, kernel_size=3, activation='relu', input_shape=(X_train.shape[1], 1)),
    MaxPooling1D(pool_size=2),
    Conv1D(64, kernel_size=3, activation='relu'),
    MaxPooling1D(pool_size=2),
    Flatten(),
    Dense(128, activation='relu'),
    Dropout(0.3),
    Dense(1)  # Saída para regressão
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# 8. Treinamento
history = model.fit(X_train, y_train, validation_split=0.2, epochs=50, batch_size=32, verbose=1)

# 9. Avaliação
loss, mae = model.evaluate(X_test, y_test)
print(f"\n✅ Test MAE: {mae:.4f}")

# 10. Plot
plt.plot(history.history['mae'], label='MAE Treino')
plt.plot(history.history['val_mae'], label='MAE Validação')
plt.xlabel("Épocas")
plt.ylabel("Erro Absoluto Médio")
plt.title("Performance do Modelo")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
