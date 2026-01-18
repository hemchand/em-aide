import datetime as dt
import json
from app.schemas import WeeklyPlanSchema, ActionSchema, RiskSchema, ContextPacketSchema
from app.llm.client import get_llm_client

SYSTEM_PROMPT = """You are EM-Aide, a decision-support copilot for Engineering Managers.
You receive ONLY sanitized delivery signals and anonymized entity references. Do not ask for code or ticket text.
Produce concrete, safe, high-leverage actions an EM can take this week.
Output MUST be valid JSON matching the provided schema. No markdown. No extra text.
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

    user_prompt = f"""ContextPacket (sanitized JSON):
{context.model_dump_json(indent=2)}

Task:
1) Propose the TOP 3 actions for the coming work week.
2) Provide TOP 5 risks with mitigations.

Rules:
- Use only the provided signals/entities.
- Actions must be operational and safe (no destructive automation).
- Evidence should cite signal names and entity IDs (e.g., 'pr_stale_count', 'PR-123').
- Confidence: 0.0–1.0.
- Output ONLY JSON.

Schema hint:
{json.dumps(schema_hint, indent=2)}
"""

    plan = llm.generate_structured(SYSTEM_PROMPT, user_prompt, WeeklyPlanSchema)

    # Fill computed week_start if missing/invalid
    if not plan.week_start:
        plan.week_start = _week_start(dt.date.today())
    return plan
