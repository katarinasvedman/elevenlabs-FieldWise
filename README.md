# FieldWise

Hands-free voice assistant for CNC machinists, built on ElevenLabs Conversational AI. See
[docs/fieldpilot-brief.md](docs/fieldpilot-brief.md) for the full scenario.

All the code/config in this repo is ready to use. The steps below are the account-level setup
only you can do (they need your own Azure subscription, Slack workspace, and ElevenLabs
login). `az`/`func` CLIs aren't installed in this environment — install them locally, or use
the Azure Portal fallback noted at each step.

## 1. Azure AI Search — resource + index
```bash
# CLI (needs az login first)
az search service create \
  --name <your-search-service> \
  --resource-group <your-rg> \
  --sku free \
  --location <your-region>

# grab the admin key
az search admin-key show --resource-group <your-rg> --service-name <your-search-service>
```
Portal fallback: Azure Portal → Create a resource → Azure AI Search → Free (F0) tier.

Then create the index and load the seed content:
```bash
cd search
pip install azure-search-documents azure-core
export AZURE_SEARCH_ENDPOINT="https://<your-search-service>.search.windows.net"
export AZURE_SEARCH_API_KEY="<admin-key>"
python create_index.py
# → "Index 'fieldpilot-knowledge' created/updated with 7 fields."
# → "Uploaded 11/11 documents."
```

## 2. Azure Function — deploy the search-lookup backend
```bash
# CLI
az functionapp create \
  --name <your-function-app> \
  --resource-group <your-rg> \
  --storage-account <your-storage-account> \
  --consumption-plan-location <your-region> \
  --runtime python --runtime-version 3.11 --functions-version 4

az functionapp config appsettings set \
  --name <your-function-app> --resource-group <your-rg> \
  --settings \
    AZURE_SEARCH_ENDPOINT="https://<your-search-service>.search.windows.net" \
    AZURE_SEARCH_API_KEY="<a query key, not the admin key, is enough here>" \
    AZURE_SEARCH_INDEX="fieldpilot-knowledge"

cd function
func azure functionapp publish <your-function-app>
```
Portal fallback: create a Function App (Python 3.11, Consumption plan), then use the portal's
"Deploy" / Kudu zip-deploy, or VS Code's Azure Functions extension, to push the `function/`
folder. Set the same three app settings under Configuration.

Grab the function key from the portal (Function App → search-lookup → Function Keys) or:
```bash
az functionapp function keys list --name <your-function-app> --resource-group <your-rg> --function-name search_lookup
```

### Test it locally first (optional but recommended)
```bash
cd function
cp local.settings.json.example local.settings.json   # fill in your real values
pip install -r requirements.txt
func start
# in another terminal:
curl -s -X POST http://localhost:7071/api/search-lookup \
  -H "Content-Type: application/json" \
  -d '{"query": "alarm 402"}'
# expect: needs_clarification: true, 3 candidates

curl -s -X POST http://localhost:7071/api/search-lookup \
  -H "Content-Type: application/json" \
  -d '{"query": "cutting speed for 6061 aluminum"}'
# expect: found: true, a single direct answer
```

## 3. Slack — incoming webhook
1. https://api.slack.com/apps → Create New App → From scratch → pick your test workspace.
2. Features → Incoming Webhooks → toggle on → Add New Webhook to Workspace → pick a channel.
3. Copy the webhook URL (`https://hooks.slack.com/services/...`).

## 4. ElevenLabs agent
[agent/system_prompt.md](agent/system_prompt.md) and the `agent/tool_*.json` files were the
*plan* for a from-scratch manual dashboard build (persona "Ava"). What's actually live diverged
from that plan (persona "FieldWise", a different prompt, and a ServiceNow integration added
via the dashboard's Integrations tab instead of the planned Slack webhook) — treat those files
as historical reference for the webhook-tool *pattern* (still accurate for `search_knowledge_base`),
not as an exact match for the live agent. Two live agents exist:

| Agent | ID | Purpose |
|---|---|---|
| Field Technician Assistant | `agent_9001m1ye0esbfxd8qcrrr8tvzy0g` | Original, flat-prompt version. Untouched by the automation scripts below — kept as a fallback. |
| Field Technician Assistant (Workflow) | `agent_1401m216hed0eec9p6k3vfsmbge7` | Current demo agent — same tools, rebuilt as an 8-node workflow with a short persona-only base prompt. |

## 5. Agent-as-code: duplicate + workflow scripts
Everything past the initial dashboard pass was done through the ElevenLabs Python SDK instead
of more manual clicking — reviewable and re-runnable, same as the rest of this repo:
```bash
pip install elevenlabs
cd agent
export ELEVENLABS_API_KEY="<your key, from Settings → Profile → API Keys or /app/settings/api-keys>"
python duplicate_agent.py   # clones the original agent, writes the new agent_id to .workflow_agent_id
python build_workflow.py    # adds the 8-node workflow + shrinks the base prompt on the clone
```
Both scripts re-fetch the live agent before writing, so re-running `build_workflow.py` after
editing `WORKFLOW` or `BASE_SYSTEM_PROMPT` in that file pushes the change without disturbing
anything else (voice, tool references, etc.). See `docs/technical-writeup.md` for why this
approach was used, the tools-vs-tool_ids and duplicate-edge API quirks hit along the way, a
misdiagnosed-then-corrected ServiceNow tool investigation, and a real workflow bug found and
fixed (nodes skipping their spoken line before transitioning).

## 6. Record the Loom
3-5 minutes, one take, presenting the working demo — see `docs/fieldpilot-brief.md` for
the golden path this walks through.

## Repo layout
```
docs/      brief, demo script, submission notes
search/    Azure AI Search index schema, seed content, create_index.py
function/  Azure Function (Python) — the search-lookup webhook backend
agent/     original manual-build plan (system prompt + tool JSON, partly superseded — see
           above) plus the current agent-as-code scripts: elevenlabs_client.py,
           duplicate_agent.py, build_workflow.py
```
