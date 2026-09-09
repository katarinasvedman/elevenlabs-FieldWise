"""Azure Functions (Python v2 model) HTTP entry point for the ElevenLabs webhook tool
'search_knowledge_base'. ElevenLabs can't call the Azure AI Search SDK directly (it's a
hosted service that only speaks HTTP), so this is the small bridge: receive the technician's
query over HTTP, run it through the SDK in search_client.py, hand back clean JSON to speak.
"""

import json
import logging

import azure.functions as func

from search_client import lookup

app = func.FunctionApp()


@app.route(route="search-lookup", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
def search_lookup(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
    except ValueError:
        body = {}

    query = (body.get("query") or "").strip()
    if not query:
        return func.HttpResponse(
            json.dumps({"error": "missing 'query'"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        result = lookup(query)
    except Exception:
        logging.exception("search-lookup failed for query=%r", query)
        return func.HttpResponse(
            json.dumps({"error": "lookup_failed"}),
            status_code=500,
            mimetype="application/json",
        )

    return func.HttpResponse(json.dumps(result), status_code=200, mimetype="application/json")
