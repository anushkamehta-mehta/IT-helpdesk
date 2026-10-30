# IT Helpdesk & Ticket Management System (Version 1)

Internal IT helpdesk: employees raise and track tickets, the IT team triages and resolves them.

**Stack:** HTML/CSS/JavaScript, FastAPI (pages + API, one server), MySQL, SQLAlchemy, Argon2, JWT in an httpOnly cookie.

```
it-helpdesk/
  api/        FastAPI app: API routers, page routes, Jinja templates, static CSS/JS,
              services (business rules), models, schemas, tests, scripts
  database/   schema.sql (tables + starter categories)
  deploy/     Nginx + systemd files and production env template for AWS
  docs/       ARCHITECTURE.md, DEPLOYMENT_AWS.md
```

## Features
**Employee:** register, log in, create ticket (category, description, priority), view own tickets, check status, comment on own tickets, close own tickets, or send a resolved ticket back with a comment if not satisfied.
**IT team:** log in, view all tickets, search (title/description/ticket #), filter (status, priority, category, assignee/unassigned), assign tickets (status becomes Assigned automatically), set status to In Progress / On Hold / Resolved, change priority, add resolution notes, comment. IT and admins cannot close tickets.
Workflow: `Open -> Assigned -> In Progress / On Hold -> Resolved -> Closed` (only the employee closes). Priorities: Low / Medium / High. See `docs/ARCHITECTURE.md` for the rules.

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
Edit `.env`: set `DB_PASSWORD` and `JWT_SECRET`. Generate the secret with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Email (optional):** when IT marks a ticket *Resolved*, the employee is emailed the resolution notes and a link to close the ticket or request changes. Fill in the `SMTP_*` values in `.env` to turn it on (leave `SMTP_HOST` empty to keep it off). For Gmail, turn on 2-Step Verification, create an App Password (Google Account > Security > App passwords) and use:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_USER=yourname@gmail.com
SMTP_PASSWORD=the-16-character-app-password
```
Restart the server after changing `.env`. If an email cannot be sent, the ticket still saves and the error is printed in the server terminal.

### 3. Install (virtual environment activated, from the project root)
```bash
pip install -r api/requirements.txt
```

### 4. Create the first admin account
```bash
cd api
python -m scripts.create_admin
```
Log in as the admin and open **http://127.0.0.1:8000/admin** to add employees, IT team members and other admins (no terminal needed after this). Employees can still self-register at `/register`.

Upgrading an existing database? Run the files in `database/migrations/` (`001_add_admin_role.sql`, `002_add_hold_and_resolved_status.sql`) once each, in order, in MySQL Workbench (as root) first.
(Optional, for demos) load sample users and tickets:
```bash
python -m scripts.seed_demo
```
It asks for one password used for all demo accounts: `alice@` and `bob@helpdesk-demo.com` (employees), `ivan@` and `priya@helpdesk-demo.com` (IT).

### 5. Run (one terminal, virtual environment activated)
```bash
cd api
uvicorn app.main:app --reload --port 8000
```
Open **http://127.0.0.1:8000**. API docs: http://127.0.0.1:8000/docs. Health check: http://127.0.0.1:8000/api/health

## Suggested demo script (10 minutes)
1. Register a new employee, log in, create a High-priority ticket.
2. Add a comment as the employee.
3. In a private window log in as an IT user: search/filter the list, open the ticket, assign it (it becomes Assigned), move it to In Progress, change priority.
4. Try to resolve without resolution notes (blocked), then add notes and mark it Resolved.
5. Back as the employee: see the resolution notes, click **Request changes** with a comment (it goes back to In Progress), then after IT resolves it again click **Yes, close ticket**. Closed tickets are read-only.
6. Show that the employee cannot open another employee's ticket (404) and IT pages redirect away.

## Tests
```bash
cd api
pip install -r requirements-dev.txt
pytest                      # uses in-memory SQLite, no MySQL needed
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
| PATCH `/tickets/{id}` | IT | Assign, status (In Progress / On Hold / Resolved), priority, resolution notes |
| POST `/tickets/{id}/close` | owner | Close the ticket |
| POST `/tickets/{id}/reopen` (`body`) | owner | Send a Resolved ticket back to In Progress with a comment |
| POST `/tickets/{id}/comments` | owner / IT | Add comment |

## Troubleshooting
* **API fails to start with a validation error:** `.env` is missing or `DB_USER`/`DB_PASSWORD`/`JWT_SECRET` are not set.
* **Login works but you are sent back to the login page:** host name mismatch (`localhost` vs `127.0.0.1`), or `COOKIE_SECURE=true` while using plain http.
* **"Cannot reach the server":** the server terminal is not running.
* **No email on Render (free plan):** Render's free plan blocks SMTP ports, so Gmail SMTP times out. Either use a paid instance, or create a free Brevo account, verify your sender address, and set `BREVO_API_KEY` and `SMTP_FROM` (the verified sender).
* **No email after resolving a ticket:** check the server terminal for `Could not send email` or `SMTP_HOST is not set`. Gmail needs an App Password, not your normal password.
* **"Invalid email or password" with the right details:** the password doesn't match the stored one. An admin can set a new one at `/admin` (Edit user), or from the terminal: `cd api` then `python -m scripts.reset_password`.
* **Data is not where you expect (local vs. Aiven):** the server prints `Database: user@host:port/name` when it starts. `cd api` then `python -m scripts.check_db` shows the connected server and row counts.
* **Database error:** check the `DB_*` values and that `database/schema.sql` was run.

## Deployment
### Vercel
The repo is ready for Vercel (`vercel.json` + `index.py` at the root; packages in the root `requirements.txt`).
In the Vercel project go to **Settings > Environment Variables** and add (for Production and Preview):

| Name | Value |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | your Aiven values |
| `DB_SSL_CA` | the full text of Aiven's `ca.pem` (open it in a text editor, copy everything including the BEGIN/END lines) |
| `JWT_SECRET` | a long random string |
| `COOKIE_SECURE` | `true` |
| `APP_BASE_URL` | your site address, e.g. `https://your-project.vercel.app` |
| `SMTP_*` | optional, for the "ticket resolved" email |

Then **Deployments > Redeploy**. Environment variables only apply to new deployments.
On Vercel the resolved email is sent during the save (serverless functions stop after responding), so that save takes a moment longer.

### AWS
See `docs/DEPLOYMENT_AWS.md`.

## Known limits of Version 1 (by design)
No password reset, email notifications, attachments, re-opening closed tickets (resolved tickets can be sent back), or login rate limiting. Schema changes are applied via `database/schema.sql`; Alembic migrations are a recommended next step.
