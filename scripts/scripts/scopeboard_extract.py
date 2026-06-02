import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
- G3: [goal 3] | Supports: VISION

BENEFITS:
- B1: [benefit 1] | Stakeholder: [who] | Delivers: [G1, G2]
- B2: [benefit 2] | Stakeholder: [who] | Delivers: [G2]
- B3: [benefit 3] | Stakeholder: [who] | Delivers: [G1, G3]

RELATIONSHIP SUMMARY:
[Briefly explain how the goals collectively deliver the vision, and how the benefits map to the goals]

TRANSCRIPT:
{transcript}"""

def extract_scopeboard_data(transcript: str) -> str:
    prompt = EXTRACT_PROMPT.format(transcript=transcript)
    return ask_claude(prompt)

if __name__ == "__main__":
    transcript = """Program Manager: Thank you for joining me today. Could you share the company's overall vision and key goals for the next few years? Executive: Absolutely. Our vision is to become the leading sustainable technology provider that empowers communities worldwide to thrive in a green economy. Our primary goals include achieving carbon neutrality by 2030, expanding our market share by 40% through innovative product lines, and increasing employee engagement scores by 25%. The main benefits we aim to deliver are enhanced environmental impact, stronger financial returns for stakeholders, and improved quality of life for our customers and teams through accessible, eco-friendly solutions."""

    print("\n--- ScopeBoard Extraction ---\n")
    result = extract_scopeboard_data(transcript)
    print(result)
