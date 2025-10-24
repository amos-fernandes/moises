# Dockerfile para ATCoin Real Trading System
FROM python:3.11-slim

# Informações do container
LABEL maintainer="ATCoin Trading Team"
LABEL description="ATCoin Real Trading System with Equilibrada_Pro Strategy"
LABEL version="3.0.0"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário não-root
RUN useradd --create-home --shell /bin/bash atcoin
WORKDIR /app

# Copia requirements primeiro (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY --chown=atcoin:atcoin . .

# Cria diretórios necessários
RUN mkdir -p /app/logs /app/data /app/static /app/templates
RUN chown -R atcoin:atcoin /app

# Muda para usuário não-root
USER atcoin

# Porta de exposição (ATCoin Real Trading)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Comando padrão - ATCoin Real Trading
CMD ["python", "app_real_trading.py"]
