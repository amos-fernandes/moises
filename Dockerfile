FROM python:3.10-slim

# Diretório de trabalho
WORKDIR /app

# Copia os arquivos do projeto
COPY . /app

# Atualiza pip e instala dependências
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Expõe porta padrão Gradio ou Uvicorn
EXPOSE 7860
# Comando de inicialização
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
