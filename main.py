"""API inicial. Executar: python -m uvicorn main:app"""
import asyncio
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from pydantic import ValidationError
from contratos import (Consulta, Busca, ResultadoConsulta, ResultadoBusca, Documento,
    RespostaConsulta, RespostaBusca, RespostaDocumento, ListaDocumentos, Saude,
    Avaliacao, RespostaAvaliacao, Erro)
from servicos import ServicosIntegrados, FalhaServico, LLMNaoConfigurada, DocumentoInvalido

servicos = ServicosIntegrados()
TEMPO_LIMITE = float(os.getenv('API_TIMEOUT_SECONDS', '60'))
ARQUIVO_AVALIACOES = Path(os.getenv('AVALIACOES_PATH', 'data/avaliacoes.jsonl'))
LIMITE_ARQUIVO = 256 * 1024


@asynccontextmanager
async def lifespan(app):
    await asyncio.to_thread(servicos.inicializar)
    yield

ERROS = {n: {'model': Erro, 'description': descricao} for n, descricao in {
    400:'Requisição malformada', 404:'Rota inexistente', 405:'Método incorreto',
    413:'Arquivo acima do limite', 415:'Tipo de conteúdo não aceito',
    422:'Entrada inválida', 500:'Falha interna', 502:'Resposta externa inválida',
    503:'Serviço externo indisponível', 504:'Tempo limite excedido'}.items()}
app = FastAPI(title='GrowUp - API integrada', version='0.2.0', responses=ERROS,
    lifespan=lifespan,
    description='Busca e documentos integrados ao ChromaDB. /query retorna 503 LLM_NOT_CONFIGURED: geração por LLM ainda não conectada.')
app.openapi_version = '3.1.0'

def erro(request, status, code, message, fields=None):
    return JSONResponse(status_code=status, content={
        'request_id': request.state.request_id, 'code': code,
        'message': message, 'fields': fields or []})

@app.middleware('http')
async def identificar_chamada(request: Request, call_next):
    request.state.request_id = str(uuid4())
    esperado = 'multipart/form-data' if request.url.path == '/documents' else 'application/json'
    recebido = request.headers.get('content-type', '').split(';')[0].strip().lower()
    if request.method == 'POST' and recebido != esperado:
        resposta = erro(request,415,'CONTENT_TYPE',f'Use Content-Type: {esperado}.')
    else:
        try:
            resposta = await call_next(request)
        except Exception:
            resposta = erro(request,500,'INTERNAL_ERROR','Não foi possível concluir a operação.')
    resposta.headers['X-Request-ID'] = request.state.request_id
    return resposta

@app.exception_handler(RequestValidationError)
async def entrada_invalida(request, exc):
    fields = ['.'.join(map(str,e['loc'])) for e in exc.errors()]
    return erro(request,422,'INVALID_INPUT','Confira os campos, tipos e limites.',fields)

@app.exception_handler(HTTPException)
async def erro_http(request, exc):
    mensagens = {400:'Requisição ou formulário inválido.',404:'Rota não encontrada.',405:'Método não permitido.',
                 413:'Arquivo maior que 256 KiB.',415:'Use arquivo .txt, .md, .py ou .qasm em UTF-8.',
                 422:'Arquivo vazio, binário ou fora da codificação UTF-8.'}
    return erro(request,exc.status_code,'HTTP_ERROR',mensagens.get(exc.status_code,'Falha na requisição.'))

@app.exception_handler(FalhaServico)
async def servico_indisponivel(request, exc):
    return erro(request,exc.status,'SERVICE_ERROR','O serviço externo não conseguiu atender à solicitação.')

@app.exception_handler(LLMNaoConfigurada)
async def llm_ausente(request, exc):
    return erro(request,503,'LLM_NOT_CONFIGURED',
                'A LLM ainda não foi configurada. Use POST /search para recuperar trechos e fontes; nenhuma resposta de IA foi gerada.')

@app.exception_handler(DocumentoInvalido)
async def documento_invalido(request, exc):
    return erro(request,422,'INVALID_DOCUMENT',
                'Não foi possível dividir o documento no limite de tokens. Revise blocos ou identificadores muito longos.')

@app.exception_handler(asyncio.TimeoutError)
async def tempo_excedido(request, exc):
    return erro(request,504,'TIMEOUT','O serviço externo excedeu o tempo limite.')

@app.exception_handler(ValidationError)
async def contrato_externo_invalido(request, exc):
    return erro(request,502,'INVALID_SERVICE_RESPONSE','O serviço externo retornou dados fora do contrato.')

async def chamar(corrotina):
    return await asyncio.wait_for(corrotina, timeout=TEMPO_LIMITE)

@app.get('/health', response_model=Saude)
async def health():
    """Confirma que a API responde; não verifica os serviços externos."""
    return Saude(mode=servicos.mode)

@app.post('/query', response_model=RespostaConsulta)
async def query(entrada: Consulta, request: Request):
    """Contrato preservado; retorna 503 LLM_NOT_CONFIGURED até a equipe conectar a LLM."""
    resultado = ResultadoConsulta.model_validate(await chamar(servicos.consultar(entrada.input)))
    return RespostaConsulta(**resultado.model_dump(), request_id=request.state.request_id, mode=servicos.mode)

@app.post('/search', response_model=RespostaBusca)
async def search(entrada: Busca, request: Request):
    """Recupera seções e fontes no ChromaDB. Resultados não garantem suficiência do contexto."""
    resultado = ResultadoBusca.model_validate(await chamar(servicos.buscar(entrada.query)))
    return RespostaBusca(**resultado.model_dump(), request_id=request.state.request_id, mode=servicos.mode)

@app.post('/documents', response_model=RespostaDocumento, status_code=201)
async def enviar_documento(file: UploadFile = File(...)):
    """Valida texto UTF-8 e indexa os trechos na mesma coleção usada pela busca."""
    try:
        conteudo = await file.read(LIMITE_ARQUIVO+1)
        nome = (file.filename or '').replace('\\','/').split('/')[-1]
        if len(conteudo) > LIMITE_ARQUIVO:
            raise HTTPException(413)
        if Path(nome).suffix.lower() not in ('.txt','.md','.py','.qasm'):
            raise HTTPException(415)
        try:
            texto = conteudo.decode('utf-8-sig')
        except UnicodeDecodeError:
            raise HTTPException(422)
        if not texto.strip() or '\x00' in texto:
            raise HTTPException(422)
        resultado = Documento.model_validate(await chamar(servicos.adicionar_documento(nome,conteudo)))
        return RespostaDocumento(**resultado.model_dump(),mode=servicos.mode)
    finally:
        await file.close()

@app.get('/documents', response_model=ListaDocumentos)
async def listar_documentos():
    """Solicita ao serviço documental a lista de documentos disponíveis."""
    documentos = await chamar(servicos.listar_documentos())
    if not isinstance(documentos,list):
        raise FalhaServico(status=502)
    return ListaDocumentos(documents=[Documento.model_validate(d) for d in documentos],mode=servicos.mode)

@app.post('/evaluate', response_model=RespostaAvaliacao, status_code=201)
async def avaliar(entrada: Avaliacao):
    """Registra notas humanas e calcula média; não avalia automaticamente a IA."""
    media = sum(n.score for n in entrada.ratings) / 5
    # Proposta operacional: zero em critério técnico/crítico exige revisão.
    critica = entrada.critical_failure or any(n.score == 0 and n.criterion in
                                             ('coerencia','aderencia','falhas') for n in entrada.ratings)
    resultado = RespostaAvaliacao(**{**entrada.model_dump(), 'critical_failure': critica,
        'critical_evidence': entrada.critical_evidence or ('Regra automática: nota zero em critério técnico/crítico.' if critica else None)},
        id=uuid4(), created_at=datetime.now(timezone.utc).isoformat(), mean=media,
        approved=media >= 4 and not critica,
        result='revisao_obrigatoria' if critica else ('aprovado' if media >= 4 else 'reprovado'))
    # Registro simples exigido pela avaliação: uma linha JSON por avaliação, sem banco adicional.
    ARQUIVO_AVALIACOES.parent.mkdir(parents=True, exist_ok=True)
    with ARQUIVO_AVALIACOES.open('a',encoding='utf-8') as arquivo:
        arquivo.write(resultado.model_dump_json()+'\n')
    return resultado
