FROM python:3.12-slim

WORKDIR /app

# Install system deps for lxml, paramiko, netmiko
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt-dev \
    libssl-dev \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Exclude sentence-transformers (pulls torch+CUDA ~2GB); Docker uses openai embeddings instead
RUN grep -v 'sentence-transformers' requirements.txt > requirements-docker.txt \
    && pip install --no-cache-dir -r requirements-docker.txt

COPY . .

CMD ["uvicorn", "aegis.main:app", "--host", "0.0.0.0", "--port", "8000"]
