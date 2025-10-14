import numpy as np
import matplotlib.pyplot as plt
from keras.models import load_model

def load_model_and_predict(model_path, X_val, y_val, ticker_index=0):
    """
    Carrega um modelo CNN salvo e plota previsão vs. valor real para um ticker específico.

    Args:
        model_path (str): Caminho para o modelo salvo (ex: 'cnn_model.keras')
        X_val (np.ndarray): Dados de entrada de validação (shape: [tickers, time, features])
        y_val (np.ndarray): Valores reais de saída de validação
        ticker_index (int): Índice do ticker a ser visualizado
    """
    print(f"Carregando modelo de {model_path}...")
    model = load_model(model_path)

    X_sample = X_val[ticker_index]
    y_true = y_val[ticker_index]

    if len(X_sample.shape) == 2:
        X_sample = X_sample[np.newaxis, ...]

    y_pred = model.predict(X_sample).squeeze()
    y_true = y_true.squeeze()

    plt.figure(figsize=(10, 5))
    plt.plot(y_true, label='Real', linewidth=2)
    plt.plot(y_pred, label='Previsto', linestyle='--')
    plt.title(f'CNN - Previsão vs Real (Ticker {ticker_index})')
    plt.xlabel('Dias Futuros')
    plt.ylabel('Preço Normalizado')
    plt.legend()
    plt.tight_layout()
    plt.show()
