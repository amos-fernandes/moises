 python train_rnn_model.py
2025-06-07 07:39:59.310646: I external/local_xla/xla/tsl/cuda/cudart_stub.cc:32] Could not find cuda drivers on your machine, GPU will not be used.
2025-06-07 07:39:59.321958: I external/local_xla/xla/tsl/cuda/cudart_stub.cc:32] Could not find cuda drivers on your machine, GPU will not be used.
2025-06-07 07:39:59.371907: E external/local_xla/xla/stream_executor/cuda/cuda_fft.cc:467] Unable to register cuFFT factory: Attempting to register factory for plugin cuFFT when one has already been registered
WARNING: All log messages before absl::InitializeLog() is called are written to STDERR
E0000 00:00:1749292799.459426   15662 cuda_dnn.cc:8579] Unable to register cuDNN factory: Attempting to register factory for plugin cuDNN when one has already been registered
E0000 00:00:1749292799.484280   15662 cuda_blas.cc:1407] Unable to register cuBLAS factory: Attempting to register factory for plugin cuBLAS when one has already been registered
W0000 00:00:1749292799.543487   15662 computation_placer.cc:177] computation placer already registered. Please check linkage and avoid linking the same target more than once.
W0000 00:00:1749292799.543564   15662 computation_placer.cc:177] computation placer already registered. Please check linkage and avoid linking the same target more than once.
W0000 00:00:1749292799.543574   15662 computation_placer.cc:177] computation placer already registered. Please check linkage and avoid linking the same target more than once.
W0000 00:00:1749292799.543582   15662 computation_placer.cc:177] computation placer already registered. Please check linkage and avoid linking the same target more than once.
/home/verticalagent/dev/Atcoin-token/.venv/lib/python3.12/site-packages/pandas_ta/__init__.py:7: UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html. The pkg_resources package is slated for removal as early as 2025-11-30. Refrain from using this package or pin to Setuptools<81.
  from pkg_resources import get_distribution, DistributionNotFound
2025-06-07 07:40:09.968679: E external/local_xla/xla/stream_executor/cuda/cuda_platform.cc:51] failed call to cuInit: INTERNAL: CUDA error: Failed call to cuInit: UNKNOWN ERROR (303)
Iniciando script de treinamento da RNN...
Buscando dados para BTC/USDT na binance com timeframe 1h...
/home/verticalagent/dev/Atcoin-token/rnn/scripts/train_rnn_model.py:65: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  since = exchange.parse8601((datetime.utcnow() - timedelta(days=days_to_fetch)).isoformat())
Buscando 1000 candles desde 2023-06-08T10:40:10.023Z...
Coletados 1000 candles. Último timestamp: 2023-07-20T02:00:00.000Z. Total: 1000
Buscando 1000 candles desde 2023-07-20T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2023-08-30T18:00:00.000Z. Total: 2000
Buscando 1000 candles desde 2023-08-30T18:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2023-10-11T10:00:00.000Z. Total: 3000
Buscando 1000 candles desde 2023-10-11T10:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2023-11-22T02:00:00.000Z. Total: 4000
Buscando 1000 candles desde 2023-11-22T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-01-02T18:00:00.000Z. Total: 5000
Buscando 1000 candles desde 2024-01-02T18:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-02-13T10:00:00.000Z. Total: 6000
Buscando 1000 candles desde 2024-02-13T10:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-03-26T02:00:00.000Z. Total: 7000
Buscando 1000 candles desde 2024-03-26T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-05-06T18:00:00.000Z. Total: 8000
Buscando 1000 candles desde 2024-05-06T18:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-06-17T10:00:00.000Z. Total: 9000
Buscando 1000 candles desde 2024-06-17T10:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-07-29T02:00:00.000Z. Total: 10000
Buscando 1000 candles desde 2024-07-29T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-09-08T18:00:00.000Z. Total: 11000
Buscando 1000 candles desde 2024-09-08T18:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-10-20T10:00:00.000Z. Total: 12000
Buscando 1000 candles desde 2024-10-20T10:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2024-12-01T02:00:00.000Z. Total: 13000
Buscando 1000 candles desde 2024-12-01T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2025-01-11T18:00:00.000Z. Total: 14000
Buscando 1000 candles desde 2025-01-11T18:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2025-02-22T10:00:00.000Z. Total: 15000
Buscando 1000 candles desde 2025-02-22T10:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2025-04-05T02:00:00.000Z. Total: 16000
Buscando 1000 candles desde 2025-04-05T02:00:00.050Z...
Coletados 1000 candles. Último timestamp: 2025-05-16T18:00:00.000Z. Total: 17000
Buscando 1000 candles desde 2025-05-16T18:00:00.050Z...
Coletados 520 candles. Último timestamp: 2025-06-07T10:00:00.000Z. Total: 17520
Total de 17520 candles OHLCV coletados para BTC/USDT.
Calculando indicadores técnicos...
Criando coluna alvo para predição...
Distribuição do Alvo:
target
0    0.748643
1    0.251357
Name: proportion, dtype: float64
Escalonando features...
Criando sequências de dados...
Shape de X (sequências de entrada): (17441, 60, 4)
Shape de y (alvos): (17441,)
Dividindo dados em treino e teste...
Tamanho do conjunto de treino: 13952, Teste: 3489
Construindo modelo LSTM...
/home/verticalagent/dev/Atcoin-token/.venv/lib/python3.12/site-packages/keras/src/layers/rnn/rnn.py:199: UserWarning: Do not pass an `input_shape`/`input_dim` argument to a layer. When using Sequential models, prefer using an `Input(shape)` object as the first layer in the model instead.
  super().__init__(**kwargs)
Model: "sequential"
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Layer (type)                         ┃ Output Shape                ┃         Param # ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ lstm (LSTM)                          │ (None, 60, 64)              │          17,664 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout (Dropout)                    │ (None, 60, 64)              │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ lstm_1 (LSTM)                        │ (None, 32)                  │          12,416 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_1 (Dropout)                  │ (None, 32)                  │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dense (Dense)                        │ (None, 32)                  │           1,056 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dropout_2 (Dropout)                  │ (None, 32)                  │               0 │
├──────────────────────────────────────┼─────────────────────────────┼─────────────────┤
│ dense_1 (Dense)                      │ (None, 1)                   │              33 │
└──────────────────────────────────────┴─────────────────────────────┴─────────────────┘
 Total params: 31,169 (121.75 KB)
 Trainable params: 31,169 (121.75 KB)
 Non-trainable params: 0 (0.00 B)
Iniciando treinamento do modelo...
Pesos de Classe para Treinamento: {0: 0.6682632436057093, 1: 1.9857671505835468}
Epoch 1/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 57s 116ms/step - accuracy: 0.4573 - loss: 0.6918 - val_accuracy: 0.4070 - val_loss: 0.6990
Epoch 2/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 116ms/step - accuracy: 0.4664 - loss: 0.6832 - val_accuracy: 0.4050 - val_loss: 0.7455
Epoch 3/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 49s 113ms/step - accuracy: 0.4887 - loss: 0.6828 - val_accuracy: 0.4285 - val_loss: 0.6778
Epoch 4/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 114ms/step - accuracy: 0.4869 - loss: 0.6831 - val_accuracy: 0.4139 - val_loss: 0.6996
Epoch 5/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 114ms/step - accuracy: 0.4983 - loss: 0.6745 - val_accuracy: 0.5007 - val_loss: 0.6649
Epoch 6/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 115ms/step - accuracy: 0.4866 - loss: 0.6859 - val_accuracy: 0.6240 - val_loss: 0.6687
Epoch 7/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 115ms/step - accuracy: 0.5359 - loss: 0.6742 - val_accuracy: 0.5067 - val_loss: 0.6813
Epoch 8/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 114ms/step - accuracy: 0.5559 - loss: 0.6728 - val_accuracy: 0.6314 - val_loss: 0.6450
Epoch 9/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 115ms/step - accuracy: 0.5436 - loss: 0.6705 - val_accuracy: 0.5056 - val_loss: 0.6872
Epoch 10/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 117ms/step - accuracy: 0.5351 - loss: 0.6703 - val_accuracy: 0.4285 - val_loss: 0.7185
Epoch 11/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 115ms/step - accuracy: 0.5336 - loss: 0.6769 - val_accuracy: 0.6420 - val_loss: 0.6415
Epoch 12/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 115ms/step - accuracy: 0.5346 - loss: 0.6737 - val_accuracy: 0.5701 - val_loss: 0.6718
Epoch 13/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 116ms/step - accuracy: 0.5799 - loss: 0.6645 - val_accuracy: 0.5219 - val_loss: 0.6836
Epoch 14/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 116ms/step - accuracy: 0.5697 - loss: 0.6682 - val_accuracy: 0.6016 - val_loss: 0.6615
Epoch 15/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 114ms/step - accuracy: 0.5654 - loss: 0.6694 - val_accuracy: 0.6048 - val_loss: 0.6633
Epoch 16/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 116ms/step - accuracy: 0.5811 - loss: 0.6673 - val_accuracy: 0.5251 - val_loss: 0.6855
Epoch 17/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 116ms/step - accuracy: 0.5703 - loss: 0.6648 - val_accuracy: 0.6028 - val_loss: 0.6629
Epoch 18/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 51s 116ms/step - accuracy: 0.6102 - loss: 0.6551 - val_accuracy: 0.6294 - val_loss: 0.6546
Epoch 19/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 50s 114ms/step - accuracy: 0.5871 - loss: 0.6652 - val_accuracy: 0.6234 - val_loss: 0.6492
Epoch 20/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 49s 113ms/step - accuracy: 0.5976 - loss: 0.6602 - val_accuracy: 0.6225 - val_loss: 0.6478
Epoch 21/50
436/436 ━━━━━━━━━━━━━━━━━━━━ 49s 112ms/step - accuracy: 0.5873 - loss: 0.6679 - val_accuracy: 0.5939 - val_loss: 0.6782
Avaliando modelo no conjunto de teste...
Perda no Teste: 0.6415
Acurácia no Teste: 0.6420
110/110 ━━━━━━━━━━━━━━━━━━━━ 6s 48ms/step   

Relatório de Classificação no Conjunto de Teste:
              precision    recall  f1-score   support

 No Rise (0)       0.80      0.69      0.74      2611
    Rise (1)       0.35      0.50      0.41       878

    accuracy                           0.64      3489
   macro avg       0.58      0.60      0.58      3489
weighted avg       0.69      0.64      0.66      3489


Matriz de Confusão no Conjunto de Teste:
[[1799  812]
 [ 437  441]]
Salvando modelo e scalers...
WARNING:absl:You are saving your model as an HDF5 file via `model.save()` or `keras.saving.save_model(model)`. This file format is considered legacy. We recommend using instead the native Keras format, e.g. `model.save('my_model.keras')` or `keras.saving.save_model(model, 'my_model.keras')`. 
Modelo salvo em: app/model/model.h5
Scaler de Preço/Volume salvo em: app/model/price_volume_scaler.joblib
Scaler de Indicadores salvo em: app/model/indicator_scaler.joblib
Gráfico do histórico de treinamento salvo em: app/model/training_history.png
Script de treinamento concluído.