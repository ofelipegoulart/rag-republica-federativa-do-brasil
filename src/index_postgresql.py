import json
import psycopg2
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

# Carrega as variáveis declaradas no arquivo .env para o ambiente
load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}


# 2. Carregar o modelo de embeddings local
print("Carregando modelo de embeddings...")
model = SentenceTransformer("all-MiniLM-L6-v2")


def config_database(cursor):
  """Habilita a extensão pgvector e cria a tabela de artigos se não existir"""
  cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles_constitution (
            id SERIAL PRIMARY KEY,
            article VARCHAR(50),
            category VARCHAR(100),
            text TEXT,
            embedding vector(384)
        );
    """)
  print("Banco configurado com sucesso (extensão vector ativa e tabela criada).")


def process_and_ingest():
  # Carregar o JSON gerado anteriormente
  try:
    with open("../artigos_filtrados_constituicao.json", "r", encoding="utf-8") as f:
      articles = json.load(f)
  except FileNotFoundError:
    print(
        "[ERRO]: Arquivo 'artigos_filtrados_constituicao.json' não encontrado."
        " Rode o script anterior primeiro!"
    )
    return

  print(f"Conectando ao PostgreSQL...")
  conn = psycopg2.connect(**DB_CONFIG)
  conn.autocommit = True
  cursor = conn.cursor()

  config_database(cursor)

  print(f"Gerando embeddings e inserindo {len(articles)} articles no Postgres...")

  for item in articles:
    article_number = item["article"]
    category = item["category"]
    text = item["text"]

    # Estratégia de Chunking: Para articles grandes, podemos fracionar se necessário,
    # mas como os articles filtrados já são focados, o text completo do artigo é o chunk ideal.
    # Se o text for muito longo, geramos o embedding dele inteiro.
    vector = model.encode(text).tolist()

    # Inserir no PostgreSQL
    cursor.execute(
        """
            INSERT INTO articles_constitution (article, category, text, embedding)
            VALUES (%s, %s, %s, %s)
        """,
        (article_number, category, text, vector),
    )

  cursor.close()
  conn.close()
  print(
      "Ingestão concluída! Todos os articles foram vetorizados e salvos no"
      " PostgreSQL."
  )


if __name__ == "__main__":
  process_and_ingest()