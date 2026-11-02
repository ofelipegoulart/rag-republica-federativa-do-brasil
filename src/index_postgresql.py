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
model = SentenceTransformer("tardellirs/colibri-embed-ptbr")


def config_database(cursor):
    """Habilita a extensão pgvector e cria a tabela de chunks atualizada se não existir"""
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # Opcional: Se quiser recriar a tabela do zero para limpar dados antigos, descomente a linha abaixo:
    cursor.execute("DROP TABLE IF EXISTS articles_constitution;")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles_constitution (
            id SERIAL PRIMARY KEY,
            article VARCHAR(50),
            label VARCHAR(150),
            part VARCHAR(20),
            category VARCHAR(100),
            text TEXT,
            embedding vector(768)
        );
    """)
    print("Banco configurado com sucesso (extensão vector ativa e tabela criada).")


def process_and_ingest():
    # Carregar o JSON gerado pelo extrator
    try:
        with open("../artigos_filtrados_constituicao.json", "r", encoding="utf-8") as f:
            chunks = json.load(f)
    except FileNotFoundError:
        print(
            "[ERRO]: Arquivo 'artigos_filtrados_constituicao.json' não encontrado."
            " Rode o script extrator primeiro!"
        )
        return

    print(f"Conectando ao PostgreSQL...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cursor = conn.cursor()

    config_database(cursor)

    print(f"Gerando embeddings e inserindo {len(chunks)} chunks no Postgres...")

    for item in chunks:
        article_number = item["article"]
        label = item["label"]
        part = item["part"]
        category = item["category"]
        text = item["text"]

        # Gera o vetor de embedding (384 dimensões para o all-MiniLM-L6-v2)
        vector = model.encode(text).tolist()

        # Inserir no PostgreSQL com os novos campos
        cursor.execute(
            """
                INSERT INTO articles_constitution (article, label, part, category, text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (article_number, label, part, category, text, vector),
        )

    cursor.close()
    conn.close()
    print(
        "Ingestão concluída! Todos os chunks foram vetorizados e salvos no"
        " PostgreSQL com sucesso."
    )


if __name__ == "__main__":
    process_and_ingest()