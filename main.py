import json
import re
from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

URL = (
    "https://www.planalto.gov.br/ccivil_03/constituicao/constituicaocompilado.htm"
)


def set_target_articles():
  allowed_articles = set()
  allowed_articles.update([21, 22, 23, 24, 25, 27, 30, 32, 144])
  allowed_articles.update(range(194, 205))
  allowed_articles.update(range(205, 215))
  allowed_articles.update(range(92, 127))
  return allowed_articles


def classifier_category(art_num):
  if art_num in [21, 22, 23, 24, 25, 30, 32]:
    return "Competências e Entes Federativos"
  elif art_num == 144:
    return "Segurança Pública"
  elif 194 <= art_num <= 204:
    return "Saúde e Seguridade Social"
  elif 205 <= art_num <= 214:
    return "Educação"
  elif art_num == 27:
    return "Poder Legislativo Estadual (Assembleias)"
  elif 92 <= art_num <= 126:
    return "Poder Judiciário (STF, STJ e Tribunais)"
  return "Geral"


def parse_and_filter():
  print("Baixando a Constituição Federal (ignorando cache)...")

  # Cabeçalhos para simular navegador E forçar o servidor a enviar o conteúdo fresco (evita o 304)
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
      ),
      "Cache-Control": "no-cache",
      "Pragma": "no-cache",
  }

  req = Request(URL, headers=headers)

  try:
    with urlopen(req, timeout=20) as response:
      print(f"Status HTTP recebido: {response.status}")
      html_bytes = response.read()
      html_content = html_bytes.decode("windows-1252", errors="ignore")
  except Exception as e:
    print(f"\n[ERRO]: Falha ao baixar a página: {e}")
    return

  if not html_content.strip():
    print("[ERRO]: O conteúdo HTML retornado está vazio.")
    return

  print("Download concluído com sucesso! Processando os artigos...")
  soup = BeautifulSoup(html_content, "html.parser")
  full_text = soup.get_text()

  pattern = re.compile(
      r"(Art\.?\s*(\d+)[º°]?[^\n]*)(.*?)(?=(Art\.?\s*\d+[º°]?|$))", re.DOTALL
  )

  matches = pattern.findall(full_text)
  target_articles = set_target_articles()
  data_rag = []

  for match in matches:
    header = match[0].strip()
    num_str = match[1]
    content = match[2].strip()

    if num_str.isdigit():
      num_art = int(num_str)
      if num_art in target_articles:
        cleaned_content = " ".join(content.split())
        full_article_text = f"{header} {cleaned_content}"

        data_rag.append({
            "artigo": f"Art. {num_art}",
            "categoria": classifier_category(num_art),
            "texto": full_article_text,
        })

  filename = "artigos_filtrados_constituicao.json"
  with open(filename, "w", encoding="utf-8") as f:
    json.dump(data_rag, f, ensure_ascii=False, indent=4)

  print(
      f"Sucesso! {len(data_rag)} artigos filtrados foram salvos em"
      f" '{filename}'."
  )


if __name__ == "__main__":
  parse_and_filter()