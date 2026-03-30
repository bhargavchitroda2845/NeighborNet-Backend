import unicodedata
from collections import defaultdict

import geonamescache
import pycountry

from member.models import City, Country, State

TARGET_COUNTRIES = [
    'India',
    'United Arab Emirates',
    'Canada',
    'South Africa',
    'Australia',
    'United States',
]


def norm(s):
    if not s:
        return ''
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return s.strip().lower()


gc = geonamescache.GeonamesCache()
geo_countries = gc.get_countries()
geo_name_to_iso = {v['name'].strip().lower(): k for k, v in geo_countries.items()}

country_objs = {}
for name in TARGET_COUNTRIES:
    c = Country.objects.filter(name__iexact=name).first()
    iso = geo_name_to_iso.get(name.lower())
    if c and iso:
        country_objs[name] = (c, iso)

state_lookup = defaultdict(dict)
for st in State.objects.all().only('id', 'country_id', 'name'):
    state_lookup[st.country_id][norm(st.name)] = st.id

admin_to_state = defaultdict(dict)
for country_name, (country_obj, iso2) in country_objs.items():
    for sub in pycountry.subdivisions.get(country_code=iso2) or []:
        code = getattr(sub, 'code', '')
        if '-' not in code:
            continue
        admin1 = code.split('-', 1)[1].upper()
        sid = state_lookup[country_obj.id].get(norm(sub.name))
        if sid:
            admin_to_state[country_obj.id][admin1] = sid

geo_cities_by_iso = defaultdict(list)
for row in gc.get_cities().values():
    iso = (row.get('countrycode') or '').upper()
    if iso:
        geo_cities_by_iso[iso].append(row)

for country_name, (country_obj, iso2) in country_objs.items():
    City.objects.filter(country=country_obj).delete()

    rows = geo_cities_by_iso.get(iso2, [])
    to_create = []
    seen = set()
    skipped_no_state = 0

    for r in rows:
        city_name = (r.get('name') or '').strip()
        if not city_name:
            continue

        admin1 = (r.get('admin1code') or '').strip().upper()
        sid = admin_to_state[country_obj.id].get(admin1)
        if not sid:
            skipped_no_state += 1
            continue

        key = (sid, city_name.lower())
        if key in seen:
            continue
        seen.add(key)

        to_create.append(City(country_id=country_obj.id, state_id=sid, name=city_name))

    City.objects.bulk_create(to_create, batch_size=1000)

    total = City.objects.filter(country=country_obj).count()
    mapped = City.objects.filter(country=country_obj, state__isnull=False).count()
    print(
        f"{country_name}: source={len(rows)} state_map={len(admin_to_state[country_obj.id])} "
        f"inserted={len(to_create)} skipped_no_state={skipped_no_state} total={total} mapped={mapped}"
    )

print('with_state', City.objects.exclude(state__isnull=True).count())
print('without_state', City.objects.filter(state__isnull=True).count())
