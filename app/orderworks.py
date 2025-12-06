"""OrderWorks integration helpers."""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

import httpx

ORDERWORKS_SESSION_REFRESH_SECONDS = 60 * 60 * 6  # refresh every 6 hours


class OrderWorksIntegrationError(Exception):
    """Base error for integration failures."""


class OrderWorksNotConfiguredError(OrderWorksIntegrationError):
    """Raised when the integration is not configured."""


class OrderWorksAuthenticationError(OrderWorksIntegrationError):
    """Raised when authentication with OrderWorks fails."""


class OrderWorksClient:
    """Simple client for communicating with the OrderWorks admin API."""

    def __init__(self, base_url: Optional[str], username: Optional[str], password: Optional[str], timeout: float = 20.0):
        self.base_url = (base_url or "").rstrip("/")
        self.username = (username or "").strip()
        self.password = (password or "").strip()
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._session_expires_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.username and self.password)

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if not self.base_url:
                raise OrderWorksNotConfiguredError("OrderWorks base URL is not configured.")
            self._client = httpx.Client(base_url=self.base_url, timeout=self._timeout, follow_redirects=False)
        return self._client

    def _session_valid(self) -> bool:
        return self._session_expires_at > time.time()

    def _login(self, force: bool = False) -> None:
        if not self.is_configured:
            raise OrderWorksNotConfiguredError("OrderWorks integration is not configured.")
        with self._lock:
            if self._session_valid() and not force:
                return
            client = self._get_client()
            client.cookies.clear()
            response = client.post(
                "/api/auth/login",
                json={"username": self.username, "password": self.password},
            )
            if response.status_code == 401:
                raise OrderWorksAuthenticationError("OrderWorks credentials were rejected.")
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise OrderWorksIntegrationError(f"OrderWorks login failed: {exc}") from exc
            if "orderworks_admin_session" not in client.cookies:
                raise OrderWorksIntegrationError("OrderWorks login did not return a session cookie.")
            self._session_expires_at = time.time() + ORDERWORKS_SESSION_REFRESH_SECONDS

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.is_configured:
            raise OrderWorksNotConfiguredError("OrderWorks integration is not configured.")
        self._login()
        client = self._get_client()
        response = client.request(method, path, **kwargs)
        if response.status_code == 401:
            self._login(force=True)
            response = client.request(method, path, **kwargs)
        return response

    def list_jobs(self, params: Optional[Dict[str, Any]] = None) -> Any:
        response = self._request("GET", "/api/jobs", params=params or {})
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OrderWorksIntegrationError(f"OrderWorks request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise OrderWorksIntegrationError("OrderWorks returned invalid JSON.") from exc
        jobs = data.get("jobs")
        if not isinstance(jobs, list):
            raise OrderWorksIntegrationError("OrderWorks response did not include jobs.")
        return jobs


_ORDERWORKS_CLIENT: Optional[OrderWorksClient] = None


def get_orderworks_client() -> OrderWorksClient:
    global _ORDERWORKS_CLIENT
    if _ORDERWORKS_CLIENT is None:
        _ORDERWORKS_CLIENT = OrderWorksClient(
            base_url=os.environ.get("ORDERWORKS_BASE_URL"),
            username=os.environ.get("ORDERWORKS_ADMIN_USERNAME"),
            password=os.environ.get("ORDERWORKS_ADMIN_PASSWORD"),
        )
    return _ORDERWORKS_CLIENT
