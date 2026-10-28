"""Create the first admin account. After that, admins manage all users at /admin.

Run once from the api/ folder:  python -m scripts.create_admin
"""
from scripts.create_it_user import create_user_interactive

if __name__ == "__main__":
    create_user_interactive("admin")
