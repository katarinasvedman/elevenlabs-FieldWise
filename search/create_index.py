"""
Create (or update) the FieldWise Azure AI Search index and upload the seed content.

Run once against your own Azure AI Search resource:

    pip install -r ../function/requirements.txt   # azure-search-documents lives there too
    export AZURE_SEARCH_ENDPOINT="https://<your-service>.search.windows.net"
    export AZURE_SEARCH_API_KEY="<admin-key>"      # admin key needed to create the index
    export AZURE_SEARCH_INDEX="fieldpilot-knowledge"  # optional, this is the default
    python create_index.py

Reads index_schema.json for the field definitions and seed_data.json for the documents,
so both files stay the single source of truth (no fields/content duplicated here).
"""

import json
import os
import sys
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SearchField, SearchFieldDataType

HERE = Path(__file__).parent

# index_schema.json uses plain "Edm.String" — map straight through, this project only uses strings.
_TYPE_MAP = {
    "Edm.String": SearchFieldDataType.String,
}


def _load_field(spec: dict) -> SearchField:
    return SearchField(
        name=spec["name"],
        type=_TYPE_MAP[spec["type"]],
        key=spec.get("key", False),
        searchable=spec.get("searchable", False),
        filterable=spec.get("filterable", False),
        facetable=spec.get("facetable", False),
    )


def main() -> None:
    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    api_key = os.environ.get("AZURE_SEARCH_API_KEY")
    index_name = os.environ.get("AZURE_SEARCH_INDEX", "fieldpilot-knowledge")

    if not endpoint or not api_key:
        print("Set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_API_KEY before running.", file=sys.stderr)
        sys.exit(1)

    schema = json.loads((HERE / "index_schema.json").read_text(encoding="utf-8"))
    seed_docs = json.loads((HERE / "seed_data.json").read_text(encoding="utf-8"))

    credential = AzureKeyCredential(api_key)
    index_client = SearchIndexClient(endpoint=endpoint, credential=credential)

    fields = [_load_field(f) for f in schema["fields"]]
    index = SearchIndex(name=index_name, fields=fields)
    index_client.create_or_update_index(index)
    print(f"Index '{index_name}' created/updated with {len(fields)} fields.")

    search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
    result = search_client.upload_documents(documents=seed_docs)
    failed = [r for r in result if not r.succeeded]
    print(f"Uploaded {len(result) - len(failed)}/{len(seed_docs)} documents.")
    if failed:
        for r in failed:
            print(f"  FAILED: {r.key} — {r.error_message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
