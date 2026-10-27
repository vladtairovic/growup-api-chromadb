"""Exercita o SDK ChromaDB real com transporte HTTP substituído, sem banco local."""
import json

import httpx

from rag import banco, configuracao


def test_sdk_configura_colecao_e_timeout(monkeypatch):
    requisicoes = []

    def responder(request):
        requisicoes.append(request)
        path = request.url.path
        if path.endswith("/auth/identity"):
            body = {"user_id": "test", "tenant": "default_tenant", "databases": ["default_database"]}
        elif path.endswith("/tenants/default_tenant"):
            body = {"name": "default_tenant"}
        elif path.endswith("/databases/default_database"):
            body = {"id": "00000000-0000-0000-0000-000000000001", "name": "default_database", "tenant": "default_tenant"}
        elif path.endswith("/collections") and request.method == "POST":
            entrada = json.loads(request.content)
            assert entrada["name"] == configuracao.NOME_COLECAO
            assert entrada["get_or_create"] is True
            body = {
                "id": "00000000-0000-0000-0000-000000000002",
                "name": entrada["name"], "metadata": entrada["metadata"],
                "configuration_json": entrada["configuration"], "serialized_schema": None,
                "dimension": None, "tenant": "default_tenant", "database": "default_database",
                "version": 0, "log_position": 0,
            }
        elif path.endswith("/count"):
            body = 0
        else:
            raise AssertionError(f"Requisição inesperada: {request.method} {path}")
        return httpx.Response(200, json=body)

    classe_original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: classe_original(
        **kw, transport=httpx.MockTransport(responder)
    ))
    monkeypatch.setenv("CHROMA_HOST", "chroma-teste")
    monkeypatch.setenv("CHROMA_HTTP_TIMEOUT_SECONDS", "7")
    banco.obter_cliente.cache_clear()
    banco.obter_colecao.cache_clear()
    try:
        colecao = banco.obter_colecao()
        assert colecao.count() == 0
        assert all(r.url.host == "chroma-teste" for r in requisicoes)
        assert requisicoes[-1].extensions["timeout"]["read"] == 7
        assert colecao.configuration["hnsw"]["space"] == "l2"
    finally:
        banco.obter_cliente.cache_clear()
        banco.obter_colecao.cache_clear()
