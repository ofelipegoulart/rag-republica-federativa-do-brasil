"""Baixa a CF/88 (Planalto) e gera chunks por caput / inciso / parágrafo.

Uso:
    python extractor.py              # baixa do Planalto
    python extractor.py arquivo.html # usa um HTML local (útil para testes)
"""
import json
import logging
import os
import re
import sys
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

# Configuração do sistema de logs detalhados (Console + Arquivo)
LOG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "extractor.log"
)
logging.basicConfig(
    level=logging.DEBUG,  # Alterado para DEBUG para capturar cada detalhe
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

URL = "https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm"
OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "artigos_filtrados_constituicao.json"
)

MAX_CHARS = 900  # tamanho máximo de um chunk (~250 tokens)
HEAD_CHARS = 160  # quanto do caput/§ é repetido como contexto nos incisos
ADCT_TITLE = "ATO DAS DISPOSIÇÕES CONSTITUCIONAIS TRANSITÓRIAS"

# Artigos da Constituição permanente que serão indexados
CF_ARTICLES = (
    {21, 22, 23, 24, 25, 27, 30, 32, 144}
    | set(range(92, 127))
    | set(range(194, 215))
)
# Artigos do ADCT a indexar (vazio = nenhum). Ex.: set(range(97, 118)) para precatórios
ADCT_ARTICLES = set()

# ---------------------------------------------------------------- regexes
ART_RE = re.compile(
    r"^Art\.?\s*(?P<num>\d+)(?P<ord>[º°])?(?:-(?P<suf>[A-Z])\b)?(?P<dot>\.)?"
    r"(?:\s+|$)(?P<rest>.*)$"
)
PAR_RE = re.compile(
    r"^§\s*(?P<num>\d+)\s*\.?\s*[º°]?(?:-(?P<suf>[A-Z])\b)?\.?\s*(?P<rest>.*)$"
)
UNICO_RE = re.compile(r"^Parágrafo único\.?\s*(?P<rest>.*)$")
INC_RE = re.compile(
    r"^(?P<num>[IVXLC]+)(?:-(?P<suf>[A-Z])\b)?"
    r"(?:\s*[-–—]\s*|\s+(?=[a-zà-ú]))(?P<rest>.*)$"
)
ALINEA_RE = re.compile(r"^[a-z]\)\s")
HEADING_RE = re.compile(
    r"^(TÍTULO|CAPÍTULO|LIVRO|PARTE|Seção|SEÇÃO|Subseção|SUBSEÇÃO)\b"
)
NOISE_RE = re.compile(
    r"\((?:Redação dada|Incluíd[oa]|Revogad[oa]s?|Vide|Vigência|Regulamento|"
    r"Produção de efeito|Renumerad[oa]|Transformad[oa]|Numerad[oa]|Promulgad)"
    r"[^)]*\)",
    re.I,
)


def classify_category(num, is_adct):
    if is_adct:
        return "ADCT"
    if num in (21, 22, 23, 24, 25, 30, 32):
        return "Competências e Entes Federativos"
    if num == 144:
        return "Segurança Pública"
    if 194 <= num <= 204:
        return "Saúde e Seguridade Social"
    if 205 <= num <= 214:
        return "Educação"
    if num == 27:
        return "Poder Legislativo Estadual (Assembleias)"
    if 92 <= num <= 126:
        return "Poder Judiciário (STF, STJ e Tribunais)"
    return "Geral"


def clean(text):
    return " ".join(NOISE_RE.sub(" ", text).split())


def is_heading(text):
    if HEADING_RE.match(text):
        return True
    if len(text) < 200 and text.isupper() and not ART_RE.match(text):
        return True
    return bool(re.match(r"^D[oa]s?\s", text) and len(text) < 150 and "." not in text)


def shorten(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def split_long(text, limit):
    if len(text) <= limit:
        return [text]
    pieces = []
    for s in re.split(r"(?<=[;.:])\s+", text):
        if len(s) > limit * 1.5:
            words, cur = s.split(), ""
            for w in words:
                if cur and len(cur) + len(w) + 1 > limit:
                    pieces.append(cur)
                    cur = w
                else:
                    cur = f"{cur} {w}".strip()
            if cur:
                pieces.append(cur)
        else:
            pieces.append(s)
    parts, cur = [], ""
    for s in pieces:
        if cur and len(cur) + 1 + len(s) > limit:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        parts.append(cur)
    return parts


# ---------------------------------------------------------------- modelo
class Article:
    def __init__(self, num, suffix, is_adct):
        self.num = num
        self.is_adct = is_adct
        self.base = f"Art. {num}" + (f"-{suffix}" if suffix else "")
        self.category = classify_category(num, is_adct)
        self.units = []
        self.caput_head = ""
        self.par_label = None
        self.par_head = ""

    def _add(self, kind, label, head, body):
        self.units.append(
            {"kind": kind, "label": label, "head": head, "text": body.strip()}
        )

    def add_caput(self, body):
        self.caput_head = shorten(body, HEAD_CHARS)
        self._add("caput", self.base, "", body)

    def add_par(self, par_label, body):
        self.par_label = par_label
        self.par_head = shorten(body, HEAD_CHARS)
        self._add("par", f"{self.base}, {par_label}", "", body)

    def add_inciso(self, numeral, body):
        label = self.base
        head = self.caput_head
        if self.par_label:
            label += f", {self.par_label}"
            head = self.par_head
        self._add("inciso", f"{label}, {numeral}", head, body)

    def append(self, text):
        if self.units:
            self.units[-1]["text"] += " " + text


def article_to_chunks(art):
    out = []
    for u in art.units:
        body = u["text"].strip()
        if not body:
            continue
        if u["kind"] in ("caput", "par") and body.endswith(":") and len(body) < 200:
            continue
        pieces = split_long(body, MAX_CHARS)
        for i, piece in enumerate(pieces, 1):
            label = u["label"]
            if len(pieces) > 1:
                label += f" (parte {i}/{len(pieces)})"
            head = f"{u['head']} " if u["head"] else ""
            out.append(
                {
                    "article": art.base,
                    "label": label,
                    "part": "ADCT" if art.is_adct else "CF",
                    "category": art.category,
                    "text": f"[{label}] {head}{piece}",
                }
            )
    return out


# ---------------------------------------------------------------- parsing
def parse_html(html):
    logging.info("Iniciando o parsing detalhado do HTML...")
    soup = BeautifulSoup(html, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with(" ")

    paragraphs = [p.get_text() for p in soup.find_all("p")]
    if not paragraphs:
        paragraphs = soup.get_text("\n").splitlines()

    logging.info(f"Total de parágrafos brutos encontrados: {len(paragraphs)}")

    chunks = []
    art = None
    is_adct = False
    adct_seen = False

    def close():
        nonlocal art
        if art is not None:
            generated = article_to_chunks(art)
            logging.debug(f"Fechando artigo {art.base}. Chunks gerados para este artigo: {len(generated)}")
            chunks.extend(generated)
        art = None

    for idx, raw in enumerate(paragraphs):
        raw = " ".join(raw.split())
        if not raw:
            continue
        revoked = "Revogad" in raw
        text = clean(raw)
        if not text:
            continue

        if text.upper() == ADCT_TITLE:
            if idx > 2000 and not adct_seen:  # Garante que só ativa o ADCT real no final do documento
                close()
                is_adct = adct_seen = True
                logging.info(f"[Índice {idx}] Marcador do ADCT encontrado.")
            else:
                logging.debug(f"[Índice {idx}] Marcador de ADCT ignorado (menção no índice/sumário inicial).")
            continue

        if is_heading(text):
            close()
            logging.debug(f"[Índice {idx}] Cabeçalho detectado: {text[:60]}...")
            continue

        skip = revoked and len(text) < 40

        m = ART_RE.match(text)
        if m and (m.group("ord") or m.group("dot") or m.group("suf")):
            close()
            num = int(m.group("num"))
            wanted = ADCT_ARTICLES if is_adct else CF_ARTICLES
            if num in wanted and not skip:
                art = Article(num, m.group("suf"), is_adct)
                logging.info(f"[Índice {idx}] Artigo desejado capturado: {art.base} (ADCT: {is_adct})")
                rest = m.group("rest").strip()
                if rest:
                    art.add_caput(rest)
            else:
                logging.debug(f"[Índice {idx}] Artigo {num} ignorado (Fora da lista de desejados ou revogado).")
            continue

        if art is None or skip:
            continue

        if (m := PAR_RE.match(text)):
            n = int(m.group("num"))
            label = f"§ {n}" + ("º" if n < 10 else "")
            if m.group("suf"):
                label += f"-{m.group('suf')}"
            art.add_par(label, m.group("rest"))
            logging.debug(f"  -> [{art.base}] Parágrafo adicionado: {label}")
        elif (m := UNICO_RE.match(text)):
            art.add_par("parágrafo único", m.group("rest"))
            logging.debug(f"  -> [{art.base}] Parágrafo único adicionado.")
        elif (m := INC_RE.match(text)):
            numeral = m.group("num") + (f"-{m.group('suf')}" if m.group("suf") else "")
            art.add_inciso(numeral, m.group("rest"))
            logging.debug(f"  -> [{art.base}] Inciso adicionado: {numeral}")
        else:
            art.append(text)
            logging.debug(f"  -> [{art.base}] Texto/alínea anexado.")

    close()
    if not adct_seen:
        logging.warning("Marcador do ADCT não encontrado no documento.")

    logging.info(f"Parsing concluído. Total geral de chunks gerados: {len(chunks)}")
    return chunks


def download():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    logging.info(f"Iniciando requisição HTTP para a URL: {URL}")
    with urlopen(Request(URL, headers=headers), timeout=30) as resp:
        logging.info(f"Resposta recebida com sucesso. Status HTTP: {resp.status}")
        return resp.read().decode("windows-1252", errors="ignore")


def main():
    logging.info("=" * 50)
    logging.info("INÍCIO DA EXECUÇÃO DO SCRIPT EXTRACTOR")
    logging.info("=" * 50)

    if len(sys.argv) > 1:
        logging.info(f"Modo arquivo local ativado. Lendo: {sys.argv[1]}")
        with open(sys.argv[1], encoding="windows-1252", errors="ignore") as f:
            html = f.read()
    else:
        try:
            html = download()
        except Exception as e:
            logging.error(f"Erro crítico ao baixar a página do Planalto: {e}", exc_info=True)
            return

    if not html.strip():
        logging.error("O conteúdo HTML obtido está vazio.")
        return

    logging.info(f"Tamanho do HTML obtido: {len(html)} caracteres.")
    chunks = parse_html(html)

    logging.info(f"Gravando o resultado no arquivo JSON de saída: {OUTPUT_FILE}")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    n_art = len({(c["part"], c["article"]) for c in chunks})
    logging.info(f"Processo finalizado com sucesso! {len(chunks)} chunks de {n_art} artigos salvos.")
    logging.info(f"Log detalhado salvo com sucesso em: {LOG_FILE}")
    logging.info("=" * 50)


if __name__ == "__main__":
    main()