"""Duplicate the original 'Field Technician Assistant' agent so the workflow rebuild in
build_workflow.py has a fresh agent to work on -- the original is never modified by these
scripts, so it stays available as a fallback / comparison point.

Copies the full live conversation_config as-is (voice, LLM, first message, and every tool
reference, including the search_knowledge_base and servicenow_* tools already attached).
Those tool references point at the same shared workspace Tool objects as the original --
duplicating the agent does not duplicate the tools themselves, which is intentional: tools
are workspace-level resources, agents are just configurations that reference them.

Usage:
    ELEVENLABS_API_KEY="sk_..." python agent/duplicate_agent.py

Writes the new agent's ID to agent/.workflow_agent_id (gitignored) for build_workflow.py
to pick up.
"""

from pathlib import Path

from elevenlabs_client import get_client

# "Field Technician Assistant" -- found via client.conversational_ai.agents.list() earlier
# in the build session. Not modified by this script; re-verify with `agents list` if it's
# ever renamed or recreated.
ORIGINAL_AGENT_ID = "agent_9001m1ye0esbfxd8qcrrr8tvzy0g"
NEW_AGENT_NAME = "Field Technician Assistant (Workflow)"

HERE = Path(__file__).parent
AGENT_ID_FILE = HERE / ".workflow_agent_id"


def main() -> None:
    client = get_client()

    original = client.conversational_ai.agents.get(agent_id=ORIGINAL_AGENT_ID)
    print(f"Source agent: {original.name} ({ORIGINAL_AGENT_ID})")

    conversation_config = original.conversation_config.model_dump(exclude_none=True)
    # The GET response expands tool_ids into a full inline `tools` list for convenience;
    # the create/update API rejects having both `tools` and `tool_ids` set at once. Keep
    # the references (`tool_ids`) and drop the expanded copy.
    conversation_config.get("agent", {}).get("prompt", {}).pop("tools", None)

    created = client.conversational_ai.agents.create(
        conversation_config=conversation_config,
        name=NEW_AGENT_NAME,
        tags=["fieldpilot", "workflow-demo"],
    )

    AGENT_ID_FILE.write_text(created.agent_id, encoding="utf-8")
    print(f"Created: {NEW_AGENT_NAME} ({created.agent_id})")
    print(f"Saved to {AGENT_ID_FILE} for build_workflow.py")
    print(f"Original agent ({ORIGINAL_AGENT_ID}) untouched.")


if __name__ == "__main__":
    main()
