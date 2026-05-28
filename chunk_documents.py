import os
import json
import re
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

load_dotenv()

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("BLOB_CONNECTION_STRING")
)

def split_into_sections(text):
    # remove page break markers — they don't carry semantic meaning
    text = text.replace("<!-- PageBreak -->", "")
    # prepend newline so a document starting with a heading is caught by the split
    text = "\n" + text
    # split on #, ##, ### headings
    parts = re.split(r'\n(#{1,3} )', text)

    sections = []
    i = 1
    # parts[0] is always preamble (content before the first heading, often empty)
    # add it only if it has actual text, then always start the loop at i=1
    if parts and parts[0].strip():
        sections.append(("", parts[0]))
    while i < len(parts) - 1:
        heading_marker = parts[i]       # e.g. "# " or "## "
        content = parts[i + 1]          # everything until next heading
        lines = content.split("\n", 1)
        heading_text = lines[0].strip()
        body = lines[1] if len(lines) > 1 else ""
        sections.append((f"{heading_marker.strip()} {heading_text}", body))
        i += 2

    return sections

def chunk_markdown(text, source_doc, max_tokens=500):
    chunks = []
    sections = split_into_sections(text)

    for i, (heading, body) in enumerate(sections):
        heading = heading.strip("#").strip() or f"Section {i}"
        body = body.strip()
        if not body:
            continue

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
