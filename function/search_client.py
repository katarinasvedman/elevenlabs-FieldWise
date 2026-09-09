"""Thin wrapper around the Azure AI Search SDK — this is the "SDK internally, not raw REST"
piece the brief calls for. Everything the HTTP function needs from Azure AI Search lives here.
"""

import os
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

_INDEX_NAME = os.environ.get("AZURE_SEARCH_INDEX", "fieldpilot-knowledge")


def _get_client() -> SearchClient:
    endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
    api_key = os.environ["AZURE_SEARCH_API_KEY"]
    return SearchClient(endpoint=endpoint, index_name=_INDEX_NAME, credential=AzureKeyCredential(api_key))


def lookup(query: str) -> dict[str, Any]:
    """Query the FieldWise knowledge index and shape a clean, speakable response.

    If the best-matching row belongs to a multi-cause group (e.g. the 3 alarm-402 causes,
    see search/seed_data.json), every candidate in that group is returned together with its
    distinguishing_condition. The agent asks ONE clarifying question and resolves from this
    same response — no second search call needed for the follow-up turn.
    """
    client = _get_client()
    results = list(client.search(search_text=query, top=5))

    if not results:
        return {"found": False, "answer": None, "needs_clarification": False, "candidates": []}

    top = results[0]
    group_id = top.get("group_id") or ""

    if group_id:
        group_results = list(client.search(search_text="*", filter=f"group_id eq '{group_id}'", top=10))
        candidates = [
            {
                "label": r["title"],
                "detail": r["content"],
                "distinguishing_condition": r["distinguishing_condition"],
            }
            for r in group_results
        ]
        return {"found": True, "answer": None, "needs_clarification": True, "candidates": candidates}

    return {"found": True, "answer": top["content"], "needs_clarification": False, "candidates": []}
