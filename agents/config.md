# EXPECTED_FEATURES_ORDER define como as colunas DEVEM ESTAR no DataFrame
# que entra na função create_sequences, APÓS o escalonamento e ANTES do sufixo _scaled.
# E também como o rnn_predictor.py espera as features ANTES de aplicar os scalers.
# Se rnn_predictor.py vai aplicar scalers separados, ele precisa dos nomes originais (ou _div_atr).
# O script de treino vai criar colunas com sufixo _scaled para alimentar o modelo.
# A lista EXPECTED_FEATURES_ORDER no config.py não é diretamente usada no train_rnn_model.py
# da forma como está agora, mas é CRUCIAL para alinhar com rnn_predictor.py.
# Fazer o train_rnn_model.py funcionar e depois alinhar o rnn_predictor.py.
# Importante que as NUM_FEATURES e o input_shape do modelo estejam corretos.

# Esta variável será usada para nomear as colunas escaladas que vão para o modelo
# e deve corresponder ao que o rnn_predictor.py espera encontrar como features escaladas.
# Os nomes aqui devem ser as colunas de BASE_FEATURE_COLS com "_scaled" no final.