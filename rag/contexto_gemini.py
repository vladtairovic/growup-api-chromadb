MENSAGEM_SEM_CONTEXTO = (
    "Não encontrei documentação suficiente "
    "para responder à pergunta com segurança."
)


def preparar_contexto(documentos, limite=12000):
    """
    Constrói o contexto para a LLM.

    Preserva os títulos, seções e URLs das fontes.
    O limite é medido em caracteres, não tokens.
    """

    if limite < 500:
        raise ValueError(
            "O limite de contexto deve ser de pelo menos 500."
        )

    partes = []
    fontes = []
    tamanho = 0

    for documento in documentos:
        texto = documento.get("texto", "").strip()

        if not texto:
            continue

        metadados = documento.get("metadados") or {}

        numero = len(fontes) + 1
        titulo = metadados.get("titulo", "Sem título")
        secao = metadados.get("secao", "Não informada")
        url = metadados.get("fonte", "")

        cabecalho = (
            f"[Fonte {numero}]\n"
            f"Título: {titulo}\n"
            f"Seção: {secao}\n"
            f"URL: {url}\n"
            "Conteúdo:\n"
        )

        restante = limite - tamanho - len(cabecalho) - 2

        if restante < 100:
            break

        trecho = texto[:restante]
        bloco = cabecalho + trecho

        partes.append(bloco)
        tamanho += len(bloco) + 2

        fontes.append({
            "numero": numero,
            "titulo": titulo,
            "secao": secao,
            "url": url,
            "id_documento": metadados.get(
                "document_id", ""
            ),
        })

        if len(trecho) < len(texto):
            break

    return "\n\n".join(partes), fontes
