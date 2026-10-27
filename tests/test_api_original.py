import asyncio
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from openapi_spec_validator import validate
import main
from tests.demo_original import ServicosDemo
from servicos import FalhaServico

@pytest.fixture
def client(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'servicos',ServicosDemo())
    monkeypatch.setattr(main,'ARQUIVO_AVALIACOES',tmp_path/'avaliacoes.jsonl')
    return TestClient(main.app,raise_server_exceptions=False)

def notas(values=(4,4,4,4,4)):
    return {'case_id':'CASO-01','evaluator':'Teste','ratings':[
        {'criterion':k,'score':v,'evidence':'Evidência sintética para o teste.'}
        for k,v in zip(('pertinencia','coerencia','aderencia','clareza','falhas'),values)]}

def test_fluxo(client):
    assert client.get('/health').json()=={'status':'ok','mode':'demo'}
    assert client.get('/documents').json()['documents']==[]
    r=client.post('/documents',files={'file':('guia.txt',b'Material Qiskit de teste.')})
    assert r.status_code==201
    assert client.get('/documents').json()['documents'][0]['id']==r.json()['id']
    assert client.post('/search',json={'query':'Qiskit'}).json()['citations']==['guia.txt']
    q=client.post('/query',json={'input':'Qiskit'})
    assert q.status_code==200 and 'SIMULAÇÃO' in q.json()['response']
    assert q.json()['sources'][0]['document_id']==r.json()['id']
    assert q.headers['X-Request-ID']==q.json()['request_id']

def test_sem_contexto(client):
    r=client.post('/query',json={'input':'Qiskit'})
    assert r.status_code==200 and r.json()['status']=='insufficient_context'
    assert r.json()['sources']==[]

@pytest.mark.parametrize('path,body',[('/query',{}),('/query',{'input':' '}),
    ('/query',{'input':'x'*30001}),('/query',{'input':'x','extra':1}),
    ('/search',{'query':''}),('/search',{'query':'x'*2001})])
def test_validacao(client,path,body):
    assert client.post(path,json=body).status_code==422

@pytest.mark.parametrize('name,body,status',[('a.pdf',b'abc',415),('a.txt',b'',422),
    ('a.txt',b'\xff',422),('a.txt',b'a\x00b',422),('a.txt',b'x'*262145,413)],
    ids=['extensao', 'vazio', 'codificacao', 'binario', 'acima_do_limite'])
def test_upload_invalido(client,name,body,status):
    assert client.post('/documents',files={'file':(name,body)}).status_code==status
    assert client.get('/documents').json()['documents']==[]

@pytest.mark.parametrize('values,mean,approved,label',[
    ((4,4,4,4,4),4,True,'aprovado'),((5,5,5,5,5),5,True,'aprovado'),
    ((3,4,4,4,4),3.8,False,'reprovado'),((5,0,5,5,5),4,False,'revisao_obrigatoria'),
    ((0,0,0,0,0),0,False,'revisao_obrigatoria')])
def test_avaliacao(client,values,mean,approved,label):
    r=client.post('/evaluate',json=notas(values));assert r.status_code==201
    d=r.json();assert (d['mean'],d['approved'],d['result'])==(mean,approved,label)
    assert json.loads(main.ARQUIVO_AVALIACOES.read_text())==d

def test_critica_reportada(client):
    data={**notas((5,5,5,5,5)),'critical_failure':True}
    assert client.post('/evaluate',json=data).status_code==422
    data['critical_evidence']='Recomendação incorreta identificada.'
    assert client.post('/evaluate',json=data).json()['approved'] is False

@pytest.mark.parametrize('value',[6,-1,True])
def test_notas_invalidas(client,value):
    assert client.post('/evaluate',json=notas((value,4,4,4,4))).status_code==422

def test_duplicacao(client):
    data=notas();data['ratings'][0]['criterion']='clareza'
    assert client.post('/evaluate',json=data).status_code==422

def test_http(client):
    assert client.get('/inexistente').status_code==404
    assert client.delete('/health').status_code==405
    assert client.post('/query',content='{}').status_code==415
    assert client.post('/query',content='{',headers={'Content-Type':'application/json'}).status_code==422
    assert client.post('/documents',json={}).status_code==415

@pytest.mark.parametrize('status',[502,503])
def test_falha_externa(client,monkeypatch,status):
    async def falhar(*args):raise FalhaServico('segredo-privado',status)
    monkeypatch.setattr(main.servicos,'consultar',falhar)
    r=client.post('/query',json={'input':'teste'})
    assert r.status_code==status and 'segredo-privado' not in r.text

def test_timeout(client,monkeypatch):
    async def lento(*args):await asyncio.sleep(.1)
    monkeypatch.setattr(main,'TEMPO_LIMITE',.01)
    monkeypatch.setattr(main.servicos,'consultar',lento)
    assert client.post('/query',json={'input':'teste'}).status_code==504

def test_saida_invalida(client,monkeypatch):
    async def invalido(*args):return {'response':'Faltam campos'}
    monkeypatch.setattr(main.servicos,'consultar',invalido)
    assert client.post('/query',json={'input':'teste'}).status_code==502

def test_erro_interno(client,monkeypatch):
    async def falhar(*args):raise RuntimeError('segredo-privado')
    monkeypatch.setattr(main.servicos,'consultar',falhar)
    r=client.post('/query',json={'input':'teste'})
    assert r.status_code==500 and 'segredo-privado' not in r.text

def test_openapi(client):
    schema=client.get('/openapi.json').json();validate(schema)
    assert schema['openapi']=='3.1.0'
    assert set(schema['paths'])=={'/health','/query','/search','/documents','/evaluate'}
    assert json.loads(Path('openapi.json').read_text())==schema
