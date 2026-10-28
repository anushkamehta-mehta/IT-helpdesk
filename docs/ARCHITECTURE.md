# Architecture

```
Browser (HTML/CSS/JS)
  |  GET /login, /tickets, ...  -->  Flask (web/)  : serves page shells + static JS/CSS only
  |  fetch /api/...  (cookie)   -->  FastAPI (api/) : auth, permissions, workflow rules
                                          |
                                          v
                                       MySQL
```

* **Flask** never touches the database and holds no business logic.
* **FastAPI** is the only service that talks to MySQL and the single place permissions are enforced.
* **Nginx** (production) serves both under one domain: `/api/*` -> FastAPI, everything else -> Flask.

## Authentication
* Passwords are hashed with Argon2.
* Login returns a signed JWT in an **httpOnly, SameSite=Lax** cookie (`Secure` in production), so JavaScript cannot read it (limits XSS token theft).
* CSRF: every non-GET API request must include `X-Requested-With: fetch`. Cross-site pages cannot send that header without a CORS preflight, which the API refuses.
* Page guards in JS only route users; **the API enforces every permission**.
* Only employees can self-register. IT accounts are created with `python -m scripts.create_it_user`.

## Permissions
| Action | Employee | IT team |
|---|---|---|
| Register / login | yes | login only |
| Create ticket | yes | no |
| View tickets | own only | all |
| Search / filter | own tickets | all tickets |
| Comment | own tickets | any ticket |
| Assign, change status/priority, resolution notes, close | no | yes |

## Ticket workflow
`Open -> Assigned -> In Progress -> Closed`

* Assigning an Open ticket moves it to Assigned automatically.
* Assigned / In Progress require an assignee.
* Closing requires resolution notes (and may be done from any open state, e.g. duplicates).
* Closed tickets are frozen: no edits, no new comments (V1 has no re-open).

## Data model
`users` 1-n `tickets` (created_by, assigned_to) | `categories` 1-n `tickets` | `tickets` 1-n `comments` | `users` 1-n `comments`.
All relations are real foreign keys; the `role`, `priority` and `status` columns are MySQL ENUMs.
