"""Show which database the app is connected to and what is stored in it.

Run from the api/ folder:  python -m scripts.check_db
"""
import sys

from sqlalchemy import inspect, text

from app.core.config import get_settings
from app.db.session import get_engine

TABLES = ("users", "categories", "tickets", "comments")


def main() -> None:
    settings = get_settings()
    print(f"Configured database: {settings.database_label}")
    try:
        with get_engine().connect() as conn:
            version = conn.scalar(text("SELECT VERSION()"))
            server = conn.scalar(text("SELECT @@hostname"))
            cipher = conn.execute(text("SHOW SESSION STATUS LIKE 'Ssl_cipher'")).first()
            print(f"Connected: MySQL {version} on server '{server}', encryption: {(cipher and cipher[1]) or 'none'}")
            existing = set(inspect(conn).get_table_names())
            missing = [t for t in TABLES if t not in existing]
            for t in TABLES:
                if t in existing:
                    print(f"  {t:<11} {conn.scalar(text(f'SELECT COUNT(*) FROM {t}'))} rows")
            if missing:
                sys.exit(f"Missing tables: {', '.join(missing)}. Run database/schema.sql (and the migrations) on this database.")
    except Exception as e:  # report any connection problem in plain words
        sys.exit(f"Could not connect: {e}")


if __name__ == "__main__":
    main()
