
"use client";
import {useState} from "react";
import type {AnalysisResponse} from "../../services/analysis-api";
import SourceDrawer, {type SourceDetails} from "./SourceDrawer";

type ResultsViewProps = {
  result: AnalysisResponse;
  code: string;
  question: string;
  onBack: () => void;
};

export default function ResultsView({
  result,
  code,
  question,
  onBack,
}: ResultsViewProps) {
 const [selected,setSelected]=useState<SourceDetails|null>(null);
 const [notice,setNotice]=useState("");
 async function copy(){try{await navigator.clipboard.writeText(result.quantum?.circuito_otimizado_qasm||result.answer);setNotice("Resultado copiado.");}catch{setNotice("Selecione o texto e use Ctrl+C.");}}
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
            ANÁLISE DE CÓDIGO
          </span>

          <h1>Resultados da análise</h1>

          <div className="result-header-actions">
            <button
              type="button"
              className="button-secondary"
              onClick={onBack}
            >
              Voltar ao editor
            </button>
          </div>
        </section>

        <section className="panel result-section" aria-label="Resultado">
          <h2>Resultado</h2>
          {result.web_status&&<p>Busca web: {result.web_status==="used"?"fontes encontradas":result.web_status==="disabled"?"desativada":"sem fontes web retornadas"}</p>}
          {result.search_suggestions_html&&<iframe
            title="Sugestões de pesquisa do Google"
            sandbox="allow-popups allow-popups-to-escape-sandbox"
            referrerPolicy="no-referrer"
            style={{width:"100%",height:180,border:0}}
            srcDoc={'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src https: data:; base-uri \'none\'; form-action \'none\'">'+result.search_suggestions_html}
          />}
          {result.warnings.map((w,i)=><p role="status" key={i}>{w}</p>)}
          <p style={{whiteSpace:"pre-wrap"}}>{result.answer}</p>
          {result.quantum&&<><h3>Métricas Qiskit</h3><div className="metrics-grid"><div className="metric-card"><span>Profundidade antes</span><strong>{result.quantum.original.profundidade}</strong></div><div className="metric-card"><span>Profundidade depois</span><strong>{result.quantum.proposta.profundidade}</strong></div></div><p>Operações: {result.quantum.original.total_operacoes} → {result.quantum.proposta.total_operacoes}</p><p>Equivalência: {result.quantum.equivalente===true?"confirmada":result.quantum.equivalente===false?"não equivalente":"não verificada"}. {result.quantum.motivo}</p><h3>Circuito otimizado</h3><pre className="comparison-code">{result.quantum.circuito_otimizado_qasm}</pre></>}
          {result.sources.length>0&&<><h3>Fontes recuperadas</h3>{result.sources.map((f,i)=><button key={f.chunk_id} className="source-item source-item-button" onClick={()=>setSelected({id:f.chunk_id,title:f.title||f.source,origin:(f.origin==="web"?"Web":"Base local")+(f.retrieved_at?" · "+f.retrieved_at:""),category:f.origin==="web"?"Pesquisa web":"Documentação",type:"documentation",excerpt:f.content,relationship:f.origin==="web"?"Afirmações da resposta vinculadas a esta fonte pelo Google; não são transcrições literais da página.":"Contexto recuperado para esta análise; citações não verificadas automaticamente.",url:/^https?:\/\//.test(f.source)?f.source:null})}>Ver fonte {i+1} ({f.origin==="web"?"web":"local"}): {f.title||f.source}</button>)}</>}
          <button className="button-secondary" onClick={copy}>Copiar resultado</button><p role="status">{notice}</p>
          <p>Solicitação: {result.request_id}</p>
        </section>

        <section className="panel result-section">
          <div className="result-section-heading">
            <h2>Dados enviados</h2>
          </div>

          <div className="question-context">
            <span>Pergunta</span>
            <strong>
              {question.trim() || "Nenhuma pergunta informada."}
            </strong>
          </div>

          <div className="comparison-panel">
            <div className="comparison-panel-heading">
              CÓDIGO OPENQASM 2
            </div>

            <pre className="comparison-code">
              <code>
                {code.trim() || "Nenhum código informado."}
              </code>
            </pre>
          </div>
        </section>

        <footer className="page-footer">
          Agente RAG · Qiskit — Ferramenta de apoio ao
          desenvolvimento quântico.
        </footer>
      </main>
      <SourceDrawer source={selected} onClose={()=>setSelected(null)}/>
    </>
  );
}