"""Load demo users and tickets for a live demonstration.

Run from the api/ folder:  python -m scripts.seed_demo
You are asked for ONE password that is used for all demo accounts (nothing is hard-coded).
Accounts: alice@helpdesk-demo.com, bob@helpdesk-demo.com (employees),
          ivan@helpdesk-demo.com, priya@helpdesk-demo.com (IT team).
"""
import getpass
import sys
from datetime import datetime, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import Category, Comment, Ticket, User

USERS = [
    ("Alice Employee", "alice@helpdesk-demo.com", "employee"),
    ("Bob Employee", "bob@helpdesk-demo.com", "employee"),
    ("Ivan IT", "ivan@helpdesk-demo.com", "it_team"),
    ("Priya IT", "priya@helpdesk-demo.com", "it_team"),
]

# (title, description, category, priority, status, creator, assignee, resolution, comments)
TICKETS = [
    ("Laptop will not boot", "Black screen after the Windows logo since this morning.", "Hardware", "High", "In Progress", "alice", "ivan", None,
     [("alice", "It also beeps twice on startup."), ("ivan", "Thanks, I'm collecting a replacement SSD for you.")]),
    ("Cannot connect to office Wi-Fi", "Phone connects fine but my laptop keeps asking for a password.", "Network", "Medium", "Assigned", "bob", "priya", None, []),
    ("Need Adobe Acrobat installed", "Required for signing contracts.", "Software", "Low", "Open", "alice", None, None, []),
    ("Outlook not syncing", "New mail has not arrived since yesterday.", "Email", "High", "Open", "bob", None, None,
     [("bob", "Restarting did not help.")]),
    ("Password reset for VPN", "Locked out of the VPN after too many attempts.", "Access / Accounts", "Medium", "Closed", "alice", "ivan",
     "VPN account unlocked and password reset. Verified login with the user.", [("ivan", "Done, please try again.")]),
    ("Printer on floor 2 jams", "Paper jams on every second print job.", "Hardware", "Low", "Closed", "bob", "priya",
     "Replaced pickup roller. Test prints OK.", []),
]


def main() -> None:
    password = getpass.getpass("Password to use for all demo accounts (min 8 chars): ")
    if len(password) < 8:
        sys.exit("Password too short.")
    pw_hash = hash_password(password)

    with get_sessionmaker()() as db:
        if db.scalar(select(User).where(User.email == USERS[0][1])):
            sys.exit("Demo data already exists. Nothing done.")

        people = {}
        for full_name, email, role in USERS:
            user = User(full_name=full_name, email=email, password_hash=pw_hash, role=role)
            db.add(user)
            people[email.split("@")[0]] = user
        db.flush()

        categories = {c.name: c for c in db.scalars(select(Category))}
        if not categories:
            sys.exit("No categories found. Run database/schema.sql first.")

        now = datetime.utcnow()
        for i, (title, desc, cat, prio, status, creator, assignee, resolution, comments) in enumerate(TICKETS):
            created = now - timedelta(days=len(TICKETS) - i, hours=i)
            ticket = Ticket(
                title=title, description=desc, category_id=categories[cat].id, priority=prio, status=status,
                created_by=people[creator].id, assigned_to=people[assignee].id if assignee else None,
                resolution_notes=resolution, created_at=created, updated_at=created,
                closed_at=created + timedelta(hours=5) if status == "Closed" else None,
            )
            db.add(ticket)
            db.flush()
            for n, (author, body) in enumerate(comments):
                db.add(Comment(ticket_id=ticket.id, author_id=people[author].id, body=body,
                               created_at=created + timedelta(hours=n + 1)))
        db.commit()
    print("Demo data created. Log in with any demo email and the password you just entered.")


if __name__ == "__main__":
    main()
