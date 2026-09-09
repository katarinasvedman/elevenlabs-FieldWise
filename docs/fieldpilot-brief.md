# Project: FieldWise (working name — originally "FieldPilot"; also considered FieldLink / FieldMate)

## Context
This is a take-home assignment for an Enterprise Solutions Engineer role at ElevenLabs.
The goal: build a voice agent on ElevenLabs' Conversational AI platform, demonstrating
tool-use and a third-party integration, then present it as an internal demo (3-5 min Loom)
to ElevenLabs' Forward Deployed Engineers (FDEs).

## The scenario
A hands-free voice assistant for field technicians / CNC machinists on a shop floor —
hands full, gloves on, machinery loud, no time to look at a screen. The premise: rather
than duplicating a company's existing documentation into ElevenLabs' native knowledge
base, the agent connects live to the company's *existing* systems — reflecting how an SE
would actually integrate ElevenLabs at a real enterprise customer (inspired by, but not
officially affiliated with, Mastercam Copilot — a real product the user helped create
the underlying solution accelerator for).

## Architecture

**1. Agent** — configured in the ElevenLabs dashboard (no code)
- Persona: short name (e.g. "Ava"), speaks briefly — user has hands full / is in a noisy environment
- System prompt should explicitly state: keep responses short, prioritize clarity over completeness

> **Update (Sep 9):** the live agent is "FieldWise," not "Ava" (plan vs. actual naming
> diverged during dashboard setup), and it's no longer flat-prompt-only. It's now an
> [ElevenLabs workflow](https://elevenlabs.io/docs/eleven-agents/customization/agent-workflows)
> (8 nodes, built via the Python SDK — see `agent/build_workflow.py`), with a short
> persona/tone-only base prompt and the situational logic (multi-cause disambiguation,
> escalation confirmation) living on individual workflow nodes instead. Two agents exist:
> the original flat-prompt one (`agent_9001m1ye0esbfxd8qcrrr8tvzy0g`, untouched, kept as a
> fallback) and the workflow rebuild (`agent_1401m216hed0eec9p6k3vfsmbge7`, what the demo
> actually runs on). Full rationale in `docs/submission-notes.md`.

**2. Tool #1 — Knowledge lookup via Azure AI Search (the core integration)**
- NOT using ElevenLabs' native RAG/knowledge-base upload feature — deliberately, because in
  a real enterprise engagement you don't want to duplicate a customer's live documentation
  into a third-party vendor's storage (staleness + governance/security concerns)
- Instead: a **webhook tool** in ElevenLabs that calls a small backend
- Backend: a lightweight Azure Function that:
  - Receives the technician's query from the ElevenLabs webhook call (HTTP, since ElevenLabs
    can't directly call an SDK — it's a hosted service, must integrate over HTTP)
  - Uses the **Azure AI Search Python/JS SDK internally** (not raw REST calls) to query a
    search index
  - Returns clean JSON back to the agent to speak
- Need to first: create an Azure AI Search resource (free tier is fine) and populate a small
  index with realistic-but-original machining content (cutting speeds/feeds by material,
  common alarm codes + first-response steps, safety procedures). Keep it tight — 1-2 focused
  documents demo better than a sprawling set.

**3. Tool #2 — Escalation via Slack (real third-party integration, simple to wire)**
- A Slack incoming webhook — agent posts to a channel when it can't resolve something,
  simulating "flag a supervisor"

> **Update (Sep 9):** escalation ended up wired through ElevenLabs' pre-built ServiceNow
> integration instead (added via the dashboard's Integrations tab) — the planned Slack
> webhook tool was never actually saved/attached to the agent, so it doesn't currently
> exist in the workspace. `servicenow_create_incident` works, verified against two live
> conversations (real incident numbers created, e.g. `INC0010002`) — an earlier pass
> through this build misdiagnosed it as platform-broken based on its static tool
> definition alone (its `instance`/`domain` path params look unpopulated at rest, but
> resolve correctly from the connection at call time). See `docs/submission-notes.md` for
> that correction, and for a real workflow bug this build did find and fix along the way.

**4. Golden demo path (what the Loom will walk through)**
1. "I'm standing in front of a machine [xxx] that is throwing alarm 402, what should I do?
 → Azure AI Search lookup via webhook tool → agent reasons about this and asks a follow-up question. Here we should simulate that AI Search returns several possible reasons so we need a follow-up questions to narrow this down. Perhaps we should use a cache so we don't need a second AI search lookup?
2. A second knowledge question showing the retrieval is real, not scripted
3. "It didn't resolve the issue, I need help" → Slack escalation tool fires → agent
   confirms a supervisor's been flagged

> **Update (Sep 9):** step 3 now demonstrates the ServiceNow tool firing and *succeeding* —
> a real trackable incident, not a Slack notification (see Tool #2 update above).

## Deliberately out of scope for the 5-day build
- MCP (Model Context Protocol) — would be the more "enterprise-grade" way to expose Azure AI
  Search (e.g. via Azure API Management's native "expose REST API as MCP server" capability),
  giving centralized governance/auth over what the agent can query. Worth a single sentence
  in the video acknowledging this as the natural next step, but not worth the build-time
  complexity for this assignment.

## Deliverables needed
- Agent link in ElevenLabs workspace + example Conversation ID
  > **Update (Sep 9):** two agents now exist (see Architecture §1 update above) — the
  > deliverable link should point at `agent_1401m216hed0eec9p6k3vfsmbge7` ("Field
  > Technician Assistant (Workflow)"), the one the demo script actually runs on.
- 3-5 min Loom, recorded in one take, presenting the working demo (NOT a build tutorial —
  present it like a customer-facing demo of the finished solution)
- Submission notes on Ashby can include the "why webhook not native KB" and "why not MCP yet"
  reasoning as a written aside
