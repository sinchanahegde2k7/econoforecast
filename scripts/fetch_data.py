"""
Pulls historical GDP growth, inflation, and unemployment data for India
from the World Bank Open Data API (free, no API key needed) and stores
it in the database using the tables we already created.

Run this once (or again later for fresh data) with:
    python scripts/fetch_data.py
"""
import sys
import os
from datetime import date

# Lets this script import from the app/ package even though it lives
# in a subfolder (scripts/), by adding the project root to the path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from app import create_app, db
from app.models import Dataset, EconomicIndicator, IndicatorValue, User

WORLD_BANK_BASE = "https://api.worldbank.org/v2/country/IN/indicator"

# World Bank's official codes for each indicator, and how we'll label them
# in our own database. These three cover the core story the report is about.
INDICATORS = [
    {
        "code": "NY.GDP.MKTP.KD.ZG",
        "name": "GDP Growth Rate",
        "unit": "% change",
        "category": "GDP",
    },
    {
        "code": "FP.CPI.TOTL.ZG",
        "name": "Inflation Rate (CPI)",
        "unit": "% change",
        "category": "Inflation",
    },
    {
        "code": "SL.UEM.TOTL.ZS",
        "name": "Unemployment Rate",
        "unit": "% of labor force",
        "category": "Employment",
    },
]


def fetch_indicator_data(indicator_code):
    """Calls the World Bank API for one indicator and returns a list of
    (year, value) tuples, skipping any years the World Bank has no data for."""
    url = f"{WORLD_BANK_BASE}/{indicator_code}"
    params = {"format": "json", "per_page": 100}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    # The World Bank API always replies as [metadata, data] -
    # the actual rows we want are in the second element.
    rows = payload[1] if len(payload) > 1 and payload[1] else []

    results = []
    for row in rows:
        if row["value"] is not None:
            results.append((int(row["date"]), float(row["value"])))

    results.sort(key=lambda pair: pair[0])
    return results


def get_or_create_system_user():
    """Every dataset needs to be linked to a user (per the schema).
    This creates one placeholder 'system' account the first time this
    script runs, and reuses it on later runs instead of duplicating it."""
    user = User.query.filter_by(email="system@econoforecast.local").first()
    if user is None:
        user = User(name="System", email="system@econoforecast.local", role="admin")
        user.set_password("not-a-real-login")
        db.session.add(user)
        db.session.commit()
    return user


def main():
    app = create_app()
    with app.app_context():
        existing_dataset = Dataset.query.filter_by(source="World Bank Open Data API").first()
        if existing_dataset is not None:
            print("World Bank data already loaded - skipping fetch.")
            return

        system_user = get_or_create_system_user()

        dataset = Dataset(
            user_id=system_user.id,
            source="World Bank Open Data API",
            filename="world_bank_india_indicators",
            status="ready",
        )
        db.session.add(dataset)
        db.session.commit()

        total_values = 0

        for spec in INDICATORS:
            print(f"Fetching {spec['name']} ({spec['code']}) ...")
            data_points = fetch_indicator_data(spec["code"])

            indicator = EconomicIndicator(
                dataset_id=dataset.id,
                name=spec["name"],
                country="India",
                unit=spec["unit"],
                category=spec["category"],
                frequency="annual",
            )
            db.session.add(indicator)
            db.session.commit()

            for year, value in data_points:
                iv = IndicatorValue(
                    indicator_id=indicator.id,
                    period=date(year, 1, 1),
                    value=value,
                )
                db.session.add(iv)
                total_values += 1

            db.session.commit()
            print(f"  -> stored {len(data_points)} yearly values")

        dataset.records = total_values
        db.session.commit()

        print(f"\nDone. Stored {total_values} total data points across {len(INDICATORS)} indicators.")


if __name__ == "__main__":
    main()
