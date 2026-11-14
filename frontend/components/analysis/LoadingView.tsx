
"use client";

type LoadingViewProps = {
  code: string;
  onBack: () => void;
};

export default function LoadingView({
  code,
  onBack,
}: LoadingViewProps) {
  const codeLines = code
    ? code.split("\n")
    : ["Nenhum código foi informado."];

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <div className="brand-symbol">Q</div>

            <div className="brand-copy">
              <strong>Agente RAG</strong>
              <span>Otimização de código</span>
            </div>
          </div>

          <div className="topbar-label">
            Qiskit · Next-Gen Computing
          </div>
        </div>
      </header>

      <main className="workspace">
        <section className="page-intro">
          <span className="eyebrow">
            ANÁLISE
          </span>

          <h1>Processamento da análise</h1>

          <p>
            Acompanhe o processamento do seu código OpenQASM 2.
          </p>
        </section>

        <div className="loading-grid">
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Código enviado</h2>

                <span>
                  Visualização da entrada original.
                </span>
              </div>

              <span className="readonly-badge">
                Somente leitura
              </span>
            </div>

            <div className="editor-shell">
              <div className="editor-toolbar">
                <span className="language-label">
                  OPENQASM 2
                </span>

                <span>OpenQASM</span>
              </div>

              <div className="readonly-code">
                {codeLines.map((line, index) => (
                  <div
                    className="readonly-code-line"
                    key={index}
                  >
                    <span className="readonly-line-number">
                      {index + 1}
                    </span>

                    <code>{line || " "}</code>
                  </div>
                ))}
              </div>
            </div>

            <div className="editor-footer">
              <span>Entrada preservada</span>

              <span>{code.length} caracteres</span>
            </div>
          </section>

          <section className="panel progress-panel">
            <div className="panel-heading">
              <div>
                <h2>Status da análise</h2>

                <span>
                  Situação atual do processamento.
                </span>
              </div>
            </div>

            <div className="unavailable-metric">
              <strong>
                Solicitação em processamento
              </strong>

              <p>
                Aguardando retorno do Qiskit e, quando solicitada, da análise documental.
              </p>
            </div>

            <div className="request-summary">
              <h3>Dados da entrada</h3>

              <div className="summary-item">
                <span>Tipo de código</span>
                <strong>OpenQASM 2</strong>
              </div>

              <div className="summary-item">
                <span>Situação</span>
                <strong>Processando</strong>
              </div>
            </div>

            <button
              type="button"
              className="button-secondary back-button"
              onClick={onBack}
            >
              ← Voltar para editar
            </button>
          </section>
        </div>

        <footer className="page-footer">
          Agente RAG · Qiskit — Ferramenta de apoio ao
          desenvolvimento quântico.
        </footer>
      </main>
    </>
  );
}