from time import perf_counter
import os
from .banco import obter_colecao
from .configuracao import criar_embeddings


def buscar_documentos(pergunta, quantidade=3, *, tempos=None):
    medidas = tempos if tempos is not None else {}
    medidas.clear()
    inicio_total = perf_counter()
    if not pergunta.strip():
        return []

    if quantidade < 1:
        raise ValueError("A quantidade deve ser pelo menos 1.")

    inicio = perf_counter()
    colecao = obter_colecao()
    medidas["Obter coleção (inclui inicialização se necessária)"] = perf_counter() - inicio
    inicio = perf_counter()
    total = colecao.count()
    medidas["Contar registros"] = perf_counter() - inicio

    if total == 0:
        return []

    inicio = perf_counter()
    vetores = criar_embeddings()([pergunta])
    medidas["Gerar embedding da pergunta"] = perf_counter() - inicio
    inicio = perf_counter()
    resultado = colecao.query(
        query_embeddings=vetores,
        n_results=min(quantidade, total),
        include=["documents", "metadatas", "distances"],
    )

    medidas["Buscar vetores no ChromaDB"] = perf_counter() - inicio
    inicio_contexto = perf_counter()
    documentos = []
    secoes_recuperadas = set()

    for identificador, metadados, distancia in zip(
        resultado["ids"][0],
        resultado["metadatas"][0],
        resultado["distances"][0],
    ):
        # Opcional: somente usar um corte definido com avaliação da equipe.
        # A distância l2 de vetores normalizados não é probabilidade/confiança.
        limite = os.getenv("RAG_MAX_DISTANCE", "").strip()
        if limite and distancia > float(limite):
            continue
        document_id = metadados["document_id"]
        secao = metadados["secao"]
        chave = (document_id, secao)

        # Evita devolver a mesma seção mais de uma vez.
        if chave in secoes_recuperadas:
            continue

        secoes_recuperadas.add(chave)

        registros = colecao.get(
            where={
                "$and": [
                    {"document_id": document_id},
                    {"secao": secao},
                ]
            },
            include=["documents", "metadatas"],
        )

        # Reconstitui a ordem original dos trechos.
        partes = sorted(
            zip(
                registros["ids"],
                registros["documents"],
                registros["metadatas"],
            ),
            key=lambda item: item[2]["indice"],
        )

        prefixo = secao + "\n\n"
        textos = [
            texto.removeprefix(prefixo)
            for _, texto, _ in partes
        ]

        documentos.append({
            "id": identificador,
            "ids_contexto": [item[0] for item in partes],
            "texto": prefixo + "\n\n".join(textos),
            "metadados": {
                "document_id": document_id,
                "secao": secao,
                "fonte": metadados["fonte"],
                "titulo": metadados["titulo"],
                "versao_documentacao": metadados["versao_documentacao"],
                "coletado_em": metadados["coletado_em"],
            },
            # Distância do chunk que levou à seção.
            "distancia": float(distancia),
        })

    medidas["Recuperar e montar seções"] = perf_counter() - inicio_contexto
    medidas["TOTAL"] = perf_counter() - inicio_total
    return documentos


if __name__ == "__main__":
    print("Conectando ao servidor ChromaDB...", flush=True)
    obter_colecao()
    print("Digite 'sair' para encerrar. A primeira consulta pode incluir aquecimento.")

    while True:
        pergunta = input("\nSua pergunta: ").strip()
        if pergunta.lower() == "sair":
            break
        if not pergunta:
            continue
        tempos = {}
        resultados = buscar_documentos(pergunta, tempos=tempos)
        print("\nTEMPOS (sem incluir a impressão dos resultados):")
        for etapa, duracao in tempos.items():
            print(f"  {etapa}: {duracao:.3f} s")
        for posicao, documento in enumerate(resultados, start=1):
            print(f"\nResultado {posicao}")
            print("Seção:", documento["metadados"]["secao"])
            print("ID encontrado:", documento["id"])
            print(f"Distância: {documento['distancia']:.4f}")
            print("Prévia:", documento["texto"][:600])
            print("Fonte:", documento["metadados"]["fonte"])
