# StockWorks Security Audit

Date: 2026-02-23  
Scope: Full repository review focused on authentication/session controls, API surface, dependency risk, and data-access safeguards.

## Methodology

- Manual code review of API, templates, DB helpers, deployment config, and dependency pins.
- Static application scan with Bandit.
- Dependency vulnerability scan with pip-audit.

Commands used:

- `bandit -q -r app -f txt`
- `pip-audit -r requirements.txt`

## Findings

### 1) Insecure default credentials and session secret can allow account compromise/session forgery (High)

**Evidence**
- App defaults to `admin/changeme` and `please-change-me` when env vars are unset.
- Docker Compose mirrors the same insecure defaults.

**Affected locations**
- `app/api.py` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY` defaults)
- `docker-compose.yml` (`ADMIN_PASSWORD`, `SECRET_KEY` default env values)

**Impact**
- If deployment leaves defaults unchanged, attackers can authenticate trivially.
- Predictable session secret allows tampering/forgery of session cookies.

**Recommended fixes**
1. Fail closed in production: refuse startup if password/secret are default placeholders.
2. Add a startup validator enforcing strong `SECRET_KEY` entropy/length.
3. Remove default password and secret from compose; require explicit values via `.env`/secrets manager.
4. Add first-run credential bootstrap flow or one-time setup token.

---

### 2) Path traversal risk in `/public/{asset_path:path}` file serving endpoint (High)

**Evidence**
- `target = PUBLIC_DIR / asset_path` is used directly and only checked with `target.is_file()`.
- No canonicalization (`resolve`) or boundary check to ensure the resolved file remains under `PUBLIC_DIR`.

**Affected location**
- `app/api.py` (`public_assets` endpoint)

**Impact**
- Crafted traversal paths (e.g. `../`) may expose unintended files from the host/container filesystem if route normalization permits them.

**Recommended fixes**
1. Resolve both paths and enforce prefix containment:
   - `resolved = (PUBLIC_DIR / asset_path).resolve()`
   - reject if `PUBLIC_DIR.resolve()` is not a parent of `resolved`.
2. Return 404/403 for out-of-root access attempts.
3. Consider mounting `StaticFiles(directory=PUBLIC_DIR)` instead of custom file serving for safer defaults.

---

### 3) Missing CSRF protections on cookie-authenticated actions (High)

**Evidence**
- Session cookie auth is used.
- Login/logout and API write endpoints rely on cookie-based auth but no CSRF token/origin verification is implemented.
- Forms do not include anti-CSRF tokens.

**Affected locations**
- `app/api.py` (`SessionMiddleware`, `/login`, `/logout`, and all state-changing endpoints)
- `app/templates/login.html` and `app/templates/index.html` forms

**Impact**
- A malicious site can potentially trigger authenticated state-changing requests from victim browsers (especially with `SameSite=Lax` and top-level navigations/forms).

**Recommended fixes**
1. Implement CSRF token issuance/verification for all cookie-authenticated modifying routes.
2. Enforce `Origin`/`Referer` checks on state-changing endpoints.
3. For API calls, prefer bearer token auth in `Authorization` header over ambient cookies.
4. Consider `SameSite=Strict` where UX permits.

---

### 4) Session hardening and brute-force controls are incomplete (Medium)

**Evidence**
- Session middleware omits `https_only=True` and explicit max-age/idle timeout settings.
- No login throttling/lockout observed on `/login`.

**Affected location**
- `app/api.py`

**Impact**
- Cookies may be exposed over non-TLS deployments.
- Unlimited login attempts increase credential-stuffing/brute-force risk.

**Recommended fixes**
1. Set session cookie security attributes (`https_only=True`, hardened max age).
2. Force TLS (reverse proxy + HSTS) and document secure deployment profile.
3. Add IP/user-based rate limiting for `/login` (e.g., slowapi, reverse-proxy limits).
4. Add audit logging and alerting for repeated failed logins.

---

### 5) Known vulnerable dependency versions in `requirements.txt` (Medium)

**Evidence (pip-audit)**
- `Jinja2==3.1.4` (multiple CVEs; fixes in 3.1.5/3.1.6)
- `python-multipart==0.0.9` (CVEs; fixes in 0.0.18/0.0.22)
- `Pillow==10.4.0` (CVE; fix in 12.1.1)
- `starlette==0.37.2` (CVEs; fixes in 0.40.0/0.47.2)

**Affected location**
- `requirements.txt`

**Impact**
- Exposure depends on reachable code paths, but vulnerable libraries increase exploitability and incident likelihood.

**Recommended fixes**
1. Upgrade vulnerable dependencies to patched versions.
2. Re-run integration tests against upgraded FastAPI/Starlette stack.
3. Add dependency scanning in CI (pip-audit/Safety/Dependabot/Renovate).

---

### 6) Dynamic SQL construction needs strict whitelist guarantees (Medium)

**Evidence**
- Bandit flagged string-built SQL in `app/api.py` and `app/orderworks.py`.
- Some query parts are parameterized correctly, but identifier fragments are dynamically composed.

**Affected locations**
- `app/api.py` (MakerWorks/ProductTemplate and Merch sync SQL statements)
- `app/orderworks.py` (`information_schema` metadata query)

**Impact**
- If any dynamically injected identifier originates from untrusted input without strict whitelisting, SQL injection risk exists.

**Recommended fixes**
1. Ensure all dynamic identifiers come only from fixed allowlists (never request payloads).
2. Centralize identifier quoting/validation and reject unexpected names.
3. Prefer SQLAlchemy expression API where possible to avoid raw SQL assembly.
4. Add unit tests that assert unsafe identifier payloads are rejected.

## Prioritized Remediation Plan

1. **Immediate (0–2 days)**
   - Remove insecure defaults for credentials/secret and enforce strong env requirements.
   - Patch `/public/{asset_path:path}` traversal guard.
   - Add CSRF protection for cookie-authenticated writes.

2. **Near-term (this sprint)**
   - Upgrade vulnerable dependencies and verify compatibility.
   - Add login rate limiting and security-focused logging.

3. **Hardening backlog**
   - Refactor dynamic SQL to structured query builders.
   - Add CI security gates (SAST + dependency scans).

## Quick Wins Checklist

- [ ] Fail startup when `ADMIN_PASSWORD` is default/empty.
- [ ] Fail startup when `SECRET_KEY` equals placeholder or entropy is too low.
- [ ] Enforce `PUBLIC_DIR` path containment before `FileResponse`.
- [ ] Add CSRF middleware/token checks for all modifying endpoints.
- [ ] Set session cookie `https_only=True` and stronger same-site policy.
- [ ] Add `/login` rate limiting and failed-attempt telemetry.
- [ ] Upgrade Jinja2, python-multipart, Pillow, and Starlette-compatible stack.
