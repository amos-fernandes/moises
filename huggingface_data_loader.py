import pandas as pd
from zipfile import ZipFile
import os

# Caminho local do cache do Hugging Face
hf_cache_path = os.path.expanduser("~/.cache/huggingface/hub/datasets--pmoe7--SP_500_Stocks_Data-ratios_news_price_10_yrs/snapshots")

# Descobre snapshot baixado
snapshot_dir = os.listdir(hf_cache_path)[0]
base_path = os.path.join(hf_cache_path, snapshot_dir)

# Carrega os dados de preços + múltiplos fundamentalistas
ratios_path = os.path.join(base_path, "sp500_daily_ratios_20yrs.zip")
with ZipFile(ratios_path, 'r') as zip_ref:
    zip_ref.extractall("data/")
ratios_df = pd.read_csv("data/sp500_daily_ratios_20yrs.csv")

# Carrega os dados de notícias e sentimentos
news_path = os.path.join(base_path, "sp500_news_290k_articles.csv")
news_df = pd.read_csv(news_path)

# Salva para uso futuro
ratios_df.to_csv("data/sp500_ratios.csv", index=False)
news_df.to_csv("data/sp500_news.csv", index=False)
