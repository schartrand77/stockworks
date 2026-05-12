"""PrintLab integration helpers."""
from __future__ import annotations

import os
import base64
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

import httpx

from .settings import get_effective_setting


class PrintLabIntegrationError(Exception):
    """Base error for integration failures."""


class PrintLabNotConfiguredError(PrintLabIntegrationError):
    """Raised when the integration is not configured."""


class PrintLabAuthenticationError(PrintLabIntegrationError):
    """Raised when authentication with PrintLab fails."""


class PrintLabClient:
    """Simple client for communicating with PrintLab."""

    def __init__(
        self,
        base_url: Optional[str],
        api_key: Optional[str] = None,
        api_auth_header: Optional[str] = None,
        bearer_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.api_auth_header = (api_auth_header or "").strip() or "X-API-Key"
        self.bearer_token = (bearer_token or "").strip()
        self.username = (username or "").strip()
        self.password = password or ""
        self._timeout = timeout
        self._clients: Dict[str, httpx.Client] = {}

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _get_client(self, base_url: Optional[str] = None) -> httpx.Client:
        resolved_base_url = (base_url or self.base_url or "").rstrip("/")
        if not resolved_base_url:
            raise PrintLabNotConfiguredError("PrintLab base URL is not configured.")
        client = self._clients.get(resolved_base_url)
        if client is None:
            client = httpx.Client(base_url=resolved_base_url, timeout=self._timeout, follow_redirects=True)
            self._clients[resolved_base_url] = client
        return client

    def _build_request_headers(self, headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if headers:
            merged.update(headers)
        if self.api_key:
            merged[self.api_auth_header] = self.api_key
        if self.bearer_token:
            merged["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.username and self.password:
            token = base64.b64encode(f"{self.username}:{self.password}".encode("utf-8")).decode("ascii")
            merged["Authorization"] = f"Basic {token}"
        return merged

    def _build_alternate_base_url(self) -> Optional[str]:
        parsed = urlparse(self.base_url)
        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return None
        if hostname == "host.docker.internal":
            alternate_host = "localhost"
        elif hostname in {"localhost", "127.0.0.1"}:
            alternate_host = "host.docker.internal"
        else:
            return None
        netloc = alternate_host
        if parsed.port is not None:
            netloc = f"{alternate_host}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))

    def _candidate_base_urls(self) -> List[str]:
        primary = (self.base_url or "").rstrip("/")
        if not primary:
            return []
        candidates = [primary]
        alternate = self._build_alternate_base_url()
        if alternate:
            alternate = alternate.rstrip("/")
            if alternate and alternate not in candidates:
                candidates.append(alternate)
        return candidates

    def _format_connect_error(self, attempted_urls: List[str], exc: httpx.HTTPError) -> str:
        attempted = ", ".join(attempted_urls) if attempted_urls else self.base_url
        return (
            f"Failed to contact PrintLab. Tried: {attempted}. "
            "If StockWorks is running on localhost, set PRINTLAB_BASE_URL to http://localhost:8080. "
            "On Unraid with a shared Docker network, use http://PrintLab:8080; "
            "on bridge networking, use http://<unraid-ip>:<mapped-printlab-port>. "
            f"Original error: {exc}"
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.is_configured:
            raise PrintLabNotConfiguredError("PrintLab integration is not configured.")
        kwargs["headers"] = self._build_request_headers(kwargs.get("headers"))
        attempted_urls: List[str] = []
        last_exc: Optional[httpx.HTTPError] = None
        for candidate_base_url in self._candidate_base_urls():
            attempted_urls.append(candidate_base_url)
            client = self._get_client(candidate_base_url)
            try:
                response = client.request(method, path, **kwargs)
                if candidate_base_url != self.base_url:
                    self.base_url = candidate_base_url
                return response
            except httpx.ConnectError as exc:
                last_exc = exc
                continue
            except httpx.HTTPError as exc:
                raise PrintLabIntegrationError(f"Failed to contact PrintLab: {exc}") from exc
        if last_exc is not None:
            raise PrintLabIntegrationError(self._format_connect_error(attempted_urls, last_exc)) from last_exc
        raise PrintLabIntegrationError("Failed to contact PrintLab.")

    def _format_http_status_error(self, exc: httpx.HTTPStatusError, operation: str) -> str:
        response = exc.response
        request = exc.request
        status_code = response.status_code if response is not None else None
        reason = response.reason_phrase if response is not None else ""
        request_url = str(request.url) if request is not None else ""
        host = urlparse(request_url).netloc
        status_label = str(status_code) if status_code is not None else "unknown"
        reason_label = f" {reason}" if reason else ""
        host_label = f" from {host}" if host else ""
        hint = ""
        if status_code in {502, 503, 504}:
            hint = (
                " Upstream PrintLab service is unavailable. On Unraid, verify StockWorks and PrintLab share a Docker "
                "network and PRINTLAB_BASE_URL uses the PrintLab container URL, or use the Unraid host IP and mapped port."
            )
        if host and "makerworks" in host.lower():
            hint += " Verify PRINTLAB_BASE_URL points to your PrintLab instance."
        return f"{operation} failed with HTTP {status_label}{reason_label}{host_label}.{hint}"

    def _parse_items_payload(self, data: Any, operation: str) -> List[Dict[str, Any]]:
        if isinstance(data, dict):
            items = data.get("items")
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        elif isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        raise PrintLabIntegrationError(f"{operation} response did not include an items list.")

    def _request_json(self, method: str, path: str, operation: str) -> Any:
        response = self._request(method, path)
        if response.status_code in {401, 403}:
            raise PrintLabAuthenticationError(
                "PrintLab rejected the request. Configure PRINTLAB_API_KEY, PRINTLAB_BEARER_TOKEN, "
                "or PRINTLAB_USERNAME and PRINTLAB_PASSWORD."
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise PrintLabIntegrationError(
                self._format_http_status_error(exc, operation)
            ) from exc
        try:
            return response.json()
        except ValueError as exc:
            raise PrintLabIntegrationError(f"{operation} response returned invalid JSON.") from exc

    def fetch_printers(self) -> List[Dict[str, Any]]:
        printers_error: Optional[PrintLabIntegrationError] = None
        try:
            data = self._request_json("GET", "/api/printers", "PrintLab printers request")
            return self._parse_items_payload(data, "PrintLab printers")
        except PrintLabAuthenticationError:
            raise
        except PrintLabIntegrationError as exc:
            printers_error = exc

        try:
            data = self._request_json("GET", "/api/fleet", "PrintLab fleet request")
            return self._parse_items_payload(data, "PrintLab fleet")
        except PrintLabAuthenticationError:
            raise
        except PrintLabIntegrationError:
            if printers_error is not None:
                raise printers_error
            raise

    def fetch_printer_state(self, printer_id: str) -> Dict[str, Any]:
        clean_printer_id = str(printer_id or "").strip()
        if not clean_printer_id:
            raise PrintLabIntegrationError("PrintLab printer id is required for state requests.")
        data = self._request_json("GET", f"/api/printers/{clean_printer_id}/state", "PrintLab printer state request")
        if not isinstance(data, dict):
            raise PrintLabIntegrationError("PrintLab printer state response did not include an object payload.")
        return data


_PRINTLAB_CLIENT: Optional[PrintLabClient] = None


def get_printlab_client(settings: Optional[Dict[str, str]] = None) -> PrintLabClient:
    if settings is not None:
        return PrintLabClient(
            base_url=get_effective_setting("PRINTLAB_BASE_URL", settings),
            api_key=get_effective_setting("PRINTLAB_API_KEY", settings),
            api_auth_header=get_effective_setting("PRINTLAB_API_AUTH_HEADER", settings),
            bearer_token=get_effective_setting("PRINTLAB_BEARER_TOKEN", settings),
            username=get_effective_setting("PRINTLAB_USERNAME", settings),
            password=get_effective_setting("PRINTLAB_PASSWORD", settings),
        )
    global _PRINTLAB_CLIENT
    if _PRINTLAB_CLIENT is None:
        _PRINTLAB_CLIENT = PrintLabClient(
            base_url=os.environ.get("PRINTLAB_BASE_URL"),
            api_key=os.environ.get("PRINTLAB_API_KEY"),
            api_auth_header=os.environ.get("PRINTLAB_API_AUTH_HEADER"),
            bearer_token=os.environ.get("PRINTLAB_BEARER_TOKEN"),
            username=os.environ.get("PRINTLAB_USERNAME"),
            password=os.environ.get("PRINTLAB_PASSWORD"),
        )
    return _PRINTLAB_CLIENT
