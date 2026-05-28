import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv

load_dotenv()

doc_client = DocumentIntelligenceClient(
    endpoint=os.getenv("DOCINT_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("DOCINT_KEY"))
)

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("BLOB_CONNECTION_STRING")
)

source_container = "transcripts"
output_container = "extracted"
archive_container = "archived"

source = blob_client.get_container_client(source_container)
extracted = blob_client.get_container_client(output_container)
archive = blob_client.get_container_client(archive_container)

skipped = 0
processed = 0
errors = 0

for blob in source.list_blobs():
    pdf_name = blob.name
    md_name = pdf_name.replace(".pdf", ".md")

    # check if markdown already exists in extracted container
    md_blob = extracted.get_blob_client(md_name)
    already_extracted = False
    try:
        md_blob.get_blob_properties()
        already_extracted = True
    except ResourceNotFoundError:
        already_extracted = False

    if already_extracted:
        print(f"Skipping (already extracted): {pdf_name}")
        # move PDF to archive
        source_url = source.get_blob_client(pdf_name).url
        archive.get_blob_client(pdf_name).start_copy_from_url(source_url)
        source.get_blob_client(pdf_name).delete_blob()
        print(f"  → Archived: {pdf_name}")
        skipped += 1
        continue

    # not yet extracted — process it
    print(f"Processing: {pdf_name}")
    try:
        blob_data = source.get_blob_client(pdf_name).download_blob().readall()

        poller = doc_client.begin_analyze_document(
            "prebuilt-layout",
            body=blob_data,
            content_type="application/pdf",
            output_content_format="markdown"
        )
        result = poller.result()

        # upload markdown to extracted container
        extracted.get_blob_client(md_name).upload_blob(result.content, overwrite=True)
        print(f"  → Extracted: {md_name} ({len(result.content)} characters, {len(result.pages)} pages)")

        # move PDF to archive on success
        source_url = source.get_blob_client(pdf_name).url
        archive.get_blob_client(pdf_name).start_copy_from_url(source_url)
        source.get_blob_client(pdf_name).delete_blob()
        print(f"  → Archived: {pdf_name}")

        processed += 1

    except Exception as e:
        print(f"  ERROR processing {pdf_name}: {e}")
        errors += 1
        # leave the PDF in transcripts so it can be retried

print(f"\nDone. Processed: {processed} | Skipped: {skipped} | Errors: {errors}")
