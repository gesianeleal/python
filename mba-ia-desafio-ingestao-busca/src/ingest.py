import os

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

PDF_PATH = os.getenv("PDF_PATH", "document.pdf")
DATABASE_URL = os.getenv("DATABASE_URL")
COLLECTION_NAME = os.getenv("PG_VECTOR_COLLECTION_NAME", "document_collection")
EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def ingest_pdf():
    documentos = PyPDFLoader(PDF_PATH).load()
    print(f"Páginas carregadas: {len(documentos)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documentos)
    print(f"Chunks gerados: {len(chunks)}")

    embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
    vector_store = PGVector(
        embeddings=embeddings,
        collection_name=COLLECTION_NAME,
        connection=DATABASE_URL,
        use_jsonb=True,
    )

    ids = vector_store.add_documents(chunks)
    print(f"Vetores armazenados: {len(ids)}")
    print(f"Collection: {COLLECTION_NAME}")
    print("Ingestão concluída.")


if __name__ == "__main__":
    ingest_pdf()
