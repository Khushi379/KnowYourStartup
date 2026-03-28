from typing import Literal

from pydantic import BaseModel, Field


class InnovationInput(BaseModel):
    project_name: str = Field(min_length=2, max_length=80)
    idea_summary: str = Field(min_length=20, max_length=800)
    domain: Literal[
        "education",
        "health",
        "sustainability",
        "finance",
        "media",
        "community",
        "developer_tools",
        "general",
    ]
    team_skills: list[str] = Field(default_factory=list, max_length=8)


class ScoreBreakdown(BaseModel):
    key: str
    label: str
    score: int = Field(ge=1, le=10)
    rationale: str


class InnovationResponse(BaseModel):
    innovation_score: int = Field(ge=0, le=100)
    verdict: Literal["Prototype Now", "Needs Validation", "Reframe Idea"]
    operator_summary: str
    operator_report: str
    summary: str
    opportunity_statement: str
    score_breakdown: list[ScoreBreakdown]
    strengths: list[str]
    risks: list[str]
    mvp_features: list[str]
    target_users: list[str]
    differentiators: list[str]
    next_steps: list[str]
