"""HTML page shells (formerly the Flask app). Pages hold no data; the JS fetches it from /api."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

APP_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = APP_DIR / "static"

# Flask-style endpoint names used by url_for() in the templates.
ENDPOINTS = {
    "auth.login": "/login",
    "auth.register": "/register",
    "employee.my_tickets": "/tickets",
    "employee.new_ticket": "/tickets/new",
    "it_team.all_tickets": "/it/tickets",
    "admin.users": "/admin",
}


def url_for(endpoint: str, **values) -> str:
    if endpoint == "static":
        return f"/static/{values['filename']}"
    return ENDPOINTS[endpoint]


templates = Environment(loader=FileSystemLoader(APP_DIR / "templates"), autoescape=select_autoescape())
# Pages and API share one origin, so the JS calls /api/... relative to the page.
templates.globals.update(url_for=url_for, api_base_url="")

# Pages contain no inline scripts/styles, so a strict CSP is possible.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}

router = APIRouter(include_in_schema=False, default_response_class=HTMLResponse)


def render(name: str, **context) -> HTMLResponse:
    return HTMLResponse(templates.get_template(name).render(**context), headers=SECURITY_HEADERS)


@router.get("/")
def index():
    return RedirectResponse("/login", status_code=302)


@router.get("/login")
def login():
    return render("login.html")


@router.get("/register")
def register():
    return render("register.html")


@router.get("/tickets")
def my_tickets():
    return render("tickets.html")


@router.get("/tickets/new")
def new_ticket():
    return render("new_ticket.html")


@router.get("/tickets/{ticket_id:int}")
def ticket_detail(ticket_id: int):
    return render("ticket_detail.html", ticket_id=ticket_id)


@router.get("/it/tickets")
def all_tickets():
    return render("it_tickets.html")


@router.get("/admin")
def admin_users():
    return render("admin.html")
