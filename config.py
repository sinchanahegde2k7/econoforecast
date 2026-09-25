import os
from dotenv import load_dotenv

# Load variables from the .env file in this folder into the environment
load_dotenv()


def _normalize_db_url(url):
    # Some hosting providers (Render included, historically) hand out
    # connection strings starting with 'postgres://', but modern
    # SQLAlchemy requires the 'postgresql://' form. This makes both work.
    if url and url.startswith('postgres://'):
        return url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    # Used by Flask to secure sessions/cookies. Change the default in your .env.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')

    # Reads the full connection string from .env (locally) or from the
    # hosting platform's environment variables (in production/Render).
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:password@localhost:5432/econoforecast'
    ))

    # Turns off a feature we don't need; keeps the console output clean.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
