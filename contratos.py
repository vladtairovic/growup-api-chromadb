"""Formatos de entrada e saída da API. Não há regras de Qiskit ou ChromaDB."""
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator

class Modelo(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

class Consulta(Modelo):
    input: Annotated[str, Field(min_length=1, max_length=30000)]

class Busca(Modelo):
    query: Annotated[str, Field(min_length=1, max_length=2000)]

class Fonte(Modelo):
    document_id: str
    chunk_id: str
    source: str
    content: str

class ResultadoConsulta(Modelo):
    response: str
    sources: list[Fonte]
    status: Literal['ok', 'insufficient_context']

class RespostaConsulta(ResultadoConsulta):
    request_id: UUID
    mode: Literal['demo', 'integrated']

class ResultadoBusca(Modelo):
    chunks: list[Fonte]
    citations: list[str]
    status: Literal['ok', 'insufficient_context']

class RespostaBusca(ResultadoBusca):
    request_id: UUID
    mode: Literal['demo', 'integrated']

class Documento(Modelo):
    id: str
    filename: str

class RespostaDocumento(Documento):
    status: Literal['sucesso'] = 'sucesso'
    mode: Literal['demo', 'integrated']

class ListaDocumentos(Modelo):
    documents: list[Documento]
    mode: Literal['demo', 'integrated']

class Saude(Modelo):
    status: Literal['ok'] = 'ok'
    mode: Literal['demo', 'integrated']

class Nota(Modelo):
    criterion: Literal['pertinencia', 'coerencia', 'aderencia', 'clareza', 'falhas']
    score: int = Field(ge=0, le=5, strict=True)
    evidence: Annotated[str, Field(min_length=5, max_length=1000)]

class Avaliacao(Modelo):
    case_id: Annotated[str, Field(min_length=1, max_length=100)]
    evaluator: Annotated[str, Field(min_length=2, max_length=100)]
    ratings: list[Nota] = Field(min_length=5, max_length=5)
    critical_failure: bool = Field(default=False, strict=True)
    critical_evidence: Annotated[str, Field(min_length=5, max_length=1000)] | None = None

    @model_validator(mode='after')
    def validar(self):
        if len({n.criterion for n in self.ratings}) != 5:
            raise ValueError('Informe os cinco critérios sem repetir.')
        if self.critical_failure and not self.critical_evidence:
            raise ValueError('Descreva a evidência da falha crítica.')
        return self

class RespostaAvaliacao(Avaliacao):
    id: UUID
    created_at: str
    rubric_version: Literal['inicial-1.0'] = 'inicial-1.0'
    mean: float
    approved: bool
    result: Literal['aprovado', 'reprovado', 'revisao_obrigatoria']

class Erro(Modelo):
    request_id: UUID
    code: str
    message: str
    fields: list[str] = Field(default_factory=list)
