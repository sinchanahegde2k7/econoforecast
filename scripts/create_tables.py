"""
Creates all database tables. Used locally the first time, and on Render
during every deploy (safe to run repeatedly - it only creates tables that
don't already exist, never touches ones that do).

Run with:
    python scripts/create_tables.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables ready.")
