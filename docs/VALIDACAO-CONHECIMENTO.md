# Validação da base de conhecimento e busca web — 13/11/2026

## Resultado

- Uma única coleção: qiskit_documentacao_multilingue.
- 21 documentos oficiais do catálogo e 2 uploads anteriores preservados.
- 5.073 trechos; maior trecho encontrado: 110 tokens.
- Comparação com o backup confirmou os mesmos textos, metadados e vetores dos dois uploads.
- Exemplos de código com realce HTML agora preservam tokens, linhas e indentação no snapshot.
- Base inicial anterior à ampliação preservada em artifacts/backup-preconhecimento.json.
- Somente alterações locais; nenhum commit ou push nesta etapa.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| Suíte Python completa em container, com o código atual montado | 102 aprovados, 1 omitido, 3 avisos de depreciação |
| Testes do coletor e grounding | 16 aprovados, incluídos no total |
| Build da API e frontend / TypeScript | Aprovado |
| pip check na imagem runtime | Sem dependências incompatíveis |
| Docker Compose real | API, frontend, Chroma e Redis iniciados |
| Busca por Parameter / assign_parameters | HTTP 200; QuantumCircuit e Parameter |
| Busca por medições | HTTP 200; construção de circuitos, medições e QuantumCircuit |
| Busca por probabilidades de Statevector | HTTP 200; primitivas e Statevector |
| Repetição da sincronização | Sem crescimento do índice ou duplicação |
| Navegador Chromium | Fluxos aprovados com Qiskit real e transporte LLM controlado |
| Chave e backup fora do Git | Confirmado por git check-ignore |

O teste live optativo da suíte exige GROWUP_TEST_URL e pressupõe LLM ausente;
não foi ativado na instalação com chave. As verificações reais de Docker, busca,
Qiskit, preservação e consulta web foram realizadas separadamente.

No navegador foram verificados entrada, otimização Qiskit real, top_k,
apresentação de fonte web, drawer/ESC, iframe isolado de sugestões Google,
erros, retry, evidência insuficiente, cancelamento e largura móvel.
SKIP_LIVE_LLM=1 foi usado somente no teste de navegador.
A resposta de produção não é substituída por uma resposta de teste.

Uma repetição de coleta encontrou HTTP 503 temporário na página IBM de
visualização. Os registros anteriores foram mantidos e as outras 20 fontes
foram reconhecidas como inalteradas. A contagem permaneceu em 5.073.
A repetição final terminou com status ok, 21 fontes unchanged e os mesmos 5.073 trechos. O estado pode ser consultado pelo comando abaixo.

## Limitação externa ainda presente

O teste direto do Gemini/Google Search retornou 429 RESOURCE_EXHAUSTED.
A chamada real ao endpoint integrado retornou 503 WEB_SEARCH_UNAVAILABLE,
sem resposta de IA fabricada. Assim, a busca web foi implementada e os
contratos foram testados, mas uma resposta real com grounding permanece
pendente da disponibilidade de cota/faturamento e suporte do modelo na conta.

A seleção de 21 fontes amplia bastante a cobertura, mas não representa toda a
documentação Qiskit nem garante a correção de qualquer resposta da LLM.
Guias e redirecionamentos IBM podem mudar a versão efetiva; snapshots registram
a origem e a data, e o catálogo identifica a versão solicitada.

## Evidências e comandos

Resultados das buscas reais e contagem: validacao-conhecimento.json.
Snapshots atuais e anteriores: volume api_data, /app/data/conhecimento.
Cópia local dos snapshots: artifacts/conhecimento (fora do Git).
Capturas do navegador: artifacts/develop-*.png (conteúdo LLM controlado de teste).

```powershell
docker compose up --build -d --wait
docker compose exec api python -m rag.sincronizar_conhecimento --status
docker compose exec api python -m rag.sincronizar_conhecimento
docker compose exec api python -m rag.sincronizar_conhecimento --reindex
```

O último comando usa snapshots locais, sem coletar a web.
Frontend: http://localhost:3000. Swagger: http://localhost:8000/docs.

## Arquivos desta implementação

Criados:
- rag/busca_web.py: Google Search via Gemini, citações e metadados.
- rag/coleta_web.py: coleta IBM com limites, robots.txt e extração HTML.
- rag/sincronizar_conhecimento.py: atualização, snapshots, trava e agendamento.
- documentos/fontes_conhecimento.json: catálogo de 21 páginas.
- tests/test_conhecimento_web.py: cenários de ingestão, falhas e grounding.
- docs/CONHECIMENTO-WEB.md: operação, arquitetura, limites e recuperação.
- docs/VALIDACAO-CONHECIMENTO.md e docs/validacao-conhecimento.json: evidências.

Atualizados:
- rag/pipeline_gemini.py, servicos.py, main.py e contratos.py.
- compose.yaml, .env.example, requirements-api.txt e openapi.json.
- frontend/services/analysis-api.ts.
- frontend/components/analysis/AnalysisForm.tsx, SettingsPanel.tsx e ResultsView.tsx.
- scripts/test_frontend.cjs e README.md.

Dockerfile, .gitignore e .dockerignore existentes continuam sendo utilizados.
A lógica científica de Qiskit não foi alterada.

