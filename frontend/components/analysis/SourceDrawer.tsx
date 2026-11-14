
"use client";

import { useEffect, useState } from "react";

export type SourceDetails = {
  id: string;
  title: string;
  origin: string;
  category: string;
  type: string;
  excerpt: string;
  relationship: string;
  url?: string | null;
};

type SourceDrawerProps = {
  source: SourceDetails | null;
  onClose: () => void;
};

export default function SourceDrawer({
  source,
  onClose,
}: SourceDrawerProps) {
  const [copyMessage, setCopyMessage] = useState("");

  useEffect(() => {
    if (!source) return;

    const previousOverflow = document.body.style.overflow;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [source, onClose]);

  useEffect(() => {
    setCopyMessage("");
  }, [source]);

  if (!source) {
    return null;
  }

  async function handleCopyReference() {
    if (!source) return;
    const reference = [
      source.title,
      source.origin,
      `Categoria: ${source.category}`,
      `Tipo: ${source.type}`,
      `Trecho: ${source.excerpt}`,
      source.url ? `Link: ${source.url}` : "",
    ]
      .filter(Boolean)
      .join("\n");

    try {
      await navigator.clipboard.writeText(reference);
      setCopyMessage("Referência copiada com sucesso!");
    } catch {
      setCopyMessage(
        "Não foi possível copiar automaticamente. Tente selecionar o texto."
      );
    }
  }

  return (
    <div
      className="source-drawer-overlay"
      onClick={onClose}
    >
      <aside
        id="source-detail-drawer"
        className="source-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-drawer-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="source-drawer-header">
          <div>
            <span className="eyebrow">
              DETALHES DA FONTE
            </span>

            <h2 id="source-drawer-title">
              Detalhe da fonte
            </h2>
          </div>

          <button
            type="button"
            className="drawer-close-button"
            onClick={onClose}
            aria-label="Fechar detalhes da fonte"
          >
            ×
          </button>
        </div>

        <section className="drawer-section">
          <span className="drawer-label">
            TÍTULO
          </span>

          <h3 className="drawer-source-title">
            {source.title}
          </h3>
        </section>

        <section className="drawer-section">
          <span className="drawer-label">
            ORIGEM E CLASSIFICAÇÃO
          </span>

          <div className="source-metadata-grid">
            <div className="metadata-item">
              <span>Origem</span>
              <strong>{source.origin}</strong>
            </div>

            <div className="metadata-item">
              <span>Categoria</span>
              <strong>{source.category}</strong>
            </div>

            <div className="metadata-item">
              <span>Tipo</span>
              <strong>{source.type}</strong>
            </div>
          </div>
        </section>

        <section className="drawer-section">
          <span className="drawer-label">
            TRECHO RECUPERADO
          </span>

          <div className="source-excerpt">
            <p>{source.excerpt}</p>
          </div>
        </section>

        <section className="drawer-section">
          <span className="drawer-label">
            RELAÇÃO COM A ANÁLISE
          </span>

          <div className="source-relationship">
            {source.relationship}
          </div>

          <p className="drawer-warning">
            A existência de uma referência documental não
            garante que o código sugerido funcione. É necessária
            validação técnica.
          </p>
        </section>

        <section className="drawer-section">
          <span className="drawer-label">
            LINK DA DOCUMENTAÇÃO
          </span>

          {source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="source-url"
            >
              {source.url}
            </a>
          ) : (
            <p>
              Nenhum link foi disponibilizado para esta fonte.
            </p>
          )}
        </section>

        <div className="source-drawer-actions">
          {source.url && (
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="button-primary drawer-action-link"
            >
              Abrir documentação
            </a>
          )}

          <button
            type="button"
            className="button-secondary"
            onClick={handleCopyReference}
          >
            Copiar referência
          </button>

          {copyMessage && (
            <p className="copy-feedback" role="status">
              {copyMessage}
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}