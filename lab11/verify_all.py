"""Independent re-check of every headline number in report.md.

TWO WAYS, ALWAYS
    A = pandas          (the method used by the analysis scripts)
    B = stdlib csv      (a separate code path over the same file)

A headline number counts as verified only when A == B exactly. Run:
    python3 verify_all.py
Every figure in the report was produced from the A path; B only audits it.
"""

from __future__ import annotations

import collections
import csv
import gzip
import json
import pathlib
import statistics
from datetime import datetime

import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
CSV = HERE / "nyc-311-2025-november(1).csv.gz"
FMT = "%m/%d/%Y %I:%M:%S %p"

NOISE = "Noise - Residential"
HEAT = "HEAT/HOT WATER"
HULL = "203 HULL STREET"
PARSONS = "78-15 PARSONS BOULEVARD"

rows: list[tuple[str, str, str, str, bool]] = []


def check(task: str, item: str, a, b, fmt="{}") -> None:
    ok = a == b
    rows.append((task, item, fmt.format(a), fmt.format(b), ok))


# =====================================================================  METHOD A
print("reading with pandas ...")
use = ["Unique Key", "Created Date", "Closed Date", "Agency",
       "Problem (formerly Complaint Type)", "Incident Address", "BBL", "Borough",
       "Status", "Open Data Channel Type"]
df = pd.read_csv(CSV, usecols=use, dtype=str, encoding="utf-8",
                 encoding_errors="replace", low_memory=False)
A = {}
A["rows"], A["cols"] = len(df), pd.read_csv(CSV, nrows=0).shape[1]
A["problems_n"] = df["Problem (formerly Complaint Type)"].nunique()
A["created"] = pd.to_datetime(df["Created Date"], format=FMT)
A["boroughs"] = df["Borough"].value_counts().to_dict()

blank = df["Closed Date"].fillna("").str.strip() == ""
A["blank_closed"] = int(blank.sum())
A["blank_status"] = df.loc[blank, "Status"].value_counts().to_dict()

df["created"] = A["created"]
df["hour"] = df["created"].dt.hour
df["closed"] = pd.to_datetime(df["Closed Date"], format=FMT, errors="coerce")
noise = df[df["Problem (formerly Complaint Type)"] == NOISE].copy()
heat = df[df["Problem (formerly Complaint Type)"] == HEAT].copy()
A["noise_peak"] = noise.hour.value_counts().idxmax()
A["noise_peak_n"] = int(noise.hour.value_counts().max())
A["heat_peak"] = heat.hour.value_counts().idxmax()
A["heat_peak_n"] = int(heat.hour.value_counts().max())

bk = df[df.Borough == "BROOKLYN"]
A["bk_top5"] = bk["Problem (formerly Complaint Type)"].value_counts().head(5).to_dict()
A["hull_n"] = int((df["Incident Address"] == HULL).sum())
A["hull_noise"] = int(((df["Incident Address"] == HULL) &
                       (df["Problem (formerly Complaint Type)"] == NOISE)).sum())

closed_heat = heat[heat["closed"].notna()].copy()
closed_heat["hours"] = (closed_heat.closed - A["created"].loc[closed_heat.index]) \
    .dt.total_seconds() / 3600
A["heat_opens"] = int(heat["closed"].isna().sum())
A["heat_total"] = int(len(heat))
A["heat_shape"] = (int(heat["created"].dt.date.nunique()), int(heat["hour"].nunique()))
A["heat_med"] = closed_heat.groupby("Borough").hours.median().to_dict()
A["heat_n"] = closed_heat.groupby("Borough").hours.size().to_dict()

h11 = closed_heat[closed_heat.closed.dt.date == pd.Timestamp("2025-11-11").date()]
A["nov11_heat"] = int(len(heat[heat["created"].dt.date == pd.Timestamp("2025-11-11").date()]))
A["nov11_cell"] = int(((A["created"].dt.date == pd.Timestamp("2025-11-11").date()) &
                       (heat.hour == 10)).sum())

par = df[df["Incident Address"] == PARSONS]
A["par_n"] = len(par)
A["par_how"] = int((par["Problem (formerly Complaint Type)"] == "Noise - House of Worship").sum())
A["par_channel"] = par["Open Data Channel Type"].value_counts().to_dict()
par_min = par["Created Date"].str[:16].value_counts()
A["par_minutes"] = int((par_min > 1).sum())
A["par_calls_in_clusters"] = int(par_min[par_min > 1].sum())

# =====================================================================  METHOD B
print("re-reading with the csv module ...")
B = {}
prob = collections.Counter()
borough = collections.Counter()
brooklyn = collections.Counter()
hour_noise = collections.Counter()
hour_heat = collections.Counter()
blank_status = collections.Counter()
heat_hours: dict[str, list[float]] = collections.defaultdict(list)
heat_grid = collections.Counter()
nov11_heat = 0
nov11_hour10 = 0
hull = hull_noise = 0
par = collections.Counter()
par_prob = collections.Counter()
par_chan = collections.Counter()
par_minute = collections.Counter()
par_bbl = set()
par_keys = set()
created_first = created_last = None
n_rows = 0

with gzip.open(CSV, "rt", encoding="utf-8", errors="replace", newline="") as fh:
    reader = csv.reader(fh)
    header = next(reader)
    idx = {name: i for i, name in enumerate(header)}
    i_prob, i_created, i_closed = (idx["Problem (formerly Complaint Type)"],
                                   idx["Created Date"], idx["Closed Date"])
    i_boro, i_status, i_addr = idx["Borough"], idx["Status"], idx["Incident Address"]
    i_chan, i_bbl, i_key = (idx["Open Data Channel Type"], idx["BBL"], idx["Unique Key"])

    for row in reader:
        n_rows += 1
        dtype_problem = row[i_prob]
        b = row[i_boro]
        prob[dtype_problem] += 1
        borough[b] += 1
        if b == "BROOKLYN":
            brooklyn[dtype_problem] += 1

        ts = None
        try:
            ts = datetime.strptime(row[i_created], FMT)
        except ValueError:
            pass
        if ts is not None:
            if created_first is None or ts < created_first:
                created_first = ts
            if created_last is None or ts > created_last:
                created_last = ts
            if dtype_problem == NOISE:
                hour_noise[ts.hour] += 1
            if dtype_problem == HEAT:
                hour_heat[ts.hour] += 1
                heat_grid[(ts.date(), ts.hour)] += 1
                if ts.date() == datetime(2025, 11, 11).date():
                    nov11_heat += 1
                    if ts.hour == 10:
                        nov11_hour10 += 1

        closed_txt = row[i_closed]
        if closed_txt.strip() == "":
            blank_status[row[i_status]] += 1
        elif dtype_problem == HEAT and ts is not None:
            try:
                ct = datetime.strptime(closed_txt, FMT)
                heat_hours[b].append((ct - ts).total_seconds() / 3600)
            except ValueError:
                pass

        if row[i_addr] == HULL:
            hull += 1
            if dtype_problem == NOISE:
                hull_noise += 1

        if row[i_addr] == PARSONS:
            par["n"] += 1
            par_prob[dtype_problem] += 1
            par_chan[row[i_chan]] += 1
            par_minute[row[i_created][:16]] += 1
            par_bbl.add(row[i_bbl])
            par_keys.add(row[i_key])

B["rows"], B["cols"] = n_rows, len(header)
B["problems_n"] = len(prob)
B["created"] = (created_first, created_last)
B["boroughs"] = dict(borough)
B["blank_closed"] = sum(blank_status.values())
B["blank_status"] = dict(blank_status)
B["noise_peak_n"] = hour_noise[max(hour_noise, key=hour_noise.get)]
B["noise_peak"] = max(hour_noise, key=hour_noise.get)
B["heat_peak_n"] = hour_heat[max(hour_heat, key=hour_heat.get)]
B["heat_peak"] = max(hour_heat, key=hour_heat.get)
B["bk_top5"] = dict(brooklyn.most_common(5))
B["hull_n"], B["hull_noise"] = hull, hull_noise
B["heat_med"] = {k: statistics.median(v) for k, v in heat_hours.items()}
B["heat_n"] = {k: len(v) for k, v in heat_hours.items()}
B["heat_opens"] = len(heat) - sum(len(v) for v in heat_hours.values())
B["nov11_heat"] = nov11_heat
B["nov11_cell"] = nov11_hour10
B["par_n"] = par["n"]
B["par_how"] = par_prob["Noise - House of Worship"]
B["par_channel"] = dict(par_chan)
B["par_minutes"] = sum(1 for v in par_minute.values() if v > 1)
B["par_calls_in_clusters"] = sum(v for v in par_minute.values() if v > 1)

# =====================================================================  COMPARE
check("1", "rows", A["rows"], B["rows"], "{:,}")
check("1", "columns", A["cols"], B["cols"])
check("1", "distinct Problem values", A["problems_n"], B["problems_n"])
check("1", "earliest Created Date", A["created"].min(), B["created"][0], "{:%Y-%m-%d %H:%M:%S}")
check("1", "latest Created Date", A["created"].max(), B["created"][1], "{:%Y-%m-%d %H:%M:%S}")
check("1", "rows with no Closed Date", A["blank_closed"], B["blank_closed"], "{:,}")
check("1", "Status mix of those rows", A["blank_status"], B["blank_status"])

for b in ["BROOKLYN", "BRONX", "QUEENS", "MANHATTAN", "STATEN ISLAND", "Unspecified"]:
    check("2", f"{b} calls", A["boroughs"][b], B["boroughs"][b], "{:,}")
for k in A["bk_top5"]:
    check("2", f"Brooklyn: {k}", A["bk_top5"][k], B["bk_top5"][k], "{:,}")
check("2", "203 Hull Street calls", A["hull_n"], B["hull_n"], "{:,}")
check("2", "203 Hull Street noise calls", A["hull_noise"], B["hull_noise"], "{:,}")

# populations: A reads the tidy JSON, B re-derives them from the raw API body
pop_a = json.loads((HERE / "borough_populations.json").read_text())
raw = json.loads((HERE / "census_ny_counties.json").read_text())
fips = {"36005": "BRONX", "36047": "BROOKLYN", "36061": "MANHATTAN",
        "36081": "QUEENS", "36085": "STATEN ISLAND"}
pop_b = {fips[r[2] + r[3]]: int(r[1]) for r in raw[1:] if r[2] + r[3] in fips}
check("3", "population total", sum(pop_a.values()), sum(pop_b.values()), "{:,}")
for b in fips.values():
    check("3", f"population {b}", pop_a[b], pop_b[b], "{:,}")

rate_a = {b: A["boroughs"][b] / pop_a[b] * 1000 for b in pop_a}
rate_b = {b: borough[b] / pop_b[b] * 1000 for b in pop_b}
for b in sorted(rate_a):
    check("3", f"calls per 1,000 {b}", round(rate_a[b], 4), round(rate_b[b], 4))
check("3", "rank order by rate", sorted(rate_a, key=rate_a.get, reverse=True),
      sorted(rate_b, key=rate_b.get, reverse=True))

check("4", "Noise peak hour", A["noise_peak"], B["noise_peak"])
check("4", "Noise calls at peak", A["noise_peak_n"], B["noise_peak_n"], "{:,}")
check("4", "Heat peak hour", A["heat_peak"], B["heat_peak"])
check("4", "Heat calls at peak", A["heat_peak_n"], B["heat_peak_n"], "{:,}")
check("4", "heat map shape", A["heat_shape"], (len({d for d, _ in heat_grid}), len({h for _, h in heat_grid})))
check("4", "heat map total (all heat rows)", A["heat_total"], sum(heat_grid.values()), "{:,}")
check("4", "Nov 11 heat calls", A["nov11_heat"], B["nov11_heat"], "{:,}")
check("4", "Nov 11 10:00 cell", A["nov11_cell"], B["nov11_cell"], "{:,}")

check("5", "open heat cases dropped", A["heat_opens"], B["heat_opens"])
for b in sorted(A["heat_med"]):
    check("5", f"closed heat cases {b}", A["heat_n"][b], B["heat_n"][b], "{:,}")
    check("5", f"median hours {b}", round(A["heat_med"][b], 4), round(B["heat_med"][b], 4))

check("6", "78-15 Parsons calls", A["par_n"], B["par_n"], "{:,}")
check("6", "Parsons house-of-worship calls", A["par_how"], B["par_how"], "{:,}")
check("6", "Parsons channel mix", A["par_channel"], B["par_channel"])
check("6", "Parsons multi-call minutes", A["par_minutes"], B["par_minutes"])
check("6", "Parsons calls inside those minutes", A["par_calls_in_clusters"],
      B["par_calls_in_clusters"], "{:,}")
print(f"Parsons rows: {len(par_keys)} keys, {len(par_bbl)} BBL")

# =====================================================================  OUTPUT
print()
w = max(len(r[1]) for r in rows) + 2
print(f"{'T':<3}{'number':<{w}}{'pandas':>22}{'csv module':>24}   ok")
print("-" * (w + 55))
fails = 0
for task, item, a, b, ok in rows:
    fails += not ok
    print(f"{task:<3}{item:<{w}}{a:>22}{b:>24}   {'PASS' if ok else 'FAIL'}")
print("-" * (w + 55))
print(f"{len(rows) - fails}/{len(rows)} checks agree exactly"
      + ("" if fails == 0 else f"  -- {fails} DISAGREE"))
raise SystemExit(1 if fails else 0)
