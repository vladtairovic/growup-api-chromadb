
"use client";

import CodeMirror from "@uiw/react-codemirror";
import { StreamLanguage } from "@codemirror/language";

type CodeEditorProps = {
  value: string;
  onChange: (value: string) => void;
};

// Palavras reservadas do OpenQASM 2
const qasmKeywords = new Set([
  "OPENQASM",
  "include",
  "qreg",
  "creg",
  "gate",
  "opaque",
  "if",
  "measure",
  "reset",
  "barrier",
  "U",
  "CX",
]);

// Portas quânticas comuns da qelib1.inc
const qasmGates = new Set([
  "id", "x", "y", "z", "h",
  "s", "sdg", "t", "tdg",
  "rx", "ry", "rz",
  "u1", "u2", "u3",
  "cx", "cy", "cz", "ch",
  "crz", "cu1", "cu3",
  "swap", "ccx", "cswap",
]);

// Funções matemáticas e constantes
const qasmBuiltins = new Set([
  "pi",
  "sin",
  "cos",
  "tan",
  "exp",
  "ln",
  "sqrt",
]);

// Reconhecimento visual básico do OpenQASM 2
const qasmLanguage = StreamLanguage.define({
  token(stream) {
    if (stream.eatSpace()) {
      return null;
    }

    // Comentários
    if (stream.match("//")) {
      stream.skipToEnd();
      return "comment";
    }

    // Strings
    if (stream.match(/"(?:[^"\\]|\\.)*"/)) {
      return "string";
    }

    // Números, incluindo notação científica
    if (
      stream.match(
        /(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?/
      )
    ) {
      return "number";
    }

    // Identificadores
    if (stream.match(/[A-Za-z_][A-Za-z0-9_]*/)) {
      const word = stream.current();

      if (qasmKeywords.has(word)) {
        return "keyword";
      }

      if (qasmGates.has(word)) {
        return "atom";
      }

      if (qasmBuiltins.has(word)) {
        return "builtin";
      }

      return "variableName";
    }

    // Operadores
    if (stream.match(/->|==|<=|>=|[=+\-*/^<>]/)) {
      return "operator";
    }

    // Pontuação
    if (stream.match(/[()[\]{},;.]/)) {
      return "punctuation";
    }

    stream.next();
    return null;
  },
});

export default function CodeEditor({
  value,
  onChange,
}: CodeEditorProps) {
  return (
    <CodeMirror
      value={value}
      height="320px"
      extensions={[qasmLanguage]}
      onChange={onChange}
      basicSetup={{
        lineNumbers: true,
        foldGutter: true,
        highlightActiveLine: true,
        bracketMatching: true,
        autocompletion: false,
      }}
    />
  );
}