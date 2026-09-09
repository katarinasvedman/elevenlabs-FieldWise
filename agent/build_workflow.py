"""Add the FieldWise golden-path workflow to the duplicated agent, and shrink its base
system prompt down to persona/tone only -- the situational instructions (what to do with
a multi-cause lookup, how to confirm an escalation, etc.) now live on the workflow's
individual nodes instead of one long flat prompt.

Note on `servicenow_create_incident`: its `instance`/`domain` path params are marked
system-provided with an empty constant_value/dynamic_variable in the static tool
definition, which initially looked like a bug (a per-node schema_overrides fix was
attempted and rejected by the API, "Cannot override system provided property"). Turned
out to be a misread: those two fields really are resolved from the tool's
`api_integration_connection_id` at call time, not from constant_value/dynamic_variable --
confirmed by inspecting two live conversations, both showing the params correctly filled
in (`dev292793`/`service-now.com`) and a real incident created. So the API's rejection of
the override was actually *correct* (you can't override a value the platform already
supplies properly). No fix needed here after all -- see docs/submission-notes.md for the
full corrected writeup, including the separate, real bug this build did find (an
override_agent node calling its next workflow-transition tool before speaking, fixed
below via explicit "speak first" wording on each node's additional_prompt).

Usage (after running duplicate_agent.py once):
    ELEVENLABS_API_KEY="sk_..." python agent/build_workflow.py

Run it again any time to push edits -- it always re-reads the live agent first and only
overwrites conversation_config.agent.prompt.prompt and workflow, leaving everything else
(voice, LLM, tool_ids, etc.) exactly as duplicate_agent.py left it.
"""

from pathlib import Path

from elevenlabs_client import get_client

HERE = Path(__file__).parent
AGENT_ID_FILE = HERE / ".workflow_agent_id"

# Found via client.conversational_ai.agents.list() / tools.get() earlier in the build
# session. Re-verify with `tools list` if either tool is ever recreated.
SEARCH_KNOWLEDGE_BASE_TOOL_ID = "tool_8901m1yerg7dekxvwbfjzrm1nff4"
SERVICENOW_CREATE_INCIDENT_TOOL_ID = "tool_6601m2149hryehs947gctpf1ph90"

BASE_SYSTEM_PROMPT = """\
You are Ava, a hands-free voice assistant for CNC machinists and field technicians on a \
shop floor. Their hands are full and it's loud -- keep every response to 1-2 short \
sentences, plain language, no filler. Never read out raw data structures, IDs, or \
confidence scores. Stay calm and clear even if the technician sounds rushed."""

WORKFLOW = {
    "nodes": {
        "start_node": {"type": "start", "position": {"x": 0, "y": 0}},
        "greet_and_listen": {
            "type": "override_agent",
            "label": "Greet & Listen",
            "position": {"x": 0, "y": 200},
            "additional_prompt": (
                "The first message already greeted the technician. Listen for what they "
                "need: a machining question (alarm code, cutting data, or safety "
                "procedure) or a direct request for help/a supervisor."
            ),
            "additional_tool_ids": [],
            "entry_behavior": "wait_for_user",
        },
        "lookup_knowledge": {
            "type": "tool",
            "position": {"x": -150, "y": 400},
            "tools": [{"tool_id": SEARCH_KNOWLEDGE_BASE_TOOL_ID}],
        },
        "answer_or_clarify": {
            "type": "override_agent",
            "label": "Answer or Clarify",
            "position": {"x": -150, "y": 600},
            "additional_prompt": (
                "You just got a knowledge base lookup result -- it is sitting in front of "
                "you right now, unspoken. Your very next action MUST be to speak it. Do "
                "NOT look it up again, even if it feels like the technician's question is "
                "still open -- it isn't, you already have the answer. Only trigger "
                "another lookup once the technician has said something NEW after you've "
                "spoken this result. If it needs clarification (multiple possible "
                "causes), ask ONE short distinguishing question, then resolve from that "
                "same result once the technician answers -- do not trigger another "
                "lookup for the follow-up, you already have everything you need. If it "
                "returned a direct answer, speak it briefly. If nothing useful was "
                "found, say so plainly and ask if they'd like a supervisor flagged."
            ),
            "additional_tool_ids": [],
            "entry_behavior": "generate_immediately",
        },
        "escalate": {
            # servicenow_create_incident works -- verified against two live conversations
            # (real incident numbers, path params correctly resolved from the connection
            # at call time). See the module docstring above for the earlier misdiagnosis
            # this corrects.
            "type": "tool",
            "position": {"x": 150, "y": 850},
            "tools": [{"tool_id": SERVICENOW_CREATE_INCIDENT_TOOL_ID}],
        },
        "escalation_confirmed": {
            "type": "override_agent",
            "label": "Escalation Confirmed",
            "position": {"x": 0, "y": 1050},
            "additional_prompt": (
                "SPEAK FIRST, before calling any tool or ending the call: tell the "
                "technician you've logged an incident in ServiceNow so maintenance can "
                "take over, and advise them to shut the machine down and follow standard "
                "lockout/tagout procedure while they wait. Two short sentences, max. Do "
                "not end or transition the conversation until you have said this out "
                "loud."
            ),
            "additional_tool_ids": [],
            "entry_behavior": "generate_immediately",
        },
        "escalation_failed": {
            "type": "override_agent",
            "label": "Escalation Failed",
            "position": {"x": 300, "y": 1050},
            "additional_prompt": (
                "SPEAK FIRST, before calling any tool or ending the call: apologize "
                "briefly that the escalation system isn't reachable right now, and tell "
                "the technician to contact their supervisor directly or log it manually. "
                "Do not end or transition the conversation until you have said this out "
                "loud."
            ),
            "additional_tool_ids": [],
            "entry_behavior": "generate_immediately",
        },
        "end_node": {"type": "end", "position": {"x": 150, "y": 1250}},
    },
    "edges": {
        "start_to_greet": {
            "source": "start_node", "target": "greet_and_listen",
            "forward_condition": {"type": "unconditional"},
        },
        "greet_to_lookup": {
            "source": "greet_and_listen", "target": "lookup_knowledge",
            "forward_condition": {
                "type": "llm",
                "condition": "The technician described a problem, alarm code, or asked a "
                              "machining/cutting-data/safety question that needs a "
                              "knowledge base lookup.",
            },
        },
        "greet_to_escalate": {
            "source": "greet_and_listen", "target": "escalate",
            "forward_condition": {
                "type": "llm",
                "condition": "The technician directly asks for a supervisor or help, "
                              "without needing a knowledge lookup first.",
            },
        },
        # One edge object per node pair -- the platform rejects a second edge between
        # the same two nodes. This pair is bidirectional (lookup succeeds -> go answer;
        # a later follow-up question -> go look up again), so it's modeled as a single
        # edge with both a forward_condition (lookup_knowledge -> answer_or_clarify) and
        # a backward_condition (answer_or_clarify -> lookup_knowledge), rather than two
        # separate entries.
        "lookup_and_clarify": {
            "source": "lookup_knowledge", "target": "answer_or_clarify",
            "forward_condition": {"type": "result", "successful": True},
            "backward_condition": {
                "type": "llm",
                "condition": "The technician's most recent message asks a knowledge or "
                              "machining question you have NOT already looked up. If you "
                              "already have an unspoken lookup result sitting in front of "
                              "you from the step you just came from, this is false -- "
                              "speak that result instead of using this edge again.",
            },
        },
        "lookup_failure": {
            "source": "lookup_knowledge", "target": "escalate",
            "forward_condition": {"type": "result", "successful": False},
        },
        "clarify_to_escalate": {
            "source": "answer_or_clarify", "target": "escalate",
            "forward_condition": {
                "type": "llm",
                "condition": "The technician says the issue isn't resolved, or asks for "
                              "a supervisor/help.",
            },
        },
        "clarify_to_end": {
            "source": "answer_or_clarify", "target": "end_node",
            "forward_condition": {
                "type": "llm",
                "condition": "The technician indicates the issue is resolved or the "
                              "conversation is wrapping up.",
            },
        },
        "escalate_success": {
            "source": "escalate", "target": "escalation_confirmed",
            "forward_condition": {"type": "result", "successful": True},
        },
        "escalate_failure": {
            "source": "escalate", "target": "escalation_failed",
            "forward_condition": {"type": "result", "successful": False},
        },
        # These two are deliberately `llm`-conditioned, not `unconditional`. An
        # unconditional edge gives the model nothing to weigh -- it's free to fire it
        # immediately on node entry, before speaking (observed live: the node's spoken
        # confirmation got skipped entirely, straight to end_call). Tying the condition
        # to "have I already spoken" forces the model to actually check that before it
        # can truthfully advance.
        "confirmed_to_end": {
            "source": "escalation_confirmed", "target": "end_node",
            "forward_condition": {
                "type": "llm",
                "condition": "The agent has already spoken the escalation confirmation "
                              "out loud in this turn.",
            },
        },
        "failed_to_end": {
            "source": "escalation_failed", "target": "end_node",
            "forward_condition": {
                "type": "llm",
                "condition": "The agent has already spoken the apology and fallback "
                              "instructions out loud in this turn.",
            },
        },
    },
}


def main() -> None:
    client = get_client()

    if not AGENT_ID_FILE.exists():
        raise SystemExit(
            f"{AGENT_ID_FILE} not found -- run duplicate_agent.py first."
        )
    agent_id = AGENT_ID_FILE.read_text(encoding="utf-8").strip()

    agent = client.conversational_ai.agents.get(agent_id=agent_id)
    print(f"Updating: {agent.name} ({agent_id})")

    conversation_config = agent.conversation_config.model_dump(exclude_none=True)
    # Same tools-vs-tool_ids conflict as duplicate_agent.py -- keep references only.
    conversation_config.get("agent", {}).get("prompt", {}).pop("tools", None)
    conversation_config["agent"]["prompt"]["prompt"] = BASE_SYSTEM_PROMPT

    client.conversational_ai.agents.update(
        agent_id=agent_id,
        conversation_config=conversation_config,
        workflow=WORKFLOW,
    )

    # Re-fetch to confirm what actually landed, not just what we sent.
    updated = client.conversational_ai.agents.get(agent_id=agent_id)
    wf = updated.workflow.model_dump(exclude_none=True) if updated.workflow else {}
    print(f"Workflow nodes: {len(wf.get('nodes', {}))}, edges: {len(wf.get('edges', {}))}")
    print(f"Prompt length: {len(updated.conversation_config.agent.prompt.prompt)} chars")
    print("Done.")


if __name__ == "__main__":
    main()
