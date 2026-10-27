"""Adaptador dos contratos HTTP para o RAG e o ChromaDB remoto."""
import asyncio
import logging
import os
import time

from contratos import Documento, Fonte, ResultadoBusca
from rag import busca_chromadb, documentos
from rag.banco import obter_cliente, obter_colecao, ColecaoIncompativel
from rag.configuracao import criar_embeddings

logger = logging.getLogger(__name__)


class FalhaServico(Exception):
    def __init__(self, message="Serviço indisponível.", status=503):
        self.status = status if status in (502, 503) else 503
        super().__init__(message)


class LLMNaoConfigurada(Exception):
    pass


class DocumentoInvalido(Exception):
    pass


class ServicosIntegrados:
    mode = "integrated"

    def inicializar(self):
        # Carregamento e aquecimento acontecem antes de aceitar requisições.
        criar_embeddings()(["Inicialização da busca documental."])
        prazo = time.monotonic() + float(os.getenv("CHROMA_STARTUP_TIMEOUT", "120"))
        while True:
            try:
                obter_cliente().heartbeat()
                obter_colecao()
                return
            except ColecaoIncompativel:
                raise
            except Exception:
                if time.monotonic() >= prazo:
                    raise
                time.sleep(2)

    async def _executar(self, funcao, *args):
        try:
            return await asyncio.to_thread(funcao, *args)
        except DocumentoInvalido:
            raise
        except (KeyError, TypeError, ColecaoIncompativel) as erro:
            logger.error("Dados do serviço fora do contrato: %s", type(erro).__name__)
            raise FalhaServico(status=502) from erro
        except Exception as erro:
            logger.error("Falha na dependência: %s", type(erro).__name__)
            raise FalhaServico(status=503) from erro

    async def buscar(self, query):
        resultados = await self._executar(busca_chromadb.buscar_documentos, query)
        try:
            fontes = [Fonte(
                document_id=r["metadados"]["document_id"], chunk_id=r["id"],
                source=r["metadados"]["fonte"], content=r["texto"],
            ) for r in resultados]
        except (KeyError, TypeError) as erro:
            raise FalhaServico(status=502) from erro
        return ResultadoBusca(
            chunks=fontes, citations=list(dict.fromkeys(f.source for f in fontes)),
            status="ok" if fontes else "insufficient_context",
        )

    async def consultar(self, texto):
        raise LLMNaoConfigurada()

    async def adicionar_documento(self, filename, content):
        def adicionar():
            try:
                return documentos.adicionar_documento(filename, content)
            except documentos.ConteudoInvalido as erro:
                raise DocumentoInvalido() from erro
        return Documento.model_validate(await self._executar(adicionar))

    async def listar_documentos(self):
        registros = await self._executar(documentos.listar_documentos)
        return [Documento.model_validate(d) for d in registros]
