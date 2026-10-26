"""Read cookie metadata from an explicitly supplied SQLite snapshot.

Cookie values, encrypted values and password stores are never selected.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import sqlite3
import time

MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_ROWS = 5000
MAX_QUERY_SECONDS = 2.0
UTC = timezone.utc


class AnalysisError(ValueError):
    """A user-facing, deliberately non-sensitive analysis error."""


def flag(value):
    if value in (1, "1"):
        return True
    if value in (0, "0"):
        return False
    return None


def expiry_date(value, browser):
    if value is None:
        return None
    try:
        number = int(value)
        if number <= 0:
            return None
        if browser == "chromium":
            return datetime(1601, 1, 1, tzinfo=UTC) + timedelta(microseconds=number)
        return datetime.fromtimestamp(number, tz=UTC)
    except (ValueError, OverflowError, OSError, TypeError):
        return None


def same_site(value, browser):
    # Chromium CookieSameSite: -1 unspecified, 0 none, 1 lax, 2 strict.
    # Firefox nsICookie: 0 none, 1 lax, 2 strict. Other values stay unknown.
    try:
        number = int(value)
    except (ValueError, TypeError):
        return "Desconocido"
    mapping = {0: "None", 1: "Lax", 2: "Strict"}
    if browser == "chromium" and number == -1:
        return "No especificado"
    return mapping.get(number, "Desconocido")


def _text(value, limit):
    if not isinstance(value, str):
        return "(no disponible)"
    return "".join(c for c in value if c.isprintable())[:limit]


def normalize(row, browser, now):
    chromium = browser == "chromium"
    domain = _text(row.get("host_key" if chromium else "host"), 253)
    expires = expiry_date(row.get("expires_utc" if chromium else "expiry"), browser)
    session = None
    # Never infer Firefox session status merely from a zero expiry value.
    if chromium:
        has_expiry = flag(row.get("has_expires"))
        persistent = flag(row.get("is_persistent"))
        if has_expiry is not None:
            session = not has_expiry
        elif persistent is not None:
            session = not persistent
        elif row.get("expires_utc") in (0, "0"):
            session = True
        elif expires is not None:
            session = False
    else:
        session = flag(row.get("isSession"))
    status = ("Sesión" if session is True else
              "Vencida" if expires is not None and expires <= now else
              "Vigente" if expires is not None else "Desconocida")
    return {
        "browser": "Chrome / Chromium" if chromium else "Firefox",
        "domain": domain,
        "name": _text(row.get("name"), 200),
        "path": _text(row.get("path"), 400),
        "secure": flag(row.get("is_secure" if chromium else "isSecure")),
        "httpOnly": flag(row.get("is_httponly" if chromium else "isHttpOnly")),
        "sameSite": same_site(row.get("samesite" if chromium else "sameSite"), browser),
        "session": session,
        "status": status,
        "expires": expires.isoformat() if expires is not None and session is not True else None,
    }


def analyze_snapshot(path, *, limit=MAX_ROWS, now=None):
    """Inspect a standalone SQLite copy, without modifying it or opening a live profile."""
    path = Path(path).resolve()
    now = now or datetime.now(UTC)
    if not 1 <= limit <= MAX_ROWS:
        raise ValueError("Invalid row limit")
    if not path.is_file() or not 16 <= path.stat().st_size <= MAX_FILE_BYTES:
        raise AnalysisError("El archivo debe ser una copia SQLite de hasta 8 MiB.")
    with path.open("rb") as handle:
        if handle.read(16) != b"SQLite format 3\x00":
            raise AnalysisError("El archivo no tiene formato SQLite válido.")
    if any(Path(str(path) + suffix).exists() for suffix in ("-wal", "-journal")):
        raise AnalysisError("Usa una copia SQLite consolidada, sin archivos WAL o journal pendientes.")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    conn = None
    deadline = time.monotonic() + MAX_QUERY_SECONDS
    try:
        conn = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=1)
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 500)
        conn.execute("PRAGMA query_only=ON")
        conn.execute("PRAGMA trusted_schema=OFF")
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, MAX_FILE_BYTES)
        conn.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 20000)
        conn.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 128)
        tables = {row[0]: row[1] for row in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('cookies', 'moz_cookies')"
        )}
        if "cookies" in tables and "moz_cookies" in tables:
            raise AnalysisError("La base contiene dos esquemas de navegador; usa una copia por navegador.")
        if "cookies" in tables:
            table, browser = "cookies", "chromium"
            required = {"host_key", "name"}
            allowed = ["host_key", "name", "path", "expires_utc", "is_secure", "is_httponly", "has_expires", "is_persistent", "samesite"]
        elif "moz_cookies" in tables:
            table, browser = "moz_cookies", "firefox"
            required = {"host", "name"}
            allowed = ["host", "name", "path", "expiry", "isSecure", "isHttpOnly", "isSession", "sameSite"]
        else:
            raise AnalysisError("No se encontró una tabla cookies o moz_cookies compatible.")
        definition = tables[table] or ""
        if "VIRTUAL" in definition.upper():
            raise AnalysisError("No se admiten tablas virtuales.")
        schema = list(conn.execute(f'PRAGMA table_xinfo("{table}")'))
        columns = {row[1] for row in schema if row[6] == 0}
        if any(row[6] != 0 for row in schema):
            raise AnalysisError("No se admiten columnas ocultas o generadas.")
        if not required <= columns:
            raise AnalysisError("El esquema no contiene las columnas de dominio y nombre necesarias.")
        selected = [column for column in allowed if column in columns]
        fields = ", ".join(f'"{name}"' for name in selected)
        # All identifiers come from fixed allowlists; values/encrypted_value are absent.
        cursor = conn.execute(f'SELECT {fields} FROM "{table}" LIMIT ?', (limit + 1,))
        data = cursor.fetchall()
        warnings = []
        if len(data) > limit:
            warnings.append(f"Muestra limitada a {limit:,} cookies de esta base. Las métricas describen solo la muestra.")
        if browser == "firefox" and "isSession" not in columns:
            warnings.append("Firefox: la base no indica isSession; no se infiere si una cookie es de sesión.")
        absent = [field for field in allowed if field not in columns]
        if absent:
            warnings.append("El esquema omite metadatos opcionales; se muestran como desconocidos cuando corresponde.")
        rows = [normalize(dict(zip(selected, row)), browser, now) for row in data[:limit]]
        if not rows:
            warnings.append("La tabla de cookies está vacía.")
        return {"cookies": rows, "source": {"browser": "Chrome / Chromium" if browser == "chromium" else "Firefox", "sha256": digest, "rows": len(rows), "truncated": len(data) > limit}, "warnings": warnings}
    except sqlite3.Error as exc:
        raise AnalysisError("No se pudo leer la copia SQLite: archivo dañado, esquema incompatible o límite de análisis alcanzado.") from exc
    finally:
        if conn is not None:
            conn.close()


def summary(cookies):
    return {
        "total": len(cookies),
        "domains": len({r["domain"].lower().lstrip(".") for r in cookies}),
        "secure": sum(r["secure"] is True for r in cookies),
        "httpOnly": sum(r["httpOnly"] is True for r in cookies),
        "expired": sum(r["status"] == "Vencida" for r in cookies),
        "session": sum(r["session"] is True for r in cookies),
        "topDomains": [{"domain": name, "count": count} for name, count in Counter(r["domain"].lower().lstrip(".") for r in cookies).most_common(6)],
    }


def demo_dataset(now=None):
    now = now or datetime.now(UTC)
    domains = [".tienda.example", "cuenta.example", ".noticias.example", "video.example", "metricas.example", "campus.example"]
    names = ["session_demo", "preferencias", "idioma", "tema", "carrito_demo", "consentimiento"]
    cookies = []
    for i in range(36):
        browser = "Chrome / Chromium" if i % 3 else "Firefox"
        session = True if i % 5 == 0 else False if browser != "Firefox" else None
        expires = now + timedelta(days=(-2 if i % 7 == 0 else 30 + i))
        weight = [0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 4, 5]
        cookies.append({"browser": browser, "domain": domains[weight[i % len(weight)]], "name": names[i % len(names)], "path": "/", "secure": i % 4 != 0, "httpOnly": i % 3 == 0, "sameSite": ["Lax", "Strict", "None", "No especificado", "Desconocido"][i % 5], "session": session, "status": "Sesión" if session else "Vencida" if expires < now else "Vigente", "expires": None if session else expires.isoformat()})
    return {"mode": "demo", "analyzedAt": now.isoformat(), "cookies": cookies, "sources": [{"browser": "Datos ficticios", "rows": len(cookies), "truncated": False, "sha256": None}], "warnings": ["Datos sintéticos: no se ha accedido a ningún navegador ni archivo personal."], "summary": summary(cookies)}
