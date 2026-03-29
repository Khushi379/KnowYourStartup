
from __future__ import annotations

import json
import os
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.schemas import (
    ArchitectureBlock,
    InnovationInput,
    InnovationResponse,
    RoadmapPhase,
    ScoreBreakdown,
)


def clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))

def clamp_signal(value: float) -> int:
    return clamp(value, 1, 10)

def normalize_skills(skills: list[str]) -> set[str]:
    return {skill.strip().lower() for skill in skills if skill.strip()}

def count_keyword_hits(text: str, keywords: set[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)

def unique_items(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered

def match_labels(text: str, mapping: dict[str, str]) -> list[str]:
    return unique_items([label for keyword, label in mapping.items() if keyword in text])

def describe_team(skills: set[str]) -> str:
    if {"frontend", "backend", "fullstack"} & skills:
        return "a product-building team"
    if {"ai", "ml", "data"} & skills:
        return "an AI-leaning team"
    if {"design", "ui", "ux"} & skills:
        return "a design-forward team"
    if skills:
        return "a multidisciplinary team"
    return "an early team"

def audience_group_phrase(audience: str) -> str:
    normalized = audience.strip().lower()
    special_cases = {
        "founders": "founders", "startup teams": "startup teams", "students": "students",
        "teachers": "teachers", "schools": "schools", "clinicians": "clinicians",
        "patients": "patients", "hospitals": "hospitals", "clinics": "clinics",
        "developers": "developers", "engineering teams": "engineering teams",
        "creators": "creators", "communities": "communities", "ngos": "NGOs",
        "finance teams": "finance teams", "financial institutions": "financial institutions",
        "merchants": "merchants", "teams": "teams", "businesses": "businesses",
        "end users": "end users",
    }
    return special_cases.get(normalized, normalized)

def clean_model_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()

def clean_model_list(value: object, *, minimum: int = 3, maximum: int = 5, min_words: int = 1) -> list[str]:
    if not isinstance(value, list):
        return []
    items = unique_items([clean_model_text(item) for item in value if isinstance(item, str)])
    filtered = [item for item in items if len(item.split()) >= min_words]
    return filtered[:maximum] if len(filtered) >= minimum else []

def score_band(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def extract_context(domain: str, summary_text: str, skills: set[str]) -> dict[str, str | list[str]]:
    audience_map = {
        "founder": "Founders", "startup": "Startup teams", "student": "Students",
        "teacher": "Teachers", "school": "Schools", "doctor": "Clinicians",
        "patient": "Patients", "hospital": "Hospitals", "clinic": "Clinics",
        "developer": "Developers", "engineer": "Engineering teams", "creator": "Creators",
        "community": "Communities", "ngo": "NGOs", "finance": "Finance teams",
        "bank": "Financial institutions", "seller": "Sellers", "merchant": "Merchants",
        "team": "Teams", "business": "Businesses", "user": "End users",
    }
    workflow_map = {
        "dashboard": "dashboard", "assistant": "assistant", "automation": "automation",
        "marketplace": "matching marketplace", "match": "matching workflow",
        "analytics": "analytics view", "report": "reporting flow",
        "recommend": "recommendation engine", "schedule": "scheduling flow",
        "booking": "booking flow", "chat": "chat workflow", "community": "community workflow",
        "collaboration": "collaboration workspace", "payment": "payment workflow",
        "alert": "alerting system", "monitor": "monitoring workflow", "api": "API workflow",
    }
    value_map = {
        "save": "time savings", "faster": "speed", "reduce": "cost reduction",
        "cost": "cost reduction", "affordable": "accessibility", "accessible": "accessibility",
        "personalized": "personalization", "insight": "better decision support",
        "predict": "predictive insight", "discover": "faster discovery",
        "validate": "validation support", "collaborat": "better coordination",
        "compliance": "compliance support",
    }
    moat_map = {
        "workflow": "workflow lock-in", "integration": "system integrations",
        "data": "unique data loops", "network": "network effects",
        "community": "community density", "automation": "automation depth",
        "ai": "AI-assisted insight", "matching": "better matching logic",
    }
    domain_fallback_users = {
        "education": ["Students", "Teachers", "Campus programs"],
        "health": ["Clinicians", "Patients", "Care teams"],
        "sustainability": ["Climate teams", "Operations teams", "Communities"],
        "finance": ["Finance teams", "Merchants", "Consumers"],
        "media": ["Creators", "Audiences", "Media teams"],
        "community": ["Communities", "NGOs", "Organizers"],
        "developer_tools": ["Developers", "Engineering teams", "Product teams"],
        "general": ["Teams", "Founders", "Businesses"],
    }
    audiences = match_labels(summary_text, audience_map)
    if not audiences:
        audiences = domain_fallback_users[domain]
    workflows = match_labels(summary_text, workflow_map)
    if not workflows:
        workflows = ["core workflow"]
    values = match_labels(summary_text, value_map)
    moats = match_labels(summary_text, moat_map)
    return {
        "audiences": audiences[:3],
        "primary_audience": audiences[0],
        "workflows": workflows[:3],
        "primary_workflow": workflows[0],
        "values": values[:3],
        "moats": moats[:3],
        "team_descriptor": describe_team(skills),
    }


def build_score_rationale(key: str, score: int, *, audience_group: str, primary_workflow: str, domain_label: str) -> str:
    band = score_band(score)
    rationale_map = {
        "painkiller": {
            "high": f"The brief suggests a painful and meaningful problem for {audience_group}.",
            "medium": f"The problem looks real, but the urgency for {audience_group} still needs sharper proof.",
            "low": f"The brief does not clearly show strong urgency or repeated pain for {audience_group}.",
        },
        "timing": {
            "high": f"The idea points to a reachable first market and a believable adoption path in {domain_label}.",
            "medium": "The go-to-market path still needs to be clearer and more specific.",
            "low": "The market entry path and adoption motion are still too vague.",
        },
        "validation": {
            "high": "The brief includes signals that suggest real demand, user pull, or early proof.",
            "medium": "The proof is still partial and needs stronger user validation.",
            "low": "There is very little evidence of interviews, pilots, traction, or real demand.",
        },
        "buildability": {
            "high": f"The team looks capable of shipping a focused first version around the {primary_workflow}.",
            "medium": f"The scope still needs discipline to keep the {primary_workflow} realistic.",
            "low": "The current scope and team setup do not strongly support a fast first release.",
        },
        "defensibility": {
            "high": "The idea hints at a wedge that could become difficult to copy over time.",
            "medium": "There may be a wedge here, but the durable advantage is not strong enough yet.",
            "low": "The idea does not yet show a clear moat, lock-in, or durable differentiation.",
        },
        "ai_fit": {
            "high": "AI appears to strengthen the core product instead of sitting on top superficially.",
            "medium": "AI could help here, but its role still needs to be more clearly justified.",
            "low": "AI does not appear essential to the value proposition in the current brief.",
        },
    }
    return rationale_map[key][band]


def build_score_breakdown(data: InnovationInput, skills: set[str]) -> list[ScoreBreakdown]:
    summary_text = data.idea_summary.lower()
    domain_boost = 1 if data.domain in {"health", "finance", "developer_tools"} else 0
    context = extract_context(data.domain, summary_text, skills)
    audience_group = audience_group_phrase(str(context["primary_audience"]))
    primary_workflow = str(context["primary_workflow"])
    domain_label = data.domain.replace("_", " ")

    urgency_keywords = {"urgent","pain","slow","manual","costly","delay","friction","problem","expensive","waste"}
    validation_keywords = {"users","customers","interview","pilot","feedback","waitlist","revenue","paid","usage","adoption"}
    moat_keywords = {"workflow","data","integration","network","proprietary","platform","automation","community"}
    distribution_keywords = {"team","sales","community","creator","school","clinic","enterprise","developer","partner"}
    build_keywords = {"dashboard","assistant","automation","prototype","mvp","api","workflow","tool"}

    pain_score = clamp_signal(4 + count_keyword_hits(summary_text, urgency_keywords) * 0.8 + domain_boost)
    market_score = clamp_signal(4 + count_keyword_hits(summary_text, distribution_keywords) * 0.65 + domain_boost)
    validation_score = clamp_signal(3 + count_keyword_hits(summary_text, validation_keywords) * 1.2)
    buildability_score = clamp_signal(4 + min(len(skills), 4) * 0.8 + count_keyword_hits(summary_text, build_keywords) * 0.45 + (1 if {"frontend","backend","fullstack"} & skills else 0))
    moat_score = clamp_signal(4 + count_keyword_hits(summary_text, moat_keywords) * 0.7)
    ai_fit_score = clamp_signal(3 + (2.5 if "ai" in summary_text else 0) + (1.5 if {"ai","ml","data"} & skills else 0) + (1 if "automation" in summary_text or "assistant" in summary_text else 0))

    return [
        ScoreBreakdown(key="painkiller", label="Urgency of Problem", score=pain_score, rationale=build_score_rationale("painkiller", pain_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
        ScoreBreakdown(key="timing", label="Market Timing", score=market_score, rationale=build_score_rationale("timing", market_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
        ScoreBreakdown(key="validation", label="Market Validation", score=validation_score, rationale=build_score_rationale("validation", validation_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
        ScoreBreakdown(key="buildability", label="Buildability", score=buildability_score, rationale=build_score_rationale("buildability", buildability_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
        ScoreBreakdown(key="defensibility", label="Competitive Advantage", score=moat_score, rationale=build_score_rationale("defensibility", moat_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
        ScoreBreakdown(key="ai_fit", label="AI Fit", score=ai_fit_score, rationale=build_score_rationale("ai_fit", ai_fit_score, audience_group=audience_group, primary_workflow=primary_workflow, domain_label=domain_label)),
    ]


ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"


def call_claude(prompt: str) -> dict | None:
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 2000,
        "system": (
            "You are a world-class startup advisor. "
            "You always respond with strict, parseable JSON — no markdown fences, no commentary, no extra keys. "
            "Every piece of advice must be grounded in the specific idea provided. "
            "Never produce generic startup advice that could apply to any idea."
        ),
        "messages": [{"role": "user", "content": prompt}],
    }
    request = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            raw = json.loads(response.read().decode("utf-8"))
        text = raw["content"][0]["text"].strip()
        text = re.sub(r"^```json\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)
    except Exception:
        return None


def build_personalized_content_prompt(
    data: InnovationInput,
    innovation_score: int,
    verdict: str,
    score_breakdown: list[ScoreBreakdown],
    context: dict[str, str | list[str]],
) -> str:
    breakdown_lines = "\n".join(f"  - {item.label}: {item.score}/10 — {item.rationale}" for item in score_breakdown)
    skills_str = ", ".join(data.team_skills) if data.team_skills else "not specified"
    project = data.project_name
    domain = data.domain.replace("_", " ")

    return f"""
You are analyzing a specific startup idea. Every output must be 100% specific to THIS idea.
Do not produce advice that could apply to any other startup.

=== STARTUP BRIEF ===
Project name: {project}
Domain: {domain}
Team skills: {skills_str}
Idea summary: {data.idea_summary}

=== SCORE CONTEXT ===
Overall innovation score: {innovation_score}/100
Verdict: {verdict}
Score breakdown:
{breakdown_lines}

Primary user group inferred: {context["primary_audience"]}
Primary workflow inferred: {context["primary_workflow"]}

=== YOUR TASK ===
Return a single JSON object with exactly these keys.

{{
  "summary": "2-3 sentence assessment of THIS specific idea.",
  "opportunity_statement": "1 sentence on the exact market gap this idea targets.",
  "strengths": ["Strength specific to this idea (min 8 words)", "Strength 2", "Strength 3"],
  "risks": ["Risk specific to this idea (min 8 words)", "Risk 2", "Risk 3"],
  "mvp_features": ["Concrete first feature for this exact product", "Feature 2", "Feature 3", "Feature 4"],
  "target_users": ["Specific user group 1 for this idea", "Group 2", "Group 3"],
  "differentiators": ["Why this beats existing alternatives", "Differentiator 2", "Differentiator 3"],
  "next_steps": ["Concrete action this team should take this week", "Step 2", "Step 3"],
  "tech_stack": ["Technology suited to this idea and team skills", "Tech 2", "Tech 3", "Tech 4"],
  "operator_summary": "2-3 sentence operator-style summary of this idea's investment-readiness.",
  "operator_report": "## Operator Score\\n{innovation_score}/100 ({verdict})\\n\\n## Investment View\\n<specific to this idea>\\n\\n## Score Breakdown Insight\\n<key score drivers>\\n\\n## Why This Could Work\\n<3 bullets>\\n\\n## Risks & Challenges\\n<3 bullets>\\n\\n## Recommended Next Steps\\n<3 bullets>",

  "architecture_blocks": [
    {{"title": "Component name specific to {project}", "detail": "What this does specifically for {project} and its {domain} users — not a generic web app description."}},
    {{"title": "Second component", "detail": "Specific role in {project}."}},
    {{"title": "Third component", "detail": "Specific role in {project}."}},
    {{"title": "Fourth component", "detail": "Specific role in {project}."}}
  ],

  "roadmap": [
    {{"title": "Phase name specific to {project} (not generic like 'Validation')", "tasks": ["Task naming the actual users, workflow, or feature from the brief", "Task 2", "Task 3"]}},
    {{"title": "Phase 2 name", "tasks": ["Task 1", "Task 2", "Task 3"]}},
    {{"title": "Phase 3 name", "tasks": ["Task 1", "Task 2", "Task 3"]}},
    {{"title": "Phase 4 name", "tasks": ["Task 1", "Task 2", "Task 3"]}},
    {{"title": "Phase 5 name", "tasks": ["Task 1", "Task 2", "Task 3"]}}
  ]
}}

RULES for architecture_blocks:
- Each block must name and describe a real component of {project} specifically.
- Detail must mention the actual product, users, or workflow — not generic "React frontend" or "FastAPI service".
- Think: what does {project} actually need to function? Input layer, matching engine, scoring logic, report surface, etc.

RULES for roadmap:
- Phase titles must be specific to {project} — e.g. "Validate the {domain} pain with 10 users" not just "Validation".
- Tasks must name the actual user group ({context["primary_audience"]}), actual workflow ({context["primary_workflow"]}), or actual feature.
- Do NOT write "Build the React frontend" or "Connect Ollama" — those are system details, not product milestones.

Return ONLY the JSON. No markdown, no commentary.
""".strip()


def fetch_claude_personalized_content(
    data: InnovationInput,
    innovation_score: int,
    verdict: str,
    score_breakdown: list[ScoreBreakdown],
    context: dict[str, str | list[str]],
) -> dict | None:
    prompt = build_personalized_content_prompt(data=data, innovation_score=innovation_score, verdict=verdict, score_breakdown=score_breakdown, context=context)
    payload = call_claude(prompt)
    if not payload:
        return None
    required_str_keys = ["summary", "opportunity_statement", "operator_summary", "operator_report"]
    required_list_keys = ["strengths", "risks", "mvp_features", "target_users", "differentiators", "next_steps", "tech_stack", "architecture_blocks", "roadmap"]
    for key in required_str_keys:
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            return None
    for key in required_list_keys:
        val = payload.get(key)
        if not isinstance(val, list) or len(val) < 2:
            return None
    return payload


def _fallback_strengths(score_breakdown, skills, summary_text, context, data):
    score_map = {item.key: item.score for item in score_breakdown}
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    domain = data.domain.replace("_", " ")
    strengths = []
    if score_map["painkiller"] >= 7:
        strengths.append(f"{project} targets a concrete pain point for {audience} in {domain}, not a vague nice-to-have.")
    if score_map["buildability"] >= 7:
        strengths.append(f"The team's skills are well-matched to ship a first {workflow} without major gaps.")
    if score_map["validation"] >= 6:
        strengths.append(f"The brief contains early demand signals that suggest {audience} would engage with {project}.")
    if score_map["ai_fit"] >= 7 and "ai" in summary_text:
        strengths.append(f"AI is woven into the core {workflow} rather than bolted on as a feature.")
    if {"frontend", "backend", "fullstack"} & skills:
        strengths.append(f"The listed skills make this team credible for shipping the {workflow} end-to-end.")
    return strengths[:4] or [f"{project} has a clear enough structure to evaluate, but the operator thesis still needs sharpening."]


def _fallback_risks(score_breakdown, skills, summary_text, context, data):
    score_map = {item.key: item.score for item in score_breakdown}
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    moats = list(context.get("moats", []))
    risks = []
    if score_map["validation"] <= 4:
        risks.append(f"{project} lacks proof that {audience} will urgently adopt this — validation must come before further building.")
    if score_map["timing"] <= 5:
        risks.append(f"The go-to-market path for reaching {audience} in {data.domain.replace('_', ' ')} is still vague.")
    if score_map["defensibility"] <= 5:
        risks.append(f"Without a clear moat, a well-funded competitor could replicate the {workflow} quickly.")
    elif moats:
        risks.append(f"{project} will need to actively turn {moats[0]} into a durable advantage.")
    if 0 < len(skills) <= 2:
        risks.append("The team is thin — a two-person crew risks slow delivery or blind spots in key areas.")
    if "ai" in summary_text and score_map["ai_fit"] <= 5:
        risks.append("AI is mentioned but the brief doesn't prove why it's necessary.")
    return risks[:4] or [f"The main execution risk is scope creep beyond the core {workflow} before demand is proven."]


def _fallback_mvp_features(domain, summary_text, context, data):
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    base = [
        f"Core {workflow} tailored specifically to {audience} — the one thing {project} does better than anything else.",
        f"Guided onboarding capturing just enough context from {audience} to personalise the {workflow}.",
        "Transparent results view that explains the output so users trust and act on it.",
    ]
    if "ai" in summary_text:
        base.append(f"One visible AI step inside the {workflow} that users can experience in under 60 seconds.")
    if "automation" in summary_text:
        base.append("One automation that removes the most repeated manual step for the user.")
    return unique_items(base)[:5]


def _fallback_target_users(domain, context):
    audiences = list(context["audiences"])
    domain_expansion = {
        "education": "Campus incubators and EdTech pilots", "health": "Health-tech startups",
        "sustainability": "Climate-focused operators", "finance": "Fintech product teams",
        "media": "Independent media startups", "community": "Social impact organisations",
        "developer_tools": "Product engineering leads", "general": "Early-stage startup founders",
    }
    return unique_items(audiences + [domain_expansion[domain]])[:4]


def _fallback_differentiators(domain, summary_text, skills, context, data):
    workflow = str(context["primary_workflow"])
    audience = audience_group_phrase(str(context["primary_audience"]))
    project = data.project_name
    moats = list(context.get("moats", []))
    diffs = [
        f"{project} offers a tighter {workflow} for {audience} than broad horizontal tools.",
        "Outputs are explainable — users see the reasoning, not just a score.",
    ]
    if "ai" in summary_text:
        diffs.append(f"AI is applied inside the {workflow} only where it materially improves outcomes.")
    if moats:
        diffs.append(f"The concept has a path to defensibility through {moats[0]} as the user base grows.")
    return diffs[:4]


def _fallback_next_steps(score_breakdown, skills, domain, context, data):
    score_map = {item.key: item.score for item in score_breakdown}
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    steps = [
        f"Write a one-page brief for {project}: one user type ({audience}), one painful workflow ({workflow}), one promised outcome.",
        f"Run five interviews with {audience} — capture their exact language, not your assumptions.",
        f"Build a single-path prototype of the {workflow} that proves core value in under two minutes.",
    ]
    if score_map["validation"] <= 5:
        steps[1] = f"Before writing code, collect 5-10 responses from {audience} confirming they actively feel this pain."
    if score_map["buildability"] <= 5:
        steps[2] = "Scope the MVP to one screen, one action, and one measurable success signal for week one."
    if not ({"marketing", "growth", "sales"} & skills):
        steps.append(f"Map one specific distribution channel in the {domain.replace('_', ' ')} space and run a small pilot.")
    return steps[:4]


def _fallback_tech_stack(data, skills, summary_text, context):
    stack: list[str] = []
    workflow = str(context["primary_workflow"])
    if {"frontend", "ui", "ux", "design"} & skills:
        stack.extend(["React", "Vite"])
    if {"backend", "fullstack", "api"} & skills:
        stack.extend(["FastAPI", "Python"])
    if not stack:
        stack.extend(["React", "FastAPI"])
    if "ai" in summary_text or {"ai", "ml", "data"} & skills:
        stack.extend(["Claude API", "Prompt orchestration layer"])
    if "dashboard" in summary_text or "analytics" in summary_text:
        stack.append("Analytics dashboard")
    if data.domain == "health":
        stack.append("Audit-friendly backend with access logging")
    if data.domain == "finance":
        stack.append("Secure transaction-ready API with encryption at rest")
    if data.domain == "developer_tools":
        stack.append("Developer-facing API with OpenAPI docs")
    stack.append(f"Focused {workflow} product flow")
    return unique_items(stack)[:8]


def _fallback_architecture_blocks(data, skills, summary_text, context):
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    domain = data.domain.replace("_", " ")
    blocks = [
        ArchitectureBlock(
            title=f"{project} input layer",
            detail=f"A focused interface where {audience} describe their {domain} problem so the system can personalise its response.",
        ),
        ArchitectureBlock(
            title=f"{workflow.capitalize()} engine",
            detail=f"The core backend logic that processes inputs, runs the {workflow}, and produces structured output for {audience}.",
        ),
    ]
    if "ai" in summary_text or {"ai", "ml", "data"} & skills:
        blocks.append(ArchitectureBlock(
            title="AI reasoning layer",
            detail=f"Calls the language model to generate personalised insights and operator-grade analysis for {project}.",
        ))
    else:
        blocks.append(ArchitectureBlock(
            title="Analysis and scoring layer",
            detail=f"Derives signal from the {domain} brief using structured scoring rules and domain-aware heuristics.",
        ))
    blocks.append(ArchitectureBlock(
        title="Results and report surface",
        detail=f"Presents the {workflow} output, score breakdown, roadmap, and next steps clearly to {audience} in one view.",
    ))
    return blocks[:4]


def _fallback_roadmap(data, score_breakdown, skills, context):
    score_map = {item.key: item.score for item in score_breakdown}
    audience = audience_group_phrase(str(context["primary_audience"]))
    workflow = str(context["primary_workflow"])
    project = data.project_name
    domain = data.domain.replace("_", " ")
    moats = list(context.get("moats", []))
    moat_str = moats[0] if moats else "unique data or workflow advantage"
    validation_task = (
        f"Collect 5-10 written responses from {audience} confirming they feel this pain before writing code."
        if score_map["validation"] <= 5
        else f"Interview five {audience} and map the exact friction in their current {workflow}."
    )
    return [
        RoadmapPhase(
            title=f"Define the {project} problem sharply",
            tasks=[
                f"Rewrite the {domain} problem as one sentence: who is {audience}, what pain they feel, and what {project} does differently.",
                f"Identify the single most painful step in the current {workflow} that {audience} want removed.",
                "Turn the project summary into one value proposition sentence and one measurable success metric.",
            ],
        ),
        RoadmapPhase(
            title=f"Validate with real {audience}",
            tasks=[
                validation_task,
                f"Test whether {audience} describe the {domain} problem in the same language as the project summary.",
                f"Collect objections and use them to sharpen the {project} pitch before building anything.",
            ],
        ),
        RoadmapPhase(
            title=f"Scope the {project} MVP",
            tasks=[
                f"Cut the first release to the single {workflow} path that delivers clear value in under two minutes.",
                f"Use the recommended MVP features as the hard scope boundary — no additions until {audience} validate the core.",
                "Define one success metric that proves the MVP worked before moving to phase four.",
            ],
        ),
        RoadmapPhase(
            title=f"Build the {project} core",
            tasks=[
                f"Build the {workflow} end-to-end using {', '.join(list(skills)[:3]) if skills else 'the listed team skills'}.",
                f"Connect the AI or analysis layer so {audience} get a personalised output, not a generic template.",
                "Ship an internal demo and test it with the users from the validation phase.",
            ],
        ),
        RoadmapPhase(
            title=f"Launch and grow {project}",
            tasks=[
                f"Run a closed beta with {audience} from the {domain} space and collect structured feedback.",
                f"Use {moat_str} as the primary retention driver — make switching away progressively harder.",
                f"Define the first paid tier and test whether {audience} will pay before scaling distribution.",
            ],
        ),
    ]


def _fallback_operator_report(data, innovation_score, verdict, strengths, risks, next_steps):
    lines = [
        "## Operator Score", f"{innovation_score}/100 ({verdict})", "",
        "## Investment View",
        f"{data.project_name} has a plausible wedge in {data.domain.replace('_', ' ')}, but wins only if the team keeps the first version brutally focused.",
        "", "## Why This Could Work", *[f"- {item}" for item in strengths[:3]],
        "", "## Risks & Challenges", *[f"- {item}" for item in risks[:3]],
        "", "## Recommended Next Steps", *[f"- {item}" for item in next_steps[:3]],
    ]
    return "\n".join(lines)


def _parse_architecture_blocks(raw: list) -> list[ArchitectureBlock]:
    blocks = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = clean_model_text(item.get("title"))
        detail = clean_model_text(item.get("detail"))
        if title and detail:
            blocks.append(ArchitectureBlock(title=title, detail=detail))
    return blocks[:4]


def _parse_roadmap(raw: list) -> list[RoadmapPhase]:
    phases = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = clean_model_text(item.get("title"))
        tasks_raw = item.get("tasks", [])
        tasks = [clean_model_text(t) for t in tasks_raw if isinstance(t, str) and t.strip()]
        if title and len(tasks) >= 2:
            phases.append(RoadmapPhase(title=title, tasks=tasks[:4]))
    return phases[:5]


def build_assessment(data: InnovationInput) -> InnovationResponse:
    skills = normalize_skills(data.team_skills)
    summary_text = data.idea_summary.lower()
    context = extract_context(data.domain, summary_text, skills)
    score_breakdown = build_score_breakdown(data, skills)
    innovation_score = clamp(sum(item.score for item in score_breakdown) / len(score_breakdown) * 10)

    if innovation_score >= 75:
        verdict = "Prototype Now"
    elif innovation_score >= 55:
        verdict = "Needs Validation"
    else:
        verdict = "Reframe Idea"

    claude_payload = fetch_claude_personalized_content(
        data=data, innovation_score=innovation_score, verdict=verdict,
        score_breakdown=score_breakdown, context=context,
    )

    if claude_payload:
        summary = clean_model_text(claude_payload.get("summary"))
        opportunity_statement = clean_model_text(claude_payload.get("opportunity_statement"))
        operator_summary = clean_model_text(claude_payload.get("operator_summary"))
        operator_report = clean_model_text(claude_payload.get("operator_report"))
        strengths = clean_model_list(claude_payload.get("strengths"), min_words=4)
        risks = clean_model_list(claude_payload.get("risks"), min_words=4)
        mvp_features = clean_model_list(claude_payload.get("mvp_features"), min_words=3)
        target_users = clean_model_list(claude_payload.get("target_users"), minimum=2, maximum=4, min_words=1)
        differentiators = clean_model_list(claude_payload.get("differentiators"), min_words=4)
        next_steps = clean_model_list(claude_payload.get("next_steps"), min_words=4)
        tech_stack = clean_model_list(claude_payload.get("tech_stack"), minimum=2, maximum=8, min_words=1)
        architecture_blocks = _parse_architecture_blocks(claude_payload.get("architecture_blocks", []))
        roadmap = _parse_roadmap(claude_payload.get("roadmap", []))
        if not architecture_blocks:
            architecture_blocks = _fallback_architecture_blocks(data, skills, summary_text, context)
        if not roadmap:
            roadmap = _fallback_roadmap(data, score_breakdown, skills, context)
    else:
        strengths = _fallback_strengths(score_breakdown, skills, summary_text, context, data)
        risks = _fallback_risks(score_breakdown, skills, summary_text, context, data)
        mvp_features = _fallback_mvp_features(data.domain, summary_text, context, data)
        target_users = _fallback_target_users(data.domain, context)
        differentiators = _fallback_differentiators(data.domain, summary_text, skills, context, data)
        next_steps = _fallback_next_steps(score_breakdown, skills, data.domain, context, data)
        tech_stack = _fallback_tech_stack(data, skills, summary_text, context)
        architecture_blocks = _fallback_architecture_blocks(data, skills, summary_text, context)
        roadmap = _fallback_roadmap(data, score_breakdown, skills, context)

        verdict_phrase = {"Prototype Now": "prototype-now", "Needs Validation": "needs-validation", "Reframe Idea": "reframe-first"}[verdict]
        listed_skills = ", ".join(sorted(skills)[:3]) if skills else "generalist skills"
        summary = (
            "This concept is strong enough to prototype now if the team keeps scope tight and proves demand quickly." if verdict == "Prototype Now"
            else "This concept has promise, but it needs sharper proof, sharper positioning, or both." if verdict == "Needs Validation"
            else "This concept needs a clearer wedge, stronger urgency, or a more believable go-to-market path before building."
        )
        opportunity_statement = (
            f"{data.project_name} can turn a {data.domain.replace('_', ' ')} challenge into "
            f"an execution-ready product by combining {listed_skills} with focused validation and operator-level execution discipline."
        )
        operator_summary = (
            f"Operator score: {innovation_score}/100. {data.project_name} currently looks {verdict_phrase} "
            f"in {data.domain.replace('_', ' ')} based on pain clarity, distribution logic, buildability, and validation signals."
        )
        operator_report = _fallback_operator_report(data=data, innovation_score=innovation_score, verdict=verdict, strengths=strengths, risks=risks, next_steps=next_steps)

    return InnovationResponse(
        innovation_score=innovation_score,
        verdict=verdict,
        operator_summary=operator_summary,
        operator_report=operator_report,
        summary=summary,
        opportunity_statement=opportunity_statement,
        score_breakdown=score_breakdown,
        strengths=strengths[:4],
        risks=risks[:4],
        mvp_features=mvp_features[:5],
        target_users=target_users[:4],
        differentiators=differentiators[:4],
        next_steps=next_steps[:4],
        tech_stack=tech_stack[:8],
        architecture_blocks=architecture_blocks[:4],
        roadmap=roadmap[:5],
    )