"""Coleta restrita ao catálogo IBM. A busca ampla é feita pelo provedor Gemini."""
import time
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

HOST = "quantum.cloud.ibm.com"
AGENTE = "GrowUpKnowledge/1.0"
MAX_BYTES = 8 * 1024 * 1024


def validar_url(url):
    p = urlsplit(url)
    if (p.scheme != "https" or p.hostname != HOST or p.port not in (None, 443)
            or p.username or p.password or p.query or p.fragment
            or not (p.path.startswith("/docs/en/") or p.path == "/robots.txt")):
        raise ValueError("Fonte fora do catálogo público IBM.")
    return url


def baixar(cliente, url, com_url=False):
    validar_url(url)
    # Redirecionamentos também passam pela lista permitida, antes de qualquer conexão.
    for _ in range(4):
        with cliente.stream("GET", url) as r:
            if r.is_redirect:
                from urllib.parse import urljoin
                url = validar_url(urljoin(url, r.headers["location"]))
                continue
            r.raise_for_status()
            if not any(t in r.headers.get("content-type", "") for t in ("text/html", "text/plain")):
                raise ValueError("Formato de página não aceito.")
            dados = bytearray()
            for parte in r.iter_bytes():
                dados.extend(parte)
                if len(dados) > MAX_BYTES:
                    raise ValueError("Página acima de 8 MiB.")
            return (dados.decode("utf-8"), url) if com_url else dados.decode("utf-8")
    raise ValueError("Redirecionamentos excessivos.")


def extrair(html):
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main")
    if main is None:
        raise ValueError("Página sem conteúdo principal.")
    for node in main.select("script,style,nav,footer,header,button,svg"):
        node.decompose()
    titulo = main.find("h1")
    titulo = titulo.get_text(" ", strip=True) if titulo else "Documentação Qiskit"
    secoes, atual = [], None
    for node in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "pre", "table"]):
        if node.find_parent(["pre", "li", "table"]):
            continue
        texto = node.get_text("" if node.name == "pre" else "\n" if node.name == "table" else " ",
                              strip=node.name != "pre")
        if not texto:
            continue
        if node.name in ("h1", "h2", "h3", "h4"):
            atual = {"titulo": f"{len(secoes) + 1}. {texto[:160]}", "blocos": []}
            secoes.append(atual)
        else:
            if atual is None:
                atual = {"titulo": "Introdução", "blocos": []}
                secoes.append(atual)
            # Texto extraído é documentação, não código executável. O snapshot preserva as linhas.
            atual["blocos"].append({"tipo": "paragrafo", "texto": texto})
    secoes = [s for s in secoes if s["blocos"]]
    tamanho = sum(len(b["texto"]) for s in secoes for b in s["blocos"])
    if tamanho < 200 or tamanho > 800000:
        raise ValueError("Conteúdo vazio, bloqueado ou acima do limite.")
    return titulo, secoes


class Coletor:
    def __enter__(self):
        self.cliente = httpx.Client(timeout=20, follow_redirects=False, headers={"User-Agent": AGENTE})
        try:
            self.robots = RobotFileParser()
            self.robots.parse(baixar(self.cliente, f"https://{HOST}/robots.txt").splitlines())
        except Exception:
            self.cliente.close()
            raise
        return self

    def coletar(self, url):
        validar_url(url)
        if not self.robots.can_fetch(AGENTE, url):
            raise ValueError("Coleta não permitida por robots.txt.")
        time.sleep(max(1, self.robots.crawl_delay(AGENTE) or 1))
        html, self.ultima_url = baixar(self.cliente, url, com_url=True)
        return extrair(html)

    def __exit__(self, *args):
        self.cliente.close()
