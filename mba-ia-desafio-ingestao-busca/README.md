# Ingestão e Busca Semântica com LangChain e Postgres

Desafio técnico do **MBA em Engenharia de Software com IA (Full Cycle)**: ingestão de um arquivo PDF em um banco vetorial (PostgreSQL + pgVector) e chat via linha de comando que responde perguntas com base **apenas** no conteúdo do PDF.

## Arquitetura

- **Ingestão** (`src/ingest.py`): carrega o PDF, divide o texto em chunks de 1000 caracteres com overlap de 150, gera os embeddings de cada chunk e grava os vetores no PostgreSQL (extensão pgVector).
- **Busca** (`src/search.py`): vetoriza a pergunta, recupera os 10 trechos mais relevantes (`k=10`) via `similarity_search_with_score` e monta o prompt com as regras de resposta.
- **Chat** (`src/chat.py`): CLI que recebe perguntas e devolve respostas geradas pela LLM com base somente no contexto recuperado do PDF. Quando a resposta não está no contexto, retorna: `Não tenho informações necessárias para responder sua pergunta.`

## Tecnologias

- Python 3.11
- LangChain (`langchain`, `langchain-openai`, `langchain-postgres`, `langchain-text-splitters`, `langchain-community`)
- PostgreSQL + pgVector (Docker Compose)
- OpenAI: embeddings `text-embedding-3-small` e chat `gpt-4o-mini`

## Estrutura do projeto

```
├── docker-compose.yml      # PostgreSQL + pgVector
├── requirements.txt        # Dependências
├── .env.example            # Template das variáveis de ambiente
├── src/
│   ├── ingest.py           # Ingestão do PDF
│   ├── search.py           # Busca semântica (top-k) e chain de resposta
│   └── chat.py             # CLI de interação com o usuário
├── document.pdf            # PDF ingerido
└── README.md
```

## Pré-requisitos

- Docker com daemon rodando (ex.: `colima start`, ou Docker Desktop)
- Python 3.11+
- API Key da OpenAI (https://platform.openai.com/api-keys)

## Configuração

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edite e preencha OPENAI_API_KEY
```

## Execução

Na raiz do projeto, com o venv ativo:

1. Subir o banco de dados:
   ```bash
   docker compose up -d
   ```
2. Executar a ingestão do PDF:
   ```bash
   python src/ingest.py
   ```
3. Rodar o chat:
   ```bash
   python src/chat.py
   ```

## Exemplo de uso

```
PERGUNTA: Qual o faturamento da Empresa SuperTechIABrazil?
RESPOSTA: O faturamento foi de 10 milhões de reais.

---

PERGUNTA: Quantos clientes temos em 2024?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

## Refazendo a ingestão

A tabela de vetores é criada na primeira ingestão já com a dimensão do modelo de embeddings. Reingestões adicionam registros duplicados e a troca do modelo de embeddings causa erro de dimensão. Para recomeçar do zero:

```bash
docker compose down -v   # remove o volume do banco
docker compose up -d
python src/ingest.py
```

## Decisões técnicas

- Chunks de 1000/150 e busca com `k=10`, conforme especificado no desafio.
- `temperature=0` na LLM para maximizar aderência ao contexto.
- Embeddings `text-embedding-3-small` (1536 dimensões) e LLM `gpt-4o-mini`: modelos leves e baratos, suficientes para o volume do desafio.
- `DATABASE_URL` no formato `postgresql+psycopg://` (driver psycopg 3), exigido pelo `langchain-postgres`.

## Solução de problemas

- **`CERTIFICATE_VERIFY_FAILED` (redes corporativas com inspeção TLS)**: se a rede faz inspeção de SSL (proxy corporativo com CA própria), aponte no `.env` o `SSL_CERT_FILE` para um bundle PEM que contenha a CA da organização (mesclada ao bundle do `certifi`, se necessário).
- **Porta 5432 ocupada**: ajuste o mapeamento no `docker-compose.yml` (ex.: `"5433:5432"`) e o `DATABASE_URL` no `.env` de acordo.
- **Recomeçar do zero**: `docker compose down -v && docker compose up -d` apaga o volume e recria o banco.
