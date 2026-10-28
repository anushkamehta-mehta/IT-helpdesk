"""Create an IT team account from the terminal (admins can also do this at /admin).

Run from the api/ folder:  python -m scripts.create_it_user
"""
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import User

ROLE_LABELS = {"it_team": "IT team", "admin": "Admin"}


def create_user_interactive(role: str) -> None:
    full_name = input("Full name: ").strip()
    email = input("Email: ").strip().lower()
    password = getpass.getpass("Password (min 8 chars): ")
    if getpass.getpass("Confirm password: ") != password:
        sys.exit("Passwords do not match.")
    if not full_name or "@" not in email or len(password) < 8:
        sys.exit("Invalid input.")

    with get_sessionmaker()() as db:
        if db.scalar(select(User).where(User.email == email)):
            sys.exit("A user with this email already exists.")
        db.add(User(full_name=full_name, email=email, password_hash=hash_password(password), role=role))
        db.commit()
    print(f"{ROLE_LABELS[role]} account created for {email}.")


def main() -> None:
    create_user_interactive("it_team")


if __name__ == "__main__":
    main()
