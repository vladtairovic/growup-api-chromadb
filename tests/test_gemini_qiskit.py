"""Gemini usa transporte controlado aqui; Qiskit executa de verdade."""
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from tests.test_integracao import contexto
from rag import pipeline_gemini, cliente_gemini
from rag.contexto_gemini import preparar_contexto

QASM = 'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; h q[0]; h q[0];'

def test_rag_com_llm_controlada(contexto, monkeypatch):
    client, _ = contexto
    monkeypatch.setenv("GEMINI_API_KEY", "chave-apenas-de-teste")
    client.post("/documents", files={"file": ("guia.txt", b"Qiskit transpila circuitos.")})
    gerar = Mock(return_value="Resposta controlada de teste [Fonte 1].")
    monkeypatch.setattr(cliente_gemini, "gerar_resposta", gerar)
    r = client.post("/query", json={"input": "Qiskit?"})
    assert r.status_code == 200
    assert r.json()["sources"][0]["source"] == "guia.txt"
    assert "[Fonte 1]" in gerar.call_args.args[1]
    assert r.json()["response"] == gerar.return_value

def test_sem_contexto_nao_chama_llm(contexto, monkeypatch):
    client, _ = contexto
    monkeypatch.setenv("GEMINI_API_KEY", "teste")
    gerar = Mock(side_effect=AssertionError("nao deveria chamar"))
    monkeypatch.setattr(cliente_gemini, "gerar_resposta", gerar)
    r = client.post("/query", json={"input": "Qiskit?"})
    assert r.status_code == 200 and r.json()["status"] == "insufficient_context"
    gerar.assert_not_called()

def test_falha_llm_nao_expoe_credencial(contexto, monkeypatch):
    client, _ = contexto
    monkeypatch.setenv("GEMINI_API_KEY", "teste")
    client.post("/documents", files={"file": ("guia.txt", b"Qiskit transpila circuitos.")})
    monkeypatch.setattr(cliente_gemini, "gerar_resposta", Mock(side_effect=RuntimeError("segredo-privado")))
    r = client.post("/query", json={"input": "Qiskit?"})
    assert r.status_code == 503 and "segredo-privado" not in r.text

def test_cliente_gemini_fecha_e_aplica_timeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "teste")
    cliente = Mock()
    cliente.models.generate_content.return_value = SimpleNamespace(text=" resultado ")
    criar = Mock(return_value=cliente)
    monkeypatch.setattr(cliente_gemini.genai, "Client", criar)
    assert cliente_gemini.gerar_resposta("pergunta", "contexto") == "resultado"
    assert criar.call_args.kwargs["http_options"].timeout == 40000
    assert criar.call_args.kwargs["http_options"].retry_options.attempts == 1
    cliente.close.assert_called_once()
    cliente.models.generate_content.return_value = SimpleNamespace(text=None)
    with pytest.raises(RuntimeError):
        cliente_gemini.gerar_resposta("pergunta", "contexto")
    assert cliente.close.call_count == 2

def test_contexto_limitado():
    docs = [{"texto": "x"*2000, "metadados": {"titulo": "teste"}}]*3
    contexto, fontes = preparar_contexto(docs, limite=500)
    assert len(contexto) <= 500 and len(fontes) == 1

def test_qiskit_http_real(contexto):
    client, _ = contexto
    r = client.post("/qiskit/optimize", json={"qasm": QASM})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["equivalente"] is True
    assert d["original"]["total_operacoes"] == 2
    assert d["proposta"]["total_operacoes"] == 0

@pytest.mark.parametrize("body", [{"qasm":"invalido"}, {"qasm":QASM,"optimization_level":True},
    {"qasm":QASM,"optimization_level":4}, {"qasm":'OPENQASM 2.0; include "/etc/passwd";'},
    {"qasm":"OPENQASM 2.0; qreg q[33];"}])
def test_qiskit_entrada_invalida(contexto, body):
    client, _ = contexto
    assert client.post("/qiskit/optimize", json=body).status_code == 422

def test_qiskit_timeout(contexto, monkeypatch):
    client, _ = contexto
    monkeypatch.setenv("QISKIT_TIMEOUT_SECONDS", "0.001")
    assert client.post("/qiskit/optimize", json={"qasm":QASM}).status_code == 504
