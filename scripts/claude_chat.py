# -*- coding: utf-8 -*-
import json
import re
try:
    from scripts.claude_chat import ask_claude
except ImportError:
    from claude_chat import ask_claude

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

    # Strip markdown code fences if present
    clean = raw.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```[a-z]*\n?", "", clean)
        clean = re.sub(r"\n?```$", "", clean)
    
    try:
        result = json.loads(clean.strip())
    except json.JSONDecodeError:
        result = {"vision": "", "goals": [], "benefits": [], "raw": raw}

    # Add flags for goals with no benefits
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

if __name__ == "__main__":
    sample = """Our vision is to become the leading sustainable technology provider. 
    Our goals include achieving carbon neutrality by 2030 and expanding market share by 40%. 
    Benefits include enhanced environmental impact and stronger financial returns."""
    
    print(json.dumps(run_extraction(sample), indent=2))
