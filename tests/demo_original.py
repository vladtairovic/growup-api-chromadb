"""Simulador original preservado SOMENTE como dublê dos testes de regressão.

A API chama consultar, buscar, adicionar_documento e listar_documentos.
Quando os serviços reais estiverem prontos, substituir o objeto usado em main.py
por uma implementação com estes mesmos métodos. Não há cliente Chroma, Qiskit,
embeddings, chunking real ou chamada a LLM neste arquivo.
"""
import re
from uuid import uuid4
from contratos import Documento, Fonte, ResultadoBusca, ResultadoConsulta

class FalhaServico(Exception):
    """A futura integração pode informar indisponibilidade (503) ou falha externa (502)."""
    def __init__(self, message='Serviço da equipe indisponível.', status=503):
        self.status = status if status in (502, 503) else 503
        # A mensagem enviada ao usuário é definida pela API, não pela exceção.
        super().__init__(message)

class ServicosDemo:
    mode = 'demo'

    def __init__(self):
        self.documentos = {}

    async def adicionar_documento(self, filename: str, content: bytes) -> Documento:
        # Somente memória de demonstração. A indexação verdadeira é responsabilidade externa.
        document_id = str(uuid4())
        texto = content.decode('utf-8-sig')
        self.documentos[document_id] = (filename, texto)
        return Documento(id=document_id, filename=filename)

    async def listar_documentos(self) -> list[Documento]:
        return [Documento(id=id, filename=nome) for id, (nome, _) in self.documentos.items()]

    async def buscar(self, query: str) -> ResultadoBusca:
        # Comparação simples de palavras para demonstrar o contrato, sem busca semântica.
        termos = {t for t in re.findall(r'\w+', query.casefold()) if len(t) >= 4}
        encontrados = []
        for id, (nome, texto) in self.documentos.items():
            palavras = set(re.findall(r'\w+', texto.casefold()))
            if termos & palavras:
                encontrados.append(Fonte(document_id=id, chunk_id=id+'_demo', source=nome, content=texto[:600]))
                if len(encontrados) == 3:
                    break
        return ResultadoBusca(chunks=encontrados, citations=[f.source for f in encontrados],
                              status='ok' if encontrados else 'insufficient_context')

    async def consultar(self, texto: str) -> ResultadoConsulta:
        busca = await self.buscar(texto)
        if not busca.chunks:
            return ResultadoConsulta(response='Contexto insuficiente. Envie um documento relacionado à consulta.',
                                     sources=[], status='insufficient_context')
        return ResultadoConsulta(
            response='SIMULAÇÃO: foi encontrado um trecho relacionado. Nenhuma IA analisou ou otimizou o código. Trecho: '+busca.chunks[0].content,
            sources=busca.chunks, status='ok')
