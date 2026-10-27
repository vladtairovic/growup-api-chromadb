"""Optativo: valida servidor, modelo e rede reais. Grava um documento de teste."""
import os
from uuid import uuid4

import httpx
import pytest


@pytest.mark.live
@pytest.mark.skipif(not os.getenv("GROWUP_TEST_URL"), reason="Defina GROWUP_TEST_URL para validar os containers reais.")
def test_fluxo_real():
    with httpx.Client(base_url=os.environ["GROWUP_TEST_URL"], timeout=120) as client:
        assert client.get("/health").json() == {"status": "ok", "mode": "integrated"}
        nome = f"teste-integracao-{uuid4().hex}.txt"
        texto = "O teste de integração GrowUp confirma que a transpilação adapta circuitos ao dispositivo."
        resposta = client.post("/documents", files={"file": (nome, texto.encode("utf-8"))})
        assert resposta.status_code == 201, resposta.text
        id = resposta.json()["id"]
        repetido = client.post("/documents", files={"file": (nome, texto.encode("utf-8"))})
        assert repetido.status_code == 201 and repetido.json()["id"] == id
        assert any(d["id"] == id for d in client.get("/documents").json()["documents"])
        busca = client.post("/search", json={"query": texto})
        assert busca.status_code == 200, busca.text
        assert any(c["document_id"] == id for c in busca.json()["chunks"])
        consulta = client.post("/query", json={"input": "O que é transpilação?"})
        assert consulta.status_code == 503 and consulta.json()["code"] == "LLM_NOT_CONFIGURED"
