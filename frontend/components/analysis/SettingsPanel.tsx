
"use client";

import { useState } from "react";

type SettingsPanelProps = {
  webSearch: boolean;
  onWebSearchChange: (value: boolean) => void;
  backend: string;
  topK: string;
  onBackendChange: (value: string) => void;
  onTopKChange: (value: string) => void;
};

export default function SettingsPanel({
  webSearch,
  onWebSearchChange,
  backend,
  topK,
  onBackendChange,
  onTopKChange,
}: SettingsPanelProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <section className="settings-panel">
      <button
        type="button"
        className="settings-toggle"
        aria-expanded={isExpanded}
        aria-controls="advanced-settings"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span className="section-label">
          CONFIGURAÇÕES
        </span>

        <span
          className={`settings-chevron ${
            isExpanded ? "is-open" : ""
          }`}
          aria-hidden="true"
        >
          ⌄
        </span>
      </button>

      <p className="settings-description">
        Configure os parâmetros de recuperação e análise.
      </p>

      <div
        id="advanced-settings"
        className="settings-content"
        hidden={!isExpanded}
      >
        <div className="field-group">
          <label><input type="checkbox" checked={webSearch} onChange={e=>onWebSearchChange(e.target.checked)}/> Consultar a internet</label>
          <span className="field-help">Complementa a base local com Google Search quando necessário. Depende da cota Gemini. As fontes web não são armazenadas na base.</span>
        </div>
        <div className="field-group">
          <label htmlFor="backend">
            Backend de destino
          </label>

          <select
            id="backend"
            value={backend}
            onChange={(event) =>
              onBackendChange(event.target.value)
            }
          >
            <option value="reference">
              Backend de referência
            </option>
          </select>

          <span className="field-help">
            Ambiente de destino utilizado na análise.
          </span>
        </div>

        <div className="field-group">
          <label htmlFor="top-k">
            Quantidade de trechos (top_k)
          </label>

          <select
            id="top-k"
            value={topK}
            onChange={(event) =>
              onTopKChange(event.target.value)
            }
          >
            <option value="3">3 trechos</option>
            <option value="5">5 trechos</option>
            <option value="8">8 trechos</option>
            <option value="10">10 trechos</option>
          </select>

          <span className="field-help">
            Quantidade máxima de fragmentos documentais
            que o sistema tentará recuperar.
          </span>
        </div>
      </div>
    </section>
  );
}