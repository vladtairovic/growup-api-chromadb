"""Adapta o fluxo Pessoa4 ao contrato HTTP, propagando falhas externas."""
import os
from . import busca_chromadb, cliente_gemini
from .contexto_gemini import preparar_contexto, MENSAGEM_SEM_CONTEXTO

def responder(pergunta):
    documentos = busca_chromadb.buscar_documentos(pergunta)
    contexto, referencias = preparar_contexto(documentos, limite=int(os.getenv("GROWUP_MAX_CONTEXT_CHARS", "12000")))
    if not contexto.strip():
        return {"response": MENSAGEM_SEM_CONTEXTO, "sources": [], "status": "insufficient_context"}
    usados = [d for d in documentos if d.get("texto", "").strip()][:len(referencias)]
    fontes = [{"document_id": d["metadados"]["document_id"], "chunk_id": d["id"],
               "source": d["metadados"]["fonte"], "content": d["texto"]} for d in usados]
    return {"response": cliente_gemini.gerar_resposta(pergunta, contexto), "sources": fontes, "status": "ok"}
