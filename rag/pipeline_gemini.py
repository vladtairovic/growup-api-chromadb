"""RAG híbrido: coleção local e Google Search opcional, com fontes identificáveis."""
import os
from . import busca_chromadb, cliente_gemini, busca_web
from .contexto_gemini import preparar_contexto, MENSAGEM_SEM_CONTEXTO


def responder(pergunta, top_k=3, web_search=None):
    habilitado = os.getenv("WEB_SEARCH_ENABLED", "0") == "1" if web_search is None else web_search
    documentos = busca_chromadb.buscar_documentos(pergunta, quantidade=top_k)
    contexto, referencias = preparar_contexto(documentos, limite=int(os.getenv("GROWUP_MAX_CONTEXT_CHARS", "12000")))
    usados = [d for d in documentos if d.get("texto", "").strip()][:len(referencias)]
    fontes = [{"document_id": d["metadados"]["document_id"], "chunk_id": d["id"],
               "source": d["metadados"]["fonte"], "content": d["texto"],
               "origin": "local", "title": d["metadados"].get("titulo"),
               "retrieved_at": d["metadados"].get("coletado_em")} for d in usados]
    if habilitado:
        try:
            resultado = busca_web.pesquisar(pergunta, contexto)
        except Exception as erro:
            # Não informa detalhes do provedor nem apresenta falha como busca bem-sucedida.
            raise busca_web.BuscaWebIndisponivel() from erro
        if not fontes and not resultado["sources"]:
            return {"response": MENSAGEM_SEM_CONTEXTO, "sources": [], "status": "insufficient_context",
                    "web_status": "not_used", "warnings": ["O provedor não retornou evidências web verificáveis."]}
        return {**resultado, "sources": fontes + resultado["sources"], "status": "ok",
                "warnings": [] if resultado["web_status"] == "used" else
                ["A busca web estava habilitada, mas o provedor não retornou fontes web. Confira as fontes locais."]}
    if not contexto.strip():
        return {"response": MENSAGEM_SEM_CONTEXTO, "sources": [], "status": "insufficient_context"}
    return {"response": cliente_gemini.gerar_resposta(pergunta, contexto), "sources": fontes, "status": "ok"}
