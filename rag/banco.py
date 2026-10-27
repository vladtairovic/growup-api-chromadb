"""Acesso exclusivo por HTTP; nunca abre ou cria um banco local."""
import os
from functools import lru_cache

from .configuracao import MODELO_EMBEDDINGS, NOME_COLECAO


class ColecaoIncompativel(ValueError):
    pass


@lru_cache(maxsize=1)
def obter_cliente():
    import chromadb
    import httpx
    from chromadb.config import Settings

    cliente = chromadb.HttpClient(
        host=os.getenv("CHROMA_HOST", "chroma"),
        port=int(os.getenv("CHROMA_PORT", "8000")),
        ssl=os.getenv("CHROMA_SSL", "0") == "1",
        tenant=os.getenv("CHROMA_TENANT", "default_tenant"),
        database=os.getenv("CHROMA_DATABASE", "default_database"),
        settings=Settings(anonymized_telemetry=False, allow_reset=False),
    )
    # No SDK 1.5.9 o transporte síncrono vem sem timeout. A versão está fixada;
    # limitar a sessão impede que operações comuns prendam threads indefinidamente.
    cliente._server._session.timeout = httpx.Timeout(
        float(os.getenv("CHROMA_HTTP_TIMEOUT_SECONDS", "30")), connect=5.0,
    )
    return cliente


@lru_cache(maxsize=1)
def obter_colecao():
    esperado = {
        "modelo_embeddings": MODELO_EMBEDDINGS,
        "normalizado": True,
        "estrategia_chunks": "secoes_tokens_v2",
    }
    colecao = obter_cliente().get_or_create_collection(
        name=NOME_COLECAO, embedding_function=None, metadata=esperado,
        configuration={"hnsw": {"space": "l2"}},
    )
    if any((colecao.metadata or {}).get(k) != v for k, v in esperado.items()):
        raise ColecaoIncompativel(
            "A coleção existente não declara o mesmo modelo, normalização e formato. "
            "Preserve a base e reconstrua a partir das fontes; não há migração automática."
        )
    if (colecao.configuration.get("hnsw") or {}).get("space") != "l2":
        raise ColecaoIncompativel("A coleção deve usar distância l2, como a indexação original.")
    return colecao
