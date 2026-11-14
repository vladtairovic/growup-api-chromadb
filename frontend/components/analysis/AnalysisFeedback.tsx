
"use client";

export type AnalysisFeedbackType =
  | "invalid-code"
  | "insufficient-evidence"
  | "service-error";

type AnalysisFeedbackProps = {
  type: AnalysisFeedbackType;
  code: string;
  question: string;
  message?: string;
  requestId?: string;
  errorLine?: number;
  onBack: () => void;
  onRetry: () => void;
};

const feedbackContent = {
  "invalid-code": {
    title: "Não foi possível analisar o código",
    heading: "Código inválido",
    message:
      "O serviço de validação identificou um problema no código enviado. Revise a entrada e tente novamente.",
  },
  "insufficient-evidence": {
    title: "Evidências insuficientes",
    heading: "Não foram encontradas evidências suficientes",
    message:
      "A base de conhecimento não retornou informações suficientes para fundamentar uma resposta.",
  },
  "service-error": {
    title: "Não foi possível concluir a análise",
    heading: "Falha no serviço",
    message:
      "O serviço responsável pela análise não conseguiu concluir a solicitação. Tente novamente mais tarde.",
  },
};

export default function AnalysisFeedback({
  type,
  code,
  question,
  message,
  requestId,
  errorLine,
  onBack,
  onRetry,
}: AnalysisFeedbackProps) {
  const content = feedbackContent[type];

  async function handleCopyRequestId() {
    if (!requestId) return;

    try {
      await navigator.clipboard.writeText(requestId);
    } catch {
      // A falha ao copiar não altera o estado da solicitação.
    }
  }

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

      <main className="workspace feedback-workspace">
        <section className="page-intro">
          <span className="eyebrow">
            ACOMPANHAMENTO DA SOLICITAÇÃO
          </span>

          <h1>{content.title}</h1>
        </section>

        <section className="feedback-alert error-alert">
          <span className="feedback-alert-icon">!</span>

          <div>
            <strong>{content.heading}</strong>
            <p>{message || content.message}</p>
          </div>
        </section>

        {type === "invalid-code" && (
          <section className="panel feedback-code-panel">
            <div className="panel-heading">
              <div>
                <h2>Código enviado</h2>
                <span>
                  Entrada preservada para revisão.
                </span>
              </div>

              <span className="readonly-badge">
                Somente leitura
              </span>
            </div>

            {errorLine !== undefined && (
              <p>
                Linha indicada pelo serviço de validação:{" "}
                {errorLine}
              </p>
            )}

            <pre className="comparison-code">
              <code>{code || "Nenhum código informado."}</code>
            </pre>
          </section>
        )}

        {type === "insufficient-evidence" && (
          <section className="panel result-section">
            <h2>Sobre a consulta</h2>

            <p>
              Não há fontes recuperadas suficientes para
              apresentar recomendações fundamentadas.
            </p>
          </section>
        )}

        {type === "service-error" && requestId && (
          <section className="panel service-error-main">
            <h2>Identificador da solicitação</h2>

            <p>{requestId}</p>

            <button
              type="button"
              className="button-secondary"
              onClick={handleCopyRequestId}
            >
              Copiar identificador
            </button>
          </section>
        )}

        {(question || code) && (
          <section className="panel result-section">
            <h2>Dados enviados</h2>

            {question && (
              <div className="question-context">
                <span>Pergunta</span>
                <strong>{question}</strong>
              </div>
            )}

            {code && (
              <div className="comparison-panel">
                <div className="comparison-panel-heading">
                  CÓDIGO OPENQASM 2
                </div>

                <pre className="comparison-code">
                  <code>{code}</code>
                </pre>
              </div>
            )}
          </section>
        )}

        <div className="feedback-actions">
          <button
            type="button"
            className="button-primary"
            onClick={onBack}
          >
            Voltar ao editor
          </button>

          <button
            type="button"
            className="button-secondary"
            onClick={onRetry}
          >
            Tentar novamente
          </button>
        </div>

        <footer className="page-footer">
          Agente RAG · Qiskit — Ferramenta de apoio ao
          desenvolvimento quântico.
        </footer>
      </main>
    </>
  );
}