"""Create an IT team account (there is no public IT signup).

Run from the api/ folder:  python -m scripts.create_it_user
"""
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import User


def main() -> None:
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
        db.add(User(full_name=full_name, email=email, password_hash=hash_password(password), role="it_team"))
        db.commit()
    print(f"IT team account created for {email}.")


if __name__ == "__main__":
    main()
