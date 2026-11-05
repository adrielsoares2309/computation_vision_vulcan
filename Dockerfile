# Dockerfile para VulcanTech Smart Metals S.A.
FROM python:3.11-slim

WORKDIR /app

# Instalar dependências de sistema necessárias para OpenCV headless
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar manifesto de dependências
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código-fonte do projeto
COPY . .

# Criar diretórios de persistência se não existirem
RUN mkdir -p database data/processed reports models/tabular

# Expor portas da API (8000) e do Streamlit (8501)
EXPOSE 8000 8501

# Comando padrão (pode ser sobrescrito pelo docker-compose)
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

