# Validação da integração — 26/10/2026

## Executado

- Inspeção de código, dependências, caminhos, coleções, embeddings e contratos nas três pastas, sem ler bancos, caches, modelos baixados ou ambientes virtuais de origem.
- Testes em ambiente temporário novo, usando o Python disponível no host: **3.15.0rc3**. O Dockerfile utiliza **Python 3.12**.
- `python -B -m pytest -q -p no:cacheprovider --tb=short`: **52 aprovados, 1 ignorado**. O teste ignorado depende de API, modelo e ChromaDB reais em execução.
- `python -m pip check` no ambiente de teste: **No broken requirements found**.
- OpenAPI regenerado e validado pelos testes; rotas e modelos de entrada/saída preservados.
- Resolução com pip `--dry-run --only-binary=:all:` para **Linux x86_64/Python 3.12**, incluindo **torch 2.14.1+cpu** e todos os requisitos de execução: concluída sem conflito. Isso valida a resolução, não equivale a executar o build ou o modelo.
- Imagem oficial `chromadb/chroma:1.5.9` consultada no registro; configuração oficial usa `/data` para persistência.
- YAML do Compose analisado nos testes: dois serviços, rede interna e único volume de banco. O estágio Docker de teste não acrescenta um serviço permanente.

Foram mantidos os testes originais de contrato da API e os seis testes de artefatos do RAG. O simulador original ficou restrito aos testes. O caso de upload acima do limite recebeu um identificador curto porque o pytest no Windows falhou ao formar o nome temporário a partir de 262.145 bytes usados como parâmetro. O conteúdo e a expectativa desse teste foram preservados.

Os novos testes cobrem upload e busca pelo código integrado, metadados/fontes, reunião e ordenação de seções, reenvio idempotente, paginação do catálogo, remoção apenas de chunks obsoletos do documento atualizado, indisponibilidade, resposta inválida, timeout, coleção incompatível e erro explícito de LLM ausente. O SDK real também é exercitado com respostas HTTP controladas; isso não prova conectividade com servidor real.

Há avisos de depreciação das bibliotecas no Python 3.15 e de configuração legada de embeddings no teste HTTP controlado; nenhum causou falha nos testes.

## Não executado neste computador

- `docker --version` e `docker compose version`: comando `docker` não encontrado. Portanto, build, subida dos dois containers, download/carregamento do modelo, busca semântica real e persistência após reiniciar os containers permanecem pendentes.
- `gh auth status`: comando `gh` não encontrado. Nenhuma autenticação foi contornada; nenhum repositório foi criado, sobrescrito ou enviado. A existência de `growup-api-chromadb` na conta ainda não pôde ser consultada.
- Dados locais não foram abertos, migrados ou testados quanto à compatibilidade binária.
- Nenhuma LLM foi chamada. `/query` retorna `503 LLM_NOT_CONFIGURED`.

## Próxima validação em máquina com Docker

Siga o README: `docker compose config --quiet`, build/subida, indexação explícita do snapshot e teste marcado `live`. Depois reinicie com `docker compose down` / `up -d` sem remover volumes e confirme que os documentos continuam pesquisáveis. Registre tempo de inicialização, primeira busca, qualidade dos resultados e eventual limiar de relevância antes de declarar o fluxo de produção validado.
