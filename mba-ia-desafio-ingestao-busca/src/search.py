import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_postgres import PGVector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
COLLECTION_NAME = os.getenv("PG_VECTOR_COLLECTION_NAME", "document_collection")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
K = 10

PROMPT_TEMPLATE = """
CONTEXTO:
{contexto}

REGRAS:
- Responda somente com base no CONTEXTO.
- Se a informação não estiver explicitamente no CONTEXTO, responda:
  "Não tenho informações necessárias para responder sua pergunta."
- Nunca invente ou use conhecimento externo.
- Nunca produza opiniões ou interpretações além do que está escrito.

EXEMPLOS DE PERGUNTAS FORA DO CONTEXTO:
Pergunta: "Qual é a capital da França?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Quantos clientes temos em 2024?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

Pergunta: "Você acha isso bom ou ruim?"
Resposta: "Não tenho informações necessárias para responder sua pergunta."

PERGUNTA DO USUÁRIO:
{pergunta}

RESPONDA A "PERGUNTA DO USUÁRIO"
"""

_vector_store = None


def _criar_vector_store() -> PGVector:
    """Cria (uma única vez) a conexão com a collection no PostgreSQL/pgVector."""
    global _vector_store
    if _vector_store is None:
        _vector_store = PGVector(
            embeddings=OpenAIEmbeddings(model=EMBEDDING_MODEL),
            collection_name=COLLECTION_NAME,
            connection=DATABASE_URL,
            use_jsonb=True,
        )
    return _vector_store


def buscar(pergunta: str, k: int = K):
    """Vetoriza a pergunta e retorna os k trechos mais relevantes, com score."""
    return _criar_vector_store().similarity_search_with_score(pergunta, k=k)


def _buscar_documentos(pergunta: str):
    return [documento for documento, _score in buscar(pergunta)]


def _formatar_contexto(documentos) -> str:
    return "\n\n".join(documento.page_content for documento in documentos)


def search_prompt(question: str | None = None) -> Any:
    """Monta a chain de busca + resposta.

    - Sem `question`: retorna a chain (para o chat.py usar com .invoke()).
    - Com `question`: retorna a resposta pontual (útil para testar).
    - Retorna None se a configuração inicial falhar (ex.: API key ausente).
    """
    try:
        _criar_vector_store()  # valida a configuração já na inicialização
        prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        llm = ChatOpenAI(model=CHAT_MODEL, temperature=0)

        chain = (
            {
                "contexto": RunnableLambda(_buscar_documentos) | _formatar_contexto,
                "pergunta": RunnablePassthrough(),
            }
            | prompt
            | llm
            | StrOutputParser()
        )
    except Exception as erro:
        print(f"Não foi possível inicializar a busca: {erro}")
        return None

    if question is not None:
        return chain.invoke(question)
    return chain


if __name__ == "__main__":
    import sys

    pergunta = " ".join(sys.argv[1:]).strip() or input("PERGUNTA: ").strip()
    resultados = buscar(pergunta)

    print(f"\nTop {len(resultados)} trechos mais relevantes para: {pergunta}\n")
    for indice, (documento, score) in enumerate(resultados, start=1):
        pagina = documento.metadata.get("page")
        previa = documento.page_content[:120].replace("\n", " ")
        print(f"[{indice}] página={pagina} score={score:.4f} :: {previa}")
