# Ashby submission — paste into the 'notes' section

**Agent:** https://elevenlabs.io/app/agents/agents/agent_1401m216hed0eec9p6k3vfsmbge7

**Example Conversation ID:** `conv_3701m25z8e11f8qtzqrmww0f80sj`
_(clean full golden-path run — swap for the exact take shown in the Loom if you prefer)_

**Loom:** https://www.loom.com/share/b4456951ea324455983a12fe55ab81ac

---

FieldWise is a hands-free voice assistant for CNC machinists on a shop floor. The demo
walks through a technician diagnosing alarm 402 (the agent asks one clarifying question,
then resolves it), a live knowledge lookup for cutting data, and an escalation that
creates a real ServiceNow incident — all through an ElevenLabs workflow rather than a
single flat prompt.

Full build, design decisions, and platform findings — including workflow behavior
uncovered through live testing and conversation-level debugging — are documented in the
repo: https://github.com/katarinasvedman/elevenlabs-FieldWise. See
`docs/technical-writeup.md` in particular.
