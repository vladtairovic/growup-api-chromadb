# Validação — 08/11/2026

## Resultado desta entrega

Executado localmente com Docker Desktop, engine 29.9.2, containers Linux/Python 3.12:

- Imagem de testes: **84 testes aprovados**, 1 teste live inicialmente ignorado por depender dos serviços ativos.
- Depois, teste live contra API e ChromaDB reais: **1 aprovado**, 84 desmarcados. Total: **85 testes aprovados nas duas fases**, sem falhas.
- Build da imagem completa com FastAPI, ChromaDB client, embeddings CPU, Google Gen AI SDK e Qiskit concluído.
- `pip check` nas imagens de teste e execução: **No broken requirements found**.
- OpenAPI exportado e validado; contratos existentes preservados, rota `POST /qiskit/optimize` acrescentada.
- Script `scripts/validar_docker.py`: **aprovado**, usando projeto isolado `growup-validacao`, API na porta 18080.
- Coleção única: 3 documentos de origem, 154 chunks e embeddings reais de 384 dimensões.
- Reindexação idempotente, busca semântica, upload, repetição sem duplicação e listagem aprovados.
- Qiskit real via HTTP: circuito H/H reduziu de 2 operações para 0; equivalência confirmada.
- ChromaDB parado: busca/listagem retornaram 503; após religar, serviço recuperado.
- Containers removidos e recriados sem excluir volumes: coleção/IDs, documentos e avaliação preservados; modelo carregou do cache com download desativado.
- `/query` sem chave: 503 `LLM_NOT_CONFIGURED`.
- Fluxo RAG/Gemini, ausência de contexto, falha do provedor, timeout configurado e fechamento do cliente cobertos por testes com transporte controlado; esses testes não são respostas reais de IA.
- Dados locais antigos, ambientes virtuais e modelos baixados não foram incorporados ao repositório.

Evidência detalhada desta execução: [validacao-docker.json](validacao-docker.json).
A CI em [.github/workflows/validar.yml](../.github/workflows/validar.yml) repete os builds e os testes com containers reais.

## Limitações confirmadas

**Não houve chamada real ao Gemini**, por escolha explícita do usuário de continuar sem credencial. Para validar essa última dependência, configure `GEMINI_API_KEY` em `.env`, confirme acesso ao `GEMINI_MODEL`, recrie a API e execute a consulta descrita no README. Ainda precisam ser avaliadas a qualidade das respostas, pertinência e fidelidade das citações.

Qiskit não executa hardware IBM nem Aer. O endpoint transpila e avalia equivalência unitária dentro dos limites do serviço original. Casos não verificáveis são identificados no retorno; não são declarados equivalentes.

Foram observados três avisos de depreciação na suíte isolada (Starlette/AnyIO e configuração legada do SDK ChromaDB no teste controlado). Não houve falha de teste ou conflito de dependências. Estes resultados comprovam os cenários exercitados, não uma garantia de ausência de qualquer defeito.

## Histórico

A primeira preparação ocorreu em 26/10/2026. A CI anterior já validou o projeto sem Gemini/Qiskit em 27/10/2026. O presente relatório substitui as antigas pendências locais de Docker e GitHub, agora disponíveis e autenticados. As fontes/commits desta nova integração constam em [INTEGRACOES.md](INTEGRACOES.md).
