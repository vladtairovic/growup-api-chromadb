FROM python:3.12-slim-bookworm AS core
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

FROM core AS test
COPY requirements-testes.txt ./
RUN pip install --no-cache-dir -r requirements-testes.txt
COPY . .
CMD ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

FROM core AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
# O modelo original roda em CPU. Não instalar as dependências CUDA do PyPI.
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.14.1 \
    && pip install --no-cache-dir -r requirements.txt \
    && pip check
RUN useradd --create-home --uid 10001 growup \
    && mkdir -p /app/data /home/growup/.cache/huggingface \
    && chown -R growup:growup /app /home/growup
COPY --chown=growup:growup main.py servicos.py contratos.py exportar_openapi.py openapi.json ./
COPY --chown=growup:growup rag ./rag
COPY --chown=growup:growup documentos ./documentos
COPY --chown=growup:growup exemplos ./exemplos
ENV HF_HOME=/home/growup/.cache/huggingface \
    TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2 \
    HF_HUB_DISABLE_TELEMETRY=1
USER growup
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
