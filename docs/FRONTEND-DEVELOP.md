# Migração local para develop — 13/11/2026

Origem: https://github.com/julia-deeck/agente-rag-otimizacao-codigo-front/tree/develop
Commit: cf592cb1df9c3df04e0b3755e544ff2ae1ed9935.

O frontend foi substituído integralmente a partir dessa revisão. CSS e assets permanecem idênticos. O design holográfico customizado anterior foi retirado.

Adaptações necessárias:
- Dockerfile, .dockerignore e next.config.ts mantêm standalone e proxy para api:8000.
- analysis-api.ts converte a entrada da branch para /qiskit/optimize e /query. Usa AbortSignal e preserva erro/request_id.
- AnalysisForm conecta processamento, resultados e feedback, preservando formulário e configurações originais.
- LoadingView apresenta processamento real sem percentuais inventados.
- ResultsView substitui o placeholder por explicação, métricas, fontes e circuito reais.
- SourceDrawer recebe fontes reais e corrige nulidade TypeScript.
- Layout usa pt-BR; fontes, identidade visual e globals.css vêm do upstream. integration.css acrescenta estilos ausentes na branch para fontes, métricas, feedback e processamento, no mesmo padrão visual.

O upstream ainda não tinha análise conectada. Portanto, esta entrega preserva seu visual, mas não é cópia byte a byte de todos os componentes: as adaptações acima são necessárias para operação real.
Não foram adicionadas opções de hardware ausentes no repositório. Não há métricas fictícias ou resposta simulada em produção.

Rollback: frontend anterior preservado em artifacts/frontend-before-develop-20261113 (ignorado pelo Git e Docker). Para reverter, pare frontend, arquive a versão atual, restaure aquela pasta como frontend e execute docker compose up --build -d frontend. Não remova volumes.

Verificações:
- Build produção Next.js/TypeScript.
- 86 testes backend aprovados; teste live separado não selecionado na suíte isolada.
- scripts/test_frontend.cjs verifica Chromium real, Qiskit, Gemini, fontes, top_k, formulários, estados de erro, retry, cancelamento e layout mobile. Falha de provedor e evidência insuficiente são controladas apenas pelo transporte do teste.
- Capturas em artifacts/develop-input.png, develop-results.png e develop-mobile.png.
- npm ci reportou 8 vulnerabilidades moderadas no conjunto de dependências herdado. Não foi aplicado upgrade incompatível automaticamente.

Nenhum push realizado. Credencial e dados existentes preservados somente localmente.
