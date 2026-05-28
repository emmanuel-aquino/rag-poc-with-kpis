import os
import time
import pyodbc
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

search_client = SearchClient(
    endpoint=os.getenv("SEARCH_ENDPOINT"),
    index_name="earnings-transcripts",
    credential=AzureKeyCredential(os.getenv("SEARCH_KEY"))
)

openai_client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
    api_key=os.getenv("OPENAI_KEY"),
    api_version="2024-02-01"
)

SYSTEM_PROMPT = """You are a financial analyst assistant. Answer questions using
ONLY the context provided from earnings call transcripts.

Rules:
- Always cite which document and section your answer comes from
- If the context does not contain enough information, say so clearly
- Be concise and specific — this is for financial analysis
- When mentioning numbers, always include the time period they refer to
- The user might ask questions about financial information withouth specifying the period. In that case, look for the most recent relevant information in the context and use it, but be sure to mention the time period in your answer.
- The question might or might not include the company name so use the context to determine which company
     the question is about and include the company name in your answer when relevant.
     If the company name is not mentioned in the question, specifically request this information from the user.
     Only retrieve chunks from the company mentioned in the question, if any. If the question does not specify a company, 
     you can retrieve chunks from multiple companies but make sure to mention the company name in your answer when relevant.
"""

def get_db_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        "Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_str)

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=os.getenv("OPENAI_EMBEDDING_DEPLOYMENT")
    )
    return response.data[0].embedding

def retrieve_chunks(question, top_k=5):
    # embed the question
    question_embedding = get_embedding(question)

    # hybrid search — vector + keyword combined
    vector_query = VectorizedQuery(
        vector=question_embedding,
        k_nearest_neighbors=top_k,
        fields="embedding"
    )

    results = search_client.search(
        search_text=question,          # keyword search
        vector_queries=[vector_query], # vector search
        query_type="semantic",
        semantic_configuration_name="semantic-config",
        top=top_k,
        select="chunk_id, source_doc, section, content"
    )

    chunks = []
    for r in results:
        chunks.append({
            "chunk_id": r["chunk_id"],
            "source_doc": r["source_doc"],
            "section": r["section"],
            "content": r["content"],
            "score": r["@search.score"]
        })
    return chunks

def build_prompt(question, chunks):
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"\n--- Source {i+1} [doc: {chunk['source_doc']} | section: {chunk['section']} | chunk_id: {chunk['chunk_id']}] ---\n"
        context += chunk["content"] + "\n"

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"""Context from earnings transcripts:
{context}

Question: {question}

Answer based only on the context above. Cite your sources."""}
    ]

def ask(question):
    start = time.time()

    # retrieve relevant chunks
    chunks = retrieve_chunks(question)

    # build prompt and call LLM
    messages = build_prompt(question, chunks)
    response = openai_client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_DEPLOYMENT"),
        messages=messages,
        temperature=0.1,   # low temperature = more factual, less creative
        max_tokens=500
    )

    latency_ms = int((time.time() - start) * 1000)
    answer = response.choices[0].message.content
    source_docs = list(set([c["source_doc"] for c in chunks]))

    # log to SQL
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO query_log
                (question, answer, source_docs, retrieved_chunks, latency_ms)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?)
        """, question, answer, ", ".join(source_docs), len(chunks), latency_ms)

        query_id = cursor.fetchone()[0]

        for chunk in chunks:
            cursor.execute("""
                INSERT INTO retrieval_log
                    (query_id, chunk_id, source_doc, section, relevance_score)
                VALUES (?, ?, ?, ?, ?)
            """, query_id, chunk["chunk_id"], chunk["source_doc"],
                chunk["section"], chunk["score"])

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Warning: failed to log to SQL — {e}")
        # don't crash the RAG pipeline if logging fails

    return {
        "question": question,
        "answer": answer,
        "chunks": chunks,
        "source_docs": source_docs,
        "retrieved_chunks": len(chunks),
        "latency_ms": latency_ms
    }
