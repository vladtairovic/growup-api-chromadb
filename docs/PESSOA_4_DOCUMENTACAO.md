# GrowUp — Pessoa 4: prompts, avaliação e contrato de integração RAG/LLM

> Material original preservado como referência para a futura LLM. Nesta entrega integrada, o README e `contratos.py` definem o comportamento atual. O esquema em português abaixo continua sendo uma proposta; `/query` informa `503 LLM_NOT_CONFIGURED`.

**Responsável:** Cauã (Pessoa 4)
**Área:** Pipeline RAG e LLM — preparação complementar à API
**Base de trabalho:** ZIP `GROWUP - RAG` e materiais de planejamento fornecidos pela equipe.

## 1. Objetivo e limite de responsabilidade

Esta entrega complementa o módulo de recuperação do Dudu e prepara os materiais que a próxima pessoa usará para integrar o LLM à API. Ela fornece prompts em português, critérios de avaliação, casos de teste e um contrato sugerido de resposta. **Não implementa o endpoint da API e não afirma que o LLM já foi conectado.**

A divisão pretendida é:
- **Pessoa responsável pela recuperação (Dudu):** disponibiliza a busca de documentos e os metadados das fontes.
- **Pessoa 4 (Cauã):** define regras de resposta do LLM, prompts, comportamento quando o contexto é insuficiente e critérios/casos de avaliação.
- **Pessoa responsável pela API:** chama a busca e o LLM, valida a entrada/saída e expõe o resultado pelo endpoint.
- **Pessoa responsável pela validação:** revisa a qualidade técnica das respostas e registra os resultados.

Confirme os nomes e a divisão final com a equipe se o planejamento tiver sido atualizado.

## 2. Diagnóstico do código recebido

O repositório recebido já contém recuperação semântica em ChromaDB. `configuracao.py` define a coleção `qiskit_documentacao_multilingue` e o embedding multilíngue `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. `busca_chromadb.py` expõe `buscar_documentos(pergunta, quantidade=3, tempos=None)`. A função retorna uma lista de resultados com `id`, `ids_contexto`, `texto`, `metadados` e `distancia`. Os metadados incluem `document_id`, `secao`, `fonte`, `titulo`, `versao_documentacao` e `coletado_em`.

O arquivo `avaliar_busca.py` avalia manualmente consultas de recuperação. O README do módulo afirma que a recuperação ainda não gera respostas com LLM, não executa circuitos e não comprova otimizações. Portanto, os prompts e testes desta entrega são materiais para a próxima etapa; não representam uma integração de LLM já executada.

## 3. Fluxo de integração proposto

1. A API recebe a pergunta do usuário.
2. A camada de aplicação chama `buscar_documentos(pergunta, quantidade=3)`.
3. A integração verifica se a busca falhou e se os trechos recuperados parecem pertinentes. Uma lista não vazia não prova, sozinha, que há contexto suficiente.
4. O contexto é montado a partir de `texto`, preservando `titulo`, `secao` e `fonte`. A pessoa da API deve controlar o tamanho enviado ao modelo, pois `texto` pode conter seções completas.
5. A chamada ao LLM usa `prompts/system_prompt_v1.md`. Para análise de otimização, use `prompts/optimization_prompt_v1.md` apenas quando os dados necessários estiverem disponíveis.
6. A camada de aplicação converte a resposta do modelo para o contrato de saída acordado abaixo.
7. Os casos de `tests/casos_avaliacao.json` são executados com o agente integrado; os resultados reais são registrados e revisados.

## 4. Contrato de resposta sugerido para a API

O conteúdo textual voltado ao usuário deve estar em **português do Brasil**. Os nomes dos campos também estão em português para facilitar a leitura; a pessoa responsável pela API deve alinhar os nomes com a equipe antes de fixá-los publicamente.

```json
{
  "resposta": "Explicação em português baseada nas fontes recuperadas.",
  "fontes": [
    {
      "titulo": "Título da fonte",
      "secao": "Seção recuperada",
      "url": "URL quando disponível",
      "id_documento": "identificador do documento"
    }
  ],
  "avisos": [],
  "estado": "respondido"
}
```

Valores sugeridos para `estado`:
- `respondido`: contexto suficiente para elaborar uma resposta fundamentada.
- `contexto_insuficiente`: as fontes recuperadas não sustentam a resposta.
- `erro_busca`: a recuperação de documentos falhou.
- `erro_geracao`: a chamada ao LLM falhou.

Esse contrato é uma **proposta de integração**, não um endpoint existente. Se a API da equipe já tiver um esquema definido, alinhar e adaptar os nomes antes de implementar. Não exibir `distancia` do ChromaDB como porcentagem de confiança: ela representa a distância do chunk encontrado, não uma probabilidade de acerto.

## 5. Requisitos dos prompts e idioma da resposta

O prompt principal e o prompt de otimização exigem:
- Resposta em português do Brasil, mesmo quando a pergunta ou os documentos estão em inglês, exceto se o usuário pedir explicitamente outro idioma.
- Preservação de nomes oficiais de bibliotecas, funções, parâmetros, código e mensagens de erro.
- Uso das fontes recuperadas sem inventar dados, versões, links, resultados ou métricas.
- Declaração explícita de contexto insuficiente.
- Separação entre fato documentado, inferência e recomendação.
- Fontes com título, seção e URL quando disponíveis.
- Avisos sobre validação de código, compatibilidade de versão e evidências experimentais.

A instrução de idioma é uma regra do prompt; sua efetividade deve ser verificada na avaliação com o LLM real, após a integração.

## 6. Critérios de avaliação das respostas

Avaliar cada resposta de 0 a 5 em cinco dimensões:
1. **Relevância:** responde à pergunta feita?
2. **Correção técnica:** está coerente com a documentação recuperada?
3. **Fundamentação:** as afirmações importantes estão apoiadas nas fontes citadas?
4. **Clareza em português:** a resposta está compreensível e em português do Brasil?
5. **Tratamento da incerteza:** reconhece contexto insuficiente e limitações?

Média proposta: soma das cinco notas dividida por cinco. Como regra inicial, média ≥ 4,0 pode indicar aprovação somente se não houver falha crítica. Média entre 3,0 e 3,9 exige revisão; abaixo de 3,0 não aprovada. A equipe deve confirmar essa escala.

Falhas críticas, independentemente da média:
- inventar uma fonte ou URL;
- responder em inglês sem o usuário pedir, quando a saída deveria ser em português;
- tratar informação ausente da base como fato documentado;
- afirmar compatibilidade sem evidência;
- prometer melhoria de circuito sem execução ou métricas;
- ocultar contexto insuficiente.

## 7. Como executar os testes locais dos artefatos

Na pasta raiz do projeto, com Python instalado:

```powershell
python -m unittest discover -s tests -v
```

Esses testes verificam o conteúdo dos prompts e a estrutura dos casos de avaliação. Eles não chamam um LLM nem provam a qualidade semântica das respostas. Para testar a recuperação real, siga o README do módulo e execute `avaliar_busca.py`; isso exige dependências, modelo de embeddings e banco ChromaDB disponíveis.

## 8. Roteiro de avaliação ponta a ponta (depois da integração)

Para cada pergunta em `tests/casos_avaliacao.json`, registrar:
- pergunta;
- IDs e fontes recuperados;
- resposta gerada, verificando se está em português do Brasil;
- avisos e estado retornado pela API;
- nota de 0 a 5 para cada critério;
- classificação: `responde`, `parcial` ou `não responde`;
- ocorrência de falha crítica;
- data e configuração/modelo usados.

Não marcar um caso como aprovado apenas porque a busca retornou algum trecho. A execução real dos casos e a avaliação das respostas ainda são pendências da integração.

## 9. Checklist de passagem para a pessoa da API

- [ ] Importar `buscar_documentos` a partir de `busca_chromadb.py`.
- [ ] Montar o contexto a partir do campo `texto` e preservar os metadados das fontes.
- [ ] Usar o prompt principal como instrução de sistema e preencher `{pergunta}` e `{contexto}`.
- [ ] Garantir que a resposta destinada ao usuário seja em português do Brasil.
- [ ] Converter a resposta para o contrato acordado (`resposta`, `fontes`, `avisos`, `estado`) ou adaptar ao contrato já adotado pela equipe.
- [ ] Tratar separadamente erro de busca, contexto insuficiente e erro de geração.
- [ ] Não expor chaves de API; usar variáveis de ambiente.
- [ ] Executar os casos de avaliação com o LLM integrado e guardar as evidências reais.
- [ ] Revisar os resultados com a pessoa responsável pela validação técnica.

## 10. Limitações conhecidas

- O módulo recebido ainda não implementa chamada a LLM, API, simulação Aer nem validação automática de equivalência.
- Os testes locais incluídos verificam os artefatos, não a qualidade das respostas de um modelo real.
- A base documental cobre páginas selecionadas sobre transpilação e otimização; não é a documentação completa de Qiskit ou Aer.
- O contrato de resposta precisa ser alinhado com a pessoa responsável pela API.
- O prompt orienta a saída em português, mas a conformidade deve ser medida com o modelo real.
