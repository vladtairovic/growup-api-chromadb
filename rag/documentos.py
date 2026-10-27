"""Ingestão mínima de arquivos textuais e catálogo derivado da mesma coleção."""
from datetime import datetime, timezone
from hashlib import sha256

from .banco import obter_colecao
from .configuracao import MODELO_EMBEDDINGS, MODELO_LOCK, obter_modelo, limite_tokens
from .indexar_documentos import atualizar_documento, validar_lote
from .preparar_chunks import gerar_chunks


class ConteudoInvalido(ValueError):
    pass


def adicionar_documento(filename, content):
    texto = content.decode("utf-8-sig")
    # Repetir exatamente o mesmo upload é idempotente, inclusive após um timeout.
    document_id = "upload_" + sha256(filename.encode("utf-8") + b"\0" + content).hexdigest()
    documento = {
        "document_id": document_id, "titulo": filename, "fonte": filename,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
        "versao_documentacao": "arquivo enviado pelo usuário",
        "secoes": [{"titulo": "Documento enviado", "blocos": [
            {"tipo": "paragrafo", "texto": texto}
        ]}],
    }
    with MODELO_LOCK:
        modelo = obter_modelo()
        try:
            chunks = gerar_chunks(documento, modelo.tokenizer, limite_tokens(), MODELO_EMBEDDINGS)
        except ValueError as erro:
            raise ConteudoInvalido(str(erro)) from erro
    for chunk in chunks:
        chunk["metadados"]["filename"] = filename
    validar_lote(chunks, MODELO_EMBEDDINGS)
    atualizar_documento(obter_colecao(), document_id, chunks)
    return {"id": document_id, "filename": filename}


def listar_documentos():
    colecao = obter_colecao()
    documentos = {}
    offset = 0
    while True:
        pagina = colecao.get(limit=256, offset=offset, include=["metadatas"])
        for meta in pagina["metadatas"]:
            documentos[meta["document_id"]] = {
                "id": meta["document_id"],
                "filename": meta.get("filename") or meta["titulo"],
            }
        if len(pagina["ids"]) < 256:
            break
        offset += 256
    return sorted(documentos.values(), key=lambda d: (d["filename"], d["id"]))
