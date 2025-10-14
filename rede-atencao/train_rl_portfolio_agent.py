# train_rl_portfolio_agent.py
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

from data_handler_multi_asset import get_multi_asset_data_for_rl, MULTI_ASSET_SYMBOLS # Do seu config/data_handler
from portfolio_environment import PortfolioEnv # Seu ambiente
from deep_portfolio import DeepPortfolioAI # Seu modelo (usado como policy)
# from config import ... # Outras configs

# 1. Carregar e preparar dados multi-ativos
# (MULTI_ASSET_SYMBOLS viria do config.py)
asset_keys_list = list(MULTI_ASSET_SYMBOLS.keys()) # ['crypto_eth', 'crypto_ada', ...]

multi_asset_df = get_multi_asset_data_for_rl(
    MULTI_ASSET_SYMBOLS, 
    timeframe_yf='1h', # Ou TIMEFRAME_YFINANCE do config
    days_to_fetch=365*2 # Ou DAYS_TO_FETCH do config
)

if multi_asset_df is None or multi_asset_df.empty:
    print("Falha ao carregar dados multi-ativos. Encerrando treinamento RL.")
    exit()

# 2. Criar o Ambiente
# O multi_asset_df já deve ter as features para observação E as colunas de preço de close original
env = PortfolioEnv(df_multi_asset_features=multi_asset_df, asset_symbols_list=asset_keys_list)

# Opcional: Verificar se o ambiente está em conformidade com a API do Gymnasium
# check_env(env) # Pode dar avisos/erros se algo estiver errado
print("Ambiente de Portfólio Criado.")
print(f"Observation Space: {env.observation_space.shape}")
print(f"Action Space: {env.action_space.shape}")

# 3. Definir a Política de Rede Neural
# Stable-Baselines3 permite que você defina uma arquitetura customizada.
# Precisamos de uma forma de passar sua arquitetura DeepPortfolioAI para o PPO.
# Uma maneira é criar uma classe de política customizada.
# Por agora, vamos usar a política padrão "MlpPolicy" e depois vemos como integrar a sua.
# Ou, se DeepPortfolioAI for uma tf.keras.Model, podemos tentar usá-la em policy_kwargs.

# Para usar sua DeepPortfolioAI, você precisaria de uma FeatureExtractor customizada
# ou uma política que a incorpore, o que é mais avançado com Stable-Baselines3.
# Vamos começar com MlpPolicy para testar o ambiente.

# policy_kwargs = dict(
#     features_extractor_class=YourCustomFeatureExtractor, # Se a entrada precisar de tratamento especial
#     features_extractor_kwargs=dict(features_dim=128),
#     net_arch=[dict(pi=[256, 128], vf=[256, 128])] # Exemplo de arquitetura para policy e value networks
# )
# Ou, se o DeepPortfolioAI puder ser adaptado para ser a policy_network:
# policy_kwargs = dict(
#    net_arch=dict(
#        pi=[{'model': DeepPortfolioAI(num_assets=env.num_assets)}], # Não é direto assim
#        vf=[] # Value function pode ser separada ou compartilhada
#    )
# )

# Para começar e testar o ambiente, use a MlpPolicy padrão.
# O input da MlpPolicy será a observação achatada (WINDOW_SIZE * num_total_features).
# Isso pode não ser ideal para dados sequenciais. "MlpLstmPolicy" é melhor.

model_ppo = PPO("MlpLstmPolicy", env, verbose=1, tensorboard_log="./ppo_portfolio_tensorboard/")
# Se "MlpLstmPolicy" não funcionar bem com o shape da observação (janela, features_totais),
# você pode precisar de um FeatureExtractor que achate a janela, ou uma política customizada.

# 4. Treinar o Agente
print("Iniciando treinamento do agente PPO...")
model_ppo.learn(total_timesteps=1000000, progress_bar=True) # Aumente timesteps para treino real

# 5. Salvar o Modelo Treinado
model_ppo.save("rl_models/ppo_deep_portfolio_agent")
print("Modelo RL treinado salvo.")

# (Opcional) Testar o agente treinado
obs, _ = env.reset()
for _ in range(200):
    action, _states = model_ppo.predict(obs, deterministic=True)
    obs, rewards, terminated, truncated, info = env.step(action)
    env.render()
    if terminated or truncated:
        obs, _ = env.reset()
env.close()