import datetime as dt
import json
from app.schemas import WeeklyPlanSchema, ActionSchema, RiskSchema, ContextPacketSchema
from app.llm.client import get_llm_client

SYSTEM_PROMPT = """
You are EM-Aide, a decision-support copilot for Engineering Managers.

You receive ONLY sanitized delivery signals and anonymized entity references.
You do NOT have access to code, diffs, ticket text, or team discussions.

Your job:
- Identify the MOST IMPORTANT actions an EM should take THIS WEEK.
- Be concise, concrete, and operational.

Rules:
- Prefer clarity over completeness.
- Avoid generic advice.
- Do not restate raw metrics unless they directly support a decision.
- Each action must be something an EM can realistically do within a week.
- Write for a busy EM reading this in under 2 minutes.

Hard limits:
- Exactly 3 actions.
- Exactly 5 risks.
- Action rationale: max 2 sentences.
- Steps: max 3 bullets.
- Risk description: max 1 sentence.
- Summary: max 3 sentences.

Output MUST be valid JSON matching the provided schema.
Do not include markdown, commentary, or extra text.
"""

def _week_start(d: dt.date) -> dt.date:
    return d - dt.timedelta(days=d.weekday())

def generate_weekly_plan(context: ContextPacketSchema) -> WeeklyPlanSchema:
    llm = get_llm_client()

    schema_hint = {
        "week_start": "YYYY-MM-DD",
        "generated_at": "ISO-8601 datetime",
        "top_actions": [{
            "title": "string",
            "rationale": "string",
            "evidence": ["string"],
            "steps": ["string"],
            "expected_impact": "string",
            "risk": "string",
            "confidence": 0.0
        }],
        "top_risks": [{
            "title": "string",
            "description": "string",
            "severity": "low|medium|high",
            "likelihood": 0.0,
            "signals": ["string"],
            "mitigations": ["string"]
        }],
        "summary": "string"
    }

    user_prompt = f"""
ContextPacket (sanitized JSON):
{context.model_dump_json(indent=2)}

Task:
Produce a focused weekly plan.

Requirements:
- Choose only the highest-leverage actions.
- If an action does not materially reduce risk or improve flow this week, exclude it.
- Cite evidence using signal names and entity IDs only (e.g. "pr_stale_count", "PR-1423").

Formatting rules:
- Keep text short and direct.
- No hedging language.
- No repeated explanations.

Schema hint:
{json.dumps(schema_hint, indent=2)}
"""

    plan = llm.generate_structured(SYSTEM_PROMPT, user_prompt, WeeklyPlanSchema)

    # Fill computed week_start if missing/invalid
    if not plan.week_start:
        plan.week_start = _week_start(dt.date.today())
    return plan
