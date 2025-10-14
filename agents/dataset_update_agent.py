# agents/dataset_update_agent.py
import pandas as pd
from datetime import datetime

def update_dataset(path="data/sp500_news.csv", new_data=pd.DataFrame()):
    df = pd.read_csv(path)
    combined = pd.concat([df, new_data]).drop_duplicates().reset_index(drop=True)
    combined.to_csv(path, index=False)
    print(f"Dataset atualizado: {path}")
