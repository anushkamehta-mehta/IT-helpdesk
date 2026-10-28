from flask import Flask

from app.config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("FLASK_SECRET_KEY is not set. Copy .env.example to .env and fill it in.")

    from app.blueprints import admin, auth, employee, it_team, tickets

    for module in (admin, auth, employee, it_team, tickets):
        app.register_blueprint(module.bp)

    api_base = app.config["API_BASE_URL"]

    @app.context_processor
    def inject_api_base():
        return {"api_base_url": api_base}

    @app.after_request
    def security_headers(response):
        # Pages contain no inline scripts/styles, so a strict CSP is possible.
        response.headers["Content-Security-Policy"] = (
            f"default-src 'self'; connect-src 'self' {api_base}; img-src 'self' data:; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response

    return app
