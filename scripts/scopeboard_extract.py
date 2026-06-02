# -*- coding: utf-8 -*-
import sys
import os
import re
try:
    from scripts.claude_chat import ask_claude
except ImportError:
    from claude_chat import ask_claude

EXTRACT_PROMPT = """You are ScopeBoard, an AI assistant that helps Program Managers extract structured portfolio information from executive interview transcripts.
Analyze the interview transcript below and extract the following, then map the relationships between them:
1. VISION: The overarching ambition or destination
2. GOALS: Specific, measurable objectives (each goal must link to the Vision)
3. BENEFITS: The value or outcomes delivered (each benefit must link to one or more Goals)
Return your response in this exact format:
VISION:
[vision statement]
GOALS:
- G1: [goal 1] | Supports: VISION
- G2: [goal 2] | Supports: VISION
BENEFITS:
- B1: [benefit 1] | Stakeholder: [who] | Delivers: [G1, G2]
- B2: [benefit 2] | Stakeholder: [who] | Delivers: [G2]
RELATIONSHIP SUMMARY:
[Briefly explain how the goals collectively deliver the vision]
TRANSCRIPT:
{transcript}"""

def extract_scopeboard_data(transcript: str) -> str:
    prompt = EXTRACT_PROMPT.format(transcript=transcript)
    return ask_claude(prompt)

def parse_extraction(raw: str) -> dict:
    result = {"vision": "", "goals": [], "benefits": [], "flags": []}
    lines = raw.split("\n")
    section = None
    for line in lines:
        line = line.strip()
        if line.startswith("VISION:"):
            section = "vision"
            text = line.replace("VISION:", "").strip()
            if text:
                result["vision"] = text
        elif line.startswith("GOALS:"):
            section = "goals"
        elif line.startswith("BENEFITS:"):
            section = "benefits"
        elif line.startswith("RELATIONSHIP SUMMARY:"):
            section = None
        elif section == "vision" and line and not line.startswith("-"):
            result["vision"] += " " + line if result["vision"] else line
        elif section == "goals" and line.startswith("- G"):
            match = re.match(r"- (G\d+): (.+?)(?:\s*\|\s*Supports:.*)?$", line)
            if match:
                result["goals"].append({
                    "id": match.group(1),
                    "text": match.group(2).strip(),
                    "relation": "VISION"
                })
        elif section == "benefits" and line.startswith("- B"):
            match = re.match(r"- (B\d+): (.+?)\s*\|\s*Stakeholder:.*?\|\s*Delivers:\s*(.+)$", line)
            if match:
                result["benefits"].append({
                    "id": match.group(1),
                    "text": match.group(2).strip(),
                    "relation": match.group(3).strip()
                })

    # Flag goals with no benefits
    goal_ids = {g["id"] for g in result["goals"]}
    covered = set()
    for b in result["benefits"]:
        for gid in b["relation"].split(","):
            covered.add(gid.strip())
    for gid in goal_ids:
        if gid not in covered:
            result["flags"].append(f"{gid} has no benefit linked to it — consider asking the executive what value this goal delivers.")

    return result

def run_extraction(transcript: str) -> dict:
    raw = extract_scopeboard_data(transcript)
    return parse_extraction(raw)
