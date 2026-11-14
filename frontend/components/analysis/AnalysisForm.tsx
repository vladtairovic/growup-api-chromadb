
"use client";

import { useState, useRef, type FormEvent } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";

import SettingsPanel from "./SettingsPanel";

const CodeEditor = dynamic(
  () => import("./CodeEditor"),
  {
    ssr: false,
    loading: () => (
      <div className="editor-loading">
        Carregando editor...
      </div>
    ),
  }
);

import LoadingView from "./LoadingView";
import ResultsView from "./ResultsView";
import AnalysisFeedback, {type AnalysisFeedbackType} from "./AnalysisFeedback";
import {submitAnalysis, AnalysisError, type AnalysisResponse} from "../../services/analysis-api";
export default function AnalysisForm() {
 const [stage,setStage]=useState<"input"|"loading"|"result"|"error">("input");
 const [result,setResult]=useState<AnalysisResponse|null>(null);
 const [failure,setFailure]=useState<{type:AnalysisFeedbackType;id?:string;message:string}>({type:"service-error",message:""});
 const active=useRef<AbortController|null>(null);
 function back(){active.current?.abort();active.current=null;setStage("input");}
 async function run(){
  const controller=new AbortController();active.current?.abort();active.current=controller;setStage("loading");
  const timeout=setTimeout(()=>controller.abort("timeout"),120000);
  try{
   const data=await submitAnalysis({question,code,backend,top_k:Number(topK),web_search:webSearch},controller.signal);
   if(active.current!==controller)return;
   if(data.status==="insufficient_context"){setFailure({type:"insufficient-evidence",id:data.request_id,message:data.answer});setStage("error");}
   else{setResult(data);setStage("result");}
  }catch(e){
   if(active.current!==controller)return;
   const err=e as AnalysisError;
   setFailure({type:err.status===422?"invalid-code":"service-error",id:err.requestId,message:controller.signal.aborted?"Tempo limite excedido. Tente novamente.":err.message});setStage("error");
  }finally{clearTimeout(timeout);}
 }
  const [code, setCode] = useState("");
  const [question, setQuestion] = useState("");

  const [backend, setBackend] = useState("reference");
  const [topK, setTopK] = useState("5");
  const [webSearch, setWebSearch] = useState(true);

  const [showInputErrors, setShowInputErrors] = useState(false);

  const [feedback, setFeedback] = useState<{
    type: "error";
    message: string;
  } | null>(null);

  const [editorMessage, setEditorMessage] = useState("");

  const examples = [
    "Reduzir profundidade",
    "Explicar o circuito",
    "Adaptar ao backend",
  ];

  function selectExample(example: string) {
    setQuestion(example);
    setFeedback(null);
  }

  async function handleCopy() {
    if (!code.trim()) {
      setEditorMessage("Não existe código para copiar.");
      return;
    }

    try {
      await navigator.clipboard.writeText(code);
      setEditorMessage("Código copiado!");
    } catch {
      setEditorMessage(
        "Não foi possível copiar automaticamente. Utilize Ctrl+C."
      );
    }
  }

  async function handlePaste() {
    try {
      const clipboardText = await navigator.clipboard.readText();

      if (!clipboardText) {
        setEditorMessage("A área de transferência está vazia.");
        return;
      }

      setCode(clipboardText);
      setEditorMessage("Código inserido!");
      setFeedback(null);
      setShowInputErrors(false);
    } catch {
      setEditorMessage(
        "Não foi possível acessar a área de transferência. Utilize Ctrl+V."
      );
    }
  }

  function handleClear() {
    setCode("");
    setQuestion("");
    setBackend("reference");
    setTopK("5");
    setWebSearch(true);
    setFeedback(null);
    setEditorMessage("");
    setShowInputErrors(false);
  }

  function handleAnalyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!code.trim() && !question.trim()) {
      setShowInputErrors(true);

      setFeedback({
        type: "error",
        message:
          "Preencha o código, a pergunta ou os dois para continuar.",
      });

      return;
    }

    setShowInputErrors(false);
    setFeedback(null);
    void run();
  }

  if(stage==="loading")return <LoadingView code={code} onBack={back}/>;
  if(stage==="result"&&result)return <ResultsView code={code} question={question} result={result} onBack={back}/>;
  if(stage==="error")return <AnalysisFeedback type={failure.type} code={code} question={question} requestId={failure.id} message={failure.message} onBack={back} onRetry={()=>void run()}/>;

  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <Image
              src="/images/logo.png"
              alt="Identidade visual do projeto Agente RAG"
              width={240}
              height={90}
              priority
              style={{
                display: "block",
                width: "220px",
                height: "auto",
                maxHeight: "76px",
                objectFit: "contain",
              }}
            />
          </div>

          <div className="topbar-label">
            Qiskit · Next-Gen Computing
          </div>
        </div>
      </header>

      <main className="workspace">
        <section className="page-intro">
          <div>
            <span className="eyebrow">
              ÁREA DE TRABALHO
            </span>

            <h1>Nova análise</h1>

            <p>
              Cole seu código OpenQASM 2, diga o que deseja entender
              ou melhorar e receba uma análise com fontes.
            </p>
          </div>
        </section>

        <form
          className="analysis-grid"
          onSubmit={handleAnalyze}
          noValidate
        >
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Código OpenQASM 2</h2>

                <span>
                  Insira o código que deseja analisar.
                </span>
              </div>

              <div className="toolbar-actions">
                <button
                  type="button"
                  className="button-quiet"
                  onClick={handlePaste}
                >
                  Colar
                </button>

                <button
                  type="button"
                  className="button-quiet"
                  onClick={handleCopy}
                >
                  Copiar
                </button>
              </div>
            </div>

            <div
              className={`editor-shell ${
                showInputErrors ? "input-invalid" : ""
              }`}
            >
              <div className="editor-toolbar">
                <span className="language-label">
                  OPENQASM 2
                </span>

                <span>OpenQASM</span>
              </div>

              <CodeEditor
                value={code}
                onChange={(value) => {
                  setCode(value);
                  setEditorMessage("");

                  if (value.trim()) {
                    setShowInputErrors(false);
                    setFeedback(null);
                  }
                }}
              />
            </div>

            <div className="editor-footer">
              <span>Editor de código OpenQASM 2</span>
              <span>{code.length} caracteres</span>
            </div>

            {editorMessage && (
              <p className="editor-message" role="status">
                {editorMessage}
              </p>
            )}
          </section>

          <section className="panel side-panel">
            <div className="field-group">
              <label htmlFor="analysis-question">
                Pergunta / objetivo
              </label>

              <textarea
                id="analysis-question"
                className={`question-input ${
                  showInputErrors ? "input-invalid-field" : ""
                }`}
                aria-invalid={showInputErrors}
                value={question}
                onChange={(event) => {
                  setQuestion(event.target.value);
                  setFeedback(null);

                  if (event.target.value.trim()) {
                    setShowInputErrors(false);
                  }
                }}
                placeholder="O que você gostaria de entender ou melhorar?"
              />
            </div>

            <div className="examples-section">
              <span className="section-label">
                EXEMPLOS DE OBJETIVO
              </span>

              <div className="example-list">
                {examples.map((example) => (
                  <button
                    key={example}
                    type="button"
                    className="example-chip"
                    onClick={() => selectExample(example)}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>

            <SettingsPanel
              backend={backend}
              topK={topK}
              webSearch={webSearch}
              onWebSearchChange={setWebSearch}
              onBackendChange={setBackend}
              onTopKChange={setTopK}
            />

            <div className="form-actions">
              <button
                type="submit"
                className="button-primary"
              >
                Analisar
                <span aria-hidden="true">→</span>
              </button>

              <button
                type="button"
                className="button-secondary"
                onClick={handleClear}
              >
                Limpar tudo
              </button>
            </div>

            <p className="form-hint">
              Preencha ao menos a pergunta ou o código.
            </p>
          </section>
        </form>

        {feedback && (
          <div
            className="form-feedback error"
            role="alert"
          >
            {feedback.message}
          </div>
        )}

        <footer className="page-footer">
          Agente RAG · Qiskit — Ferramenta de apoio ao
          desenvolvimento quântico.
        </footer>
      </main>
    </>
  );
}