"""Lab 11, step 3a - pull the 2020 Census populations for NYC's five boroughs.

The Census Data API rejects keyless requests (HTTP 302 -> missing_key.html),
so the key is read from, in order:
    1. the CENSUS_API_KEY environment variable
    2. ./.census_key  (one line, just the key)
    3. the first command-line argument

Usage:
    CENSUS_API_KEY=abc123... python3 fetch_populations.py
    python3 fetch_populations.py abc123...
    echo 'abc123...' > .census_key && python3 fetch_populations.py
"""

import json
import os
import pathlib
import sys
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
RAW = HERE / "census_ny_counties.json"

# 2020 Census FIPS code -> borough name used in the 311 file.
BOROUGHS = {
    "36005": "BRONX",
    "36047": "BROOKLYN",
    "36061": "MANHATTAN",
    "36081": "QUEENS",
    "36085": "STATEN ISLAND",
}

URL = ("https://api.census.gov/data/2020/dec/pl"
       "?get=NAME,P1_001N&for=county:*&in=state:36&key={key}")


def get_key() -> str:
    key = os.environ.get("CENSUS_API_KEY", "").strip()
    if not key and (HERE / ".census_key").exists():
        key = (HERE / ".census_key").read_text().strip()
    if not key and len(sys.argv) > 1:
        key = sys.argv[1].strip()
    if not key:
        sys.exit(
            "No Census API key found.\n"
            "Get one free at https://api.census.gov/data/key_signup.html "
            "(arrives by email in a minute), then either\n"
            "    export CENSUS_API_KEY=yourkey\n"
            "or  echo 'yourkey' > ~/Documents/lab11/.census_key"
        )
    return key


def main() -> None:
    url = URL.format(key=get_key())
    with urllib.request.urlopen(url, timeout=90) as r:
        body = r.read().decode("utf-8")
    RAW.write_text(body)                      # keep the raw answer for the writeup

    rows = json.loads(body)
    header, data = rows[0], rows[1:]
    print(f"columns requested: {header}")
    print(f"NY counties returned by the API: {len(data)}")

    pop = {}
    for name, total, state, county in data:
        fips = state + county
        if fips in BOROUGHS:
            pop[BOROUGHS[fips]] = int(total)

    print(f"\n{'Borough':<14}{'County (API NAME)':<24}{'FIPS':<7}{'Population':>12}")
    print("-" * 57)
    for name, total, state, county in sorted(data, key=lambda r: -int(r[1])):
        fips = state + county
        if fips in BOROUGHS:
            print(f"{BOROUGHS[fips]:<14}{name.replace(' County, New York', ' County'):<24}"
                  f"{fips:<7}{int(total):>12,}")

    missing = set(BOROUGHS) - {r[2] + r[3] for r in data}
    if missing:
        sys.exit(f"\nERROR: these FIPS codes were not in the response: {sorted(missing)}")

    total = sum(pop.values())
    print("-" * 57)
    print(f"{'NYC total':<45}{total:>12,}")

    # Sanity check the lab asks for: the five should add up to about 8.8 million.
    if 8_700_000 <= total <= 8_900_000:
        print("\nSANITY CHECK PASSED: the five boroughs sum to ~8.8 million.")
    else:
        print(f"\nSANITY CHECK FAILED: sum is {total:,}, not ~8.8M "
              "- wrong column or wrong counties?")

    # Cheap proof we grabbed total population and not, say, housing units:
    # NYC's five counties were 8,804,190 in the 2020 Census.
    if total == 8_804_190:
        print("Exact match to the published 2020 count (8,804,190). "
              "P1_001N is total population.")

    (HERE / "borough_populations.json").write_text(json.dumps(pop, indent=2) + "\n")
    print(f"\nWrote {RAW.name} and borough_populations.json")


if __name__ == "__main__":
    main()
