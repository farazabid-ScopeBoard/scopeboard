# -*- coding: utf-8 -*-
"""
ScopeBoard — Missing Benefits Suggestion Engine  (V2 — V1 Schema)
-----------------------------------------------------------------
Takes extraction output + project context (industry, archetypes per goal)
and returns missing benefits from the Platform Benefits Library.

Usage (standalone):
    python scripts/scopeboard_suggest.py

Usage (imported):
    from scripts.scopeboard_suggest import run_suggestion
    results = run_suggestion(extraction, industry, archetypes_by_goal)
"""

import json
import os
try:
    from scripts.claude_chat import ask_claude  # when called from app.py
except ImportError:
    from claude_chat import ask_claude  # when run directly

# ── Path to library ──────────────────────────────────────────────────
LIBRARY_PATH = os.path.join(os.path.dirname(__file__), "benefits_library.json")


# ════════════════════════════════════════════════════════════════════
# LIBRARY HELPERS
# ════════════════════════════════════════════════════════════════════

def load_library(path: str = LIBRARY_PATH) -> list:
    """Load and return the list of benefit entries from the library JSON."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("benefits", [])


def filter_library(benefits: list, archetype: str = None, industry: str = None) -> list:
    """
    Filter library entries by archetype and/or industry.
    Returns all active entries that match either primary or secondary archetype,
    and include the given industry in their applicability list.
    """
    results = []
    for b in benefits:
        if b.get("status") != "Active":
            continue

        # Archetype match (primary or secondary)
        if archetype:
            primary_match = archetype.lower() in b.get("primary_archetype", "").lower()
            secondary_match = any(
                archetype.lower() in a.lower()
                for a in b.get("secondary_archetypes", [])
            )
            if not (primary_match or secondary_match):
                continue

        # Industry match
        if industry:
            industry_match = any(
                industry.lower() in ind.lower()
                for ind in b.get("industry_applicability", [])
            )
            if not industry_match:
                continue

        results.append(b)

    return results


# ════════════════════════════════════════════════════════════════════
# AI MATCHING
# ════════════════════════════════════════════════════════════════════

MATCH_PROMPT = """
You are a benefits analyst for ScopeBoard, a programme management intelligence tool.

TASK:
Given a list of EXTRACTED BENEFITS from an executive interview, and a LIBRARY of known benefit patterns,
identify which library benefits are NOT already covered by the extracted benefits.

A library benefit is "covered" if:
- An extracted benefit directly matches it in meaning (not just wording), OR
- An extracted benefit is a more specific version of the library benefit

A library benefit is "missing" if:
- It is relevant to the stated goals, AND
- It is not represented at all in the extracted benefits

GOAL CONTEXT:
{goal_text}

EXTRACTED BENEFITS LINKED TO THIS GOAL:
{extracted_benefits}

LIBRARY BENEFITS TO CHECK (filtered by archetype and industry):
{library_entries}

OUTPUT FORMAT — respond with valid JSON only, no other text:
{{
  "matched": [
    {{"benefit_id": "BL-001", "matched_to": "Brief description of which extracted benefit covers it"}}
  ],
  "missing": [
    {{"benefit_id": "BL-002", "relevance": "One sentence on why this benefit is relevant to the goal"}}
  ]
}}
"""


def match_benefits_for_goal(goal_text: str, extracted_benefits: list,
                             library_entries: list) -> dict:
    """
    Use Claude to match extracted benefits against library entries for a single goal.
    Returns dict with 'matched' and 'missing' lists.
    """
    if not library_entries:
        return {"matched": [], "missing": []}

    # Format library entries for the prompt
    library_formatted = "\n".join([
        f"- [{b['benefit_id']}] {b['title']}: {b['description'][:200]}..."
        for b in library_entries
    ])

    extracted_formatted = "\n".join([
        f"- {b}" for b in extracted_benefits
    ]) if extracted_benefits else "No benefits extracted for this goal."

    prompt = MATCH_PROMPT.format(
        goal_text=goal_text,
        extracted_benefits=extracted_formatted,
        library_entries=library_formatted
    )

    raw = ask_claude(prompt)

    # Parse JSON response
    try:
        # Strip markdown code fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception:
        return {"matched": [], "missing": [], "parse_error": raw}


# ════════════════════════════════════════════════════════════════════
# FOLLOW-UP QUESTION GENERATION
# ════════════════════════════════════════════════════════════════════

FOLLOWUP_PROMPT = """
You are a programme manager coach helping a PgM prepare for a follow-up executive interview.

A benefit was identified as MISSING from the executive's articulation of this initiative.
Your job is to write ONE sharp, conversational follow-up question the PgM can ask the executive
to draw out this benefit naturally — without it feeling like a survey question.

The question should:
- Feel natural in an executive conversation
- Target the specific missing benefit without naming it directly
- Be open-ended (not yes/no)
- Be 1–2 sentences maximum

GOAL: {goal_text}
MISSING BENEFIT: {benefit_title}
WHY IT'S RELEVANT: {relevance}

Respond with the follow-up question only. No preamble.
"""


def generate_followup_question(goal_text: str, benefit_title: str, relevance: str) -> str:
    """Generate a follow-up interview question for a missing benefit."""
    prompt = FOLLOWUP_PROMPT.format(
        goal_text=goal_text,
        benefit_title=benefit_title,
        relevance=relevance
    )
    return ask_claude(prompt).strip()


# ════════════════════════════════════════════════════════════════════
# MAIN SUGGESTION ENGINE
# ════════════════════════════════════════════════════════════════════

def run_suggestion(extraction: dict, industry: str,
                   archetypes_by_goal: dict = None) -> dict:
    """
    Main entry point for the suggestion engine.

    Args:
        extraction:        Output dict from scopeboard_extract.py with keys:
                           'vision', 'goals', 'benefits', 'flags'
        industry:          Project-level industry (e.g. "Sustainable Technology & ESG")
        archetypes_by_goal: Optional dict mapping goal IDs to archetype names.
                            e.g. {"G1": "Sustainable Technology & ESG", "G2": "Digital Transformation"}
                            If not provided, library is filtered by industry only.

    Returns:
        dict with structure:
        {
          "industry": str,
          "goal_results": [
            {
              "goal_id": "G1",
              "goal_text": "...",
              "archetype": "...",
              "extracted_benefits": [...],
              "matched_library_benefits": [...],
              "missing_benefits": [
                {
                  "benefit_id": "BL-001",
                  "title": "...",
                  "benefit_type": "...",
                  "value_category": [...],
                  "relevance": "...",
                  "measurement_approach": "...",
                  "example_metrics": [...],
                  "qualitative_indicators": [...],
                  "difficulty_to_realize": "...",
                  "typical_time_horizon": "...",
                  "follow_up_question": "..."
                }
              ]
            }
          ],
          "summary": {
            "total_goals": int,
            "goals_with_missing_benefits": int,
            "total_missing_benefits": int
          }
        }
    """
    if archetypes_by_goal is None:
        archetypes_by_goal = {}

    library = load_library()
    goals   = extraction.get("goals", [])
    benefits = extraction.get("benefits", [])

    goal_results = []

    for goal in goals:
        goal_id   = goal.get("id", "")
        goal_text = goal.get("text", "")
        archetype = archetypes_by_goal.get(goal_id)

        # Find benefits linked to this goal
        linked_benefits = [
            b["text"] for b in benefits
            if goal_id in b.get("relation", "")
        ]

        # Filter library for this goal's context
        filtered = filter_library(library, archetype=archetype, industry=industry)

        if not filtered:
            goal_results.append({
                "goal_id": goal_id,
                "goal_text": goal_text,
                "archetype": archetype or "Not assigned",
                "extracted_benefits": linked_benefits,
                "matched_library_benefits": [],
                "missing_benefits": [],
                "note": "No library entries found for this industry/archetype combination."
            })
            continue

        # AI matching
        match_result = match_benefits_for_goal(goal_text, linked_benefits, filtered)
        matched_ids  = {m["benefit_id"] for m in match_result.get("matched", [])}
        missing_raw  = match_result.get("missing", [])

        # Build enriched missing benefits list
        missing_enriched = []
        library_by_id = {b["benefit_id"]: b for b in filtered}

        for miss in missing_raw:
            bid       = miss.get("benefit_id")
            relevance = miss.get("relevance", "")
            lib_entry = library_by_id.get(bid)

            if not lib_entry:
                continue

            followup = generate_followup_question(
                goal_text      = goal_text,
                benefit_title  = lib_entry["title"],
                relevance      = relevance
            )

            missing_enriched.append({
                "benefit_id":           bid,
                "title":                lib_entry["title"],
                "benefit_type":         lib_entry.get("benefit_type", ""),
                "value_category":       lib_entry.get("value_category", []),
                "relevance":            relevance,
                "measurement_approach": lib_entry.get("measurement_approach", ""),
                "example_metrics":      lib_entry.get("example_metrics", []),
                "qualitative_indicators": lib_entry.get("qualitative_indicators", []),
                "difficulty_to_realize": lib_entry.get("difficulty_to_realize", ""),
                "typical_time_horizon":  lib_entry.get("typical_time_horizon", ""),
                "follow_up_question":   followup
            })

        goal_results.append({
            "goal_id":                  goal_id,
            "goal_text":                goal_text,
            "archetype":                archetype or "Not assigned",
            "extracted_benefits":       linked_benefits,
            "matched_library_benefits": match_result.get("matched", []),
            "missing_benefits":         missing_enriched
        })

    # Summary
    goals_with_missing = sum(
        1 for r in goal_results if r.get("missing_benefits")
    )
    total_missing = sum(
        len(r.get("missing_benefits", [])) for r in goal_results
    )

    return {
        "industry":    industry,
        "goal_results": goal_results,
        "summary": {
            "total_goals":                 len(goals),
            "goals_with_missing_benefits": goals_with_missing,
            "total_missing_benefits":      total_missing
        }
    }


# ════════════════════════════════════════════════════════════════════
# STANDALONE TEST
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Sample extraction output (mimics scopeboard_extract.py output)
    sample_extraction = {
        "vision": "Become the most trusted sustainable technology partner in our sector by 2030.",
        "goals": [
            {"id": "G1", "text": "Reduce our carbon footprint by 40% through technology-led initiatives", "relation": "VISION"},
            {"id": "G2", "text": "Build partnerships with green technology suppliers to modernise our supply chain", "relation": "VISION"},
        ],
        "benefits": [
            {"id": "B1", "text": "Improved environmental reporting and ESG compliance", "relation": "G1"},
            {"id": "B2", "text": "Cost savings from energy efficiency programmes", "relation": "G1,G2"},
        ],
        "flags": []
    }

    sample_archetypes = {
        "G1": "Sustainable Technology & ESG",
        "G2": "Sustainable Technology & ESG"
    }

    print("Running suggestion engine...\n")
    results = run_suggestion(
        extraction         = sample_extraction,
        industry           = "Energy & Utilities",
        archetypes_by_goal = sample_archetypes
    )

    print(f"Industry: {results['industry']}")
    print(f"Summary: {results['summary']}\n")

    for gr in results["goal_results"]:
        print(f"\n{'='*60}")
        print(f"Goal {gr['goal_id']}: {gr['goal_text']}")
        print(f"Archetype: {gr['archetype']}")
        print(f"Extracted benefits: {gr['extracted_benefits']}")
        print(f"\nMISSING BENEFITS ({len(gr['missing_benefits'])}):")
        for mb in gr["missing_benefits"]:
            print(f"\n  [{mb['benefit_id']}] {mb['title']} ({mb['benefit_type']})")
            print(f"  Relevance: {mb['relevance']}")
            print(f"  Difficulty: {mb['difficulty_to_realize']} | Time: {mb['typical_time_horizon']}")
            print(f"  Follow-up Q: {mb['follow_up_question']}")
