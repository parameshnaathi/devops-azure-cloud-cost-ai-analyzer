\# Prompt 2: OpenAI API Integration for Cost Analysis



Build on top of the existing FastAPI backend. Add AI-powered cost analysis using the OpenAI API directly.



\## What to build



\- Create an `ai\_analyzer.py` module in `backend/` that:

&#x20; - Takes the list of Azure resources (from `azure\_scanner.py`) as input.

&#x20; - Builds a prompt asking the AI to analyze the resources for: over-provisioning, unused/idle resources, misconfigurations, wrong pricing tiers, and cost optimization opportunities.

&#x20; - Calls the OpenAI chat completions API (`gpt-4o`) and returns the structured analysis.

\- The AI response should include: a summary, list of issues found (with severity: high/medium/low), estimated savings, and actionable fix commands (Azure CLI commands the user can run).

\- Update `POST /api/analyze` to call `azure\_scanner` first, then pass results to `ai\_analyzer`, and return the final analysis.

\- Store the OpenAI API key in environment variables. Add a `.env.example` file.

\- Update `requirements.txt` — add `openai`, `python-dotenv`.



\## Project structure update



```

backend/

├── main.py          (updated)

├── azure\_scanner.py (no change)

├── ai\_analyzer.py   (new)

├── requirements.txt (updated)

├── .env.example     (new — OPENAI\_API\_KEY)

```



Refer to `Architecture.MD` and `RequestFlow.MD`. This covers step ⑤ of the request flow.

