"""Local-only cookie metadata dashboard. Run with: python app.py."""
from datetime import datetime, timezone
import hmac
from pathlib import Path
import secrets
import tempfile
from urllib.parse import urlsplit

from flask import Flask, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException

from analyzer import AnalysisError, MAX_FILE_BYTES, analyze_snapshot, demo_dataset, summary


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=secrets.token_hex(32),
        MAX_CONTENT_LENGTH=17 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=100_000,
        MAX_FORM_PARTS=6,
        TRUSTED_HOSTS=["localhost", "127.0.0.1", "[::1]"],
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Strict",
    )
    if test_config:
        app.config.update(test_config)

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    @app.after_request
    def protect(response):
        response.headers.update({
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        })
        return response

    @app.get("/")
    def index():
        return render_template("index.html", csrf=csrf_token())

    @app.get("/api/demo")
    def demo():
        return jsonify(demo_dataset())

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/analyze")
    def analyze():
        received = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf", "")
        if not expected or not hmac.compare_digest(received, expected):
            return jsonify(error="La sesión de análisis venció. Recarga la página e inténtalo de nuevo."), 403
        origin = request.headers.get("Origin")
        if origin and urlsplit(origin).netloc != request.host:
            return jsonify(error="El origen de la solicitud no está permitido."), 403
        files = request.files.getlist("files")
        if not 1 <= len(files) <= 2:
            return jsonify(error="Selecciona una o dos copias SQLite, máximo 8 MiB por archivo."), 400
        now = datetime.now(timezone.utc)
        cookies, sources, warnings = [], [], []
        # The client filename is never used as a path, retained or returned.
        with tempfile.TemporaryDirectory(prefix="cookie-metadata-") as work:
            for index, upload in enumerate(files):
                path = Path(work) / f"snapshot-{index}.sqlite"
                with path.open("wb") as target:
                    size = 0
                    while chunk := upload.stream.read(65536):
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise AnalysisError("Cada archivo debe pesar como máximo 8 MiB.")
                        target.write(chunk)
                result = analyze_snapshot(path, now=now)
                if any(s["sha256"] == result["source"]["sha256"] for s in sources):
                    raise AnalysisError("Seleccionaste la misma base dos veces. Usa una copia por navegador.")
                cookies.extend(result["cookies"])
                sources.append(result["source"])
                warnings.extend(result["warnings"])
        return jsonify(mode="snapshot", analyzedAt=now.isoformat(), cookies=cookies, sources=sources, warnings=list(dict.fromkeys(warnings)), summary=summary(cookies))

    @app.errorhandler(AnalysisError)
    def bad_snapshot(error):
        return jsonify(error=str(error)), 400

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {413: "La carga supera el límite permitido de 17 MiB.", 400: "Solicitud no válida o nombre de servidor no permitido.", 404: "Recurso no encontrado.", 405: "Método no permitido."}
        return jsonify(error=messages.get(error.code, "No se pudo completar la solicitud.")), error.code

    return app


app = create_app()

if __name__ == "__main__":
    # Never scan local browser profiles, enable debug, or bind all interfaces.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
