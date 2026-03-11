"""FastAPI application implementing inventory control for a 3D printing service."""
from __future__ import annotations

import base64
import json
import mimetypes
import logging
import os
import re
import secrets
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlmodel import Session, func, select
from starlette.middleware.sessions import SessionMiddleware

from .barcodes import render_barcode_png
from .bambu_invoice import DEFAULT_SUPPLIER, parse_invoice_pdf, resolve_upload_dir, store_upload
from .printlab import (
    PrintLabAuthenticationError,
    PrintLabIntegrationError,
    PrintLabNotConfiguredError,
    get_printlab_client,
)
from .color_resolver import normalize_hex, normalize_hex_list
from .db import get_session, init_db
from .filament_types import bambu_x1c_filament_types
from .normalization import normalize_barcode, normalize_sku
from .orderworks import (
    OrderWorksAuthenticationError,
    OrderWorksDatabaseUnavailableError,
    OrderWorksIntegrationError,
    OrderWorksNotConfiguredError,
    get_orderworks_client,
    list_orderworks_jobs_via_database,
)
from .models import (
    HardwareItem,
    HardwareItemCreate,
    HardwareItemRead,
    HardwareItemUpdate,
    HardwareMovement,
    HardwareMovementCreate,
    HardwareMovementRead,
    InventoryItem,
    InventoryItemCreate,
    InventoryItemRead,
    InventoryItemUpdate,
    InboundInvoice,
    InboundInvoiceLine,
    InboundInvoiceLineRead,
    InboundInvoiceRead,
    InboundInvoiceVerifyRequest,
    Material,
    MaterialCreate,
    MaterialRead,
    MaterialUpdate,
    PaginatedHardwareRead,
    PaginatedInventoryRead,
    PaginatedMaterialsRead,
    PaginatedModelsRead,
    MaterialCostHistory,
    MaterialCostHistoryCreate,
    MaterialCostHistoryRead,
    PricingBreakdown,
    PricingRequest,
    PricingResponse,
    PrintModel,
    PrintModelCreate,
    PrintModelRead,
    PrintModelMovement,
    PrintModelMovementCreate,
    PrintModelMovementRead,
    PrintModelSale,
    PrintModelSaleCreate,
    PrintModelSaleRead,
    PrintModelUpdate,
    StockMovement,
    StockMovementCreate,
    StockMovementRead,
)


def _normalize_origin(scheme: str, netloc: str) -> str:
    host, sep, port = netloc.partition(":")
    if sep and ((scheme.lower() == "https" and port == "443") or (scheme.lower() == "http" and port == "80")):
        netloc = host
    return f"{scheme.lower()}://{netloc.lower()}"


def _parse_origin_list(raw_origins: str) -> list[str]:
    parsed_origins: list[str] = []
    for raw_origin in raw_origins.split(","):
        origin = raw_origin.strip()
        if not origin:
            continue
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            raise RuntimeError(f"Invalid origin value: {origin!r}")
        parsed_origins.append(_normalize_origin(parsed.scheme, parsed.netloc))
    return parsed_origins


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
PUBLIC_DIR = BASE_DIR.parent / "public"
INBOUND_INVOICE_DIR = resolve_upload_dir(BASE_DIR.parent)
MANIFEST_FILE = STATIC_DIR / "site.webmanifest"
SERVICE_WORKER_FILE = STATIC_DIR / "sw.js"
FAVICON_ICO_FILE = PUBLIC_DIR / "favicon.ico"
FAVICON_PNG_FILE = PUBLIC_DIR / "favicon.png"
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

mimetypes.add_type("application/manifest+json", ".webmanifest")

ADMIN_USERNAME = (os.environ.get("ADMIN_USERNAME") or "admin").strip() or "admin"
ADMIN_PASSWORD = (os.environ.get("ADMIN_PASSWORD") or "").strip()
SECRET_KEY = (os.environ.get("SECRET_KEY") or "").strip()
SESSION_COOKIE = "stockworks-session"
SESSION_MAX_AGE_SECONDS = int(os.environ.get("SESSION_MAX_AGE_SECONDS", "28800"))
SESSION_SAME_SITE = (os.environ.get("SESSION_SAME_SITE") or "strict").strip().lower()
SESSION_HTTPS_ONLY = (os.environ.get("SESSION_HTTPS_ONLY") or "1").strip().lower() in {"1", "true", "yes", "on"}
TRUST_X_FORWARDED_FOR = (os.environ.get("TRUST_X_FORWARDED_FOR") or "0").strip().lower() in {"1", "true", "yes", "on"}
CORS_ALLOW_ORIGINS = _parse_origin_list(os.environ.get("CORS_ALLOW_ORIGINS") or "")
CORS_ALLOW_CREDENTIALS = (os.environ.get("CORS_ALLOW_CREDENTIALS") or "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
CSRF_TRUSTED_ORIGINS = set(_parse_origin_list(os.environ.get("CSRF_TRUSTED_ORIGINS") or ""))
CSRF_TOKEN_LENGTH = 48
LOGIN_RATE_LIMIT_ATTEMPTS = int(os.environ.get("LOGIN_RATE_LIMIT_ATTEMPTS", "5"))
LOGIN_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "300"))
LOGIN_RATE_LIMIT_BLOCK_SECONDS = int(os.environ.get("LOGIN_RATE_LIMIT_BLOCK_SECONDS", "900"))
_SECURE_PLACEHOLDERS = {
    "",
    "changeme",
    "please-change-me",
    "replace-me",
    "default",
    "admin",
    "password",
    "secret",
}
_LOGIN_RATE_LIMIT_LOCK = threading.Lock()
_LOGIN_RATE_LIMIT_STATE: dict[str, dict[str, Any]] = {}
logger = logging.getLogger(__name__)


def _validate_security_config() -> None:
    if not ADMIN_PASSWORD:
        raise RuntimeError("ADMIN_PASSWORD must be configured via environment variable.")
    if ADMIN_PASSWORD.lower() in _SECURE_PLACEHOLDERS:
        raise RuntimeError("ADMIN_PASSWORD must not be a default placeholder value.")
    if len(ADMIN_PASSWORD) < 12:
        raise RuntimeError("ADMIN_PASSWORD must be at least 12 characters.")
    if not SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be configured via environment variable.")
    if SECRET_KEY.lower() in _SECURE_PLACEHOLDERS:
        raise RuntimeError("SECRET_KEY must not be a default placeholder value.")
    if len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters.")
    if SESSION_SAME_SITE not in {"lax", "strict", "none"}:
        raise RuntimeError("SESSION_SAME_SITE must be one of: lax, strict, none.")
    if SESSION_MAX_AGE_SECONDS < 300:
        raise RuntimeError("SESSION_MAX_AGE_SECONDS must be at least 300.")
    if CORS_ALLOW_CREDENTIALS and "*" in CORS_ALLOW_ORIGINS:
        raise RuntimeError("CORS_ALLOW_ORIGINS cannot contain '*' when CORS_ALLOW_CREDENTIALS is enabled.")


_validate_security_config()

app = FastAPI(title="StockWorks", version="1.0.0")
if CORS_ALLOW_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGINS,
        allow_credentials=CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie=SESSION_COOKIE,
    same_site=SESSION_SAME_SITE,
    https_only=SESSION_HTTPS_ONLY,
    max_age=SESSION_MAX_AGE_SECONDS,
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), microphone=(), geolocation=()")
        if SESSION_HTTPS_ONLY:
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def stockworks_api_prefix_compat(request: Request, call_next):
    """Support legacy /api/stockworks/* paths by rewriting to root routes."""
    prefix = "/api/stockworks"
    path = request.scope.get("path", "")
    if path == prefix or path.startswith(prefix + "/"):
        rewritten = path[len(prefix) :] or "/"
        request.scope["path"] = rewritten
        request.scope["raw_path"] = rewritten.encode("utf-8")
    return await call_next(request)


def _static_file_response(path: Path, media_type: str) -> FileResponse:
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
    return FileResponse(path, media_type=media_type)


@app.get("/sw.js", include_in_schema=False)
@app.get("/service-worker.js", include_in_schema=False)
def service_worker() -> FileResponse:
    """Serve the PWA service worker at the root scope."""
    return _static_file_response(SERVICE_WORKER_FILE, media_type="application/javascript")


@app.get("/manifest.webmanifest", include_in_schema=False)
def web_manifest() -> FileResponse:
    """Expose the web manifest at the root for install prompts."""
    return _static_file_response(MANIFEST_FILE, media_type="application/manifest+json")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Serve favicon requests expected by browsers."""
    if FAVICON_ICO_FILE.exists():
        return _static_file_response(FAVICON_ICO_FILE, media_type="image/x-icon")
    return _static_file_response(FAVICON_PNG_FILE, media_type="image/png")


@app.get("/public/{asset_path:path}", include_in_schema=False)
def public_assets(asset_path: str) -> FileResponse:
    """Serve files from the repository-level public directory, even when not mounted."""
    public_root = PUBLIC_DIR.resolve()
    target = (PUBLIC_DIR / asset_path).resolve()
    if public_root not in target.parents and target != public_root:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public asset not found")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public asset not found")
    media_type, _ = mimetypes.guess_type(str(target))
    return FileResponse(target, media_type=media_type or "application/octet-stream")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def _is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def _new_csrf_token() -> str:
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def _ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token or not isinstance(token, str):
        token = _new_csrf_token()
        request.session["csrf_token"] = token
    return token


def _same_origin(request: Request) -> bool:
    expected_origins = {_normalize_origin(request.url.scheme, request.url.netloc)}
    expected_origins.update(CSRF_TRUSTED_ORIGINS)

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_proto:
        host = forwarded_host or (request.headers.get("host") or "").strip()
        if host:
            expected_origins.add(_normalize_origin(forwarded_proto, host))

    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    candidate = origin or referer
    if not candidate:
        return False
    parsed = urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        return False
    candidate_origin = _normalize_origin(parsed.scheme, parsed.netloc)
    return candidate_origin in expected_origins


def _require_same_origin(request: Request) -> None:
    # Some browser/proxy combinations omit Origin/Referer on same-site form posts.
    # In that case we still require a valid CSRF token and allow the request.
    if not request.headers.get("origin") and not request.headers.get("referer"):
        return
    if not _same_origin(request):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin.")


def _validate_csrf_token(request: Request, csrf_token: str | None) -> None:
    expected = request.session.get("csrf_token")
    if not expected or not csrf_token or not isinstance(expected, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing CSRF token.")
    if not secrets.compare_digest(expected, csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token.")


def _is_basic_auth_valid(authorization: str | None) -> bool:
    if not authorization:
        return False
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "basic" or not token:
        return False
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
    except Exception:
        return False
    username, sep, password = decoded.partition(":")
    if not sep:
        return False
    return _credentials_valid(username, password)


def require_auth(request: Request, authorization: str | None = Header(default=None, alias="Authorization")) -> bool:
    if not _is_authenticated(request):
        if not _is_basic_auth_valid(authorization):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return True


def require_csrf(
    request: Request,
    csrf_header: str | None = Header(default=None, alias="X-CSRF-Token"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> bool:
    if _is_basic_auth_valid(authorization):
        # Non-cookie API auth does not rely on browser sessions, so CSRF is not applicable.
        return True
    _require_same_origin(request)
    _validate_csrf_token(request, csrf_header)
    return True


def _credentials_valid(username: str, password: str) -> bool:
    normalized_username = username.strip()
    if not secrets.compare_digest(normalized_username, ADMIN_USERNAME):
        return False
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        return True
    # Tolerate accidental leading/trailing whitespace from copy/paste.
    return secrets.compare_digest(password.strip(), ADMIN_PASSWORD)


def _login_rate_limit_key(request: Request, username: str) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "") if TRUST_X_FORWARDED_FOR else ""
    client_ip = (forwarded_for.split(",")[0].strip() if forwarded_for else "") or (request.client.host if request.client else "unknown")
    return f"{client_ip.lower()}::{username.strip().lower()}"


def _is_login_rate_limited(key: str) -> int:
    now = time.time()
    with _LOGIN_RATE_LIMIT_LOCK:
        state = _LOGIN_RATE_LIMIT_STATE.get(key)
        if not state:
            return 0
        blocked_until = float(state.get("blocked_until", 0.0))
        if blocked_until > now:
            return max(1, int(blocked_until - now))
        failures = [float(ts) for ts in state.get("failures", []) if now - float(ts) <= LOGIN_RATE_LIMIT_WINDOW_SECONDS]
        if failures:
            state["failures"] = failures
            _LOGIN_RATE_LIMIT_STATE[key] = state
        else:
            _LOGIN_RATE_LIMIT_STATE.pop(key, None)
        return 0


def _record_failed_login(key: str) -> int:
    now = time.time()
    with _LOGIN_RATE_LIMIT_LOCK:
        state = _LOGIN_RATE_LIMIT_STATE.setdefault(key, {"failures": [], "blocked_until": 0.0})
        failures = [float(ts) for ts in state.get("failures", []) if now - float(ts) <= LOGIN_RATE_LIMIT_WINDOW_SECONDS]
        failures.append(now)
        state["failures"] = failures
        if len(failures) >= LOGIN_RATE_LIMIT_ATTEMPTS:
            blocked_until = now + LOGIN_RATE_LIMIT_BLOCK_SECONDS
            state["blocked_until"] = blocked_until
            _LOGIN_RATE_LIMIT_STATE[key] = state
            return max(1, int(blocked_until - now))
        _LOGIN_RATE_LIMIT_STATE[key] = state
        return 0


def _clear_failed_logins(key: str) -> None:
    with _LOGIN_RATE_LIMIT_LOCK:
        _LOGIN_RATE_LIMIT_STATE.pop(key, None)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    """Serve the HTML shell for the single-page UI."""
    if not _is_authenticated(request):
        return RedirectResponse("/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "csrf_token": _ensure_csrf_token(request)},
        headers={"Cache-Control": "no-store"},
    )


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None, "username": "", "csrf_token": _ensure_csrf_token(request)},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    _require_same_origin(request)
    _validate_csrf_token(request, csrf_token)
    key = _login_rate_limit_key(request, username)
    blocked_for = _is_login_rate_limited(key)
    if blocked_for:
        logger.warning("Blocked login attempt for key=%s blocked_for=%ss", key, blocked_for)
        context = {
            "request": request,
            "error": f"Too many login attempts. Try again in {blocked_for} seconds.",
            "username": username,
            "csrf_token": _ensure_csrf_token(request),
        }
        return templates.TemplateResponse("login.html", context, status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    if _credentials_valid(username, password):
        _clear_failed_logins(key)
        request.session["authenticated"] = True
        request.session["username"] = ADMIN_USERNAME
        request.session["csrf_token"] = _new_csrf_token()
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    blocked_for = _record_failed_login(key)
    logger.warning("Failed login for key=%s blocked_for=%ss", key, blocked_for)
    context = {
        "request": request,
        "error": "Invalid username or password." if not blocked_for else f"Too many login attempts. Try again in {blocked_for} seconds.",
        "username": username,
        "csrf_token": _ensure_csrf_token(request),
    }
    return templates.TemplateResponse("login.html", context, status_code=status.HTTP_401_UNAUTHORIZED)


@app.get("/filament-types/bambu-x1c")
def list_bambu_x1c_filament_types(_: bool = Depends(require_auth)) -> dict[str, list[str]]:
    return {"filament_types": bambu_x1c_filament_types()}


@app.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    _require_same_origin(request)
    _validate_csrf_token(request, csrf_token)
    request.session.clear()
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


# Material endpoints
@app.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    data = payload.dict()
    normalized_hexes = normalize_hex_list(data.get("color_hexes"))
    primary_hex = normalize_hex(data.get("color_hex"))
    data["color_hexes"] = normalized_hexes or None
    data["color_hex"] = primary_hex or (normalized_hexes[0] if normalized_hexes else None)
    data["barcode"] = normalize_barcode(data.get("barcode"))
    data["refill_barcode"] = normalize_barcode(data.get("refill_barcode"))
    data["name"] = _ensure_unique_material_name(session, data["name"])
    material = Material(**data)
    session.add(material)
    session.commit()
    session.refresh(material)
    history = MaterialCostHistory(
        material_id=material.id,
        unit_cost_per_gram=material.price_per_gram,
        vendor=material.supplier,
        reference="material_create",
        note="Initial material cost",
    )
    session.add(history)
    session.commit()
    return _material_to_read(material)


@app.get("/materials", response_model=PaginatedMaterialsRead)
def list_materials(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Material.name.ilike(pattern),
                Material.brand.ilike(pattern),
                Material.category.ilike(pattern),
                Material.color.ilike(pattern),
                Material.supplier.ilike(pattern),
                Material.filament_type.ilike(pattern),
            )
        )
    statement = select(Material).order_by(Material.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(Material)
    if filters:
        total_statement = total_statement.where(*filters)
    materials = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedMaterialsRead(
        items=[_material_to_read(material) for material in materials],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/materials/{material_id}", response_model=MaterialRead)
def get_material(material_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return _material_to_read(material)


@app.put("/materials/{material_id}", response_model=MaterialRead)
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    previous_price = material.price_per_gram
    previous_supplier = material.supplier
    update_data = payload.dict(exclude_unset=True)
    if {"brand", "color", "color_hex", "color_hexes"} & update_data.keys():
        normalized_hexes = normalize_hex_list(update_data.get("color_hexes", material.color_hexes))
        color_hex = update_data.get("color_hex", material.color_hex)
        update_data["color_hexes"] = normalized_hexes or None
        update_data["color_hex"] = normalize_hex(color_hex) or (normalized_hexes[0] if normalized_hexes else None)
    if "barcode" in update_data:
        update_data["barcode"] = normalize_barcode(update_data.get("barcode"))
    if "refill_barcode" in update_data:
        update_data["refill_barcode"] = normalize_barcode(update_data.get("refill_barcode"))
    for key, value in update_data.items():
        setattr(material, key, value)
    session.add(material)
    session.commit()
    session.refresh(material)
    if payload.price_per_gram is not None and payload.price_per_gram != previous_price:
        history = MaterialCostHistory(
            material_id=material.id,
            unit_cost_per_gram=material.price_per_gram,
            vendor=payload.supplier if payload.supplier is not None else previous_supplier,
            reference="material_update",
            note="Price updated",
        )
        session.add(history)
        session.commit()
    return _material_to_read(material)


@app.get("/materials/{material_id}/cost-history", response_model=List[MaterialCostHistoryRead])
def list_material_cost_history(
    material_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")
    statement = select(MaterialCostHistory).where(MaterialCostHistory.material_id == material_id).order_by(
        MaterialCostHistory.recorded_at.desc()
    )
    return session.exec(statement).all()


@app.post("/materials/{material_id}/cost-history", response_model=MaterialCostHistoryRead, status_code=status.HTTP_201_CREATED)
def create_material_cost_history(
    material_id: int,
    payload: MaterialCostHistoryCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    if material_id != payload.material_id:
        raise HTTPException(status_code=400, detail="Material ID mismatch")
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    entry = MaterialCostHistory.from_orm(payload)
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


@app.get("/materials/{material_id}/barcode")
def get_material_barcode(
    material_id: int,
    value: str | None = None,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    selected_value = normalize_barcode(value) if value is not None else None
    available_values = {normalize_barcode(material.barcode), normalize_barcode(material.refill_barcode)}
    available_values.discard(None)
    if selected_value and selected_value not in available_values:
        raise HTTPException(status_code=400, detail="Barcode value does not match this material")
    barcode_to_render = selected_value or normalize_barcode(material.barcode) or normalize_barcode(material.refill_barcode)
    if not barcode_to_render:
        raise HTTPException(status_code=404, detail="Material barcode not set")
    png_bytes = render_barcode_png(barcode_to_render)
    headers = {"Cache-Control": "no-store"}
    return Response(content=png_bytes, media_type="image/png", headers=headers)


@app.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_material(
    material_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    material = session.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    try:
        _delete_material_dependencies(session, material_id)
        session.delete(material)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Material cannot be deleted because related records still reference it.",
        )
    return None


# Inventory endpoints
@app.post("/inventory", response_model=InventoryItemRead, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryItemCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    _ensure_material_exists(session, payload.material_id)
    data = payload.dict()
    data["spool_serial"] = normalize_barcode(data.get("spool_serial"))
    inventory_item = InventoryItem(**data)
    session.add(inventory_item)
    session.commit()
    session.refresh(inventory_item)
    return inventory_item


@app.get("/inventory", response_model=PaginatedInventoryRead)
def list_inventory_items(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                InventoryItem.location.ilike(pattern),
                InventoryItem.spool_serial.ilike(pattern),
                Material.name.ilike(pattern),
                Material.color.ilike(pattern),
            )
        )
    statement = (
        select(InventoryItem)
        .join(Material, InventoryItem.material_id == Material.id, isouter=True)
        .options(selectinload(InventoryItem.material))
        .order_by(InventoryItem.id)
        .offset(offset)
        .limit(limit)
    )
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(InventoryItem).join(
        Material, InventoryItem.material_id == Material.id, isouter=True
    )
    if filters:
        total_statement = total_statement.where(*filters)
    items = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedInventoryRead(items=items, total=total, limit=limit, offset=offset)


@app.get("/inventory/{item_id}", response_model=InventoryItemRead)
def get_inventory_item(item_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@app.put("/inventory/{item_id}", response_model=InventoryItemRead)
def update_inventory_item(
    item_id: int,
    payload: InventoryItemUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    update_data = payload.dict(exclude_unset=True)
    if "material_id" in update_data:
        _ensure_material_exists(session, update_data["material_id"])
    if "spool_serial" in update_data:
        update_data["spool_serial"] = normalize_barcode(update_data.get("spool_serial"))
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/inventory/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(InventoryItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    session.delete(item)
    session.commit()
    return None


@app.get("/inbound-invoices", response_model=List[InboundInvoiceRead])
def list_inbound_invoices(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    statement = (
        select(InboundInvoice)
        .options(selectinload(InboundInvoice.lines))
        .order_by(InboundInvoice.uploaded_at.desc())
        .offset(offset)
        .limit(limit)
    )
    invoices = session.exec(statement).all()
    return [_inbound_invoice_to_read(invoice) for invoice in invoices]


@app.get("/inbound-invoices/{invoice_id}", response_model=InboundInvoiceRead)
def get_inbound_invoice(
    invoice_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice_id)
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Inbound invoice not found")
    return _inbound_invoice_to_read(invoice)


@app.post("/inbound-invoices/upload", response_model=InboundInvoiceRead, status_code=status.HTTP_201_CREATED)
def upload_inbound_invoice(
    invoice_pdf: UploadFile = File(...),
    expected_location: str = Form(default="Receiving"),
    reorder_level: float = Form(default=0),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    filename = (invoice_pdf.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Invoice upload must be a PDF.")
    source_filename, stored_path = store_upload(invoice_pdf, INBOUND_INVOICE_DIR, "invoice")
    try:
        parsed = parse_invoice_pdf(Path(stored_path))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to parse Bambu invoice PDF: {exc}") from exc

    duplicate = session.exec(
        select(InboundInvoice).where(
            InboundInvoice.invoice_number == parsed.invoice_number,
            InboundInvoice.vendor == (parsed.supplier or DEFAULT_SUPPLIER),
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail=f"Invoice {parsed.invoice_number} has already been uploaded.")

    invoice = InboundInvoice(
        vendor=parsed.supplier or DEFAULT_SUPPLIER,
        invoice_number=parsed.invoice_number,
        order_number=parsed.order_number,
        invoice_date=parsed.invoice_date,
        delivery_date=parsed.delivery_date,
        payment_date=parsed.payment_date,
        source_filename=source_filename,
        invoice_file_path=stored_path,
        status="pending_packing_slip",
        expected_location=(expected_location or "Receiving").strip() or "Receiving",
        reorder_level=max(float(reorder_level or 0), 0),
        total_expected_grams=sum(line.total_grams for line in parsed.lines),
    )
    session.add(invoice)
    session.flush()
    for parsed_line in parsed.lines:
        material = _upsert_bambu_material(
            session,
            vendor=invoice.vendor,
            sku=parsed_line.sku,
            filament_type=parsed_line.filament_type,
            category=parsed_line.category,
            color=parsed_line.color,
            spool_weight_grams=parsed_line.weight_grams,
            unit_cost_per_gram=parsed_line.unit_cost_per_gram,
            package_type=parsed_line.package_type,
            invoice_number=invoice.invoice_number,
        )
        line = InboundInvoiceLine(
            invoice_id=invoice.id,
            material_id=material.id,
            sku=parsed_line.sku,
            product_name=parsed_line.product_name,
            filament_type=parsed_line.filament_type,
            category=parsed_line.category,
            color=parsed_line.color,
            variant_code=parsed_line.variant_code,
            package_type=parsed_line.package_type,
            spool_weight_grams=parsed_line.weight_grams,
            expected_quantity=parsed_line.quantity,
            received_quantity=0,
            unit_cost_per_gram=parsed_line.unit_cost_per_gram,
            items_subtotal=parsed_line.items_subtotal,
            tax_name=parsed_line.tax_name,
            tax_amount=parsed_line.tax_amount,
            status="pending",
        )
        session.add(line)
    session.commit()
    session.refresh(invoice)
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice.id)
    ).first()
    return _inbound_invoice_to_read(invoice)


@app.post("/inbound-invoices/{invoice_id}/packing-slip", response_model=InboundInvoiceRead)
def upload_packing_slip(
    invoice_id: int,
    packing_slip_pdf: UploadFile = File(...),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice_id)
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Inbound invoice not found")
    if invoice.verified_at:
        raise HTTPException(status_code=400, detail="Verified inbound invoices cannot be changed.")
    filename = (packing_slip_pdf.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Packing slip upload must be a PDF.")
    source_filename, stored_path = store_upload(packing_slip_pdf, INBOUND_INVOICE_DIR, "packing-slip")
    invoice.packing_slip_filename = source_filename
    invoice.packing_slip_file_path = stored_path
    invoice.packing_slip_uploaded_at = datetime.utcnow()
    invoice.status = "ready_for_verification"
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice.id)
    ).first()
    return _inbound_invoice_to_read(invoice)


@app.post("/inbound-invoices/{invoice_id}/verify", response_model=InboundInvoiceRead)
def verify_inbound_invoice(
    invoice_id: int,
    payload: InboundInvoiceVerifyRequest,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice_id)
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Inbound invoice not found")
    if invoice.verified_at:
        raise HTTPException(status_code=400, detail="Inbound invoice has already been verified.")
    if not invoice.packing_slip_file_path:
        raise HTTPException(status_code=400, detail="Upload a packing slip before verifying receipt.")

    location = (payload.location or invoice.expected_location or "Receiving").strip() or "Receiving"
    received_lookup = {line.line_id: int(line.received_quantity) for line in payload.lines}
    total_received_grams = 0.0
    for line in invoice.lines:
        received_quantity = max(received_lookup.get(line.id, 0), 0)
        line.received_quantity = received_quantity
        if received_quantity == 0:
            line.status = "missing"
        elif received_quantity < line.expected_quantity:
            line.status = "partial"
        elif received_quantity == line.expected_quantity:
            line.status = "received"
        else:
            line.status = "over_received"
        material = session.get(Material, line.material_id) if line.material_id else None
        if material is None:
            material = _upsert_bambu_material(
                session,
                vendor=invoice.vendor,
                sku=line.sku,
                filament_type=line.filament_type,
                category=line.category,
                color=line.color,
                spool_weight_grams=line.spool_weight_grams,
                unit_cost_per_gram=line.unit_cost_per_gram,
                package_type=line.package_type,
                invoice_number=invoice.invoice_number,
            )
            line.material_id = material.id
        if received_quantity > 0:
            inventory_item = _get_or_create_inventory_item_for_receipt(
                session,
                material_id=material.id,
                location=location,
                reorder_level=invoice.reorder_level,
            )
            grams_received = received_quantity * line.spool_weight_grams
            total_received_grams += grams_received
            inventory_item.quantity_grams += grams_received
            movement = StockMovement(
                inventory_item_id=inventory_item.id,
                movement_type="incoming",
                change_grams=grams_received,
                reference=invoice.invoice_number,
                note=f"Verified against packing slip for order {invoice.order_number} SKU {line.sku}",
            )
            session.add(inventory_item)
            session.add(movement)
            cost_entry = MaterialCostHistory(
                material_id=material.id,
                unit_cost_per_gram=line.unit_cost_per_gram,
                vendor=invoice.vendor,
                reference=invoice.invoice_number,
                note=f"Verified inbound invoice {invoice.order_number} SKU {line.sku}",
            )
            session.add(cost_entry)
        session.add(line)

    invoice.expected_location = location
    invoice.total_received_grams = total_received_grams
    invoice.verification_note = payload.note.strip() if payload.note else None
    invoice.verified_at = datetime.utcnow()
    invoice.status = "verified"
    session.add(invoice)
    session.commit()
    session.refresh(invoice)
    invoice = session.exec(
        select(InboundInvoice).options(selectinload(InboundInvoice.lines)).where(InboundInvoice.id == invoice.id)
    ).first()
    return _inbound_invoice_to_read(invoice)


# Stock movement endpoints
@app.post("/movements", response_model=StockMovementRead, status_code=status.HTTP_201_CREATED)
def create_stock_movement(
    payload: StockMovementCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(InventoryItem, payload.inventory_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    new_qty = item.quantity_grams + payload.change_grams
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock level cannot be negative")

    movement = StockMovement.from_orm(payload)
    item.quantity_grams = new_qty
    session.add(movement)
    session.add(item)
    session.commit()
    session.refresh(movement)
    return movement


@app.get("/inventory/{item_id}/movements", response_model=List[StockMovementRead])
def list_movements(item_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_inventory_exists(session, item_id)
    statement = select(StockMovement).where(StockMovement.inventory_item_id == item_id).order_by(
        StockMovement.created_at.desc()
    )
    movements = session.exec(statement).all()
    return movements


# Hardware endpoints
@app.post("/hardware", response_model=HardwareItemRead, status_code=status.HTTP_201_CREATED)
def create_hardware_item(
    payload: HardwareItemCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = HardwareItem.from_orm(payload)
    session.add(item)
    session.flush()
    _sync_hardware_item_to_makerworks_product_template(
        session,
        item,
        include_catalog_fields=True,
        allow_create=True,
    )
    session.commit()
    session.refresh(item)
    return item


@app.get("/hardware", response_model=PaginatedHardwareRead)
def list_hardware_items(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                HardwareItem.name.ilike(pattern),
                HardwareItem.category.ilike(pattern),
                HardwareItem.merch_color.ilike(pattern),
                HardwareItem.merch_size.ilike(pattern),
                HardwareItem.merch_style.ilike(pattern),
                HardwareItem.merch_sku.ilike(pattern),
                HardwareItem.supplier.ilike(pattern),
                HardwareItem.manufacturer_part_number.ilike(pattern),
                HardwareItem.bin_location.ilike(pattern),
            )
        )
    statement = select(HardwareItem).order_by(HardwareItem.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    total_statement = select(func.count()).select_from(HardwareItem)
    if filters:
        total_statement = total_statement.where(*filters)
    items = session.exec(statement).all()
    total = session.exec(total_statement).one()
    return PaginatedHardwareRead(items=items, total=total, limit=limit, offset=offset)


@app.get("/hardware/{hardware_id}", response_model=HardwareItemRead)
def get_hardware_item(hardware_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    return item


@app.put("/hardware/{hardware_id}", response_model=HardwareItemRead)
def update_hardware_item(
    hardware_id: int,
    payload: HardwareItemUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)
    session.add(item)
    session.flush()
    _sync_merch_variant_family_to_makerworks(session, item, include_catalog_fields=True)
    session.commit()
    session.refresh(item)
    return item


@app.delete("/hardware/{hardware_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hardware_item(
    hardware_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(HardwareItem, hardware_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    template_id = (item.makerworks_product_template_id or "").strip()
    if template_id:
        if (item.category or "").strip().lower() == "merch":
            _delete_makerworks_merch_item(session, template_id)
        else:
            item.quantity_on_hand = 0
            _sync_hardware_item_to_makerworks_product_template(session, item, include_catalog_fields=False)
    session.delete(item)
    session.commit()
    return None


@app.post("/hardware/movements", response_model=HardwareMovementRead, status_code=status.HTTP_201_CREATED)
def create_hardware_movement(
    payload: HardwareMovementCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    item = session.get(HardwareItem, payload.hardware_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Hardware item not found")
    new_qty = item.quantity_on_hand + payload.change_units
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Stock level cannot be negative")
    movement = HardwareMovement.from_orm(payload)
    item.quantity_on_hand = new_qty
    session.add(item)
    session.add(movement)
    session.flush()
    _sync_merch_variant_family_to_makerworks(session, item, include_catalog_fields=False)
    session.commit()
    session.refresh(movement)
    return movement


@app.get("/hardware/{hardware_id}/movements", response_model=List[HardwareMovementRead])
def list_hardware_movements(hardware_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_hardware_exists(session, hardware_id)
    statement = select(HardwareMovement).where(HardwareMovement.hardware_item_id == hardware_id).order_by(
        HardwareMovement.created_at.desc()
    )
    return session.exec(statement).all()


@app.post("/makerworks/merch/sync")
def sync_makerworks_merch_inventory(
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    return _sync_makerworks_merch_to_hardware(session)


# 3D model endpoints
@app.post("/models", response_model=PrintModelRead, status_code=status.HTTP_201_CREATED)
def create_print_model(
    payload: PrintModelCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    data = payload.dict()
    data["sku"] = normalize_sku(data.get("sku"))
    model = PrintModel(**data)
    session.add(model)
    session.flush()
    _sync_model_to_makerworks_product_template(session, model)
    session.commit()
    session.refresh(model)
    return _model_read_with_totals(session, model)


@app.get("/models", response_model=PaginatedModelsRead)
def list_print_models(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, min_length=1),
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
):
    filters = []
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                PrintModel.name.ilike(pattern),
                PrintModel.category.ilike(pattern),
                PrintModel.sku.ilike(pattern),
                PrintModel.designer.ilike(pattern),
                PrintModel.platform.ilike(pattern),
            )
        )
    statement = select(PrintModel).order_by(PrintModel.name).offset(offset).limit(limit)
    if filters:
        statement = statement.where(*filters)
    models = session.exec(statement).all()
    total_statement = select(func.count()).select_from(PrintModel)
    if filters:
        total_statement = total_statement.where(*filters)
    total = session.exec(total_statement).one()
    totals = _model_sales_summary(session, [model.id for model in models if model.id])
    return PaginatedModelsRead(
        items=[_model_read_with_totals(session, model, totals) for model in models],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/models/{model_id}", response_model=PrintModelRead)
def get_print_model(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return _model_read_with_totals(session, model)


@app.put("/models/{model_id}", response_model=PrintModelRead)
def update_print_model(
    model_id: int,
    payload: PrintModelUpdate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    update_data = payload.dict(exclude_unset=True)
    if "sku" in update_data:
        update_data["sku"] = normalize_sku(update_data.get("sku"))
    for key, value in update_data.items():
        setattr(model, key, value)
    session.add(model)
    session.flush()
    _sync_model_to_makerworks_product_template(session, model)
    session.commit()
    session.refresh(model)
    return _model_read_with_totals(session, model)


@app.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_print_model(
    model_id: int,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    model = session.get(PrintModel, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    sales = session.exec(select(PrintModelSale).where(PrintModelSale.model_id == model_id)).all()
    for sale in sales:
        session.delete(sale)
    movements = session.exec(select(PrintModelMovement).where(PrintModelMovement.model_id == model_id)).all()
    for movement in movements:
        session.delete(movement)
    session.delete(model)
    session.commit()
    return None


@app.post("/models/movements", response_model=PrintModelMovementRead, status_code=status.HTTP_201_CREATED)
def create_print_model_movement(
    payload: PrintModelMovementCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    model = session.get(PrintModel, payload.model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    new_qty = float(model.quantity_on_hand or 0) + payload.change_units
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Movement would reduce model stock below zero")
    model.quantity_on_hand = new_qty
    movement = PrintModelMovement.from_orm(payload)
    session.add(model)
    session.add(movement)
    session.flush()
    _sync_model_to_makerworks_product_template(session, model)
    session.commit()
    session.refresh(movement)
    return movement


@app.get("/models/{model_id}/movements", response_model=List[PrintModelMovementRead])
def list_print_model_movements(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_model_exists(session, model_id)
    statement = select(PrintModelMovement).where(PrintModelMovement.model_id == model_id).order_by(
        PrintModelMovement.created_at.desc()
    )
    return session.exec(statement).all()


@app.post("/models/sales", response_model=PrintModelSaleRead, status_code=status.HTTP_201_CREATED)
def create_print_model_sale(
    payload: PrintModelSaleCreate,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    model = session.get(PrintModel, payload.model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    new_qty = float(model.quantity_on_hand or 0) - payload.quantity
    if new_qty < 0:
        raise HTTPException(status_code=400, detail="Sale would reduce model stock below zero")
    sale = PrintModelSale.from_orm(payload)
    movement = PrintModelMovement(
        model_id=payload.model_id,
        movement_type="sale",
        change_units=-float(payload.quantity),
        reference=payload.reference,
        note=payload.note or payload.channel,
    )
    model.quantity_on_hand = new_qty
    session.add(model)
    session.add(sale)
    session.add(movement)
    session.flush()
    _sync_model_to_makerworks_product_template(session, model)
    session.commit()
    session.refresh(sale)
    return sale


@app.get("/models/{model_id}/sales", response_model=List[PrintModelSaleRead])
def list_print_model_sales(model_id: int, session: Session = Depends(get_session), _: bool = Depends(require_auth)):
    _ensure_model_exists(session, model_id)
    statement = select(PrintModelSale).where(PrintModelSale.model_id == model_id).order_by(
        PrintModelSale.sold_at.desc()
    )
    return session.exec(statement).all()


# Pricing endpoint
@app.post("/pricing/quote", response_model=PricingResponse)
def calculate_quote(
    payload: PricingRequest,
    session: Session = Depends(get_session),
    _: bool = Depends(require_auth),
    _csrf: bool = Depends(require_csrf),
):
    material = session.get(Material, payload.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found for quote")

    material_cost = payload.weight_grams * material.price_per_gram
    machine_cost = payload.print_time_hours * payload.machine_hour_rate
    subtotal = material_cost + machine_cost + payload.labor_cost
    margin_amount = subtotal * (payload.margin_pct / 100)
    total_price = subtotal + margin_amount

    breakdown = PricingBreakdown(
        material_cost=round(material_cost, 2),
        machine_cost=round(machine_cost, 2),
        labor_cost=round(payload.labor_cost, 2),
        subtotal=round(subtotal, 2),
        margin_amount=round(margin_amount, 2),
        total_price=round(total_price, 2),
    )

    return PricingResponse(pricing=breakdown, material_snapshot=MaterialRead.from_orm(material))


@app.get("/orderworks/jobs")
def fetch_orderworks_jobs(
    _: bool = Depends(require_auth),
    session: Session = Depends(get_session),
):
    base_url_override = os.environ.get("ORDERWORKS_BASE_URL", "")
    try:
        jobs = list_orderworks_jobs_via_database(session)
    except OrderWorksDatabaseUnavailableError as db_error:
        client = get_orderworks_client()
        if not client.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"{db_error}. Provide ORDERWORKS_* credentials for HTTP fallback or verify DATABASE_URL.",
            )
        try:
            jobs = client.list_jobs()
        except OrderWorksNotConfiguredError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="OrderWorks integration is not configured.",
            )
        except OrderWorksAuthenticationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
        except OrderWorksIntegrationError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
        return {"jobs": jobs, "base_url": client.base_url}
    return {"jobs": jobs, "base_url": base_url_override}


@app.get("/printlab/filaments")
@app.get("/bambu-view/filaments")
def fetch_printlab_filaments(_: bool = Depends(require_auth)):
    trace_id = secrets.token_hex(4)
    _printlab_trace(trace_id, "start")
    client = get_printlab_client()
    if not client.is_configured:
        _printlab_trace(trace_id, "not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PrintLab integration is not configured. Set PRINTLAB_BASE_URL.",
        )
    try:
        fleet = client.fetch_printers()
    except PrintLabNotConfiguredError:
        _printlab_trace(trace_id, "not_configured_exception")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PrintLab integration is not configured.",
        )
    except PrintLabAuthenticationError as exc:
        _printlab_trace(trace_id, "auth_error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    except PrintLabIntegrationError as exc:
        _printlab_trace(trace_id, "integration_error", error=str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    _printlab_trace(trace_id, "fleet_loaded", fleet_count=len(fleet))
    printers = []
    loaded_count = 0
    for printer in fleet:
        if not isinstance(printer, dict):
            continue
        printer_id = str(printer.get("id") or "").strip()
        if not printer_id:
            continue
        state = {}
        try:
            state = client.fetch_printer_state(printer_id)
        except PrintLabIntegrationError as exc:
            _printlab_trace(trace_id, "printer_state_error", printer_id=printer_id, error=str(exc))
            if isinstance(printer.get("ams"), dict) or isinstance(printer.get("trays"), list):
                state = printer

        ams, trays = _extract_ams_trays(state if isinstance(state, dict) else {})
        if not trays:
            trays = _extract_printlab_trays(ams)
        _printlab_trace(
            trace_id,
            "printer_parsed",
            printer_id=printer_id,
            printer_keys=sorted(printer.keys()),
            ams_keys=sorted(ams.keys()) if isinstance(ams, dict) else [],
            tray_candidates=len(trays),
        )
        loaded_trays = [_normalize_loaded_tray(item) for item in trays if _is_loaded_tray(item)]
        loaded_count += len(loaded_trays)
        ams_slots = ams.get("slots")
        ams_slot_count = len(ams_slots) if isinstance(ams_slots, list) else ams.get("slots")
        ams_units = 1 if isinstance(ams_slots, list) and ams_slots else 0
        printers.append(
            {
                "printer_id": printer_id,
                "printer_name": str(printer.get("name") or printer_id or "Printer"),
                "ams_slots": ams_slot_count,
                "ams_units": ams_units,
                "loaded_trays": loaded_trays,
            }
        )
    _printlab_trace(trace_id, "done", printer_count=len(printers), loaded_count=loaded_count)
    payload = {"printers": printers, "loaded_count": loaded_count, "base_url": client.base_url}
    if _printlab_trace_enabled():
        payload["trace_id"] = trace_id
    return payload


@app.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


def _ensure_material_exists(session: Session, material_id: int) -> None:
    if not session.get(Material, material_id):
        raise HTTPException(status_code=404, detail="Material not found")


def _find_bambu_material(
    session: Session,
    *,
    sku: str,
    filament_type: str,
    category: str | None,
    color: str,
) -> Material | None:
    material = session.exec(select(Material).where((Material.barcode == sku) | (Material.refill_barcode == sku))).first()
    if material:
        return material
    return session.exec(
        select(Material).where(
            Material.brand == "Bambu Lab",
            Material.filament_type == filament_type,
            Material.category == category,
            Material.color == color,
        )
    ).first()


def _upsert_bambu_material(
    session: Session,
    *,
    vendor: str,
    sku: str,
    filament_type: str,
    category: str | None,
    color: str,
    spool_weight_grams: int,
    unit_cost_per_gram: float,
    package_type: str,
    invoice_number: str,
) -> Material:
    material = _find_bambu_material(
        session,
        sku=sku,
        filament_type=filament_type,
        category=category,
        color=color,
    )
    if material is None:
        material = Material(
            name=sku,
            brand="Bambu Lab",
            filament_type=filament_type,
            category=category,
            color=color,
            supplier=vendor or DEFAULT_SUPPLIER,
            price_per_gram=unit_cost_per_gram,
            spool_weight_grams=spool_weight_grams,
            notes=f"Created from inbound invoice {invoice_number}",
        )
        if package_type.lower() == "refill":
            material.refill_barcode = sku
        else:
            material.barcode = sku
        session.add(material)
        session.flush()
        return material

    material.brand = "Bambu Lab"
    material.filament_type = filament_type
    material.category = category
    material.color = color
    material.supplier = vendor or DEFAULT_SUPPLIER
    material.price_per_gram = unit_cost_per_gram
    material.spool_weight_grams = spool_weight_grams
    if package_type.lower() == "refill":
        material.refill_barcode = sku
    else:
        material.barcode = sku
    session.add(material)
    session.flush()
    return material


def _get_or_create_inventory_item_for_receipt(
    session: Session,
    *,
    material_id: int,
    location: str,
    reorder_level: float,
) -> InventoryItem:
    item = session.exec(
        select(InventoryItem).where(
            InventoryItem.material_id == material_id,
            InventoryItem.location == location,
        )
    ).first()
    if item:
        if reorder_level > item.reorder_level:
            item.reorder_level = reorder_level
            session.add(item)
            session.flush()
        return item
    item = InventoryItem(
        material_id=material_id,
        location=location,
        quantity_grams=0,
        reorder_level=reorder_level,
        spool_serial=None,
        unit_cost_override=None,
    )
    session.add(item)
    session.flush()
    return item


def _is_loaded_tray(tray: object) -> bool:
    if not isinstance(tray, dict):
        return False
    material = _first_non_empty_str(
        tray.get("material"),
        tray.get("tray_type"),
        tray.get("type"),
        tray.get("filament_type"),
    )
    name = _first_non_empty_str(
        tray.get("name"),
        tray.get("tray_id_name"),
        tray.get("tray_name"),
        tray.get("filament_name"),
    )
    state_value = _first_non_empty_str(
        tray.get("state"),
        tray.get("tray_state"),
        tray.get("status"),
    ).lower()
    if _looks_like_loaded_label(material) or name:
        return True
    if state_value in {"loaded", "ready", "available", "installed", "active", "in_use", "in-use"}:
        return True
    remain = tray.get("remain")
    if isinstance(remain, (int, float)) and remain >= 0:
        return True
    if isinstance(remain, str) and remain.strip():
        try:
            if float(remain) >= 0:
                return True
        except ValueError:
            pass
    tray_uuid = _first_non_empty_str(tray.get("tray_uuid"))
    if tray_uuid and tray_uuid.strip("0"):
        return True
    tag_uid = _first_non_empty_str(tray.get("tag_uid"))
    if tag_uid and tag_uid.strip("0"):
        return True
    if state_value in {"", "none", "empty"}:
        return False
    return False


def _normalize_loaded_tray(tray: object) -> dict[str, object]:
    if not isinstance(tray, dict):
        return {
            "id": "",
            "unit": None,
            "slot": None,
            "material": "",
            "name": "",
            "color": "",
            "colors": [],
            "state": "",
        }
    color_value = _first_non_empty_str(
        tray.get("color"),
        tray.get("tray_color"),
    )
    color_values: list[str] = []
    if color_value:
        color_values.append(color_value)
    if not color_value:
        cols = tray.get("cols")
        if isinstance(cols, list):
            for item in cols:
                if isinstance(item, str) and item.strip():
                    color_value = item.strip()
                    break
    cols = tray.get("cols")
    if isinstance(cols, list):
        color_values.extend(item.strip() for item in cols if isinstance(item, str) and item.strip())
    normalized_colors = normalize_hex_list(color_values)
    if not color_value and normalized_colors:
        color_value = normalized_colors[0]
    tray_id = _first_non_empty_str(
        tray.get("id"),
        tray.get("tray_id"),
    )
    return {
        "id": tray_id,
        "unit": _first_non_empty_value(tray.get("unit"), tray.get("ams_id"), tray.get("__unit")),
        "slot": _first_non_empty_value(tray.get("slot"), tray.get("tray_id"), tray.get("id"), tray.get("__slot")),
        "material": _first_non_empty_str(
            tray.get("material"),
            tray.get("tray_type"),
            tray.get("type"),
            tray.get("filament_type"),
        ),
        "name": _first_non_empty_str(
            tray.get("name"),
            tray.get("tray_id_name"),
            tray.get("tray_name"),
            tray.get("filament_name"),
        ),
        "color": color_value,
        "colors": normalized_colors,
        "state": _first_non_empty_str(
            tray.get("state"),
            tray.get("tray_state"),
            tray.get("status"),
        ),
    }


def _is_loaded_spool(spool: object) -> bool:
    if not isinstance(spool, dict):
        return False
    material = _first_non_empty_str(spool.get("material"))
    color = _first_non_empty_str(spool.get("color"))
    tray_label = _first_non_empty_str(spool.get("tray"))
    # /api/spools can include library placeholders (e.g. "Spool <date>") with no tray linkage.
    # Treat a spool as loaded only when it carries tray/material/color identity from the printer state.
    return bool(tray_label or material or color)


def _normalize_spool_tray(spool: dict[str, Any], fallback_slot: int) -> dict[str, object]:
    tray_label = _first_non_empty_str(spool.get("tray"))
    unit, slot = _parse_tray_label(tray_label)
    if slot is None:
        slot = fallback_slot
    name = _first_non_empty_str(spool.get("name"))
    material = _first_non_empty_str(spool.get("material"))
    remaining = spool.get("remaining_pct")
    state = "loaded"
    if isinstance(remaining, (int, float)):
        state = f"{remaining:.0f}% remaining"
    elif isinstance(remaining, str) and remaining.strip():
        state = f"{remaining.strip()}% remaining"
    return {
        "id": _first_non_empty_str(spool.get("id")),
        "unit": unit,
        "slot": slot,
        "material": material,
        "name": name,
        "color": _first_non_empty_str(spool.get("color")),
        "colors": normalize_hex_list([_first_non_empty_str(spool.get("color"))]),
        "state": state,
    }


def _parse_tray_label(label: str) -> tuple[object, object]:
    value = label.strip().upper()
    if not value:
        return None, None
    match = re.fullmatch(r"([A-Z]?)(\d+)", value)
    if not match:
        return None, None
    unit_code = match.group(1)
    slot_value = int(match.group(2))
    unit: object = 1
    if unit_code:
        unit = ord(unit_code) - ord("A") + 1
    return unit, slot_value


def _extract_printlab_trays(ams: dict[str, Any]) -> list[dict[str, Any]]:
    slots = ams.get("slots")
    if not isinstance(slots, list):
        return []
    ams_index = ams.get("ams_index")
    if isinstance(ams_index, int):
        unit_hint: object = ams_index + 1
    else:
        unit_hint = ams_index
    trays: list[dict[str, Any]] = []
    for raw_slot in slots:
        if not isinstance(raw_slot, dict):
            continue
        slot_index = raw_slot.get("index")
        if isinstance(slot_index, int):
            slot_value: object = slot_index + 1
        else:
            slot_value = slot_index
        if bool(raw_slot.get("empty")):
            continue
        state = "loaded"
        remain = raw_slot.get("remain_percent")
        if isinstance(remain, (int, float)):
            state = f"{remain:.0f}% remaining"
        elif isinstance(remain, str) and remain.strip():
            state = f"{remain.strip()}% remaining"
        trays.append(
            {
                "id": _first_non_empty_str(raw_slot.get("id"), raw_slot.get("name")),
                "unit": unit_hint,
                "slot": slot_value,
                "type": _first_non_empty_str(raw_slot.get("type")),
                "name": _first_non_empty_str(raw_slot.get("name")),
                "color": _first_non_empty_str(raw_slot.get("color_hex")),
                "state": state,
            }
        )
    return trays


def _extract_ams_trays(printer: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    ams = printer.get("ams") if isinstance(printer.get("ams"), dict) else {}
    trays: list[dict[str, Any]] = []

    def _append_trays(items: object, unit_hint: object = None) -> None:
        if not isinstance(items, list):
            return
        for idx, tray in enumerate(items):
            if not isinstance(tray, dict):
                continue
            normalized = dict(tray)
            if normalized.get("unit") is None and unit_hint is not None:
                normalized["__unit"] = unit_hint
            if normalized.get("slot") is None:
                normalized["__slot"] = idx
            trays.append(normalized)

    _append_trays(ams.get("trays"))
    _append_trays(ams.get("tray"))

    units = ams.get("ams")
    if isinstance(units, list):
        for unit_idx, unit in enumerate(units):
            if not isinstance(unit, dict):
                continue
            unit_hint = _first_non_empty_value(unit.get("id"), unit_idx)
            _append_trays(unit.get("tray"), unit_hint=unit_hint)
            _append_trays(unit.get("trays"), unit_hint=unit_hint)

    if not trays and isinstance(printer.get("trays"), list):
        _append_trays(printer.get("trays"))

    if "units" not in ams:
        if isinstance(units, list):
            ams = {**ams, "units": len(units)}
        elif trays:
            ams = {**ams, "units": 1}
    if "slots" not in ams and trays:
        ams = {**ams, "slots": len(trays)}

    return ams, trays


def _first_non_empty_str(*values: object) -> str:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return ""


def _first_non_empty_value(*values: object) -> object:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _looks_like_loaded_label(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    return normalized not in {"empty", "none", "null", "unknown", "n/a", "-"}


def _printlab_trace_enabled() -> bool:
    raw = (os.environ.get("PRINTLAB_TRACE") or os.environ.get("BAMBU_VIEW_TRACE") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _printlab_trace(trace_id: str, event: str, **fields: Any) -> None:
    if not _printlab_trace_enabled():
        return
    if fields:
        logger.warning("printlab_trace trace_id=%s event=%s fields=%s", trace_id, event, fields)
        return
    logger.warning("printlab_trace trace_id=%s event=%s", trace_id, event)


def _delete_material_dependencies(session: Session, material_id: int) -> None:
    inventory_items = session.exec(select(InventoryItem).where(InventoryItem.material_id == material_id)).all()
    inventory_ids = [item.id for item in inventory_items if item.id is not None]

    if inventory_ids:
        movements = session.exec(
            select(StockMovement).where(StockMovement.inventory_item_id.in_(inventory_ids))
        ).all()
        for movement in movements:
            session.delete(movement)

    for item in inventory_items:
        session.delete(item)

    cost_history_entries = session.exec(
        select(MaterialCostHistory).where(MaterialCostHistory.material_id == material_id)
    ).all()
    for entry in cost_history_entries:
        session.delete(entry)


def _material_to_read(material: Material) -> MaterialRead:
    raw_hexes = material.color_hexes
    if isinstance(raw_hexes, list):
        color_hexes = raw_hexes
    elif isinstance(raw_hexes, str):
        stripped = raw_hexes.strip()
        if not stripped or stripped.lower() == "null":
            color_hexes = []
        else:
            try:
                parsed = json.loads(stripped)
            except Exception:
                parsed = None
            color_hexes = parsed if isinstance(parsed, list) else []
    else:
        color_hexes = []
    return MaterialRead.model_validate({
        "id": material.id,
        "name": material.name,
        "brand": material.brand,
        "filament_type": material.filament_type,
        "category": material.category,
        "color": material.color,
        "color_hex": material.color_hex,
        "color_hexes": color_hexes,
        "supplier": material.supplier,
        "price_per_gram": material.price_per_gram,
        "spool_weight_grams": material.spool_weight_grams,
        "barcode": material.barcode,
        "refill_barcode": material.refill_barcode,
        "notes": material.notes,
    })


def _inbound_invoice_to_read(invoice: InboundInvoice) -> InboundInvoiceRead:
    return InboundInvoiceRead.model_validate(
        {
            "id": invoice.id,
            "vendor": invoice.vendor,
            "invoice_number": invoice.invoice_number,
            "order_number": invoice.order_number,
            "invoice_date": invoice.invoice_date,
            "delivery_date": invoice.delivery_date,
            "payment_date": invoice.payment_date,
            "source_filename": invoice.source_filename,
            "invoice_file_path": invoice.invoice_file_path,
            "packing_slip_filename": invoice.packing_slip_filename,
            "packing_slip_file_path": invoice.packing_slip_file_path,
            "status": invoice.status,
            "expected_location": invoice.expected_location,
            "reorder_level": invoice.reorder_level,
            "verification_note": invoice.verification_note,
            "total_expected_grams": invoice.total_expected_grams,
            "total_received_grams": invoice.total_received_grams,
            "uploaded_at": invoice.uploaded_at,
            "packing_slip_uploaded_at": invoice.packing_slip_uploaded_at,
            "verified_at": invoice.verified_at,
            "lines": [
                InboundInvoiceLineRead.model_validate(
                    {
                        "id": line.id,
                        "invoice_id": line.invoice_id,
                        "material_id": line.material_id,
                        "sku": line.sku,
                        "product_name": line.product_name,
                        "filament_type": line.filament_type,
                        "category": line.category,
                        "color": line.color,
                        "variant_code": line.variant_code,
                        "package_type": line.package_type,
                        "spool_weight_grams": line.spool_weight_grams,
                        "expected_quantity": line.expected_quantity,
                        "received_quantity": line.received_quantity,
                        "unit_cost_per_gram": line.unit_cost_per_gram,
                        "items_subtotal": line.items_subtotal,
                        "tax_name": line.tax_name,
                        "tax_amount": line.tax_amount,
                        "status": line.status,
                        "note": line.note,
                    }
                )
                for line in sorted(invoice.lines, key=lambda entry: entry.id or 0)
            ],
        }
    )


def _ensure_unique_material_name(session: Session, name: str) -> str:
    base = (name or "").strip()
    if not base:
        return base
    normalized = base.lower()
    exists = session.exec(select(Material).where(func.lower(Material.name) == normalized)).first()
    if not exists:
        return base
    suffix = 1
    while True:
        candidate = f"{base} {suffix}"
        candidate_exists = session.exec(
            select(Material).where(func.lower(Material.name) == candidate.lower())
        ).first()
        if not candidate_exists:
            return candidate
        suffix += 1


def _ensure_inventory_exists(session: Session, item_id: int) -> None:
    if not session.get(InventoryItem, item_id):
        raise HTTPException(status_code=404, detail="Inventory item not found")


def _ensure_hardware_exists(session: Session, hardware_id: int) -> None:
    if not session.get(HardwareItem, hardware_id):
        raise HTTPException(status_code=404, detail="Hardware item not found")


def _ensure_model_exists(session: Session, model_id: int) -> None:
    if not session.get(PrintModel, model_id):
        raise HTTPException(status_code=404, detail="Model not found")


def _model_sales_summary(session: Session, model_ids: List[int]) -> dict[int, tuple[int, float]]:
    if not model_ids:
        return {}
    statement = (
        select(
            PrintModelSale.model_id,
            func.sum(PrintModelSale.quantity),
            func.sum(PrintModelSale.quantity * PrintModelSale.unit_price),
        )
        .where(PrintModelSale.model_id.in_(model_ids))
        .group_by(PrintModelSale.model_id)
    )
    rows = session.exec(statement).all()
    summary: dict[int, tuple[int, float]] = {}
    for model_id, total_units, total_revenue in rows:
        summary[int(model_id)] = (int(total_units or 0), float(total_revenue or 0))
    return summary


def _model_read_with_totals(
    session: Session,
    model: PrintModel,
    summary: dict[int, tuple[int, float]] | None = None,
) -> PrintModelRead:
    data = PrintModelRead.from_orm(model)
    if model.id is None:
        return data
    totals = summary.get(model.id) if summary is not None else _model_sales_summary(session, [model.id])
    if isinstance(totals, dict):
        totals = totals.get(model.id)
    if totals:
        data.total_sold = int(totals[0] or 0)
        data.total_revenue = float(totals[1] or 0)
    return data


def _sync_model_to_makerworks_product_template(session: Session, model: PrintModel) -> None:
    if model.id is None:
        return
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return
    conn = session.connection()
    exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
            """
        )
    ).first()
    if not exists:
        return

    description = (model.notes or "").strip() or (model.category or "").strip() or None
    now = datetime.utcnow()
    available_columns = _fetch_table_columns(conn, "public", "ProductTemplate")
    id_column = _find_matching_column(available_columns, ["id"])
    title_column = _find_matching_column(available_columns, ["title", "name"])
    description_column = _find_matching_column(available_columns, ["description", "details"])
    active_column = _find_matching_column(available_columns, ["isActive", "active", "enabled"])
    stockworks_link_column = _find_matching_column(
        available_columns,
        ["stockworksInventoryItemId", "stockworks_inventory_item_id"],
    )
    quantity_column = _find_matching_column(
        available_columns,
        [
            "quantityOnHand",
            "stockOnHand",
            "inventoryQuantity",
            "inventoryCount",
            "availableQuantity",
            "onHand",
            "stock",
        ],
    )
    in_stock_column = _find_matching_column(
        available_columns,
        ["isInStock", "inStock", "available", "isAvailable", "in_stock"],
    )
    sold_out_column = _find_matching_column(available_columns, ["isSoldOut", "soldOut", "outOfStock", "sold_out"])
    stock_status_column = _find_matching_column(
        available_columns,
        ["stockStatus", "availability", "inventoryStatus", "stock_status"],
    )
    type_column = _find_matching_column(
        available_columns,
        [
            "productType",
            "product_type",
            "templateType",
            "template_type",
            "itemType",
            "item_type",
            "listingType",
            "listing_type",
            "templateKind",
            "template_kind",
            "kind",
        ],
    )
    merch_flag_column = _find_matching_column(
        available_columns,
        [
            "isMerch",
            "is_merch",
            "merch",
            "isMerchandise",
            "is_merchandise",
        ],
    )
    existing = None
    template_id = (model.makerworks_product_template_id or "").strip()
    if template_id and id_column:
        existing = conn.execute(
            text(
                f'''
                SELECT {_quote_identifier(id_column)}
                FROM public."ProductTemplate"
                WHERE {_quote_identifier(id_column)} = :product_id
                LIMIT 1
                '''
            ),
            {"product_id": template_id},
        ).first()
    if not existing and stockworks_link_column:
        existing = conn.execute(
            text(
                f'''
                SELECT {_quote_identifier(id_column or "id")}
                FROM public."ProductTemplate"
                WHERE {_quote_identifier(stockworks_link_column)} = :model_id
                LIMIT 1
                '''
            ),
            {"model_id": model.id},
        ).first()

    target_product_id: str | None = None
    try:
        if existing:
            target_product_id = str(existing[0])
        else:
            target_product_id = f"stockworks-model-{model.id}"
            insert_columns = []
            insert_values = []
            insert_params: dict[str, Any] = {}
            if id_column:
                insert_columns.append(id_column)
                insert_values.append(":id")
                insert_params["id"] = target_product_id
            if title_column:
                insert_columns.append(title_column)
                insert_values.append(":title")
                insert_params["title"] = model.name
            if description_column:
                insert_columns.append(description_column)
                insert_values.append(":description")
                insert_params["description"] = description
            if active_column:
                insert_columns.append(active_column)
                insert_values.append(":is_active")
                insert_params["is_active"] = bool(model.active)
            if stockworks_link_column:
                insert_columns.append(stockworks_link_column)
                insert_values.append(":stockworks_inventory_item_id")
                insert_params["stockworks_inventory_item_id"] = model.id
            created_at_column = _find_matching_column(available_columns, ["createdAt", "created_at"])
            updated_at_column = _find_matching_column(available_columns, ["updatedAt", "updated_at"])
            if created_at_column:
                insert_columns.append(created_at_column)
                insert_values.append(":created_at")
                insert_params["created_at"] = now
            if updated_at_column:
                insert_columns.append(updated_at_column)
                insert_values.append(":updated_at")
                insert_params["updated_at"] = now
            conn.execute(
                text(
                    f'INSERT INTO public."ProductTemplate" ('
                    f'{", ".join(_quote_identifier(col) for col in insert_columns)}'
                    f') VALUES ({", ".join(insert_values)})'
                ),
                insert_params,
            )
        model.makerworks_product_template_id = target_product_id
        session.add(model)
        set_parts: list[str] = []
        params: dict[str, Any] = {"product_id": target_product_id}
        if title_column:
            set_parts.append(f'{_quote_identifier(title_column)} = :title')
            params["title"] = model.name
        if description_column:
            set_parts.append(f'{_quote_identifier(description_column)} = :description')
            params["description"] = description
        if active_column:
            set_parts.append(f'{_quote_identifier(active_column)} = :is_active')
            params["is_active"] = bool(model.active)
        if stockworks_link_column:
            set_parts.append(f'{_quote_identifier(stockworks_link_column)} = :stockworks_inventory_item_id')
            params["stockworks_inventory_item_id"] = model.id
        if quantity_column:
            set_parts.append(f'{_quote_identifier(quantity_column)} = :quantity_on_hand')
            params["quantity_on_hand"] = float(model.quantity_on_hand or 0)
        has_stock = float(model.quantity_on_hand or 0) > 0
        if in_stock_column:
            set_parts.append(f'{_quote_identifier(in_stock_column)} = :is_in_stock')
            params["is_in_stock"] = has_stock
        if sold_out_column:
            set_parts.append(f'{_quote_identifier(sold_out_column)} = :is_sold_out')
            params["is_sold_out"] = not has_stock
        if stock_status_column:
            set_parts.append(f'{_quote_identifier(stock_status_column)} = :stock_status')
            params["stock_status"] = "in_stock" if has_stock else "sold_out"
        updated_at_column = _find_matching_column(available_columns, ["updatedAt", "updated_at"])
        if updated_at_column:
            set_parts.append(f'{_quote_identifier(updated_at_column)} = :updated_at')
            params["updated_at"] = now
        if set_parts and id_column:
            conn.execute(
                text(
                    f'UPDATE public."ProductTemplate" '
                    f'SET {", ".join(set_parts)} '
                    f'WHERE {_quote_identifier(id_column)} = :product_id'
                ),
                params,
            )
        _set_makerworks_product_template_classification(
            conn,
            template_id=target_product_id,
            type_column=type_column,
            merch_flag_column=merch_flag_column,
            is_merch=False,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to sync model to MakerWorks ProductTemplate: {exc}",
        ) from exc


def _sync_hardware_item_to_makerworks_product_template(
    session: Session,
    item: HardwareItem,
    *,
    include_catalog_fields: bool = True,
    allow_create: bool = False,
) -> None:
    category = (item.category or "").strip().lower()
    if category == "merch":
        _sync_hardware_item_to_makerworks_merch_item(
            session,
            item,
            include_catalog_fields=include_catalog_fields,
            allow_create=allow_create,
        )
        return

    template_id = (item.makerworks_product_template_id or "").strip()
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    conn = session.connection()
    table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
            """
        )
    ).first()
    if not table_exists:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks table public."ProductTemplate" was not found for merch sync writeback.',
        )

    available_columns = _fetch_table_columns(conn, "public", "ProductTemplate")
    id_column = _find_matching_column(available_columns, ["id"])
    if not id_column:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks ProductTemplate is missing required "id" column for merch sync writeback.',
        )

    title_column = _find_matching_column(available_columns, ["title", "name"])
    description_column = _find_matching_column(available_columns, ["description", "details"])
    active_column = _find_matching_column(available_columns, ["isActive", "active", "enabled"])
    stockworks_link_column = _find_matching_column(
        available_columns,
        ["stockworksInventoryItemId", "stockworks_inventory_item_id"],
    )
    quantity_column = _find_matching_column(
        available_columns,
        [
            "quantityOnHand",
            "stockOnHand",
            "inventoryQuantity",
            "inventoryCount",
            "availableQuantity",
            "onHand",
            "stock",
        ],
    )
    category_column = _find_matching_column(available_columns, ["category", "productCategory", "type"])
    color_column = _find_matching_column(available_columns, ["color", "colour"])
    size_column = _find_matching_column(available_columns, ["size", "variantSize"])
    style_column = _find_matching_column(available_columns, ["style", "variantStyle"])
    sku_column = _find_matching_column(available_columns, ["sku", "variantSku", "code"])
    in_stock_column = _find_matching_column(
        available_columns,
        ["isInStock", "inStock", "available", "isAvailable", "in_stock"],
    )
    sold_out_column = _find_matching_column(available_columns, ["isSoldOut", "soldOut", "outOfStock", "sold_out"])
    stock_status_column = _find_matching_column(
        available_columns,
        ["stockStatus", "availability", "inventoryStatus", "stock_status"],
    )
    type_column = _find_matching_column(
        available_columns,
        [
            "productType",
            "product_type",
            "templateType",
            "template_type",
            "itemType",
            "item_type",
            "listingType",
            "listing_type",
            "templateKind",
            "template_kind",
            "kind",
        ],
    )
    merch_flag_column = _find_matching_column(
        available_columns,
        [
            "isMerch",
            "is_merch",
            "merch",
            "isMerchandise",
            "is_merchandise",
        ],
    )
    reorder_column = _find_matching_column(available_columns, ["reorderLevel", "reorderPoint", "restockThreshold"])
    unit_column = _find_matching_column(available_columns, ["unitOfMeasure", "uom", "unit"])
    created_at_column = _find_matching_column(available_columns, ["createdAt", "created_at"])
    updated_at_column = _find_matching_column(available_columns, ["updatedAt", "updated_at"])

    if not template_id:
        if not allow_create:
            return
        category = (item.category or "").strip().lower()
        if category != "merch" or item.id is None:
            return
        if not title_column:
            return
        template_id = f"stockworks-merch-{item.id}"
        now = datetime.utcnow()
        insert_columns = [id_column, title_column]
        insert_values = [":id", ":title"]
        insert_params: dict[str, Any] = {"id": template_id, "title": item.name}
        if description_column:
            insert_columns.append(description_column)
            insert_values.append(":description")
            insert_params["description"] = (item.notes or "").strip() or None
        if active_column:
            insert_columns.append(active_column)
            insert_values.append(":is_active")
            insert_params["is_active"] = True
        if type_column:
            insert_columns.append(type_column)
            insert_values.append(":product_type")
            insert_params["product_type"] = "merch"
        if merch_flag_column:
            insert_columns.append(merch_flag_column)
            insert_values.append(":is_merch")
            insert_params["is_merch"] = True
        if created_at_column:
            insert_columns.append(created_at_column)
            insert_values.append(":created_at")
            insert_params["created_at"] = now
        if updated_at_column:
            insert_columns.append(updated_at_column)
            insert_values.append(":updated_at")
            insert_params["updated_at"] = now
        try:
            conn.execute(
                text(
                    f'INSERT INTO public."ProductTemplate" ('
                    f'{", ".join(_quote_identifier(col) for col in insert_columns)}'
                    f') VALUES ({", ".join(insert_values)})'
                ),
                insert_params,
            )
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to create merch item in MakerWorks ProductTemplate: {exc}",
            ) from exc
        item.makerworks_product_template_id = template_id
        session.add(item)

    set_parts: list[str] = []
    params: dict[str, Any] = {"makerworks_id": template_id}

    if quantity_column:
        set_parts.append(f'{_quote_identifier(quantity_column)} = :quantity_on_hand')
        params["quantity_on_hand"] = float(item.quantity_on_hand or 0)
    has_stock = float(item.quantity_on_hand or 0) > 0
    if in_stock_column:
        set_parts.append(f'{_quote_identifier(in_stock_column)} = :is_in_stock')
        params["is_in_stock"] = has_stock
    if sold_out_column:
        set_parts.append(f'{_quote_identifier(sold_out_column)} = :is_sold_out')
        params["is_sold_out"] = not has_stock
    if stock_status_column:
        set_parts.append(f'{_quote_identifier(stock_status_column)} = :stock_status')
        params["stock_status"] = "in_stock" if has_stock else "sold_out"
    if type_column:
        set_parts.append(f'{_quote_identifier(type_column)} = :product_type')
        params["product_type"] = "merch"
    if merch_flag_column:
        set_parts.append(f'{_quote_identifier(merch_flag_column)} = :is_merch')
        params["is_merch"] = True
    if reorder_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(reorder_column)} = :reorder_level')
        params["reorder_level"] = float(item.reorder_level or 0)
    if unit_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(unit_column)} = :unit_of_measure')
        params["unit_of_measure"] = (item.unit_of_measure or "piece").strip() or "piece"
    if title_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(title_column)} = :title')
        params["title"] = item.name
    if description_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(description_column)} = :description')
        params["description"] = (item.notes or "").strip() or None
    if category_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(category_column)} = :category')
        params["category"] = (item.category or "").strip() or None
    if stockworks_link_column:
        # Prevent merch templates from being interpreted as model-linked templates.
        set_parts.append(f'{_quote_identifier(stockworks_link_column)} = NULL')
    if color_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(color_column)} = :merch_color')
        params["merch_color"] = (item.merch_color or "").strip() or None
    if size_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(size_column)} = :merch_size')
        params["merch_size"] = (item.merch_size or "").strip() or None
    if style_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(style_column)} = :merch_style')
        params["merch_style"] = (item.merch_style or "").strip() or None
    if sku_column and include_catalog_fields:
        set_parts.append(f'{_quote_identifier(sku_column)} = :merch_sku')
        params["merch_sku"] = (item.merch_sku or "").strip() or None
    if updated_at_column:
        set_parts.append(f'{_quote_identifier(updated_at_column)} = :updated_at')
        params["updated_at"] = datetime.utcnow()

    if not set_parts:
        return

    query = text(
        f'UPDATE public."ProductTemplate" '
        f'SET {", ".join(set_parts)} '
        f'WHERE {_quote_identifier(id_column)} = :makerworks_id'
    )
    try:
        result = conn.execute(query, params)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to sync merch item to MakerWorks ProductTemplate: {exc}",
        ) from exc

    if (result.rowcount or 0) < 1:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'MakerWorks ProductTemplate "{template_id}" was not found for merch sync writeback.',
        )


def _sync_merch_variant_family_to_makerworks(
    session: Session,
    item: HardwareItem,
    *,
    include_catalog_fields: bool,
) -> None:
    template_id = (item.makerworks_product_template_id or "").strip()
    if not template_id:
        _sync_hardware_item_to_makerworks_product_template(
            session,
            item,
            include_catalog_fields=include_catalog_fields,
            allow_create=True,
        )
        template_id = (item.makerworks_product_template_id or "").strip()
        if not template_id:
            return

    category = (item.category or "").strip().lower()
    if category != "merch":
        _sync_hardware_item_to_makerworks_product_template(session, item, include_catalog_fields=include_catalog_fields)
        return

    name_key = (item.name or "").strip().lower()
    color_key = (item.merch_color or "").strip().lower()
    style_key = (item.merch_style or "").strip().lower()
    if not name_key:
        _sync_hardware_item_to_makerworks_product_template(session, item, include_catalog_fields=include_catalog_fields)
        return

    siblings = session.exec(
        select(HardwareItem).where(
            HardwareItem.makerworks_product_template_id.is_not(None),
            func.lower(HardwareItem.name) == name_key,
            func.lower(func.coalesce(HardwareItem.merch_color, "")) == color_key,
            func.lower(func.coalesce(HardwareItem.merch_style, "")) == style_key,
        )
    ).all()
    if not siblings:
        siblings = [item]

    for sibling in siblings:
        _sync_hardware_item_to_makerworks_product_template(
            session,
            sibling,
            include_catalog_fields=include_catalog_fields,
            allow_create=False,
        )


def _sync_makerworks_merch_to_hardware(session: Session) -> dict[str, Any]:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MakerWorks merch sync requires a shared PostgreSQL database connection.",
        )

    conn = session.connection()
    merch_table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'MerchItem'
            """
        )
    ).first()
    if merch_table_exists:
        return _sync_makerworks_merch_item_to_hardware(session)

    table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
            """
        )
    ).first()
    if not table_exists:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks table public."ProductTemplate" was not found.',
        )

    available_columns = _fetch_table_columns(conn, "public", "ProductTemplate")
    id_column = _find_matching_column(available_columns, ["id"])
    title_column = _find_matching_column(available_columns, ["title", "name"])
    description_column = _find_matching_column(available_columns, ["description", "details"])
    active_column = _find_matching_column(available_columns, ["isActive", "active", "enabled"])
    stockworks_link_column = _find_matching_column(
        available_columns, ["stockworksInventoryItemId", "stockworks_inventory_item_id"]
    )
    quantity_column = _find_matching_column(
        available_columns,
        [
            "quantityOnHand",
            "stockOnHand",
            "inventoryQuantity",
            "inventoryCount",
            "availableQuantity",
            "onHand",
            "stock",
        ],
    )
    category_column = _find_matching_column(available_columns, ["category", "productCategory", "type"])
    type_column = _find_matching_column(
        available_columns,
        [
            "productType",
            "product_type",
            "templateType",
            "template_type",
            "itemType",
            "item_type",
            "listingType",
            "listing_type",
            "templateKind",
            "template_kind",
            "kind",
        ],
    )
    merch_flag_column = _find_matching_column(
        available_columns,
        [
            "isMerch",
            "is_merch",
            "merch",
            "isMerchandise",
            "is_merchandise",
        ],
    )
    color_column = _find_matching_column(available_columns, ["color", "colour"])
    size_column = _find_matching_column(available_columns, ["size", "variantSize"])
    style_column = _find_matching_column(available_columns, ["style", "variantStyle"])
    sku_column = _find_matching_column(available_columns, ["sku", "variantSku", "code"])
    reorder_column = _find_matching_column(available_columns, ["reorderLevel", "reorderPoint", "restockThreshold"])
    unit_column = _find_matching_column(available_columns, ["unitOfMeasure", "uom", "unit"])

    if not id_column or not title_column:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks ProductTemplate is missing required merch columns ("id" and/or "title").',
        )

    select_parts = [
        f'{_quote_identifier(id_column)} AS "makerworks_id"',
        f'{_quote_identifier(title_column)} AS "title"',
    ]
    if description_column:
        select_parts.append(f'{_quote_identifier(description_column)} AS "description"')
    else:
        select_parts.append('NULL AS "description"')
    if active_column:
        select_parts.append(f'{_quote_identifier(active_column)} AS "is_active"')
    else:
        select_parts.append('TRUE AS "is_active"')
    if stockworks_link_column:
        select_parts.append(f'{_quote_identifier(stockworks_link_column)} AS "stockworks_inventory_item_id"')
    else:
        select_parts.append('NULL AS "stockworks_inventory_item_id"')
    if quantity_column:
        select_parts.append(f'{_quote_identifier(quantity_column)} AS "quantity_on_hand"')
    else:
        select_parts.append('NULL AS "quantity_on_hand"')
    if category_column:
        select_parts.append(f'{_quote_identifier(category_column)} AS "category"')
    else:
        select_parts.append('NULL AS "category"')
    if type_column:
        select_parts.append(f'{_quote_identifier(type_column)} AS "product_type"')
    else:
        select_parts.append('NULL AS "product_type"')
    if merch_flag_column:
        select_parts.append(f'{_quote_identifier(merch_flag_column)} AS "is_merch"')
    else:
        select_parts.append('NULL AS "is_merch"')
    if color_column:
        select_parts.append(f'{_quote_identifier(color_column)} AS "merch_color"')
    else:
        select_parts.append('NULL AS "merch_color"')
    if size_column:
        select_parts.append(f'{_quote_identifier(size_column)} AS "merch_size"')
    else:
        select_parts.append('NULL AS "merch_size"')
    if style_column:
        select_parts.append(f'{_quote_identifier(style_column)} AS "merch_style"')
    else:
        select_parts.append('NULL AS "merch_style"')
    if sku_column:
        select_parts.append(f'{_quote_identifier(sku_column)} AS "merch_sku"')
    else:
        select_parts.append('NULL AS "merch_sku"')
    if reorder_column:
        select_parts.append(f'{_quote_identifier(reorder_column)} AS "reorder_level"')
    else:
        select_parts.append('NULL AS "reorder_level"')
    if unit_column:
        select_parts.append(f'{_quote_identifier(unit_column)} AS "unit_of_measure"')
    else:
        select_parts.append('NULL AS "unit_of_measure"')

    where_fragments = []
    if active_column:
        quoted_active = _quote_identifier(active_column)
        where_fragments.append(f"COALESCE({quoted_active}, TRUE) = TRUE")
    where_sql = f"WHERE {' AND '.join(where_fragments)}" if where_fragments else ""
    select_sql = ", ".join(select_parts)
    query = text(
        f'SELECT {select_sql} FROM public."ProductTemplate" {where_sql} ORDER BY {_quote_identifier(title_column)} ASC'
    )

    rows = conn.execute(query).mappings().all()
    linked_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_not(None))
    ).all()
    unlinked_merch_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_(None))
    ).all()
    linked_by_template_id = {
        str(item.makerworks_product_template_id): item
        for item in linked_items
        if item.makerworks_product_template_id
    }
    unlinked_merch_by_name = {
        (item.name or "").strip().lower(): item
        for item in unlinked_merch_items
        if (item.category or "").strip().lower() == "merch" and (item.name or "").strip()
    }

    created = 0
    updated = 0
    skipped = 0
    source_count = len(rows)
    synced_ids: set[str] = set()

    for row in rows:
        makerworks_id = str(row.get("makerworks_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not makerworks_id or not title:
            skipped += 1
            continue
        raw_is_merch = row.get("is_merch")
        is_merch_flag = False
        if raw_is_merch is not None:
            is_merch_flag = str(raw_is_merch).strip().lower() in {"1", "true", "t", "yes", "y", "on"}
        product_type = str(row.get("product_type") or "").strip().lower()
        source_category = str(row.get("category") or "").strip()
        normalized_category = source_category.lower()
        is_merch_type = product_type in {"merch", "merchandise", "apparel", "accessory", "accessories"}
        is_merch_category = normalized_category in {"merch", "merchandise", "apparel", "accessory", "accessories"}
        if not (is_merch_flag or is_merch_type or is_merch_category):
            skipped += 1
            continue
        synced_ids.add(makerworks_id)
        item = linked_by_template_id.get(makerworks_id)
        if item is None:
            item = unlinked_merch_by_name.get(title.lower())
        quantity_on_hand = _coerce_non_negative_number(row.get("quantity_on_hand"))
        reorder_level = _coerce_non_negative_number(row.get("reorder_level"))
        unit_of_measure = str(row.get("unit_of_measure") or "").strip() or "piece"
        description = str(row.get("description") or "").strip() or None
        category = source_category or "merch"
        merch_color = str(row.get("merch_color") or "").strip() or None
        merch_size = str(row.get("merch_size") or "").strip() or None
        merch_style = str(row.get("merch_style") or "").strip() or None
        merch_sku = str(row.get("merch_sku") or "").strip() or None

        if item:
            item.name = title
            item.category = category
            item.makerworks_product_template_id = makerworks_id
            item.unit_of_measure = unit_of_measure
            item.merch_color = merch_color
            item.merch_size = merch_size
            item.merch_style = merch_style
            item.merch_sku = merch_sku
            if quantity_on_hand is not None:
                item.quantity_on_hand = quantity_on_hand
            if reorder_level is not None:
                item.reorder_level = reorder_level
            if description and not item.notes:
                item.notes = description
            session.add(item)
            updated += 1
            continue

        created_item = HardwareItem(
            name=title,
            category=category,
            unit_of_measure=unit_of_measure,
            merch_color=merch_color,
            merch_size=merch_size,
            merch_style=merch_style,
            merch_sku=merch_sku,
            quantity_on_hand=quantity_on_hand if quantity_on_hand is not None else 0,
            reorder_level=reorder_level if reorder_level is not None else 0,
            notes=description,
            makerworks_product_template_id=makerworks_id,
        )
        session.add(created_item)
        created += 1

    session.commit()

    return {
        "source_count": source_count,
        "synced_count": len(synced_ids),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "quantity_source_column": quantity_column,
        "reorder_source_column": reorder_column,
        "unit_source_column": unit_column,
    }


def _sync_hardware_item_to_makerworks_merch_item(
    session: Session,
    item: HardwareItem,
    *,
    include_catalog_fields: bool = True,
    allow_create: bool = False,
) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    conn = session.connection()
    table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'MerchItem'
            """
        )
    ).first()
    if not table_exists:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks table public."MerchItem" was not found for merch sync writeback.',
        )

    merch_id = (item.makerworks_product_template_id or "").strip()
    now = datetime.utcnow()
    has_stock = float(item.quantity_on_hand or 0) > 0
    availability = "in_stock" if has_stock else "sold_out"

    if not merch_id:
        if not allow_create or item.id is None:
            return
        merch_id = f"stockworks-merch-{item.id}"
        insert_params: dict[str, Any] = {
            "id": merch_id,
            "title": item.name,
            "description": (item.notes or "").strip() or None,
            "category": _makerworks_merch_category(item),
            "price_usd": float(item.unit_cost or 0),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "availability": availability,
        }
        try:
            conn.execute(
                text(
                    """
                    INSERT INTO public."MerchItem" (
                        "id",
                        "title",
                        "description",
                        "category",
                        "priceUsd",
                        "isActive",
                        "createdAt",
                        "updatedAt",
                        "availability"
                    ) VALUES (
                        :id,
                        :title,
                        :description,
                        :category,
                        :price_usd,
                        :is_active,
                        :created_at,
                        :updated_at,
                        :availability
                    )
                    """
                ),
                insert_params,
            )
        except SQLAlchemyError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f'Failed to create merch item in MakerWorks "MerchItem": {exc}',
            ) from exc
        item.makerworks_product_template_id = merch_id
        session.add(item)

    set_parts = ['"availability" = :availability', '"updatedAt" = :updated_at']
    params: dict[str, Any] = {
        "id": merch_id,
        "availability": availability,
        "updated_at": now,
    }
    if include_catalog_fields:
        set_parts.extend(
            [
                '"title" = :title',
                '"description" = :description',
                '"category" = :category',
                '"priceUsd" = :price_usd',
                '"isActive" = :is_active',
            ]
        )
        params.update(
            {
                "title": item.name,
                "description": (item.notes or "").strip() or None,
                "category": _makerworks_merch_category(item),
                "price_usd": float(item.unit_cost or 0),
                "is_active": True,
            }
        )

    try:
        result = conn.execute(
            text(
                f'UPDATE public."MerchItem" '
                f'SET {", ".join(set_parts)} '
                f'WHERE "id" = :id'
            ),
            params,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Failed to sync merch item to MakerWorks "MerchItem": {exc}',
        ) from exc
    if (result.rowcount or 0) < 1:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'MakerWorks MerchItem "{merch_id}" was not found for merch sync writeback.',
        )


def _sync_makerworks_merch_item_to_hardware(session: Session) -> dict[str, Any]:
    conn = session.connection()
    rows = conn.execute(
        text(
            """
            SELECT
                "id" AS makerworks_id,
                "title" AS title,
                "description" AS description,
                "category" AS category,
                "priceUsd" AS price_usd,
                COALESCE("isActive", TRUE) AS is_active,
                "availability" AS availability
            FROM public."MerchItem"
            WHERE COALESCE("isActive", TRUE) = TRUE
            ORDER BY "title" ASC
            """
        )
    ).mappings().all()

    linked_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_not(None))
    ).all()
    unlinked_merch_items = session.exec(
        select(HardwareItem).where(HardwareItem.makerworks_product_template_id.is_(None))
    ).all()
    linked_by_template_id = {
        str(item.makerworks_product_template_id): item
        for item in linked_items
        if item.makerworks_product_template_id
    }
    unlinked_merch_by_name = {
        (item.name or "").strip().lower(): item
        for item in unlinked_merch_items
        if (item.category or "").strip().lower() == "merch" and (item.name or "").strip()
    }

    created = 0
    updated = 0
    skipped = 0
    synced_ids: set[str] = set()

    for row in rows:
        makerworks_id = str(row.get("makerworks_id") or "").strip()
        title = str(row.get("title") or "").strip()
        if not makerworks_id or not title:
            skipped += 1
            continue
        synced_ids.add(makerworks_id)
        item = linked_by_template_id.get(makerworks_id)
        if item is None:
            item = unlinked_merch_by_name.get(title.lower())

        description = str(row.get("description") or "").strip() or None
        price_usd = row.get("price_usd")
        makerworks_category = str(row.get("category") or "").strip().lower()
        notes = description
        if makerworks_category:
            notes = f"[MakerWorks category: {makerworks_category}] {description or ''}".strip()

        if item:
            item.name = title
            item.category = "merch"
            item.makerworks_product_template_id = makerworks_id
            if price_usd is not None:
                item.unit_cost = max(float(price_usd), 0.0)
            if notes:
                item.notes = notes
            session.add(item)
            updated += 1
            continue

        created_item = HardwareItem(
            name=title,
            category="merch",
            unit_of_measure="piece",
            unit_cost=max(float(price_usd or 0), 0.0),
            quantity_on_hand=0,
            reorder_level=0,
            notes=notes,
            makerworks_product_template_id=makerworks_id,
        )
        session.add(created_item)
        created += 1

    session.commit()
    return {
        "source_count": len(rows),
        "synced_count": len(synced_ids),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "source_table": "MerchItem",
    }


def _delete_makerworks_merch_item(session: Session, template_id: str) -> None:
    bind = session.get_bind()
    if bind is None or bind.dialect.name != "postgresql":
        return

    conn = session.connection()
    table_exists = conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'MerchItem'
            """
        )
    ).first()
    if not table_exists:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='MakerWorks table public."MerchItem" was not found for merch delete writeback.',
        )

    try:
        result = conn.execute(
            text(
                """
                DELETE FROM public."MerchItem"
                WHERE "id" = :makerworks_id
                """
            ),
            {"makerworks_id": template_id},
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'Failed to delete merch item from MakerWorks "MerchItem": {exc}',
        ) from exc

    if (result.rowcount or 0) < 1:
        # Backward compatibility: clean up legacy rows created in ProductTemplate.
        legacy_table_exists = conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'ProductTemplate'
                """
            )
        ).first()
        if legacy_table_exists:
            legacy_result = conn.execute(
                text(
                    """
                    DELETE FROM public."ProductTemplate"
                    WHERE "id" = :makerworks_id
                    """
                ),
                {"makerworks_id": template_id},
            )
            if (legacy_result.rowcount or 0) > 0:
                return
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f'MakerWorks merch id "{template_id}" was not found in "MerchItem" or legacy "ProductTemplate".',
        )


def _makerworks_merch_category(item: HardwareItem) -> str:
    raw = (item.merch_style or "").strip().lower() or (item.category or "").strip().lower()
    if raw in {"apparel", "accessories"}:
        return raw
    hint = f"{(item.name or '').strip().lower()} {raw}"
    apparel_terms = ("shirt", "tee", "hoodie", "sweat", "jogger", "tank", "jersey", "onesie")
    if any(term in hint for term in apparel_terms):
        return "apparel"
    return "accessories"


def _set_makerworks_product_template_classification(
    connection: Any,
    *,
    template_id: str | None,
    type_column: str | None,
    merch_flag_column: str | None,
    is_merch: bool,
) -> None:
    if not template_id or (not type_column and not merch_flag_column):
        return

    set_parts: list[str] = []
    params: dict[str, Any] = {"template_id": template_id}
    if type_column:
        set_parts.append(f'{_quote_identifier(type_column)} = :product_type')
        params["product_type"] = "merch" if is_merch else "model"
    if merch_flag_column:
        set_parts.append(f'{_quote_identifier(merch_flag_column)} = :is_merch')
        params["is_merch"] = bool(is_merch)
    if not set_parts:
        return

    connection.execute(
        text(
            f'UPDATE public."ProductTemplate" '
            f'SET {", ".join(set_parts)} '
            f'WHERE "id" = :template_id'
        ),
        params,
    )


def _fetch_table_columns(connection: Any, schema: str, table: str) -> set[str]:
    result = connection.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    )
    return {str(row[0]) for row in result}


def _find_matching_column(available: set[str], candidates: list[str]) -> Optional[str]:
    lowered = {column.lower(): column for column in available}
    for candidate in candidates:
        found = lowered.get(candidate.lower())
        if found:
            return found
    return None


def _quote_identifier(identifier: str) -> str:
    if not identifier or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Unsupported SQL identifier encountered: {identifier!r}",
        )
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _coerce_non_negative_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return 0.0
    return number
