import os
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SearchField, SearchFieldDataType,
    SimpleField, SearchableField, VectorSearch,
    HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticConfiguration, SemanticSearch,
    SemanticPrioritizedFields, SemanticField
)
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv

load_dotenv()

client = SearchIndexClient(
    endpoint=os.getenv("SEARCH_ENDPOINT"),
    credential=AzureKeyCredential(os.getenv("SEARCH_KEY"))
)

fields = [
    SimpleField(name="chunk_id", type=SearchFieldDataType.String, key=True),
    SimpleField(name="source_doc", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="section", type=SearchFieldDataType.String, filterable=True),
    SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
    SearchableField(name="content", type=SearchFieldDataType.String),
    SearchField(
        name="embedding",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
        searchable=True,
        vector_search_dimensions=1536,
        vector_search_profile_name="hnsw-profile"
    )
]

vector_search = VectorSearch(
    algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
    profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw")]
)

semantic_config = SemanticConfiguration(
    name="semantic-config",
    prioritized_fields=SemanticPrioritizedFields(
        content_fields=[SemanticField(field_name="content")]
    )
)

index = SearchIndex(
    name="earnings-transcripts",
    fields=fields,
    vector_search=vector_search,
    semantic_search=SemanticSearch(configurations=[semantic_config])
)

client.create_or_update_index(index)
print("Index created successfully.")
