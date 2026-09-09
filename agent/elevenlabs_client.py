"""Shared ElevenLabs SDK client factory for the automation scripts in this folder.

Requires ELEVENLABS_API_KEY set in the environment (never hardcode it here or anywhere
in this repo -- pass it inline on the command line for each run, same pattern used for
the Azure/ServiceNow credentials elsewhere in this project):

    ELEVENLABS_API_KEY="sk_..." python agent/duplicate_agent.py
"""

import os
import sys

from elevenlabs import ElevenLabs


def get_client() -> ElevenLabs:
    if not os.environ.get("ELEVENLABS_API_KEY"):
        print("Set ELEVENLABS_API_KEY before running this script.", file=sys.stderr)
        sys.exit(1)
    return ElevenLabs()
