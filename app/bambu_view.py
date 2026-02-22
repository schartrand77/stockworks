"""Bambu View integration helpers."""
from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

BAMBU_VIEW_SESSION_REFRESH_SECONDS = 60 * 60 * 6  # refresh every 6 hours


class BambuViewIntegrationError(Exception):
    """Base error for integration failures."""


class BambuViewNotConfiguredError(BambuViewIntegrationError):
    """Raised when the integration is not configured."""


class BambuViewAuthenticationError(BambuViewIntegrationError):
    """Raised when authentication with Bambu View fails."""


class BambuViewClient:
    """Simple client for communicating with Bambu View."""

    def __init__(
        self,
        base_url: Optional[str],
        api_key: Optional[str] = None,
        api_auth_header: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 20.0,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = (api_key or "").strip()
        self.api_auth_header = (api_auth_header or "").strip() or "X-API-Key"
        self.username = (username or "").strip()
        self.password = (password or "").strip()
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._session_expires_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    @property
    def has_auth(self) -> bool:
        return bool(self.api_key or (self.username and self.password))

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            if not self.base_url:
                raise BambuViewNotConfiguredError("Bambu View base URL is not configured.")
            self._client = httpx.Client(base_url=self.base_url, timeout=self._timeout, follow_redirects=True)
        return self._client

    def _session_valid(self) -> bool:
        return self._session_expires_at > time.time()

    def _login(self, force: bool = False) -> None:
        if self.api_key:
            return
        if not self.username or not self.password:
            return
        with self._lock:
            if self._session_valid() and not force:
                return
            client = self._get_client()
            client.cookies.clear()
            try:
                response = client.post(
                    "/login",
                    data={"username": self.username, "password": self.password},
                )
            except httpx.HTTPError as exc:
                raise BambuViewIntegrationError(f"Failed to contact Bambu View during login: {exc}") from exc
            if response.status_code == 401:
                raise BambuViewAuthenticationError("Bambu View credentials were rejected.")
            if response.status_code >= 400:
                raise BambuViewIntegrationError(f"Bambu View login failed: HTTP {response.status_code}.")
            self._session_expires_at = time.time() + BAMBU_VIEW_SESSION_REFRESH_SECONDS

    def _build_request_headers(self, headers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if headers:
            merged.update(headers)
        if self.api_key:
            merged[self.api_auth_header] = self.api_key
        return merged

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.is_configured:
            raise BambuViewNotConfiguredError("Bambu View integration is not configured.")
        self._login()
        client = self._get_client()
        kwargs["headers"] = self._build_request_headers(kwargs.get("headers"))
        try:
            response = client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise BambuViewIntegrationError(f"Failed to contact Bambu View: {exc}") from exc
        if response.status_code == 401 and self.username and self.password:
            self._login(force=True)
            kwargs["headers"] = self._build_request_headers(kwargs.get("headers"))
            try:
                response = client.request(method, path, **kwargs)
            except httpx.HTTPError as exc:
                raise BambuViewIntegrationError(
                    f"Failed to contact Bambu View after refreshing the session: {exc}"
                ) from exc
        return response

    def fetch_fleet(self) -> List[Dict[str, Any]]:
        response = self._request("GET", "/api/fleet")
        if response.status_code == 401:
            raise BambuViewAuthenticationError(
                "Bambu View rejected the request. Configure BAMBU_VIEW_API_KEY or BAMBU_VIEW_ADMIN_* credentials."
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BambuViewIntegrationError(f"Bambu View request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise BambuViewIntegrationError("Bambu View returned invalid JSON.") from exc
        fleet = data.get("fleet")
        if not isinstance(fleet, list):
            raise BambuViewIntegrationError("Bambu View response did not include fleet data.")
        return fleet

    def fetch_spools(self, printer_id: Optional[str] = None) -> Dict[str, Any]:
        params: Dict[str, str] = {}
        if printer_id:
            params["printer_id"] = printer_id
        response = self._request("GET", "/api/spools", params=params or None)
        if response.status_code == 401:
            raise BambuViewAuthenticationError(
                "Bambu View rejected the spools request. Configure BAMBU_VIEW_API_KEY or BAMBU_VIEW_ADMIN_* credentials."
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BambuViewIntegrationError(f"Bambu View spools request failed: {exc}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise BambuViewIntegrationError("Bambu View spools response returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise BambuViewIntegrationError("Bambu View spools response did not include an object payload.")
        return data


_BAMBU_VIEW_CLIENT: Optional[BambuViewClient] = None


def get_bambu_view_client() -> BambuViewClient:
    global _BAMBU_VIEW_CLIENT
    if _BAMBU_VIEW_CLIENT is None:
        _BAMBU_VIEW_CLIENT = BambuViewClient(
            base_url=os.environ.get("BAMBU_VIEW_BASE_URL"),
            api_key=os.environ.get("BAMBU_VIEW_API_KEY"),
            api_auth_header=os.environ.get("BAMBU_VIEW_API_AUTH_HEADER"),
            username=os.environ.get("BAMBU_VIEW_ADMIN_USERNAME"),
            password=os.environ.get("BAMBU_VIEW_ADMIN_PASSWORD"),
        )
    return _BAMBU_VIEW_CLIENT
