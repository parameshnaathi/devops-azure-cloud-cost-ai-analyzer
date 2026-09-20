"""Azure CLI wrapper used to discover resource groups and their resources."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

AZ_TIMEOUT_SECONDS = 120


class AzureCliError(Exception):
    """Raised when the Azure CLI cannot be used or returns an error."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _az_executable() -> str:
    for candidate in ("az", "az.cmd"):
        path = shutil.which(candidate)
        if path:
            return path
    raise AzureCliError(
        "Azure CLI ('az') was not found on this machine. Install it from "
        "https://learn.microsoft.com/cli/azure/install-azure-cli and try again.",
        status_code=503,
    )


def _classify_error(stderr: str, resource_group: str | None) -> AzureCliError:
    lowered = stderr.lower()

    if "az login" in lowered or "not logged in" in lowered or "please run" in lowered:
        return AzureCliError(
            "Not logged in to Azure. Run 'az login' and try again.", status_code=401
        )
    if "subscription" in lowered and "not found" in lowered:
        return AzureCliError(
            "No accessible Azure subscription was found for the current login.",
            status_code=403,
        )
    if "resourcegroupnotfound" in lowered or (
        resource_group and "could not be found" in lowered
    ):
        return AzureCliError(
            f"Resource group '{resource_group}' was not found in the current subscription.",
            status_code=404,
        )

    detail = stderr.strip() or "Unknown Azure CLI failure."
    return AzureCliError(f"Azure CLI command failed: {detail}", status_code=502)


def _run_az(args: list[str], resource_group: str | None = None) -> Any:
    command = [_az_executable(), *args, "-o", "json"]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=AZ_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as exc:  # pragma: no cover - guarded by _az_executable
        raise AzureCliError(
            "Azure CLI ('az') was not found on this machine.", status_code=503
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AzureCliError(
            f"Azure CLI command timed out after {AZ_TIMEOUT_SECONDS} seconds.",
            status_code=504,
        ) from exc

    if completed.returncode != 0:
        raise _classify_error(completed.stderr, resource_group)

    stdout = completed.stdout.strip()
    if not stdout:
        return []

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise AzureCliError(
            "Could not parse JSON output returned by the Azure CLI.", status_code=502
        ) from exc


def _extract_sku(resource: dict[str, Any]) -> dict[str, Any] | None:
    sku = resource.get("sku")
    if not isinstance(sku, dict):
        return None

    normalized = {
        key: sku.get(key)
        for key in ("name", "tier", "size", "family", "capacity")
        if sku.get(key) is not None
    }
    return normalized or None


def resource_group_exists(resource_group: str) -> bool:
    """Return True when the resource group exists in the active subscription."""
    return _run_az(["group", "exists", "--name", resource_group], resource_group) is True


def list_resource_groups() -> list[dict[str, Any]]:
    """Return every resource group in the active subscription."""
    groups = _run_az(["group", "list"])

    return [
        {
            "name": group.get("name"),
            "location": group.get("location"),
            "id": group.get("id"),
            "tags": group.get("tags") or {},
        }
        for group in groups
        if isinstance(group, dict)
    ]


def list_resources(resource_group: str) -> list[dict[str, Any]]:
    """Return every resource inside the given resource group."""
    resources = _run_az(
        ["resource", "list", "--resource-group", resource_group],
        resource_group=resource_group,
    )

    # Some CLI versions return an empty array instead of failing for an unknown
    # group, so verify existence explicitly to surface a useful 404.
    if not resources and not resource_group_exists(resource_group):
        raise AzureCliError(
            f"Resource group '{resource_group}' was not found in the current subscription.",
            status_code=404,
        )

    return [
        {
            "name": resource.get("name"),
            "type": resource.get("type"),
            "location": resource.get("location"),
            "sku": _extract_sku(resource),
            "tags": resource.get("tags") or {},
            "id": resource.get("id"),
            "kind": resource.get("kind"),
        }
        for resource in resources
        if isinstance(resource, dict)
    ]
