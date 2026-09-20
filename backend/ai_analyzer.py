"""AI-powered Azure cost analysis using the OpenAI API (step 5 of the request flow)."""

from __future__ import annotations

import json
import os
from typing import Any, Literal

from openai import APIError, AuthenticationError, OpenAI, OpenAIError, RateLimitError
from pydantic import BaseModel, Field, ValidationError

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_RESOURCES_IN_PROMPT = 200

SYSTEM_PROMPT = """You are a FinOps / cloud cost optimization expert specializing in Microsoft Azure.
Given a JSON list of Azure resources from one resource group, analyze them for:
- Over-provisioning (VMs, disks, App Service plans, etc. sized larger than the workload needs)
- Unused or idle resources (deallocated VMs still incurring disk/IP cost, unattached disks,
  empty App Service plans, unused public IPs, etc.)
- Misconfigurations (missing auto-shutdown, no lifecycle policies, redundant resources, etc.)
- Wrong pricing tiers / SKUs (Premium/Standard used where a cheaper tier would suffice)
- General cost optimization opportunities (reservations, autoscale, right-sizing, cleanup)

Respond with ONLY a single JSON object (no markdown fences, no commentary) matching exactly
this schema:
{
  "summary": "<2-4 sentence plain-English summary of overall cost health>",
  "issues": [
    {
      "resource_name": "<name of the affected resource>",
      "resource_type": "<Azure resource type>",
      "issue_type": "over_provisioned" | "unused" | "misconfigured" | "wrong_pricing_tier" | "other",
      "severity": "high" | "medium" | "low",
      "description": "<what is wrong and why it costs money>",
      "recommendation": "<what to change>",
      "fix_command": "<a single runnable Azure CLI command that fixes this specific issue>"
    }
  ],
  "estimated_savings": {
    "monthly_usd": <number, best-effort estimate, 0 if none>,
    "currency": "USD",
    "notes": "<assumptions behind the estimate>"
  },
  "fix_commands": [
    {
      "description": "<what this command does>",
      "command": "<a single runnable Azure CLI command>"
    }
  ]
}
"fix_commands" should list every distinct command from the issues above (deduplicated), for a
consolidated "run all fixes" view. If there are no resources or no issues, return empty lists
and an estimated_savings of 0 with an explanatory summary. Do not invent resources that were
not provided."""


class AIAnalyzerError(Exception):
    """Raised when the OpenAI API cannot be used or returns an unusable response."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class Issue(BaseModel):
    resource_name: str = "unknown"
    resource_type: str = "unknown"
    issue_type: Literal[
        "over_provisioned", "unused", "misconfigured", "wrong_pricing_tier", "other"
    ] = "other"
    severity: Literal["high", "medium", "low"] = "low"
    description: str = ""
    recommendation: str = ""
    fix_command: str = ""


class EstimatedSavings(BaseModel):
    monthly_usd: float = 0.0
    currency: str = "USD"
    notes: str = ""


class FixCommand(BaseModel):
    description: str = ""
    command: str = ""


class CostAnalysis(BaseModel):
    summary: str
    issues: list[Issue] = Field(default_factory=list)
    estimated_savings: EstimatedSavings = Field(default_factory=EstimatedSavings)
    fix_commands: list[FixCommand] = Field(default_factory=list)


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIAnalyzerError(
            "OPENAI_API_KEY is not set. Add it to backend/.env (see .env.example).",
            status_code=500,
        )
    return OpenAI(api_key=api_key)


def _resource_group_summary(resource_group: str, resources: list[dict[str, Any]]) -> str:
    trimmed = resources[:MAX_RESOURCES_IN_PROMPT]
    payload = {
        "resource_group": resource_group,
        "resource_count": len(resources),
        "resources": trimmed,
    }
    prompt = (
        f"Resource group: {resource_group}\n"
        f"Total resources: {len(resources)}\n\n"
        "Resources (JSON):\n"
        f"{json.dumps(payload['resources'], indent=2, default=str)}"
    )
    if len(resources) > MAX_RESOURCES_IN_PROMPT:
        prompt += (
            f"\n\n(Note: only the first {MAX_RESOURCES_IN_PROMPT} of {len(resources)} "
            "resources are shown above due to size limits.)"
        )
    return prompt


def _empty_analysis(resource_group: str) -> CostAnalysis:
    return CostAnalysis(
        summary=f"No resources were found in resource group '{resource_group}', "
        "so there is nothing to optimize.",
    )


def analyze_resources(resource_group: str, resources: list[dict[str, Any]]) -> CostAnalysis:
    """Send the scanned resources to OpenAI and return a structured cost analysis."""
    if not resources:
        return _empty_analysis(resource_group)

    client = _client()
    user_prompt = _resource_group_summary(resource_group, resources)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
    except AuthenticationError as exc:
        raise AIAnalyzerError(
            "OpenAI rejected the API key. Check OPENAI_API_KEY.", status_code=401
        ) from exc
    except RateLimitError as exc:
        raise AIAnalyzerError(
            "OpenAI rate limit or quota exceeded. Try again later.", status_code=429
        ) from exc
    except APIError as exc:
        raise AIAnalyzerError(f"OpenAI API error: {exc}", status_code=502) from exc
    except OpenAIError as exc:
        raise AIAnalyzerError(f"Failed to call OpenAI API: {exc}", status_code=502) from exc

    content = (response.choices[0].message.content or "").strip()
    if not content:
        raise AIAnalyzerError("OpenAI returned an empty analysis.", status_code=502)

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIAnalyzerError(
            "OpenAI response was not valid JSON.", status_code=502
        ) from exc

    try:
        return CostAnalysis.model_validate(parsed)
    except ValidationError as exc:
        raise AIAnalyzerError(
            f"OpenAI response did not match the expected schema: {exc}", status_code=502
        ) from exc
