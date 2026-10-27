"""Gera chunks por seção, incluindo o título no orçamento de tokens."""
import json
import re
from pathlib import Path

PASTA = Path(__file__).resolve().parents[1] / "documentos"


def gerar_chunks(documento, tokenizer, limite, nome_modelo):
    if not documento.get("secoes"):
        raise ValueError("O JSON ainda não tem seções. Execute coletar_documentos.py atualizado primeiro.")

    def contar(texto):
        return len(tokenizer.encode(texto, add_special_tokens=True, truncation=False))

    chunks = []

    def salvar(texto, secao, tipo, fragmentado=False):
        tokens = contar(texto)
        if tokens > limite:
            raise ValueError("Chunk excedeu o limite; nenhum arquivo foi salvo.")
        indice = len(chunks)
        chunks.append({
            "id": f"{documento['document_id']}_chunk_{indice}",
            "texto": texto,
            "metadados": {
                "document_id": documento["document_id"],
                "titulo": documento["titulo"],
                "fonte": documento["fonte"],
                "versao_documentacao": documento["versao_documentacao"],
                "coletado_em": documento["coletado_em"],
                "indice": indice,
                "tokens": tokens,
                "modelo_embeddings": nome_modelo,
                "secao": secao,
                "tipo_bloco": tipo,
                "fragmentado": fragmentado,
                "estrategia_chunks": "secoes_tokens_v2",
                "versao_alvo_qiskit": documento.get("versao_alvo_qiskit", "não definida"),
            },
        })

    for secao in documento["secoes"]:
        titulo = secao["titulo"]
        prefixo = titulo + "\n\n"
        if contar(prefixo) >= limite:
            raise ValueError(f"Título muito longo: {titulo}")
        for bloco in secao["blocos"]:
            texto = bloco["texto"].rstrip() if bloco["tipo"] == "codigo" else bloco["texto"].strip()
            if not texto:
                continue
            if contar(prefixo + texto) <= limite:
                salvar(prefixo + texto, titulo, bloco["tipo"])
                continue
            # Fragmentos de código são trechos documentais, não scripts executáveis.
            # Mantém linhas e indentação; o original completo permanece no JSON.
            if bloco["tipo"] == "codigo":
                buffer_codigo = ""
                for linha in texto.splitlines(keepends=True):
                    if contar(prefixo + linha) > limite:
                        raise ValueError(f"Linha de código excede o limite na seção '{titulo}'. Lote anterior preservado.")
                    if contar(prefixo + buffer_codigo + linha) > limite:
                        salvar(prefixo + buffer_codigo, titulo, "codigo", True)
                        buffer_codigo = ""
                    buffer_codigo += linha
                if buffer_codigo:
                    salvar(prefixo + buffer_codigo, titulo, "codigo", True)
                continue
            # Mantém frases inteiras sempre que couberem.
            frases = re.split(r"(?<=[.!?])\s+", texto)
            buffer = ""
            for frase in frases:
                candidato = (buffer + " " + frase).strip()
                if contar(prefixo + candidato) <= limite:
                    buffer = candidato
                    continue
                if buffer:
                    salvar(prefixo + buffer, titulo, bloco["tipo"], True)
                    buffer = ""
                if contar(prefixo + frase) <= limite:
                    buffer = frase
                    continue
                # Frases longas são divididas em palavras, sem cortar identificadores.
                for palavra in frase.split():
                    candidato = (buffer + " " + palavra).strip()
                    if contar(prefixo + candidato) <= limite:
                        buffer = candidato
                    else:
                        if not buffer or contar(prefixo + palavra) > limite:
                            raise ValueError(f"Identificador excede o limite na seção '{titulo}'.")
                        salvar(prefixo + buffer, titulo, bloco["tipo"], True)
                        buffer = palavra
            if buffer:
                salvar(prefixo + buffer, titulo, bloco["tipo"], True)
    if not chunks:
        raise ValueError("Nenhum chunk gerado.")
    return chunks


def main():
    from .configuracao import MODELO_EMBEDDINGS, obter_modelo

    documentos = json.loads((PASTA / "base_documental.json").read_text(encoding="utf-8"))
    if not documentos:
        raise ValueError("Lote vazio. Execute a coleta primeiro.")
    ids = [d["document_id"] for d in documentos]
    if len(ids) != len(set(ids)):
        raise ValueError("Documentos duplicados no lote.")
    modelo = obter_modelo()
    limite = min(110, modelo.max_seq_length)
    todos = []
    for documento in documentos:
        chunks = gerar_chunks(documento, modelo.tokenizer, limite, MODELO_EMBEDDINGS)
        todos.extend(chunks)
        print(documento["document_id"], ":", len(chunks), "chunks")
    # Validação de todos os documentos termina antes da gravação.
    destino = PASTA / "chunks_base.json"
    temporario = destino.with_suffix(".tmp")
    temporario.write_text(json.dumps(todos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(destino)
    print("Total de documentos:", len(documentos))
    print("Total de chunks:", len(todos))
    print("Maior chunk:", max(c["metadados"]["tokens"] for c in todos), "tokens")
    print("Todos os chunks respeitam o limite de", limite, "tokens, incluindo os títulos.")


if __name__ == "__main__":
    main()
