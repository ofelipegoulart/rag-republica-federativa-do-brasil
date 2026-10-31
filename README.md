# 🏛️ App Cívico: Quem Faz O Quê?

Um aplicativo cívico educacional de código aberto desenvolvido para empoderar o cidadão brasileiro, esclarecendo de forma simples e direta **qual ente federativo (União, Estados, Distrito Federal ou Municípios)** é o verdadeiro responsável por cada área da gestão pública (saúde, educação, segurança, infraestrutura, entre outras).

---

## 🎯 O Problema & A Solução

Muitas vezes, a população cobra o prefeito por problemas estaduais ou federais (e vice-versa), gerando desinformação e enfraquecendo o controle social. 

O **App Cívico** resolve isso utilizando inteligência artificial e arquitetura **RAG (Retrieval-Augmented Generation)** baseada diretamente na **Constituição Federal de 1988**, permitindo que qualquer cidadão tire dúvidas de forma natural e receba respostas fundamentadas na lei.

---

## 🛠️ Stack Tecnológica

O projeto foi construído combinando engenharia de dados jurídicos e desenvolvimento backend/banco de dados moderno:

* **Python:** Scripts de extração de dados, limpeza HTML e pipeline de ingestão.
* **BeautifulSoup:** Web scraping estruturado da Constituição Federal direto do site do Planalto.
* **PostgreSQL + pgvector:** Armazenamento relacional unificado com buscas vetoriais (similaridade de cosseno) para recuperação semântica de artigos.
* **Sentence-Transformers:** Geração de embeddings otimizados para língua portuguesa (`all-MiniLM-L6-v2`).

---

## 📂 Arquitetura da Base de Dados (RAG)

O sistema filtra e vetoriza seções estratégicas da Constituição Federal focadas em organização do Estado, competências e direitos fundamentais:

1. **Competências Federativas:** Artigos 21, 22, 23, 24, 25, 30 e 32 (Competências exclusivas, comuns, concorrentes, dos Estados e Municípios).
2. **Segurança Pública:** Artigo 144 (Responsabilidades das polícias federais, civis, militares e penais).
3. **Saúde e Seguridade Social:** Artigos 194 a 204 (Sistema Único de Saúde - SUS e seguridade).
4. **Educação:** Artigos 205 a 214 (Deveres do Estado, diretrizes e repasses de ensino).
5. **Organização dos Poderes:** Poder Judiciário (STF, STJ, Justiças Estaduais/Federais) e Poder Legislativo Estadual (Assembleias Legislativas).

---

## 🚀 Como Executar o Projeto

### 1. Pré-requisitos
* Python 3.10+ instalado.
* PostgreSQL instalado com a extensão `pgvector` habilitada.

### 2. Instalação das Dependências
Clone o repositório e instale os pacotes necessários:
```bash
pip install requests beautifulsoup4 psycopg2-binary sentence-transformers