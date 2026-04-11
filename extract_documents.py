import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
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

# create output container if it doesn't exist
#blob_client.create_container(output_container)

# loop through every PDF in the source container
container = blob_client.get_container_client(source_container)

for blob in container.list_blobs():
    print(f"Processing: {blob.name}")

    # download the PDF as bytes
    blob_data = container.get_blob_client(blob.name).download_blob().readall()

    # send to Document Intelligence — Layout model, Markdown output



    # send to Document Intelligence — Layout model, Markdown output
    poller = doc_client.begin_analyze_document(
        "prebuilt-layout",
        body=blob_data,
        content_type="application/pdf",
        output_content_format="markdown"
    )

    result = poller.result()

    print(len(result.pages))
    # save the Markdown to the output container
    output_name = blob.name.replace(".pdf", ".md")

    blob_client.get_blob_client(
        container=output_container,
        blob=output_name
    ).upload_blob(result.content, overwrite=True)

    print(f"Saved: {output_name} ({len(result.content)} characters)")

print("All done.")
