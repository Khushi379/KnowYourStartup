from __future__ import annotations

import json
import os
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.schemas import InnovationInput, InnovationResponse, ScoreBreakdown


def clamp(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def clamp_signal(value: float) -> int:
    return clamp(value, 1, 10)


def normalize_skills(skills: list[str]) -> set[str]:
    return {skill.strip().lower() for skill in skills if skill.strip()}


def count_keyword_hits(text: str, keywords: set[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def build_assessment(data: InnovationInput) -> InnovationResponse:
    skills = normalize_skills(data.team_skills)
    summary_text = data.idea_summary.lower()
    score_breakdown = build_score_breakdown(data, skills)
    innovation_score = clamp(
        sum(item.score for item in score_breakdown) / len(score_breakdown) * 10
    )

    if innovation_score >= 75:
        verdict = "Prototype Now"
    elif innovation_score >= 55:
        verdict = "Needs Validation"
    else:
        verdict = "Reframe Idea"

    strengths = build_strengths(score_breakdown, skills, summary_text)
    risks = build_risks(score_breakdown, skills, summary_text)
    mvp_features = recommend_features(data.domain, summary_text)
    target_users = recommend_users(data.domain)
    differentiators = recommend_differentiators(data.domain, summary_text, skills)
    next_steps = recommend_next_steps(score_breakdown, skills, data.domain)

    listed_skills = ", ".join(sorted(skills)[:3]) if skills else "generalist"
    opportunity_statement = (
        f"{data.project_name} can turn a {data.domain.replace('_', ' ')} challenge into "
        f"an execution-ready product by combining {listed_skills} capabilities "
        "with focused validation and operator-level execution discipline."
    )

    summary = (
        "This concept is strong enough to prototype now if the team keeps scope tight and proves demand quickly."
        if verdict == "Prototype Now"
        else "This concept has promise, but it needs sharper proof, sharper positioning, or both."
        if verdict == "Needs Validation"
        else "This concept needs a clearer wedge, stronger urgency, or a more believable go-to-market path before building."
    )

    operator_summary = (
        f"Operator score: {innovation_score}/100. "
        f"{data.project_name} looks like a {verdict.lower()} idea in {data.domain.replace('_', ' ')} "
        "based on pain clarity, distribution logic, buildability, and validation signals pulled from the founder brief."
    )
    operator_report = generate_operator_report(
        data=data,
        innovation_score=innovation_score,
        verdict=verdict,
        score_breakdown=score_breakdown,
        strengths=strengths,
        risks=risks,
        next_steps=next_steps,
    )

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
        mvp_features=mvp_features,
        target_users=target_users,
        differentiators=differentiators,
        next_steps=next_steps,
    )


def build_score_breakdown(
    data: InnovationInput, skills: set[str]
) -> list[ScoreBreakdown]:
    summary_text = data.idea_summary.lower()
    domain_boost = 1 if data.domain in {"health", "finance", "developer_tools"} else 0

    urgency_keywords = {
        "urgent",
        "pain",
        "slow",
        "manual",
        "costly",
        "delay",
        "friction",
        "problem",
        "expensive",
        "waste",
    }
    validation_keywords = {
        "users",
        "customers",
        "interview",
        "pilot",
        "feedback",
        "waitlist",
        "revenue",
        "paid",
        "usage",
        "adoption",
    }
    moat_keywords = {
        "workflow",
        "data",
        "integration",
        "network",
        "proprietary",
        "platform",
        "automation",
        "community",
    }
    distribution_keywords = {
        "team",
        "sales",
        "community",
        "creator",
        "school",
        "clinic",
        "enterprise",
        "developer",
        "partner",
    }
    build_keywords = {
        "dashboard",
        "assistant",
        "automation",
        "prototype",
        "mvp",
        "api",
        "workflow",
        "tool",
    }

    pain_score = clamp_signal(
        4 + count_keyword_hits(summary_text, urgency_keywords) * 0.8 + domain_boost
    )
    market_score = clamp_signal(
        4 + count_keyword_hits(summary_text, distribution_keywords) * 0.65 + domain_boost
    )
    validation_score = clamp_signal(
        3 + count_keyword_hits(summary_text, validation_keywords) * 1.2
    )
    buildability_score = clamp_signal(
        4
        + min(len(skills), 4) * 0.8
        + count_keyword_hits(summary_text, build_keywords) * 0.45
        + (1 if {"frontend", "backend", "fullstack"} & skills else 0)
    )
    moat_score = clamp_signal(4 + count_keyword_hits(summary_text, moat_keywords) * 0.7)
    ai_fit_score = clamp_signal(
        3
        + (2.5 if "ai" in summary_text else 0)
        + (1.5 if {"ai", "ml", "data"} & skills else 0)
        + (1 if "automation" in summary_text or "assistant" in summary_text else 0)
    )

    return [
        ScoreBreakdown(
            key="painkiller",
            label="Painkiller Strength",
            score=pain_score,
            rationale="Higher when the brief describes urgent, costly, or repeated pain.",
        ),
        ScoreBreakdown(
            key="timing",
            label="Market Timing",
            score=market_score,
            rationale="Higher when the brief hints at a reachable market and a credible adoption context.",
        ),
        ScoreBreakdown(
            key="validation",
            label="Validation Proof",
            score=validation_score,
            rationale="Higher when the brief mentions user interviews, pilots, traction, or real demand signals.",
        ),
        ScoreBreakdown(
            key="buildability",
            label="Buildability",
            score=buildability_score,
            rationale="Higher when the product is narrow enough to ship and the listed skills match the build.",
        ),
        ScoreBreakdown(
            key="defensibility",
            label="Defensibility",
            score=moat_score,
            rationale="Higher when the idea has workflow lock-in, unique data, or a repeatable advantage.",
        ),
        ScoreBreakdown(
            key="ai_fit",
            label="AI Fit",
            score=ai_fit_score,
            rationale="Higher when AI clearly improves the core product instead of being a thin add-on.",
        ),
    ]


def recommend_features(domain: str, summary_text: str) -> list[str]:
    base = [
        "Focused founder input form with sharp problem framing",
        "Operator-style scoring output with clear rationale",
        "Recommendation engine for MVP scope and target users",
        "Execution checklist for the first validation sprint",
    ]

    if "ai" in summary_text:
        base.append("Visible AI workflow that users can understand and test in one session")
    if domain in {"education", "health", "community"}:
        base.append("User persona and stakeholder needs mapping")
    else:
        base.append("Market and differentiator checklist for first distribution tests")

    return base[:5]


def recommend_users(domain: str) -> list[str]:
    mapping = {
        "education": ["Student founders", "Campus incubators", "Hackathon teams"],
        "health": ["Health startups", "Student innovation labs", "Wellness founders"],
        "sustainability": ["Climate builders", "Green startup teams", "Civic innovators"],
        "finance": ["Fintech teams", "Student entrepreneurs", "Startup accelerators"],
        "media": ["Creator-tech founders", "Media startups", "Hackathon builders"],
        "community": ["NGOs", "Student communities", "Social innovation teams"],
        "developer_tools": ["Devtool founders", "Engineering teams", "Product hackers"],
        "general": ["Hackathon teams", "Student founders", "Early-stage startups"],
    }
    return mapping[domain]


def recommend_differentiators(
    domain: str, summary_text: str, skills: set[str]
) -> list[str]:
    differentiators = [
        "A clearer operating thesis than generic idea-validation tools.",
        "Explainable scoring that reads like an operator memo instead of a black-box score.",
        "Focused next steps that convert analysis into immediate execution moves.",
    ]

    if "ai" in summary_text:
        differentiators.append(
            "AI is treated as a product lever only when it makes the core workflow materially better."
        )
    if {"design", "ui", "ux"} & skills:
        differentiators.append(
            "A stronger design angle can improve clarity, adoption, and demo quality."
        )
    if domain in {"education", "health", "community"}:
        differentiators.append(
            "The concept can show both practical value and broader social impact."
        )

    return differentiators[:4]


def build_strengths(
    score_breakdown: list[ScoreBreakdown], skills: set[str], summary_text: str
) -> list[str]:
    strengths = []
    score_map = {item.key: item.score for item in score_breakdown}

    if score_map["painkiller"] >= 7:
        strengths.append(
            "The brief suggests a real painkiller problem instead of a nice-to-have idea."
        )
    if score_map["buildability"] >= 7:
        strengths.append(
            "This looks narrow enough to ship as an MVP without boiling the ocean."
        )
    if score_map["validation"] >= 6:
        strengths.append(
            "There are signs of real-world demand or customer learning in the brief."
        )
    if {"frontend", "backend", "fullstack"} & skills:
        strengths.append(
            "The listed team skills are credible for shipping a first working version."
        )
    if "ai" in summary_text and score_map["ai_fit"] >= 7:
        strengths.append(
            "AI appears to improve the core workflow rather than acting like a cosmetic add-on."
        )

    return strengths[:4] or [
        "The concept has enough structure to evaluate, but it still needs a sharper operator thesis."
    ]


def build_risks(
    score_breakdown: list[ScoreBreakdown], skills: set[str], summary_text: str
) -> list[str]:
    risks = []
    score_map = {item.key: item.score for item in score_breakdown}

    if score_map["validation"] <= 4:
        risks.append(
            "The brief does not show enough proof that users will urgently adopt this."
        )
    if score_map["timing"] <= 5:
        risks.append("The go-to-market path is still vague, which makes adoption riskier.")
    if score_map["defensibility"] <= 5:
        risks.append(
            "The wedge is not yet differentiated enough to stay defensible once copied."
        )
    if 0 < len(skills) <= 2:
        risks.append(
            "A thin team could turn a good concept into a slow or incomplete launch."
        )
    if "ai" in summary_text and score_map["ai_fit"] <= 5:
        risks.append("AI is mentioned, but the brief does not yet prove why AI is required.")

    return risks[:4] or [
        "The main risk is execution drift if the first version expands beyond one obvious workflow."
    ]


def recommend_next_steps(
    score_breakdown: list[ScoreBreakdown], skills: set[str], domain: str
) -> list[str]:
    score_map = {item.key: item.score for item in score_breakdown}
    next_steps = [
        "Rewrite the idea as one user, one painful workflow, and one promised outcome.",
        "Interview five target users and capture the exact language they use to describe the problem.",
        "Build a single-path MVP demo that proves the core value in under two minutes.",
    ]

    if score_map["validation"] <= 5:
        next_steps[1] = "Validate demand with five to ten user calls before adding more features."
    if score_map["buildability"] <= 5:
        next_steps[2] = "Cut the MVP to one screen, one workflow, and one success metric for week one."
    if not ({"marketing", "growth", "sales"} & skills):
        next_steps.append(
            f"Define a first distribution wedge for the {domain.replace('_', ' ')} market."
        )

    return next_steps[:4]


def generate_operator_report(
    *,
    data: InnovationInput,
    innovation_score: int,
    verdict: str,
    score_breakdown: list[ScoreBreakdown],
    strengths: list[str],
    risks: list[str],
    next_steps: list[str],
) -> str:
    ollama_report = fetch_ollama_report(
        data=data,
        innovation_score=innovation_score,
        verdict=verdict,
        score_breakdown=score_breakdown,
        strengths=strengths,
        risks=risks,
        next_steps=next_steps,
    )
    if ollama_report:
        return ollama_report

    lines = [
        "## Operator Score",
        f"{innovation_score}/100 ({verdict})",
        "",
        "## Investment View",
        f"{data.project_name} has a plausible wedge in {data.domain.replace('_', ' ')}, but it wins only if the team keeps the first version brutally focused.",
        "",
        "## Why This Could Work",
        *[f"- {item}" for item in strengths[:3]],
        "",
        "## What Breaks It",
        *[f"- {item}" for item in risks[:3]],
        "",
        "## Next 3 Moves",
        *[f"- {item}" for item in next_steps[:3]],
    ]
    return "\n".join(lines)


def fetch_ollama_report(
    *,
    data: InnovationInput,
    innovation_score: int,
    verdict: str,
    score_breakdown: list[ScoreBreakdown],
    strengths: list[str],
    risks: list[str],
    next_steps: list[str],
) -> str | None:
    prompt = build_ollama_prompt(
        data=data,
        innovation_score=innovation_score,
        verdict=verdict,
        score_breakdown=score_breakdown,
        strengths=strengths,
        risks=risks,
        next_steps=next_steps,
    )
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "qwen3-coder"),
        "prompt": prompt,
        "stream": False,
    }
    request = Request(
        os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (TimeoutError, URLError, OSError, json.JSONDecodeError):
        return None

    response_text = body.get("response", "").strip()
    cleaned = re.sub(r"<think>.*?</think>", "", response_text, flags=re.DOTALL).strip()
    return cleaned or None


def build_ollama_prompt(
    *,
    data: InnovationInput,
    innovation_score: int,
    verdict: str,
    score_breakdown: list[ScoreBreakdown],
    strengths: list[str],
    risks: list[str],
    next_steps: list[str],
) -> str:
    breakdown = "\n".join(
        f"- {item.label}: {item.score}/10. {item.rationale}" for item in score_breakdown
    )
    strength_lines = "\n".join(f"- {item}" for item in strengths[:4])
    risk_lines = "\n".join(f"- {item}" for item in risks[:4])
    next_step_lines = "\n".join(f"- {item}" for item in next_steps[:4])

    return f"""
You are a startup operator writing a concise investment-style memo.
Score the idea only from the founder input below and the supplied scoring hints.
Do not mention readiness signals, sliders, or UI.
Write plain Markdown with exactly these headings:
## Operator Score
## Investment View
## Why This Could Work
## What Breaks It
## Next 3 Moves

Founder input:
Project: {data.project_name}
Domain: {data.domain}
Team skills: {", ".join(data.team_skills) if data.team_skills else "Not provided"}
Summary: {data.idea_summary}

Scoring hints:
Overall score: {innovation_score}/100
Verdict: {verdict}
{breakdown}

Strengths:
{strength_lines}

Risks:
{risk_lines}

Recommended next steps:
{next_step_lines}

Keep it under 220 words.
""".strip()
