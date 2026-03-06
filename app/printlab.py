"""PrintLab integration helpers."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx


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
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.api_auth_header = (api_auth_header or "").strip() or "X-API-Key"
        self.bearer_token = (bearer_token or "").strip()
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if not self.base_url:
                raise PrintLabNotConfiguredError("PrintLab base URL is not configured.")
            self._client = httpx.Client(base_url=self.base_url, timeout=self._timeout, follow_redirects=True)
        return self._client

    def _build_request_headers(self, headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if headers:
            merged.update(headers)
        if self.api_key:
            merged[self.api_auth_header] = self.api_key
        if self.bearer_token:
            merged["Authorization"] = f"Bearer {self.bearer_token}"
        return merged

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.is_configured:
            raise PrintLabNotConfiguredError("PrintLab integration is not configured.")
        client = self._get_client()
        kwargs["headers"] = self._build_request_headers(kwargs.get("headers"))
        try:
            response = client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise PrintLabIntegrationError(f"Failed to contact PrintLab: {exc}") from exc
        return response

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
            hint = " Upstream PrintLab service is unavailable."
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
                "PrintLab rejected the request. Configure PRINTLAB_API_KEY or PRINTLAB_BEARER_TOKEN."
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


def _read_env(primary: str, fallback: str) -> Optional[str]:
    value = os.environ.get(primary)
    if value is not None:
        return value
    return os.environ.get(fallback)


def get_printlab_client() -> PrintLabClient:
    global _PRINTLAB_CLIENT
    if _PRINTLAB_CLIENT is None:
        _PRINTLAB_CLIENT = PrintLabClient(
            base_url=_read_env("PRINTLAB_BASE_URL", "BAMBU_VIEW_BASE_URL"),
            api_key=_read_env("PRINTLAB_API_KEY", "BAMBU_VIEW_API_KEY"),
            api_auth_header=_read_env("PRINTLAB_API_AUTH_HEADER", "BAMBU_VIEW_API_AUTH_HEADER"),
            bearer_token=os.environ.get("PRINTLAB_BEARER_TOKEN"),
        )
    return _PRINTLAB_CLIENT
