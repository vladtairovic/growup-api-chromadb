"""Atualiza os documentos do lote, sem apagar documentos não incluídos nele."""
import json
from collections import defaultdict
from pathlib import Path
from threading import RLock
from .configuracao import MODELO_EMBEDDINGS, MODELO_LOCK, criar_embeddings, obter_modelo, limite_tokens
from .banco import obter_colecao

ESCRITA_LOCK = RLock()


def validar_lote(chunks, modelo):
    if not isinstance(chunks, list) or not chunks:
        raise ValueError("Lote de chunks vazio ou inválido.")
    grupos = defaultdict(list)
    ids = set()
    for chunk in chunks:
        meta = chunk["metadados"]
        if chunk["id"] in ids:
            raise ValueError("IDs duplicados no lote.")
        ids.add(chunk["id"])
        if not chunk["texto"].strip() or not meta.get("document_id") or not meta.get("secao"):
            raise ValueError("Texto, documento ou seção ausente.")
        for campo in ("titulo", "fonte", "versao_documentacao", "coletado_em"):
            if not isinstance(meta.get(campo), str) or not meta[campo].strip():
                raise ValueError(f"Metadado obrigatório ausente: {campo}.")
        if type(meta.get("indice")) is not int or meta["indice"] < 0:
            raise ValueError("Índice inválido.")
        if not chunk["id"].startswith(meta["document_id"] + "_chunk_"):
            raise ValueError("ID incompatível com o documento.")
        if meta.get("modelo_embeddings") != modelo:
            raise ValueError("Modelo diferente da configuração. Prepare os chunks novamente.")
        if not 0 < meta.get("tokens", 0) <= 110:
            raise ValueError("Contagem de tokens inválida.")
        grupos[meta["document_id"]].append(chunk)
    return grupos


def atualizar_documento(colecao, document_id, chunks):
    validar_lote(chunks, MODELO_EMBEDDINGS)
    if any(c["metadados"]["document_id"] != document_id for c in chunks):
        raise ValueError("Lote mistura documentos.")
    # Calcula todos os vetores antes de começar a alterar os registros.
    vetores = criar_embeddings()([c["texto"] for c in chunks])
    with ESCRITA_LOCK:
        return _gravar_documento(colecao, document_id, chunks, vetores)


def _gravar_documento(colecao, document_id, chunks, vetores):
    antigos = set(colecao.get(where={"document_id": document_id})["ids"])
    atuais = {c["id"] for c in chunks}
    for inicio in range(0, len(chunks), 64):
        lote = chunks[inicio:inicio + 64]
        colecao.upsert(
            ids=[c["id"] for c in lote],
            documents=[c["texto"] for c in lote],
            metadatas=[c["metadados"] for c in lote],
            embeddings=vetores[inicio:inicio + 64],
        )
    obsoletos = sorted(antigos - atuais)
    if obsoletos:
        colecao.delete(ids=obsoletos)
    finais = set(colecao.get(where={"document_id": document_id})["ids"])
    if finais != atuais:
        raise RuntimeError(f"Falha na verificação de {document_id}.")
    return len(obsoletos)


def main():
    import argparse
    from .preparar_chunks import gerar_chunks

    parser = argparse.ArgumentParser(description="Reconstrói o índice remoto a partir do snapshot de documentos.")
    parser.add_argument("--origem", type=Path, default=Path("documentos/base_documental.json"))
    args = parser.parse_args()
    documentos = json.loads(args.origem.read_text(encoding="utf-8"))
    if not isinstance(documentos, list) or not documentos:
        raise ValueError("Lote documental vazio ou inválido.")
    if len({d["document_id"] for d in documentos}) != len(documentos):
        raise ValueError("Documentos duplicados no snapshot.")
    chunks = []
    with MODELO_LOCK:
        modelo = obter_modelo()
        for documento in documentos:
            chunks.extend(gerar_chunks(documento, modelo.tokenizer, limite_tokens(), MODELO_EMBEDDINGS))
    grupos = validar_lote(chunks, MODELO_EMBEDDINGS)
    colecao = obter_colecao()
    for document_id, trechos in grupos.items():
        removidos = atualizar_documento(colecao, document_id, trechos)
        print(document_id, "|", len(trechos), "chunks |", removidos, "obsoletos removidos")
    print("Documentos processados:", len(grupos))
    print("Total de chunks na coleção:", colecao.count())
    print("Documentos fora deste lote foram preservados.")


if __name__ == "__main__":
    main()
