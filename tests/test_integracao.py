"""Fluxos reais do adaptador/RAG, com coleção e embeddings substituídos em memória."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import main
import servicos
from rag import banco, busca_chromadb, configuracao, documentos, indexar_documentos


class TokenizerTeste:
    def encode(self, text, **kwargs):
        return list(range(len(text.split()) + 2))


class ColecaoTeste:
    def __init__(self):
        self.registros = {}
        self.falhar_escrita = False
        self.metadata = {
            "modelo_embeddings": configuracao.MODELO_EMBEDDINGS,
            "normalizado": True, "estrategia_chunks": "secoes_tokens_v2",
        }
        self.configuration = {"hnsw": {"space": "l2"}}

    def count(self):
        return len(self.registros)

    def upsert(self, ids, documents, metadatas, embeddings):
        if self.falhar_escrita:
            raise ConnectionError("falha de teste")
        assert len(ids) == len(documents) == len(metadatas) == len(embeddings)
        for id, texto, meta, vetor in zip(ids, documents, metadatas, embeddings):
            self.registros[id] = (texto, deepcopy(meta), vetor)

    def get(self, where=None, include=None, limit=None, offset=0):
        filtros = (where or {}).get("$and", [where or {}])
        itens = [(id, r) for id, r in self.registros.items()
                 if all(all(r[1].get(k) == v for k, v in f.items()) for f in filtros)]
        itens = itens[offset:offset + limit if limit is not None else None]
        return {"ids": [i[0] for i in itens], "documents": [i[1][0] for i in itens],
                "metadatas": [i[1][1] for i in itens]}

    def delete(self, ids):
        for id in ids:
            self.registros.pop(id, None)

    def query(self, query_embeddings, n_results, include):
        assert query_embeddings
        # Ordem invertida para verificar reconstituição por indice.
        itens = list(reversed(list(self.registros.items())))[:n_results]
        return {"ids": [[i[0] for i in itens]],
                "metadatas": [[i[1][1] for i in itens]],
                "distances": [[0.2 for _ in itens]]}


@pytest.fixture
def contexto(monkeypatch, tmp_path):
    colecao = ColecaoTeste()
    modelo = SimpleNamespace(tokenizer=TokenizerTeste(), max_seq_length=128)
    vetores = lambda: lambda textos: [[1.0, 0.0] for _ in textos]
    monkeypatch.setattr(documentos, "obter_modelo", lambda: modelo)
    monkeypatch.setattr(documentos, "limite_tokens", lambda: 110)
    monkeypatch.setattr(documentos, "obter_colecao", lambda: colecao)
    monkeypatch.setattr(busca_chromadb, "obter_colecao", lambda: colecao)
    monkeypatch.setattr(busca_chromadb, "criar_embeddings", vetores)
    monkeypatch.setattr(indexar_documentos, "criar_embeddings", vetores)
    monkeypatch.delenv("RAG_MAX_DISTANCE", raising=False)
    service = servicos.ServicosIntegrados()
    monkeypatch.setattr(service, "inicializar", lambda: None)
    monkeypatch.setattr(main, "servicos", service)
    monkeypatch.setattr(main, "ARQUIVO_AVALIACOES", tmp_path / "avaliacoes.jsonl")
    with TestClient(main.app, raise_server_exceptions=False) as client:
        yield client, colecao


def test_upload_busca_listagem_e_repeticao(contexto):
    client, colecao = contexto
    texto = "Qiskit adapta circuitos ao dispositivo. " + " ".join(f"palavra{i}" for i in range(220))
    envio = client.post("/documents", files={"file": ("guia.txt", texto.encode())})
    assert envio.status_code == 201
    id = envio.json()["id"]
    assert envio.json()["mode"] == "integrated"
    total = colecao.count()
    assert total >= 2
    repetido = client.post("/documents", files={"file": ("guia.txt", texto.encode())})
    assert repetido.json()["id"] == id
    assert colecao.count() == total
    lista = client.get("/documents").json()
    assert lista == {"documents": [{"id": id, "filename": "guia.txt"}], "mode": "integrated"}
    busca = client.post("/search", json={"query": "Qiskit"})
    assert busca.status_code == 200
    body = busca.json()
    assert body["mode"] == "integrated" and body["status"] == "ok"
    assert body["citations"] == ["guia.txt"]
    assert len(body["chunks"]) == 1  # seção única, vários candidatos
    fonte = body["chunks"][0]
    assert set(fonte) == {"document_id", "chunk_id", "source", "content"}
    assert fonte["document_id"] == id
    assert fonte["content"].index("palavra0") < fonte["content"].index("palavra219")
    assert "distancia" not in fonte
    assert busca.headers["X-Request-ID"] == body["request_id"]


def test_base_vazia_e_corte_opcional(contexto, monkeypatch):
    client, _ = contexto
    resultado = client.post("/search", json={"query": "sem base"}).json()
    assert resultado["status"] == "insufficient_context" and not resultado["chunks"]
    client.post("/documents", files={"file": ("guia.txt", b"Qiskit documentacao.")})
    monkeypatch.setenv("RAG_MAX_DISTANCE", "0.1")
    resultado = client.post("/search", json={"query": "outra pergunta"}).json()
    assert resultado["status"] == "insufficient_context"


def test_query_informa_llm_ausente(contexto):
    client, _ = contexto
    resposta = client.post("/query", json={"input": "Otimize este circuito"})
    assert resposta.status_code == 503
    assert resposta.json()["code"] == "LLM_NOT_CONFIGURED"
    assert "nenhuma resposta de IA" in resposta.json()["message"]
    assert set(resposta.json()) == {"request_id", "code", "message", "fields"}


def test_indisponibilidade_nao_retorna_sucesso_ou_contexto_vazio(contexto, monkeypatch):
    client, colecao = contexto
    def falhar():
        raise ConnectionError("mensagem-privada")
    monkeypatch.setattr(busca_chromadb, "obter_colecao", falhar)
    resposta = client.post("/search", json={"query": "Qiskit"})
    assert resposta.status_code == 503 and "mensagem-privada" not in resposta.text
    colecao.falhar_escrita = True
    resposta = client.post("/documents", files={"file": ("guia.txt", b"Qiskit.")})
    assert resposta.status_code == 503
    assert client.get("/documents").json()["documents"] == []


def test_metadados_invalidos_viram_502(contexto, monkeypatch):
    client, _ = contexto
    monkeypatch.setattr(busca_chromadb, "buscar_documentos", lambda _: [{"id": "incompleto"}])
    resposta = client.post("/search", json={"query": "Qiskit"})
    assert resposta.status_code == 502


def test_timeout_busca(contexto, monkeypatch):
    client, _ = contexto
    async def lento(_):
        await asyncio.sleep(0.1)
    monkeypatch.setattr(main.servicos, "buscar", lento)
    monkeypatch.setattr(main, "TEMPO_LIMITE", 0.01)
    resposta = client.post("/search", json={"query": "Qiskit"})
    assert resposta.status_code == 504 and resposta.json()["code"] == "TIMEOUT"


def test_upload_inviavel_retorna_422(contexto, monkeypatch):
    client, _ = contexto
    def falhar(*args):
        raise ValueError("Identificador excede o limite")
    monkeypatch.setattr(documentos, "gerar_chunks", falhar)
    resposta = client.post("/documents", files={"file": ("guia.txt", b"texto")})
    assert resposta.status_code == 422 and resposta.json()["code"] == "INVALID_DOCUMENT"


def test_reindexacao_remove_apenas_chunks_obsoletos_do_documento(contexto):
    client, colecao = contexto
    client.post("/documents", files={"file": ("primeiro.txt", b"Qiskit material.")})
    client.post("/documents", files={"file": ("outro.txt", b"Outro documento.")})
    id, (texto, meta, vetor) = next(iter(colecao.registros.items()))
    obsoleto = meta["document_id"] + "_chunk_99"
    colecao.upsert(ids=[obsoleto], documents=[texto], metadatas=[meta], embeddings=[vetor])
    lote = [{"id": id, "texto": texto, "metadados": meta}]
    assert indexar_documentos.atualizar_documento(colecao, meta["document_id"], lote) == 1
    assert obsoleto not in colecao.registros
    assert len(documentos.listar_documentos()) == 2


def test_listagem_percorre_paginas_sem_duplicar(contexto):
    _, colecao = contexto
    for i in range(300):
        colecao.registros[str(i)] = ("texto", {
            "document_id": "doc_" + str(i % 2), "titulo": "Titulo " + str(i % 2),
        }, [1.0, 0.0])
    assert documentos.listar_documentos() == [
        {"id": "doc_0", "filename": "Titulo 0"}, {"id": "doc_1", "filename": "Titulo 1"}
    ]


def test_cliente_http_recebe_configuracao_sem_caminho_local(monkeypatch):
    import chromadb
    chamadas = []
    monkeypatch.setenv("CHROMA_HOST", "servidor-interno")
    monkeypatch.setenv("CHROMA_PORT", "8123")
    cliente = SimpleNamespace(_server=SimpleNamespace(_session=SimpleNamespace(timeout=None)))
    monkeypatch.setattr(chromadb, "HttpClient", lambda **kw: chamadas.append(kw) or cliente)
    banco.obter_cliente.cache_clear()
    try:
        banco.obter_cliente()
        assert chamadas[0]["host"] == "servidor-interno"
        assert chamadas[0]["port"] == 8123
        assert "path" not in chamadas[0]
        assert cliente._server._session.timeout.read == 30
    finally:
        banco.obter_cliente.cache_clear()


def test_colecao_incompativel_e_recusada_sem_alteracao(monkeypatch):
    colecao = ColecaoTeste()
    colecao.metadata["modelo_embeddings"] = "outro-modelo"
    cliente = SimpleNamespace(get_or_create_collection=lambda **kw: colecao)
    monkeypatch.setattr(banco, "obter_cliente", lambda: cliente)
    banco.obter_colecao.cache_clear()
    try:
        with pytest.raises(banco.ColecaoIncompativel):
            banco.obter_colecao()
        assert colecao.metadata["modelo_embeddings"] == "outro-modelo"
    finally:
        banco.obter_colecao.cache_clear()


def test_colecao_compartilhada_tem_configuracao_unica(monkeypatch):
    colecao = ColecaoTeste()
    chamadas = []
    cliente = SimpleNamespace(get_or_create_collection=lambda **kw: chamadas.append(kw) or colecao)
    monkeypatch.setattr(banco, "obter_cliente", lambda: cliente)
    banco.obter_colecao.cache_clear()
    try:
        assert banco.obter_colecao() is colecao
        assert banco.obter_colecao() is colecao
        assert len(chamadas) == 1
        assert chamadas[0]["name"] == configuracao.NOME_COLECAO
        assert chamadas[0]["embedding_function"] is None
        assert chamadas[0]["configuration"] == {"hnsw": {"space": "l2"}}
    finally:
        banco.obter_colecao.cache_clear()
