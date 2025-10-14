# train_rnn_model.py

import os
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import joblib 
import matplotlib.pyplot as plt
from datetime import timezone # Adicionado para datetime.now(timezone.utc)

# Importar configurações e módulos
from config import (
    NUM_FEATURES, SYMBOL, TIMEFRAME, DAYS_OF_DATA_TO_FETCH, LIMIT_PER_FETCH,
    WINDOW_SIZE, BASE_FEATURE_COLS, # NUM_FEATURES é derivado no model_builder
    PREDICTION_HORIZON, PRICE_CHANGE_THRESHOLD,
    EPOCHS, BATCH_SIZE, # LSTM_UNITS, DENSE_UNITS, etc., são usados em model_builder
    MODEL_SAVE_DIR, MODEL_NAME,
    PRICE_VOL_SCALER_NAME, INDICATOR_SCALER_NAME, PRICE_VOL_SCALER_NAME, INDICATOR_SCALER_NAME, # Nomes dos arquivos
    EXPECTED_SCALED_FEATURES_FOR_MODEL, EXPECTED_FEATURES_ORDER # Usaremos esta para as colunas de entrada das sequências

)
# Note: LEARNING_RATE é usado em model_builder, não precisa importar aqui diretamente se não for para os callbacks.

from data_handler import fetch_ohlcv_data_ccxt, calculate_technical_indicators, calculate_targets, create_sequences
from model_builder import build_lstm_model

# Para métricas de classificação
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_class_weight


def main():
    print("Iniciando script de treinamento da RNN...")
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

    # --- 1. Obter e Pré-processar Dados ---
    try:
        ohlcv_df_raw = fetch_ohlcv_data_ccxt(SYMBOL, TIMEFRAME, DAYS_OF_DATA_TO_FETCH, LIMIT_PER_FETCH)
    except Exception as e:
        print(f"Falha ao buscar dados com CCXT: {e}")
        # ... (lógica de fallback para CSV como antes) ...
        return
    
    if ohlcv_df_raw.empty: print("DataFrame de dados raw está vazio."); return

    ohlcv_df_with_ta = calculate_technical_indicators(ohlcv_df_raw)
    if ohlcv_df_with_ta.empty: print("DataFrame vazio após cálculo de indicadores."); return
    
    ohlcv_df_final_features = calculate_targets(ohlcv_df_with_ta, PREDICTION_HORIZON, PRICE_CHANGE_THRESHOLD)
    if ohlcv_df_final_features.empty: print("DataFrame vazio após cálculo de alvos."); return

    # --- 2. Salvar Scalers para API (Fitados nas Colunas Base) ---
    
    api_price_vol_atr_cols = [ # Features que já estão normalizadas ou são valores de preço/vol normalizados
        'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 
        'volume_div_atr', 'body_size_norm_atr'
        ]
    # Garante que só pegamos o que está em BASE_FEATURE_COLS
    api_price_vol_cols = [col for col in api_price_vol_atr_cols if col in BASE_FEATURE_COLS]

    api_indicator_cols = [ # Features que são indicadores brutos ou taxas
        'log_return_1', 'rsi_14', 'atr', 'bbp', 'cci_37', 'mfi_37', 
        'body_vs_avg_body', 'macd', 'sma_10_div_atr' 
        ]
    
    # Garante que só pegamos o que está em BASE_FEATURE_COLS e não está no outro grupo
    api_indicator_cols = [col for col in api_indicator_cols if col in BASE_FEATURE_COLS and col not in api_price_vol_cols]
   
    print("Preparando e salvando scalers para a API...")

    # Garantir que todas as colunas de BASE_FEATURE_COLS existem ANTES de tentar fitar os scalers
    missing_base_for_api_scalers = [col for col in BASE_FEATURE_COLS if col not in ohlcv_df_final_features.columns]
    if missing_base_for_api_scalers:
        print(f"ERRO: Colunas de BASE_FEATURE_COLS ({missing_base_for_api_scalers}) não encontradas para fitar scalers da API.")
        print(f"Disponíveis: {ohlcv_df_final_features.columns.tolist()}")
        return

    api_price_vol_cols = [col for col in BASE_FEATURE_COLS if 'close_div_atr' in col or 'volume_div_atr' in col]
    api_indicator_cols = [col for col in BASE_FEATURE_COLS if col not in api_price_vol_cols]

    if api_price_vol_cols:
        price_volume_scaler_api = MinMaxScaler()
        price_volume_scaler_api.fit(ohlcv_df_final_features[api_price_vol_cols])
        joblib.dump(price_volume_scaler_api, os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME))
        print(f"Scaler de Preço/Volume (API: {api_price_vol_cols}) salvo.")
    else:
        print("Aviso: Nenhuma coluna de preço/volume definida para o scaler da API.")

    if api_indicator_cols:
        indicator_scaler_api = MinMaxScaler()
        indicator_scaler_api.fit(ohlcv_df_final_features[api_indicator_cols])
        joblib.dump(indicator_scaler_api, os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME))
        print(f"Scaler de Indicadores (API: {api_indicator_cols}) salvo.")
    else:
        print("Aviso: Nenhuma coluna de indicador definida para o scaler da API.")
        
    # --- 3. Escalonar TODAS as Features para Treinamento do Modelo Atual ---
    # Este scaler é apenas para o processo de treinamento aqui.
    # Ele é treinado em TODAS as BASE_FEATURE_COLS juntas.
    print(f"Escalonando features para treinamento (colunas: {BASE_FEATURE_COLS})...")
    training_features_df = ohlcv_df_final_features[BASE_FEATURE_COLS].copy()
    
    general_training_scaler = MinMaxScaler()
    scaled_values_for_training = general_training_scaler.fit_transform(training_features_df)
    
    # DataFrame com colunas escaladas, ex: 'close_div_atr_scaled', 'rsi_14_scaled'
    # Usa EXPECTED_SCALED_FEATURES_FOR_MODEL do config.py
    df_scaled_for_sequences = pd.DataFrame(
        scaled_values_for_training, 
        columns=EXPECTED_SCALED_FEATURES_FOR_MODEL, 
        index=training_features_df.index
    )
    
    # Juntar o target de volta
    df_for_sequences = df_scaled_for_sequences.join(ohlcv_df_final_features[['target']])
    df_for_sequences.dropna(inplace=True) # Se o join criar NaNs (improvável)
    if df_for_sequences.empty: print("DataFrame para sequências vazio após escalonamento/join."); return

    # --- 4. Criar Sequências ---
    # As colunas para as sequências são as EXPECTED_SCALED_FEATURES_FOR_MODEL
    X, y = create_sequences(df_for_sequences, "target", WINDOW_SIZE, EXPECTED_SCALED_FEATURES_FOR_MODEL)
    if X.shape[0] == 0: print("Nenhuma sequência criada."); return

    print("Preparando, fitando e salvando scalers...")
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)

    # Garantir que todas as colunas de BASE_FEATURE_COLS existem em ohlcv_df_final_features
    missing_base_cols = [col for col in BASE_FEATURE_COLS if col not in ohlcv_df_final_features.columns]
    if missing_base_cols:
        print(f"ERRO FATAL: Colunas de BASE_FEATURE_COLS ({missing_base_cols}) não encontradas em ohlcv_df_final_features.")
        return

    # Definir quais colunas de BASE_FEATURE_COLS vão para cada scaler
    # Estas são as colunas que representam valores normalizados pelo ATR (preço, volume, corpo)
    price_vol_atr_norm_cols = [
        'open_div_atr', 'high_div_atr', 'low_div_atr', 'close_div_atr', 
        'volume_div_atr', 'body_size_norm_atr' 
    ]
    # Remover colunas que podem não existir se você não as adicionou a BASE_FEATURE_COLS
    price_vol_atr_norm_cols = [col for col in price_vol_atr_norm_cols if col in BASE_FEATURE_COLS]


    # As colunas restantes de BASE_FEATURE_COLS são os "outros indicadores"
    other_indicator_cols = [col for col in BASE_FEATURE_COLS if col not in price_vol_atr_norm_cols]

    # DataFrames para fitar os scalers
    df_for_pv_scaler = ohlcv_df_final_features[price_vol_atr_norm_cols].copy()
    df_for_ind_scaler = ohlcv_df_final_features[other_indicator_cols].copy()

    # Fitar e Salvar o Price/Volume (ATR Normalized) Scaler
    if not df_for_pv_scaler.empty:
        pv_atr_scaler = MinMaxScaler()
        pv_atr_scaler.fit(df_for_pv_scaler)
        joblib.dump(pv_atr_scaler, os.path.join(MODEL_SAVE_DIR, PRICE_VOL_SCALER_NAME))
        print(f"Scaler de Preço/Volume (ATR Norm) (API: {price_vol_atr_norm_cols}) salvo.")
        # Transformar os dados para o treinamento com este scaler
        scaled_pv_data = pv_atr_scaler.transform(df_for_pv_scaler)
    else:
        print(f"AVISO: Sem dados para o scaler de Preço/Volume (ATR Norm) ({price_vol_atr_norm_cols}).")
        scaled_pv_data = pd.DataFrame() # DataFrame vazio para evitar erro de concatenação

    # Fitar e Salvar o Other Indicators Scaler
    if not df_for_ind_scaler.empty:
        other_ind_scaler = MinMaxScaler()
        other_ind_scaler.fit(df_for_ind_scaler)
        joblib.dump(other_ind_scaler, os.path.join(MODEL_SAVE_DIR, INDICATOR_SCALER_NAME))
        print(f"Scaler de Outros Indicadores (API: {other_indicator_cols}) salvo.")
        # Transformar os dados para o treinamento com este scaler
        scaled_other_ind_data = other_ind_scaler.transform(df_for_ind_scaler)
    else:
        print(f"AVISO: Sem dados para o scaler de Outros Indicadores ({other_indicator_cols}).")
        scaled_other_ind_data = pd.DataFrame()

    # --- Montar o DataFrame com TODAS as features escaladas para o treinamento ---
    # As colunas devem estar na ORDEM DE EXPECTED_SCALED_FEATURES_FOR_MODEL
    # (que é derivada da ordem de BASE_FEATURE_COLS)

    df_scaled_for_sequences = pd.DataFrame(index=ohlcv_df_final_features.index)

    # Adicionar colunas escaladas de preço/volume
    if not df_for_pv_scaler.empty:
        for i, col_name in enumerate(price_vol_atr_norm_cols):
            df_scaled_for_sequences[f"{col_name}_scaled"] = scaled_pv_data[:, i]
    
    # Adicionar colunas escaladas de outros indicadores
    if not df_for_ind_scaler.empty:
        for i, col_name in enumerate(other_indicator_cols):
            df_scaled_for_sequences[f"{col_name}_scaled"] = scaled_other_ind_data[:, i]
            
    # Verificar se todas as colunas escaladas esperadas foram criadas
    # `EXPECTED_SCALED_FEATURES_FOR_MODEL` vem do config.py
    missing_scaled_cols = [col for col in EXPECTED_SCALED_FEATURES_FOR_MODEL if col not in df_scaled_for_sequences.columns]
    if missing_scaled_cols:
        print(f"ERRO FATAL: Colunas escaladas esperadas ({missing_scaled_cols}) não foram criadas para as sequências.")
        print(f"Colunas escaladas disponíveis: {df_scaled_for_sequences.columns.tolist()}")
        return

    # Reordenar colunas para garantir a ordem de EXPECTED_SCALED_FEATURES_FOR_MODEL
    df_scaled_for_sequences = df_scaled_for_sequences[EXPECTED_SCALED_FEATURES_FOR_MODEL]
    
    # Juntar o target de volta
    df_for_sequences = df_scaled_for_sequences.join(ohlcv_df_final_features[['target']])
    df_for_sequences.dropna(inplace=True) 
    if df_for_sequences.empty: print("DataFrame para sequências vazio após escalonamento/join."); return

    # --- 5. Dividir Dados ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Treino: {X_train.shape[0]} amostras, Teste: {X_test.shape[0]} amostras.")

    X, y = create_sequences(df_for_sequences, "target", WINDOW_SIZE, EXPECTED_SCALED_FEATURES_FOR_MODEL)
    if X.shape[0] == 0: print("Nenhuma sequência criada."); return

        # --- 6. Dividir Dados ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"Treino: {X_train.shape[0]} amostras, Teste: {X_test.shape[0]} amostras.")

    # --- 7. Construir e Treinar Modelo ---
    print("Construindo modelo LSTM...")
    # NUM_FEATURES é importado de config.py e deve ser len(BASE_FEATURE_COLS)
    # EXPECTED_SCALED_FEATURES_FOR_MODEL também é de config.py e é [f"{col}_scaled" for col in BASE_FEATURE_COLS]
    # O número de colunas em X_train (X_train.shape[2]) DEVE ser igual a NUM_FEATURES.
    # E NUM_FEATURES DEVE ser igual a len(EXPECTED_SCALED_FEATURES_FOR_MODEL).
    
    actual_num_features = NUM_FEATURES # Se estiverem consistentes

    model_input_shape = (WINDOW_SIZE, actual_num_features) 
    model = build_lstm_model(model_input_shape) # model_builder.py usa LEARNING_RATE do config

    print("Iniciando treinamento do modelo...")
    reduce_lr_cb = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', 
        factor=0.5, # Reduz pela metade, um pouco menos agressivo que 0.2
        patience=7, 
        min_lr=1e-7, # Pode ser 1e-6 também
        verbose=1
    )
    early_stopping_cb = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', 
        patience=25, # Mantém sua paciência maior
        restore_best_weights=True # MUITO IMPORTANTE
    )
    callbacks_list = [early_stopping_cb, reduce_lr_cb]

    class_weights_map = {
        0: 0.4,  # Diminui o peso da classe majoritária
        1: 4.0   # Aumenta BASTANTE o peso da classe minoritária (Rise)
    }
    
    unique_classes, counts = np.unique(y_train, return_counts=True)
    print(f"Distribuição das classes no treino: {dict(zip(unique_classes, counts))}")
    class_weights_vals = compute_class_weight('balanced', classes=unique_classes, y=y_train)
    class_weights_map = {cls: weight for cls, weight in zip(unique_classes, class_weights_vals)}

  
    
    class_weights_map = {0: 0.5, 1: 3.5}
    


    print(f"Pesos de Classe: {class_weights_map}")

    """  class_weights_map = {
        0: 0.4,  # Diminui o peso da classe majoritária
        1: 4.0   # Aumenta BASTANTE o peso da classe minoritária (Rise)
    } """


    history = model.fit(X_train, y_train, epochs=EPOCHS, batch_size=BATCH_SIZE,
                        validation_split=0.1, # Usa 10% do X_train/y_train para validação
                        callbacks=callbacks_list, class_weight=class_weights_map, verbose=1)
    
    # --- 8. Avaliar o Modelo TREINADO ---
    # O modelo 'model' aqui é o treinado, com os melhores pesos restaurados pelo EarlyStopping
    print("Avaliando modelo treinado no conjunto de teste...")
    loss, accuracy_keras = model.evaluate(X_test, y_test, verbose=0)
    print(f"Perda no Teste (Keras): {loss:.4f}")
    print(f"Acurácia no Teste (Keras, thr=0.5): {accuracy_keras:.4f}")



    # Após model.evaluate()
    from sklearn.metrics import classification_report, confusion_matrix
    y_pred_probs = model.predict(X_test)
    y_pred_classes = (y_pred_probs > 0.65).astype(int) # 0.5, 0.6, 0.65, 0.7, 0.75 Valores de referencia par Thresholud

    print("\nRelatório de Classificação no Conjunto de Teste:")
    print(classification_report(y_test, y_pred_classes, target_names=['No Rise (0)', 'Rise (1)']))

    print("\nMatriz de Confusão no Conjunto de Teste:")
    cm = confusion_matrix(y_test, y_pred_classes)
    print(cm)
    import seaborn as sns # Para um plot mais bonito da matriz
    plt.figure(figsize=(6,5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=['No Rise', 'Rise'], yticklabels=['No Rise', 'Rise'])
    plt.xlabel('Predito')
    plt.ylabel('Verdadeiro')
    plt.title('Matriz de Confusão')
    plt.savefig(os.path.join(MODEL_SAVE_DIR, "confusion_matrix.png"))

    # --- 9. Salvar Modelo e Scalers ---
    print("Salvando modelo e scalers...")
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True) # Cria o diretório se não existir
    
    model_path = os.path.join(MODEL_SAVE_DIR, MODEL_NAME)
    model.save(model_path)
    print(f"Modelo salvo em: {model_path}")

    # --- 9. Salvar o Modelo TREINADO ---
    # Não reconstrua o modelo aqui! Salve o que foi treinado.
    model_save_path = os.path.join(MODEL_SAVE_DIR, MODEL_NAME)
    model.save(model_save_path)
    print(f"Modelo TREINADO salvo em: {model_save_path}")



    # --- 10. Plotar Histórico de Treinamento (Opcional) ---
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['accuracy'], label='Acurácia Treino')
    plt.plot(history.history['val_accuracy'], label='Acurácia Validação')
    plt.title('Acurácia do Modelo')
    plt.xlabel('Época')
    plt.ylabel('Acurácia')
    plt.legend()

    plt.subplot(1, 2, 2)
    plt.plot(history.history['loss'], label='Perda Treino')
    plt.plot(history.history['val_loss'], label='Perda Validação')
    plt.title('Perda do Modelo')
    plt.xlabel('Época')
    plt.ylabel('Perda')
    plt.legend()
    
    # Salvar o gráfico
    plot_path = os.path.join(MODEL_SAVE_DIR, "training_history.png")
    plt.savefig(plot_path)
    print(f"Gráfico do histórico de treinamento salvo em: {plot_path}")
    plt.show() # Descomente se quiser ver o gráfico imediatamente


    # --- Imprimindo rodade de Tresh

    print("\nAnálise com diferentes thresholds de predição no conjunto de teste:")
    y_pred_probs = model.predict(X_test) 
    thresholds_to_test = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]
    for thresh in thresholds_to_test:
        print(f"\n--- Resultados com Threshold: {thresh:.2f} ---")
        y_pred_classes = (y_pred_probs > thresh).astype(int)
        # Use target_names se suas classes forem 0 e 1. Se y_test tiver outros valores, ajuste.
        # Supondo que 0 é 'No Rise' e 1 é 'Rise'
        print(classification_report(y_test, y_pred_classes, target_names=['No Rise (0)', 'Rise (1)'], zero_division=0))
        print("Matriz de Confusão:")
        print(confusion_matrix(y_test, y_pred_classes))







    print("Script de treinamento concluído.")



if __name__ == "__main__":
    main()

  # Configurar GPU (Opcional, se tiver TensorFlow com suporte a GPU)
    print("Iniciando configuração de GPU")
    gpus = tf.config.experimental.list_physical_devices('GPU')
    if gpus:
        try:
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            logical_gpus = tf.config.experimental.list_logical_devices('GPU')
            print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
        except RuntimeError as e:
            print(e)


