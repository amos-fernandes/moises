import matplotlib.pyplot as plt
import json

def plot_training_history(history):
    # Caso tenha sido salvo como objeto History
    if isinstance(history, dict):
        hist = history
    else:
        hist = history.history  # Keras History object

    plt.figure(figsize=(12, 5))

    # Plot Loss
    plt.subplot(1, 2, 1)
    plt.plot(hist['loss'], label='Train Loss')
    plt.plot(hist['val_loss'], label='Val Loss')
    plt.title('Loss por Época')
    plt.xlabel('Época')
    plt.ylabel('MSE')
    plt.legend()

    # Plot MAE
    plt.subplot(1, 2, 2)
    plt.plot(hist['mae'], label='Train MAE')
    plt.plot(hist['val_mae'], label='Val MAE')
    plt.title('Erro Absoluto Médio por Época')
    plt.xlabel('Época')
    plt.ylabel('MAE')
    plt.legend()

    plt.tight_layout()
    plt.show()


# Exemplo: carregando histórico salvo como JSON (opcional)
def load_history_from_json(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

# Exemplo de uso:
# history = load_history_from_json("cnn_training_history.json")
# plot_training_history(history)
