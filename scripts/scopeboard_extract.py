# -*- coding: utf-8 -*-
import os
import json
import re
import anthropic

def ask_claude(prompt: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY environment variable is not set.")
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    )
    return "\n".join(block.text for block in message.content if block.type == "text")

EXTRACT_PROMPT = """You are ScopeBoard, an AI assistant that helps Program Managers extract structured portfolio information from executive interview transcripts.

Analyse the transcript below and extract:
1. VISION: The overarching ambition or long-term destination
2. GOALS: Specific objectives that support the vision
3. BENEFITS: Value or outcomes delivered, each linked to one or more goals

Return ONLY valid JSON with this exact structure — no other text:
{{
  "vision": "the vision statement here",
  "goals": [
    {{"id": "G1", "text": "goal text here", "relation": "VISION"}},
    {{"id": "G2", "text": "goal text here", "relation": "VISION"}}
  ],
  "benefits": [
    {{"id": "B1", "text": "benefit text here", "relation": "G1,G2"}},
    {{"id": "B2", "text": "benefit text here", "relation": "G1"}}
  ]
}}

TRANSCRIPT:
{transcript}"""

def run_extraction(transcript: str) -> dict:
    prompt = EXTRACT_PROMPT.format(transcript=transcript)
    raw = ask_claude(prompt)
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-z]*\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean)
    try:
        result = json.loads(clean.strip())
    except json.JSONDecodeError:
        result = {"vision": "", "goals": [], "benefits": [], "raw": raw}
    goal_ids = {g["id"] for g in result.get("goals", [])}
    covered = set()
    for b in result.get("benefits", []):
        for gid in b.get("relation", "").split(","):
            covered.add(gid.strip())
    result["flags"] = [
        f"{gid} has no benefit linked — ask the executive what value this goal delivers."
        for gid in goal_ids if gid not in covered
    ]
    return result
