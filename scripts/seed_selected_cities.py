#!/usr/bin/env python
"""
Seed ONLY City table for selected countries with all available cities.
No State rows are created or used; each City is saved with state=None.

Default 6 countries:
1) India
2) UAE (United Arab Emirates)
3) Canada
4) South Africa
5) Australia
6) United States

Usage:
  pip install geonamescache
  python scripts/seed_selected_cities.py --reset
  python scripts/seed_selected_cities.py
  python scripts/seed_selected_cities.py --countries "India,UAE,Canada,South Africa,Australia,United States"
"""

import argparse
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hello.settings")
sys.path.insert(0, BASE_DIR)

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from member.models import City, Country  # noqa: E402

try:
    import geonamescache
except ImportError as exc:
    raise SystemExit(
        f"Missing dependency: {exc}. Install with: pip install geonamescache"
    )

ALIASES = {
    "UAE": "United Arab Emirates",
    "US": "United States",
    "USA": "United States",
    "Africa": "South Africa",
}

DEFAULT_COUNTRIES = [
    "India",
    "UAE",
    "Canada",
    "South Africa",
    "Australia",
    "United States",
]


def _resolve_country(name: str):
    canonical = ALIASES.get(name.strip(), name.strip())
    obj = Country.objects.filter(name__iexact=canonical).first()
    return obj, canonical


def _countries_iso2_map():
    gc = geonamescache.GeonamesCache()
    data = gc.get_countries()
    # data key is ISO2; each row has name
    return {row["name"].lower(): iso2 for iso2, row in data.items()}


def seed_cities(countries, reset=False):
    gc = geonamescache.GeonamesCache()
    all_cities = gc.get_cities().values()

    # Group geonames cities by countrycode (ISO2)
    cities_by_iso2 = defaultdict(list)
    for row in all_cities:
        iso2 = row.get("countrycode")
        if iso2:
            cities_by_iso2[iso2].append(row)

    name_to_iso2 = _countries_iso2_map()
    selected = []
    missing_in_db = []
    missing_iso = []

    for req_name in countries:
        country_obj, canonical = _resolve_country(req_name)
        if not country_obj:
            missing_in_db.append(canonical)
            continue

        iso2 = name_to_iso2.get(canonical.lower())
        if not iso2:
            missing_iso.append(canonical)
            continue

        selected.append((country_obj, canonical, iso2))

    created = 0
    exists = 0

    with transaction.atomic():
        if reset:
            # Only for selected countries
            selected_country_ids = [obj.id for obj, _, _ in selected]
            City.objects.filter(country_id__in=selected_country_ids).delete()

        for country_obj, canonical, iso2 in selected:
            rows = cities_by_iso2.get(iso2, [])
            for row in rows:
                city_name = (row.get("name") or "").strip()
                if not city_name:
                    continue

                _, is_new = City.objects.get_or_create(
                    country=country_obj,
                    state=None,
                    name=city_name,
                )
                if is_new:
                    created += 1
                else:
                    exists += 1

            print(f"Loaded cities for {canonical}: {len(rows)} source rows")

    print("Done")
    print(f"Created city rows: {created}")
    print(f"Existing city rows: {exists}")
    if missing_in_db:
        print("Missing in Country table:", ", ".join(missing_in_db))
    if missing_iso:
        print("No ISO mapping found for:", ", ".join(missing_iso))


def main():
    parser = argparse.ArgumentParser(description="Seed ONLY City table for selected countries")
    parser.add_argument("--reset", action="store_true", help="Delete existing City rows for selected countries first")
    parser.add_argument(
        "--countries",
        type=str,
        default=",".join(DEFAULT_COUNTRIES),
        help="Comma-separated country names",
    )
    args = parser.parse_args()

    country_list = [x.strip() for x in args.countries.split(",") if x.strip()]
    seed_cities(country_list, reset=args.reset)


if __name__ == "__main__":
    main()
