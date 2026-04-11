import os
import json
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI
from dotenv import load_dotenv
import time

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

with open("chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model=os.getenv("OPENAI_EMBEDDING_DEPLOYMENT")
    )
    return response.data[0].embedding

# upload in batches of 10
batch_size = 10
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i + batch_size]
    docs = []
    for chunk in batch:
        embedding = get_embedding(chunk["content"])
        docs.append({
            "chunk_id": chunk["chunk_id"],
            "source_doc": chunk["source_doc"],
            "section": chunk["section"],
            "chunk_index": chunk["chunk_index"],
            "content": chunk["content"],
            "embedding": embedding
        })
        time.sleep(0.1)  # small delay to avoid rate limits

    search_client.upload_documents(documents=docs)
    print(f"Uploaded batch {i//batch_size + 1} — chunks {i} to {i+len(batch)}")

print(f"\nAll {len(chunks)} chunks indexed.")
