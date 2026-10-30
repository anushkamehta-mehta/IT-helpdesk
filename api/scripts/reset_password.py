"""Set a new password for any account from the terminal (e.g. a forgotten admin password).
Admins can also do this at /admin (Edit user > New password).

Run from the api/ folder:  python -m scripts.reset_password
"""
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import get_sessionmaker
from app.models import User


def main() -> None:
    email = input("Email of the account: ").strip().lower()
    with get_sessionmaker()() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            sys.exit(f"No account with email {email}.")
        password = getpass.getpass("New password (min 8 chars): ")
        if getpass.getpass("Confirm password: ") != password:
            sys.exit("Passwords do not match.")
        if len(password) < 8:
            sys.exit("Password must be at least 8 characters.")
        user.password_hash = hash_password(password)
        db.commit()
    print(f"Password updated for {user.full_name} ({email}, {user.role}). You can log in now.")


if __name__ == "__main__":
    main()
