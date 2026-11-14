"""Atualização incremental do catálogo, com snapshots e limites de crescimento."""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .coleta_web import Coletor, validar_url

log = logging.getLogger(__name__)
CATALOGO = Path(__file__).resolve().parents[1] / "documentos/fontes_conhecimento.json"


def pasta():
    return Path(os.getenv("KNOWLEDGE_PATH", "/app/data/conhecimento"))


def gravar(path, dados):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def ler_status():
    try:
        return json.loads((pasta() / "status.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"status": "not_started", "documents": []}


def sincronizar(reindexar=False):
    from .banco import obter_colecao
    from .configuracao import MODELO_EMBEDDINGS, MODELO_LOCK, obter_modelo, limite_tokens
    from .preparar_chunks import gerar_chunks
    from .indexar_documentos import atualizar_documento
    # Docker Linux: flock é liberado inclusive se o processo morrer.
    import fcntl
    destino = pasta()
    destino.mkdir(parents=True, exist_ok=True)
    with (destino / ".sync.lock").open("w") as trava:
        try:
            fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running"}
        catalogo = json.loads(CATALOGO.read_text(encoding="utf-8"))
        if len(catalogo) > 32 or len({d["document_id"] for d in catalogo}) != len(catalogo):
            raise ValueError("Catálogo duplicado ou acima de 32 páginas.")
        for fonte in catalogo:
            validar_url(fonte["url"])
            if not fonte["document_id"].replace("_", "").isalnum():
                raise ValueError("Identificador de documento inválido.")
        colecao = obter_colecao()
        status = {"status": "running", "started_at": datetime.now(timezone.utc).isoformat(), "documents": []}
        gravar(destino / "status.json", status)
        # Reindexação usa somente snapshots locais, mesmo sem internet.
        from contextlib import nullcontext
        try:
            with (nullcontext(None) if reindexar else Coletor()) as coletor:
                for fonte in catalogo:
                    doc_id = fonte["document_id"]
                    arquivo = destino / f"{doc_id}.json"
                    status["current_document"] = doc_id
                    gravar(destino / "status.json", status)
                    try:
                        anterior = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else None
                        if reindexar:
                            if anterior is None:
                                raise ValueError("Snapshot ainda não coletado.")
                            documento = anterior
                        else:
                            titulo, secoes = coletor.coletar(fonte["url"])
                            documento = {
                                "document_id": doc_id, "titulo": titulo, "fonte": getattr(coletor, "ultima_url", fonte["url"]),
                                "url_solicitada": fonte["url"],
                                "secoes": secoes, "versao_documentacao": fonte["versao"],
                                "versao_alvo_qiskit": "2.6",
                                "coletado_em": datetime.now(timezone.utc).isoformat(),
                            }
                        digest = hashlib.sha256(json.dumps(
                            [documento["secoes"], documento["fonte"], MODELO_EMBEDDINGS],
                            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                        existentes = colecao.get(where={"document_id": doc_id}, include=[])["ids"]
                        if (not reindexar and anterior and anterior.get("hash") == digest
                                and anterior.get("indexed") is True
                                and len(existentes) == anterior.get("chunks")):
                            resultado = "unchanged"
                            n = len(existentes)
                        else:
                            with MODELO_LOCK:
                                modelo = obter_modelo()
                                chunks = gerar_chunks(documento, modelo.tokenizer, limite_tokens(), MODELO_EMBEDDINGS)
                            n = len(chunks)
                            if n > 4000 or colecao.count() - len(existentes) + n > 20000:
                                raise ValueError("Limite de 4000 trechos/página ou 20000 na coleção atingido.")
                            # Guarda o texto antes da escrita remota; uma falha permite repetir a operação.
                            documento.update(hash=digest, chunks=n, indexed=False)
                            if anterior and anterior.get("indexed"):
                                gravar(destino / f"{doc_id}.previous.json", anterior)
                            gravar(arquivo, documento)
                            atualizar_documento(colecao, doc_id, chunks)
                            documento["indexed"] = True
                            gravar(arquivo, documento)
                            resultado = "indexed"
                        status["documents"].append({"id": doc_id, "status": resultado, "chunks": n})
                    except Exception as erro:
                        log.warning("Coleta %s falhou: %s", doc_id, type(erro).__name__)
                        status["documents"].append({"id": doc_id, "status": "error", "error": str(erro)[:240]})
                    gravar(destino / "status.json", status)
            status["status"] = "partial" if any(d["status"] == "error" for d in status["documents"]) else "ok"
        except Exception as erro:
            status.update(status="error", error=type(erro).__name__)
        status.pop("current_document", None)
        status["finished_at"] = datetime.now(timezone.utc).isoformat()
        status["collection_chunks"] = colecao.count()
        gravar(destino / "status.json", status)
        return status


async def agendar():
    intervalo = max(3600, int(os.getenv("KNOWLEDGE_SYNC_INTERVAL_SECONDS", "604800")))
    while True:
        try:
            status = ler_status()
            ultima = status.get("finished_at")
            passou = time.time() - datetime.fromisoformat(ultima).timestamp() if ultima else intervalo
            if passou >= intervalo:
                # Processo separado permite encerrar coleta e liberar lock no desligamento da API.
                processo = await asyncio.create_subprocess_exec(
                    "python", "-m", "rag.sincronizar_conhecimento")
                try:
                    await processo.wait()
                except asyncio.CancelledError:
                    if processo.returncode is None:
                        processo.terminate()
                        await processo.wait()
                    raise
        except Exception:
            log.exception("Falha na atualização agendada.")
        await asyncio.sleep(min(intervalo, 3600))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reindex", action="store_true", help="Reconstrói usando snapshots, sem acessar a web.")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    resultado = ler_status() if args.status else sincronizar(args.reindex)
    print(json.dumps(resultado, ensure_ascii=True, indent=2))
    if resultado["status"] in ("error", "partial"):
        raise SystemExit(1)
