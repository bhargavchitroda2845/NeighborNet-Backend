#!/usr/bin/env python
"""
Seed Country, State, City master tables with world data.

Usage:
  python scripts/seed_world_locations.py --all-cities
  python scripts/seed_world_locations.py --max-cities-per-country 500
  python scripts/seed_world_locations.py --min-population 10000 --reset

Requirements:
  pip install pycountry geonamescache
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
from member.models import City, Country, State  # noqa: E402


def _require_third_party():
    try:
        import pycountry  # noqa: F401
        import geonamescache  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: {}. Install with: pip install pycountry geonamescache".format(exc)
        )


def _state_like(subdivision_type: str) -> bool:
    if not subdivision_type:
        return False
    t = subdivision_type.lower()
    keywords = (
        "state",
        "province",
        "region",
        "territory",
        "district",
        "governorate",
        "department",
        "county",
        "prefecture",
        "oblast",
        "municipality",
        "canton",
        "republic",
        "autonomous",
    )
    return any(k in t for k in keywords)


def seed_world_locations(all_cities=False, max_cities_per_country=300, min_population=20000, reset=False):
    import pycountry
    import geonamescache

    created = {"country": 0, "state": 0, "city": 0}
    existing = {"country": 0, "state": 0, "city": 0}

    with transaction.atomic():
        if reset:
            City.objects.all().delete()
            State.objects.all().delete()
            Country.objects.all().delete()

        countries_by_iso2 = {}
        for c in pycountry.countries:
            country_obj, is_new = Country.objects.get_or_create(name=c.name)
            countries_by_iso2[getattr(c, "alpha_2", "")] = country_obj
            if is_new:
                created["country"] += 1
            else:
                existing["country"] += 1

        states_by_country_admin_code = {}
        states_by_country_name = {}

        for s in pycountry.subdivisions:
            iso_country = getattr(s, "country_code", None)
            if not iso_country:
                continue

            if not _state_like(getattr(s, "type", "")):
                continue

            country_obj = countries_by_iso2.get(iso_country)
            if not country_obj:
                continue

            state_obj, is_new = State.objects.get_or_create(
                country=country_obj,
                name=s.name,
            )
            if is_new:
                created["state"] += 1
            else:
                existing["state"] += 1

            code = getattr(s, "code", "")
            admin_code = code.split("-", 1)[1] if "-" in code else ""
            if admin_code:
                states_by_country_admin_code[(iso_country, admin_code.upper())] = state_obj
            states_by_country_name[(iso_country, s.name.strip().lower())] = state_obj

        gc = geonamescache.GeonamesCache()
        cities = list(gc.get_cities().values())

        grouped = defaultdict(list)
        for city in cities:
            country_code = city.get("countrycode")
            if country_code:
                grouped[country_code].append(city)

        for iso_country, city_rows in grouped.items():
            country_obj = countries_by_iso2.get(iso_country)
            if not country_obj:
                continue

            city_rows.sort(key=lambda x: int(x.get("population") or 0), reverse=True)

            selected = []
            for row in city_rows:
                population = int(row.get("population") or 0)
                if all_cities or population >= min_population:
                    selected.append(row)

            if not all_cities and max_cities_per_country and len(selected) > max_cities_per_country:
                selected = selected[:max_cities_per_country]

            for row in selected:
                city_name = (row.get("name") or "").strip()
                if not city_name:
                    continue

                admin_code = (row.get("admin1code") or "").strip().upper()
                state_obj = states_by_country_admin_code.get((iso_country, admin_code))

                if not state_obj and admin_code:
                    fallback_state_name = f"Region {admin_code}"
                    state_obj, is_new_state = State.objects.get_or_create(
                        country=country_obj,
                        name=fallback_state_name,
                    )
                    if is_new_state:
                        created["state"] += 1
                    else:
                        existing["state"] += 1
                    states_by_country_admin_code[(iso_country, admin_code)] = state_obj

                _, is_new_city = City.objects.get_or_create(
                    country=country_obj,
                    state=state_obj,
                    name=city_name,
                )
                if is_new_city:
                    created["city"] += 1
                else:
                    existing["city"] += 1

    print("Seeding completed")
    print("Created:", created)
    print("Existing:", existing)
    print("Totals:", {
        "country": Country.objects.count(),
        "state": State.objects.count(),
        "city": City.objects.count(),
    })


def main():
    _require_third_party()

    parser = argparse.ArgumentParser(description="Seed world Country/State/City master tables")
    parser.add_argument("--all-cities", action="store_true", help="Import all available cities")
    parser.add_argument(
        "--max-cities-per-country",
        type=int,
        default=300,
        help="When not using --all-cities, cap cities per country (default: 300)",
    )
    parser.add_argument(
        "--min-population",
        type=int,
        default=20000,
        help="When not using --all-cities, minimum city population (default: 20000)",
    )
    parser.add_argument("--reset", action="store_true", help="Delete existing Country/State/City before seeding")

    args = parser.parse_args()
    seed_world_locations(
        all_cities=args.all_cities,
        max_cities_per_country=args.max_cities_per_country,
        min_population=args.min_population,
        reset=args.reset,
    )


if __name__ == "__main__":
    main()
