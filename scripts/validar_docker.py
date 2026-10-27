"""Validação com Docker/embeddings reais em um projeto Compose isolado.

Execute da raiz: python scripts/validar_docker.py
Requer as imagens da aplicação e growup-api-tests já construídas.
Usa porta 18080 e volumes growup-validacao_*; não toca nos volumes de produção.
O teste reinicia seus containers, preservando os volumes, e não apaga os dados.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"
PROJECT = "growup-validacao"
ENV = {
    **os.environ, "API_PORT": "18080", "GROWUP_PERMITIR_DOWNLOAD": "1",
    "CHROMA_COLLECTION": "qiskit_documentacao_multilingue",
    "EMBEDDING_MODEL": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "RAG_MAX_DISTANCE": "", "API_TIMEOUT_SECONDS": "120",
}
COMPOSE = ["docker", "compose", "-p", PROJECT]
REPORT = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "etapas": []}


def registrar(etapa, **dados):
    REPORT["etapas"].append({"etapa": etapa, **dados})
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "validacao-docker.json").write_text(
        json.dumps(REPORT, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"etapa": etapa, **dados}, ensure_ascii=False), flush=True)


def executar(args, timeout=900):
    result = subprocess.run(
        args, cwd=ROOT, env=ENV, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError(
            f"Comando falhou ({result.returncode}): {args}\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout.strip()


def dentro(codigo):
    return executar(COMPOSE + ["exec", "-T", "api", "python", "-c", codigo])


def estado_banco():
    return json.loads(dentro(
        "import json; from rag.banco import obter_cliente, obter_colecao; "
        "c=obter_colecao(); r=c.get(include=['metadatas']); "
        "v=c.get(limit=1,include=['embeddings'])['embeddings']; "
        "print(json.dumps({'colecoes':obter_cliente().count_collections(),"
        "'nome':c.name,'id_colecao':str(c.id),'chunks':c.count(),"
        "'ids':sorted(r['ids']),'documentos':sorted({m['document_id'] for m in r['metadatas']}),"
        "'dimensao':len(v[0]) if v is not None and len(v) else None,"
        "'modelo':(c.metadata or {}).get('modelo_embeddings')}))"
    ))


def requisicao(method, path, payload=None, arquivo=None):
    headers = {}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if arquivo is not None:
        nome, conteudo = arquivo
        boundary = "growup" + uuid4().hex
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{nome}"'
            '\r\nContent-Type: text/plain\r\n\r\n'
        ).encode("utf-8") + conteudo + f"\r\n--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = Request("http://127.0.0.1:18080" + path, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=180) as response:
            return response.status, json.load(response), dict(response.headers)
    except HTTPError as response:
        return response.code, json.load(response), dict(response.headers)


def conferir(method, path, esperado, payload=None, arquivo=None):
    status, body, headers = requisicao(method, path, payload, arquivo)
    assert status == esperado, (path, esperado, status, body)
    return body, headers


def aguardar_banco():
    prazo = time.monotonic() + 120
    while time.monotonic() < prazo:
        try:
            status, _, _ = requisicao("GET", "/documents")
            if status == 200:
                return
        except (URLError, TimeoutError):
            pass
        time.sleep(2)
    raise RuntimeError("Banco não voltou a responder em 120 segundos.")


def main():
    config = json.loads(executar(COMPOSE + ["config", "--format", "json"]))
    assert set(config["services"]) == {"api", "chroma"}
    assert not config["services"]["chroma"].get("ports")
    assert config["networks"]["banco"]["internal"] is True
    # Não reutilizar silenciosamente um volume de validação já preenchido.
    # Em reexecuções locais, preserve-o e escolha conscientemente outro ambiente.
    executar(COMPOSE + ["up", "-d", "--wait", "--wait-timeout", "900"], timeout=1000)
    health, _ = conferir("GET", "/health", 200)
    assert health == {"status": "ok", "mode": "integrated"}
    inicial = estado_banco()
    assert inicial["colecoes"] == 1
    assert inicial["chunks"] == 0, "O volume de validação já contém dados; preserve-o."
    vazio, _ = conferir("POST", "/search", 200, {"query": "transpilação"})
    assert vazio["status"] == "insufficient_context" and vazio["chunks"] == []
    registrar("containers_iniciados_base_vazia", colecoes=inicial["colecoes"])

    indice = executar(COMPOSE + [
        "exec", "-T", "api", "python", "-m", "rag.indexar_documentos",
        "--origem", "documentos/base_documental.json",
    ])
    primeiro = estado_banco()
    fontes = json.loads((ROOT / "documentos" / "base_documental.json").read_text(encoding="utf-8"))
    assert primeiro["documentos"] == sorted(d["document_id"] for d in fontes)
    assert primeiro["chunks"] > 3 and primeiro["dimensao"] == 384
    assert len(primeiro["ids"]) == len(set(primeiro["ids"]))
    assert primeiro["colecoes"] == 1
    registrar("snapshot_indexado", documentos=len(primeiro["documentos"]),
              chunks=primeiro["chunks"], dimensao=primeiro["dimensao"], saida=indice)

    executar(COMPOSE + ["exec", "-T", "api", "python", "-m", "rag.indexar_documentos"])
    segundo = estado_banco()
    assert segundo == primeiro
    registrar("reindexacao_idempotente", chunks=segundo["chunks"])

    inicio = time.perf_counter()
    busca, headers = conferir("POST", "/search", 200, {"query": "Para que serve a transpilação?"})
    assert busca["status"] == "ok" and busca["mode"] == "integrated"
    assert busca["chunks"] and all(c["content"].strip() for c in busca["chunks"])
    assert any("transpil" in c["content"].lower() for c in busca["chunks"])
    assert set(busca["citations"]).issubset({d["fonte"] for d in fontes})
    assert {k.lower(): v for k, v in headers.items()}["x-request-id"] == busca["request_id"]
    registrar("busca_semantica_real", segundos=round(time.perf_counter() - inicio, 3),
              fontes=busca["citations"])

    nome = "validacao-persistencia-" + uuid4().hex + ".txt"
    texto = (
        "O observatório GrowUp armazena registros de auroras violetas no planeta Zafira. "
        "O instrumento específico desta validação se chama espectrômetro Jacarandá."
    ).encode("utf-8")
    upload, _ = conferir("POST", "/documents", 201, arquivo=(nome, texto))
    doc_id = upload["id"]
    repetido, _ = conferir("POST", "/documents", 201, arquivo=(nome, texto))
    assert repetido["id"] == doc_id
    lista, _ = conferir("GET", "/documents", 200)
    assert sum(d["id"] == doc_id for d in lista["documents"]) == 1
    recuperado, _ = conferir("POST", "/search", 200, {"query": texto.decode("utf-8")})
    assert any(c["document_id"] == doc_id and c["source"] == nome for c in recuperado["chunks"])
    registrar("upload_listagem_busca_e_reenvio", document_id=doc_id)

    falta_llm, _ = conferir("POST", "/query", 503, {"input": "Otimize o circuito."})
    assert falta_llm["code"] == "LLM_NOT_CONFIGURED"
    assert "nenhuma resposta de IA" in falta_llm["message"]
    conferir("POST", "/query", 422, {})
    conferir("POST", "/search", 422, {"query": ""})
    conferir("POST", "/documents", 415, arquivo=("arquivo.pdf", b"texto"))
    conferir("POST", "/documents", 422, arquivo=("vazio.txt", b""))
    conferir("POST", "/documents", 413, arquivo=("grande.txt", b"x" * 262145))
    registrar("validacoes_http_e_llm_ausente", codigo_llm=falta_llm["code"])

    avaliacao = json.loads((ROOT / "exemplos" / "avaliacao.json").read_text(encoding="utf-8"))
    avaliacao["case_id"] = "validacao-docker-" + uuid4().hex
    avaliada, _ = conferir("POST", "/evaluate", 201, avaliacao)
    assert avaliada["approved"] is True
    antes = estado_banco()
    assert antes["colecoes"] == 1
    registrar("avaliacao_gravada", id=avaliada["id"])

    executar(COMPOSE + ["stop", "chroma"])
    falha, _ = conferir("POST", "/search", 503, {"query": "Qiskit"})
    assert falha["code"] == "SERVICE_ERROR"
    conferir("GET", "/documents", 503)
    conferir("GET", "/health", 200)  # liveness, conforme o contrato
    executar(COMPOSE + ["start", "chroma"])
    aguardar_banco()
    registrar("indisponibilidade_e_recuperacao", http_busca=503)

    executar(COMPOSE + ["down"])  # sem -v: preserva os volumes
    ENV["GROWUP_PERMITIR_DOWNLOAD"] = "0"
    executar(COMPOSE + ["up", "-d", "--wait", "--wait-timeout", "900"], timeout=1000)
    depois = estado_banco()
    assert depois == antes
    lista, _ = conferir("GET", "/documents", 200)
    assert any(d["id"] == doc_id for d in lista["documents"])
    recuperado, _ = conferir("POST", "/search", 200, {"query": texto.decode("utf-8")})
    assert any(c["document_id"] == doc_id for c in recuperado["chunks"])
    ids_avaliacoes = json.loads(dentro(
        "import json,os; from pathlib import Path; "
        "print(json.dumps([json.loads(l)['id'] for l in "
        "Path(os.environ['AVALIACOES_PATH']).read_text().splitlines() if l.strip()]))"
    ))
    assert avaliada["id"] in ids_avaliacoes
    registrar("persistencia_apos_recriar_containers",
              chunks=depois["chunks"], documentos=len(depois["documentos"]),
              colecoes=depois["colecoes"], modelo_carregado_sem_download=True,
              avaliacao_preservada=True)

    conferir_deps = executar(COMPOSE + ["exec", "-T", "api", "python", "-m", "pip", "check"])
    registrar("dependencias_no_container", resultado=conferir_deps)
    live = executar([
        "docker", "run", "--rm", "--network", PROJECT + "_banco",
        "-e", "GROWUP_TEST_URL=http://api:8000", "growup-api-tests",
        "python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "live",
    ])
    registrar("teste_pytest_live", resultado=live)
    REPORT["resultado"] = "aprovado"
    REPORT["fim_utc"] = datetime.now(timezone.utc).isoformat()
    registrar("validacao_concluida", resultado="aprovado")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        REPORT["resultado"] = "falhou"
        registrar("falha", tipo=type(erro).__name__, mensagem=str(erro))
        raise
