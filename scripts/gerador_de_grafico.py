import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os

# Criar pasta para salvar os gráficos
output_dir = "graficos_tese"
os.makedirs(output_dir, exist_ok=True)

# ============================
# Figura 1 – Endividamento vs. Inadimplência
# ============================
anos = list(range(2005, 2025))
endividamento = [46, 49, 53, 56, 58, 59, 59.8, 61, 62.5, 64.3, 66.5, 68.1, 70, 71.4, 72.8, 74.3, 76.1, 77.9, 78.5, 78.5]
inadimplencia = [6.2, 6.4, 6.8, 7.1, 7.3, 7.9, 8.1, 8.4, 9.1, 9.7, 10.3, 10.9, 11.3, 11.7, 12.1, 12.3, 12.4, 12.6, 12.7, 12.7]

fig, ax1 = plt.subplots(figsize=(10, 6))
ax1.plot(anos, endividamento, 'b-', label='Famílias Endividadas (%)')
ax2 = ax1.twinx()
ax2.plot(anos, inadimplencia, 'r-', label='Inadimplência (%)')

ax1.set_xlabel('Ano')
ax1.set_ylabel('Endividamento (%)', color='blue')
ax2.set_ylabel('Inadimplência (%)', color='red')
plt.title('Figura 1 – Evolução da Inadimplência e Endividamento (2005–2024)')
fig.tight_layout()
plt.savefig(f"{output_dir}/figura_1.png")
plt.close()

# ============================
# Figura 2 – Comparativo Internacional de Spread Bancário
# ============================
spread_data = pd.DataFrame({
    'País': ['Brasil', 'Chile', 'México', 'Índia', 'EUA'],
    'Spread (%)': [30.2, 12.4, 9.8, 7.1, 3.5]
})
plt.figure(figsize=(8, 5))
sns.barplot(x='Spread (%)', y='País', data=spread_data, palette='flare')
plt.title('Figura 2 – Spread Bancário por País (2024)')
plt.tight_layout()
plt.savefig(f"{output_dir}/figura_2.png")
plt.close()

# ============================
# Figura 3 – Comprometimento da Renda com Dívidas
# ============================
comp_renda = [18.2, 19.4, 20.6, 21.2, 22.5, 23.1, 24.4, 25.3, 26.7, 27.9, 28.7, 29.4, 30.1, 30.2, 30.5, 30.6, 30.6, 30.6, 30.6, 30.6]
plt.figure(figsize=(9, 5))
plt.plot(anos, comp_renda, color='darkgreen', marker='o')
plt.title('Figura 3 – Comprometimento da Renda Familiar com Dívidas (2005–2024)')
plt.xlabel('Ano')
plt.ylabel('Comprometimento (%)')
plt.grid(True)
plt.tight_layout()
plt.savefig(f"{output_dir}/figura_3.png")
plt.close()

# ============================
# Figura 4 – SELIC, IPCA e Inadimplência
# ============================
df_macro = pd.DataFrame({
    'Ano': [2010, 2015, 2020, 2022, 2024],
    'SELIC (%)': [10.75, 14.25, 2.0, 13.75, 10.5],
    'IPCA (%)': [5.91, 10.67, 4.52, 5.79, 5.8],
    'Inadimplência (%)': [6.2, 8.1, 11.3, 12.1, 12.7]
})
df_macro.set_index('Ano', inplace=True)
df_macro.plot(marker='o', figsize=(10, 6))
plt.title('Figura 2 – SELIC, IPCA e Inadimplência no Brasil (2010–2024)')
plt.ylabel('Percentual (%)')
plt.grid(True)
plt.tight_layout()
plt.savefig(f"{output_dir}/figura_2.png")
plt.close()

# Você pode adicionar outros gráficos aqui com a mesma estrutura...

print(f"✅ Gráficos salvos com sucesso em: ./{output_dir}/")




import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

data = pd.DataFrame({
    'País': ['Brasil', 'Chile', 'México', 'Índia', 'EUA'],
    'Spread Bancário (%)': [30.2, 12.4, 9.8, 7.1, 3.5]
})

plt.figure(figsize=(8, 5))
sns.barplot(x='Spread Bancário (%)', y='País', data=data, palette='flare')
plt.title('Comparativo de Spread Bancário Internacional (2024)')
plt.xlabel('Spread (%)')
plt.tight_layout()
plt.savefig(f"{output_dir}/figura_2.png")

plt.show()
plt.close()



#------

import matplotlib.pyplot as plt
import pandas as pd
import os

# Criar diretório para salvar
output_dir = "graficos_tese"
os.makedirs(output_dir, exist_ok=True)

# Dados simulados com base em fontes públicas (ajuste conforme necessário)
anos = list(range(2005, 2024))
crescimento_credito = [15.2, 17.8, 20.1, 18.5, 16.3, 14.7, 13.2, 12.5, 11.1, 10.4, 9.8, 8.6, 7.9, 6.5, 5.2, 6.1, 7.4, 8.2, 9.1]
crescimento_pib = [3.2, 4.0, 6.1, 5.2, -0.1, 7.5, 3.9, 1.9, 3.0, 0.5, -3.5, -3.3, 1.3, 1.8, 1.1, -4.1, 4.6, 2.9, 2.3]

# Criar DataFrame
df = pd.DataFrame({
    'Ano': anos,
    'Crescimento do Crédito (%)': crescimento_credito,
    'Crescimento do PIB (%)': crescimento_pib
})

# Plotar gráfico
plt.figure(figsize=(10, 6))
plt.plot(df['Ano'], df['Crescimento do Crédito (%)'], label='Crescimento do Crédito (%)', marker='o', color='blue')
plt.plot(df['Ano'], df['Crescimento do PIB (%)'], label='Crescimento do PIB (%)', marker='s', color='green')
plt.title('Figura 3.1 – Correlação entre Crescimento do Crédito e PIB Real (2005–2023)')
plt.xlabel('Ano')
plt.ylabel('Variação (%)')
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.savefig(f"{output_dir}/figura_3_1.png")
plt.close()

print(f"✅ Figura 3.1 salva com sucesso em: ./{output_dir}/figura_3_1.png")
