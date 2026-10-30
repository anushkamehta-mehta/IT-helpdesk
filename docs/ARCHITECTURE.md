# Architecture

```
Browser (HTML/CSS/JS)
  |  GET /login, /tickets, ...  -->  FastAPI pages router (api/app/routers/pages.py): page shells + /static JS/CSS
  |  fetch /api/...  (cookie)   -->  FastAPI API routers (api/app/routers/*)       : auth, permissions, workflow rules
                                          |
                                          v
                                       MySQL
```

* One FastAPI app on one port serves both the pages and the API (same origin, so no CORS needed).
* The page routes never touch the database and hold no business logic; the API routers are the single place permissions are enforced.
* **Nginx** (production) proxies everything to the FastAPI service.

## Authentication
* Passwords are hashed with Argon2.
* Login returns a signed JWT in an **httpOnly, SameSite=Lax** cookie (`Secure` in production), so JavaScript cannot read it (limits XSS token theft).
* CSRF: every non-GET API request must include `X-Requested-With: fetch`. Cross-site pages cannot send that header without a CORS preflight, which the API refuses.
* Page guards in JS only route users; **the API enforces every permission**.
* Only employees can self-register. Admins create accounts of any role (employee, IT team, admin) at `/admin`; the first admin is created with `python -m scripts.create_admin`.

## Permissions
| Action | Employee | IT team | Admin |
|---|---|---|---|
| Register / login | yes | login only | login only |
| Create ticket | yes | no | no |
| View tickets | own only | all | - |
| Search / filter | own tickets | all tickets | - |
| Comment | own tickets | any ticket | - |
| Edit title/description/category/priority, delete | own tickets | any ticket | - |
| Assign, change status, resolution notes | no | yes | - |
| Close, or send a resolved ticket back | own tickets | no | no |
| Add, edit, deactivate, delete users (`/admin`) | no | no | yes |

## Ticket workflow
`Open -> Assigned -> In Progress / On Hold -> Resolved -> Closed`

* Assigning a ticket (or reassigning it to a different person) sets it to Assigned automatically, unless IT picks a new status in the same save.
* An Open ticket must be assigned before IT can change its status.
* IT moves tickets between In Progress, On Hold and Resolved (and back from Resolved to In Progress). Resolving requires resolution notes.
* Only the employee who raised the ticket can close it (IT and admins cannot). They can close it at any time.
* When a ticket is Resolved, the employee either closes it or sends it back with a comment explaining what still needs to change; it returns to In Progress with the same assignee.
* Closed tickets are frozen: no edits, no new comments.

## Data model
`users` 1-n `tickets` (created_by, assigned_to) | `categories` 1-n `tickets` | `tickets` 1-n `comments` | `users` 1-n `comments`.
All relations are real foreign keys; the `role`, `priority` and `status` columns are MySQL ENUMs.
