# agents/investment_agent.py
def execute_investment(prediction, threshold=0.8):
    if prediction > threshold:
        print("Comprar ativos com probabilidade:", prediction)
        # chamada API para execução real
    else:
        print("Não investir. Probabilidade baixa:", prediction)
