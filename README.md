# IT Helpdesk & Ticket Management System (Version 1)

Internal IT helpdesk: employees raise and track tickets, the IT team triages and resolves them.

**Stack:** HTML/CSS/JavaScript, Flask (pages), FastAPI (API), MySQL, SQLAlchemy, Argon2, JWT in an httpOnly cookie.

```
it-helpdesk/
  api/        FastAPI app: routers, services (business rules), models, schemas, tests, scripts
  web/        Flask app: page routes, Jinja templates, static CSS/JS
  database/   schema.sql (tables + starter categories)
  deploy/     Nginx + systemd files and production env template for AWS
  docs/       ARCHITECTURE.md, DEPLOYMENT_AWS.md
```

## Features
**Employee:** register, log in, create ticket (category, description, priority), view own tickets, check status, comment on own tickets.
**IT team:** log in, view all tickets, search (title/description/ticket #), filter (status, priority, category, assignee/unassigned), assign tickets, change status and priority, add resolution notes, close tickets, comment.
Workflow: `Open -> Assigned -> In Progress -> Closed`. Priorities: Low / Medium / High. See `docs/ARCHITECTURE.md` for the rules.

## Local setup (Python 3.10+, MySQL 8, MySQL Workbench)

### 1. Database
In MySQL Workbench connect as an admin (root), open `database/schema.sql` and run it (Lightning icon). Then create the app user (choose your own password):
```sql
CREATE USER 'helpdesk_app'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON it_helpdesk.* TO 'helpdesk_app'@'localhost';
```

### 2. Configuration
```bash
cp .env.example .env          # Windows: copy .env.example .env
```
Edit `.env`: set `DB_PASSWORD`, `JWT_SECRET` and `FLASK_SECRET_KEY`. Generate secrets with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
Use the same host name everywhere (`127.0.0.1` in the URL and in `API_BASE_URL`/`CORS_ORIGINS`), otherwise the login cookie will not be sent.

### 3. Install (virtual environment activated, from the project root)
```bash
pip install -r api/requirements.txt -r web/requirements.txt
```

### 4. Create the first IT team account
```bash
cd api
python -m scripts.create_it_user
```
(Optional, for demos) load sample users and tickets:
```bash
python -m scripts.seed_demo
```
It asks for one password used for all demo accounts: `alice@` and `bob@helpdesk-demo.com` (employees), `ivan@` and `priya@helpdesk-demo.com` (IT).

### 5. Run (two terminals, virtual environment activated in both)
```bash
# Terminal 1: API on port 8000
cd api
uvicorn app.main:app --reload --port 8000

# Terminal 2: Web on port 5000
cd web
flask --app wsgi run --port 5000
```
Open **http://127.0.0.1:5000**. API docs: http://127.0.0.1:8000/docs. Health check: http://127.0.0.1:8000/api/health

## Suggested demo script (10 minutes)
1. Register a new employee, log in, create a High-priority ticket.
2. Add a comment as the employee.
3. In a private window log in as an IT user: search/filter the list, open the ticket, assign it, move it to In Progress, change priority.
4. Try to close without resolution notes (blocked), then add notes and close.
5. Back as the employee: see the status, resolution notes, and that closed tickets are read-only.
6. Show that the employee cannot open another employee's ticket (404) and IT pages redirect away.

## Tests
```bash
cd api
pip install -r requirements-dev.txt
pytest                      # uses in-memory SQLite, no MySQL needed
cd ../web
pip install pytest
pytest
```

## API summary (all under `/api`)
| Method & path | Who | Purpose |
|---|---|---|
| POST `/auth/register` | public | Create employee account |
| POST `/auth/login`, `/auth/logout` | public / any | Start / end session (cookie) |
| GET `/auth/me` | any | Current user |
| GET `/categories` | any | Category list |
| GET `/users/it-team` | IT | Assignable IT members |
| POST `/tickets` | employee | Create ticket |
| GET `/tickets` (`q,status,priority,category_id,assigned_to,unassigned`) | any | Own tickets (employee) / all (IT) |
| GET `/tickets/{id}` | owner / IT | Ticket with comments |
| PATCH `/tickets/{id}` | IT | Assign, status, priority, resolution notes |
| POST `/tickets/{id}/comments` | owner / IT | Add comment |

## Troubleshooting
* **API fails to start with a validation error:** `.env` is missing or `DB_USER`/`DB_PASSWORD`/`JWT_SECRET` are not set.
* **Login works but you are sent back to the login page:** host name mismatch (`localhost` vs `127.0.0.1`), or `COOKIE_SECURE=true` while using plain http.
* **"Cannot reach the server":** the API terminal is not running, or `API_BASE_URL` is wrong.
* **Database error:** check the `DB_*` values and that `database/schema.sql` was run.

## Deployment
See `docs/DEPLOYMENT_AWS.md`.

## Known limits of Version 1 (by design)
No password reset, email notifications, attachments, re-opening closed tickets, or login rate limiting. Schema changes are applied via `database/schema.sql`; Alembic migrations are a recommended next step.
