import psycopg2
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "postgres"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432"),
}

# 1. Carregar o mesmo modelo usado na ingestão
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# 2. Definir a pergunta de teste do usuário
question = "Qual artigo fala de quem é responsável pelo saneamento básico?"
vector_question = model.encode(question).tolist()

# 3. Conectar e buscar no banco usando a distância do cosseno (<=>)
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Busca os 3 artigos mais próximos semanticamente da pergunta
cursor.execute(
    """
    SELECT article, category, text, 1 - (embedding <=> %s::vector) AS similarity
    FROM articles_constitution
    ORDER BY embedding <=> %s::vector
    LIMIT 3;
""",
    (vector_question, vector_question),
)

results = cursor.fetchall()

print(f"\n🔍 Pergunta de teste: '{question}'\n" + "=" * 50)
for row in results:
  article, category, text, similarity = row
  print(f"Artigo: {article} | Categoria: {category} (Similaridade: {similarity:.4f})")
  print(f"Texto: {text[:150]}...\n" + "-" * 50)

cursor.close()
conn.close()