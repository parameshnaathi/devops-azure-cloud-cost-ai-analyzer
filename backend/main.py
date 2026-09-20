"""FastAPI backend for the AI Cloud Cost Detective (steps 1 through 6 of the request flow)."""

from __future__ import annotations

import uuid
from collections import Counter
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

import ai_analyzer
import auth
import azure_scanner
import db
from ai_analyzer import AIAnalyzerError, CostAnalysis
from auth import AuthError, LoginRequest, SignupRequest, TokenResponse, get_current_user
from azure_scanner import AzureCliError
from db import DatabaseError

load_dotenv()


class ProgressManager:
    """Tracks WebSocket clients listening for a given analysis_id and
    broadcasts progress messages to them."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, analysis_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(analysis_id, []).append(websocket)

    def disconnect(self, analysis_id: str, websocket: WebSocket) -> None:
        connections = self._connections.get(analysis_id)
        if not connections:
            return
        if websocket in connections:
            connections.remove(websocket)
        if not connections:
            self._connections.pop(analysis_id, None)

    async def send(self, analysis_id: str, message: str) -> None:
        """Send a progress message to every client listening on analysis_id.

        Best-effort only: does nothing if nobody is connected, and must never
        block or fail the analysis itself.
        """
        for websocket in list(self._connections.get(analysis_id, [])):
            try:
                await websocket.send_json({"analysis_id": analysis_id, "message": message})
            except Exception:
                self.disconnect(analysis_id, websocket)


progress_manager = ProgressManager()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await db.init_db()
    except DatabaseError as error:
        # Don't crash the whole API if PostgreSQL is unreachable at boot;
        # persistence endpoints will simply report 503 until it recovers.
        print(f"[startup] {error.message}")
    try:
        yield
    finally:
        await db.close_db()


app = FastAPI(
    title="AI Cloud Cost Detective API",
    description="Scans Azure resource groups via the Azure CLI.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    resource_group: str = Field(..., min_length=1, description="Azure resource group name")
    analysis_id: str | None = Field(
        default=None,
        description=(
            "Optional client-generated UUID. Connect to "
            "ws://localhost:8000/ws/progress/{analysis_id} with this same value "
            "*before* calling this endpoint to receive live progress updates."
        ),
    )


class ResourceGroup(BaseModel):
    name: str | None = None
    location: str | None = None
    id: str | None = None
    tags: dict[str, Any] = {}


class Resource(BaseModel):
    name: str | None = None
    type: str | None = None
    location: str | None = None
    sku: dict[str, Any] | None = None
    tags: dict[str, Any] = {}
    id: str | None = None
    kind: str | None = None


class AnalyzeResponse(BaseModel):
    analysis_id: str
    resource_group: str
    resource_count: int
    resources: list[Resource]
    summary: dict[str, Any]
    ai_analysis: CostAnalysis


class HistoryItem(BaseModel):
    id: str
    resource_group: str
    resources_scanned: int
    issues_found: int
    estimated_savings: str | None = None
    analysis_result: dict[str, Any] | None = None
    status: str
    created_at: Any


def _handle(error: AzureCliError | AIAnalyzerError | DatabaseError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.message)


def _build_summary(resources: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "by_type": dict(Counter(r.get("type") or "unknown" for r in resources)),
        "by_location": dict(Counter(r.get("location") or "unknown" for r in resources)),
        "untagged_resources": sum(1 for r in resources if not r.get("tags")),
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/signup", response_model=TokenResponse, status_code=201)
async def signup(request: SignupRequest) -> TokenResponse:
    try:
        return await auth.signup(request)
    except (AuthError, DatabaseError) as error:
        raise _handle(error) from error


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    try:
        return await auth.login(request)
    except (AuthError, DatabaseError) as error:
        raise _handle(error) from error


@app.get("/api/resource-groups", response_model=list[ResourceGroup])
def get_resource_groups(current_user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    try:
        return azure_scanner.list_resource_groups()
    except AzureCliError as error:
        raise _handle(error) from error


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: AnalyzeRequest, current_user: dict[str, Any] = Depends(get_current_user)
) -> dict[str, Any]:
    resource_group = request.resource_group.strip()
    if not resource_group:
        raise HTTPException(status_code=422, detail="'resource_group' must not be empty.")

    user_id = current_user["id"]
    analysis_id = request.analysis_id or str(uuid.uuid4())
    try:
        analysis_uuid = uuid.UUID(analysis_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="'analysis_id' must be a valid UUID."
        ) from exc

    try:
        await db.create_analysis(analysis_uuid, user_id, resource_group)
    except Exception as exc:  # noqa: BLE001 - persistence is best-effort
        print(f"[analyze] failed to record analysis start: {exc}")

    try:
        await progress_manager.send(analysis_id, "Fetching resource groups...")
        await run_in_threadpool(azure_scanner.list_resource_groups)

        await progress_manager.send(analysis_id, f"Scanning resources in {resource_group}...")
        resources = await run_in_threadpool(azure_scanner.list_resources, resource_group)
    except AzureCliError as error:
        await progress_manager.send(analysis_id, f"Analysis failed: {error.message}")
        try:
            await db.fail_analysis(analysis_uuid, error.message)
        except Exception as exc:  # noqa: BLE001 - persistence is best-effort
            print(f"[analyze] failed to record analysis failure: {exc}")
        raise _handle(error) from error

    await progress_manager.send(analysis_id, "Analyzing costs with AI...")
    try:
        ai_analysis = await run_in_threadpool(
            ai_analyzer.analyze_resources, resource_group, resources
        )
    except AIAnalyzerError as error:
        # Degrade gracefully: the Azure scan itself succeeded, so still return
        # the real resource data with a placeholder analysis instead of
        # failing the whole request just because the AI provider is
        # unavailable (e.g. no OpenAI credits configured yet).
        await progress_manager.send(analysis_id, f"AI analysis unavailable: {error.message}")
        ai_analysis = CostAnalysis(
            summary=(
                "AI cost analysis is currently unavailable "
                f"({error.message}). Showing scanned resources only."
            )
        )

    await progress_manager.send(analysis_id, "Storing results...")
    summary = _build_summary(resources)
    savings = ai_analysis.estimated_savings
    estimated_savings_text = f"${savings.monthly_usd:,.2f} {savings.currency}/mo"
    result_payload = {
        "resource_group": resource_group,
        "resource_count": len(resources),
        "resources": resources,
        "summary": summary,
        "ai_analysis": ai_analysis.model_dump(),
    }
    try:
        await db.complete_analysis(
            analysis_uuid,
            len(resources),
            len(ai_analysis.issues),
            estimated_savings_text,
            result_payload,
        )
    except Exception as exc:  # noqa: BLE001 - persistence is best-effort
        print(f"[analyze] failed to store analysis result: {exc}")

    await progress_manager.send(analysis_id, "Analysis complete")

    return {
        "analysis_id": analysis_id,
        "resource_group": resource_group,
        "resource_count": len(resources),
        "resources": resources,
        "summary": summary,
        "ai_analysis": ai_analysis,
    }


@app.get("/api/history", response_model=list[HistoryItem])
async def get_history(
    current_user: dict[str, Any] = Depends(get_current_user)
) -> list[dict[str, Any]]:
    try:
        return await db.get_history(current_user["id"])
    except DatabaseError as error:
        raise _handle(error) from error


@app.websocket("/ws/progress/{analysis_id}")
async def websocket_progress(websocket: WebSocket, analysis_id: str) -> None:
    user = await auth.get_user_from_ws_token(websocket)
    if user is None:
        await websocket.close(code=4401)
        return

    await progress_manager.connect(analysis_id, websocket)
    try:
        while True:
            # The client doesn't need to send anything; this just lets us
            # detect disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        progress_manager.disconnect(analysis_id, websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
