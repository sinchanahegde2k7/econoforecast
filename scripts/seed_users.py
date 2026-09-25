"""
Creates two demo accounts for logging into the app: one analyst account
and one admin account. Safe to run more than once - it skips accounts
that already exist instead of duplicating them.

Run with:
    python scripts/seed_users.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User

DEMO_ACCOUNTS = [
    {"name": "Sneha Hegde", "email": "analyst@econoforecast.local", "password": "analyst123", "role": "analyst"},
    {"name": "Admin", "email": "admin@econoforecast.local", "password": "admin123", "role": "admin"},
]


def main():
    app = create_app()
    with app.app_context():
        for acc in DEMO_ACCOUNTS:
            existing = User.query.filter_by(email=acc["email"]).first()
            if existing:
                print(f"Already exists: {acc['email']}")
                continue
            user = User(name=acc["name"], email=acc["email"], role=acc["role"])
            user.set_password(acc["password"])
            db.session.add(user)
            db.session.commit()
            print(f"Created: {acc['email']} / {acc['password']}  (role: {acc['role']})")


if __name__ == "__main__":
    main()
