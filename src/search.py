import json
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

# 1. Usar o mesmo modelo exato da ingestão (all-MiniLM-L6-v2)
print("Carregando modelo de embeddings...")
model = SentenceTransformer("tardellirs/colibri-embed-ptbr")

# 2. Definir a pergunta de teste do usuário
question = "Qual artigo fala de quem é responsável pelo saneamento básico?"
vector_question = model.encode(question).tolist()

# 3. Conectar e buscar no banco usando a distância do cosseno (<=>)
print("Conectando ao PostgreSQL e realizando a busca semântica...")
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Busca os 3 chunks mais próximos semanticamente da pergunta, trazendo também o label e a parte (CF/ADCT)
cursor.execute(
    """
    SELECT article, label, part, category, text, 1 - (embedding <=> %s::vector) AS similarity
    FROM articles_constitution
    ORDER BY embedding <=> %s::vector
    LIMIT 3;
""",
    (vector_question, vector_question),
)

results = cursor.fetchall()

print(f"\nPergunta de teste: '{question}'\n" + "=" * 50)
for row in results:
    article, label, part, category, text, similarity = row
    print(f"Artigo: {article} | Rótulo: {label} ({part})")
    print(f"Categoria: {category} | Similaridade: {similarity:.4f}")
    print(f"Texto: {text}\n" + "-" * 50)

cursor.close()
conn.close()