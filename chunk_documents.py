import os
import json
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("BLOB_CONNECTION_STRING")
)

def chunk_markdown(text, source_doc, max_tokens=500):
    chunks = []
    # split on ## headings — natural section boundaries in earnings transcripts
    sections = text.split("\n## ")

    for i, section in enumerate(sections):
        if not section.strip():
            continue

        # extract section heading if present
        lines = section.strip().split("\n")
        heading = lines[0].strip("#").strip() if lines else f"Section {i}"
        body = "\n".join(lines[1:]).strip()

        # if section is short enough, keep as one chunk
        words = body.split()
        if len(words) <= max_tokens:
            if body:
                chunks.append({
                    "chunk_id": f"{source_doc}_s{i}",
                    "source_doc": source_doc,
                    "section": heading,
                    "content": f"{heading}\n{body}",
                    "chunk_index": len(chunks)
                })
        else:
            # split long sections into smaller chunks with overlap
            overlap = 50  # words of overlap between chunks
            step = max_tokens - overlap
            for j in range(0, len(words), step):
                chunk_words = words[j:j + max_tokens]
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "chunk_id": f"{source_doc}_s{i}_c{j}",
                    "source_doc": source_doc,
                    "section": heading,
                    "content": f"{heading}\n{chunk_text}",
                    "chunk_index": len(chunks)
                })

    return chunks

# process all markdown files from extracted container
container = blob_client.get_container_client("extracted")
all_chunks = []

for blob in container.list_blobs():
    print(f"Chunking: {blob.name}")
    content = container.get_blob_client(blob.name).download_blob().readall().decode("utf-8")
    doc_name = blob.name.replace(".md", "")
    chunks = chunk_markdown(content, doc_name)
    all_chunks.extend(chunks)
    print(f"  → {len(chunks)} chunks")

print(f"\nTotal chunks: {len(all_chunks)}")

# save chunks locally as JSON for inspection before indexing
with open("chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, indent=2, ensure_ascii=False)

print("Saved to chunks.json — review before indexing.")
