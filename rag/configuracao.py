"""Configuração compartilhada: indexação e busca usam o mesmo modelo e servidor."""
import os
from functools import lru_cache
from threading import RLock

NOME_COLECAO = os.getenv("CHROMA_COLLECTION", "qiskit_documentacao_multilingue")
MODELO_EMBEDDINGS = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
MODELO_LOCK = RLock()


@lru_cache(maxsize=1)
def obter_modelo():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODELO_EMBEDDINGS,
        device="cpu",
        local_files_only=os.getenv("GROWUP_PERMITIR_DOWNLOAD", "0") != "1",
        trust_remote_code=False,
    )


def criar_embeddings():
    # A mesma função é usada na escrita e na consulta. Nenhum embedding é gerado
    # pelo servidor e não há fallback para o modelo padrão do ChromaDB.
    def gerar(textos):
        with MODELO_LOCK:
            return obter_modelo().encode(
                textos, normalize_embeddings=True, convert_to_numpy=True,
                show_progress_bar=False,
            ).tolist()
    return gerar


def limite_tokens():
    return min(110, obter_modelo().max_seq_length)
