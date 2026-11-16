"""Lab 11, Task 5 - the same job, in five places.

HEAT/HOT WATER only: one complaint type, one agency (HPD), five boroughs.
If the boroughs differ, it cannot be because they do different work.

Outputs
    fig-same-job.png
    heat_queens_closed.csv   (for the spreadsheet / statistics.median check)
"""

import csv
import pathlib
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = pathlib.Path(__file__).resolve().parent
CSV = HERE / "nyc-311-2025-november(1).csv.gz"

df = pd.read_csv(CSV, usecols=["Problem (formerly Complaint Type)", "Created Date",
                               "Closed Date", "Status", "Borough", "Agency"],
                 dtype=str, encoding="utf-8", encoding_errors="replace")
h = df[df["Problem (formerly Complaint Type)"] == "HEAT/HOT WATER"].copy()
print(f"HEAT/HOT WATER rows: {len(h):,} | agencies: {h.Agency.unique().tolist()}")
print(f"status counts: {h.Status.value_counts().to_dict()}")

# Same parsing as Task 5. Closed Date is text; parse explicitly, let bad values be NaT.
h["created"] = pd.to_datetime(h["Created Date"], format="%m/%d/%Y %I:%M:%S %p")
h["closed"] = pd.to_datetime(h["Closed Date"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")

# Open-case policy, stated out loud: drop rows with no Closed Date (all 34 are Status=Open).
opens = h["closed"].isna()
print(f"\nDROPPED {int(opens.sum())} open cases (blank Closed Date, Status=Open); "
      f"all other rows are Status=Closed: {(h.Status == 'Closed').sum():,}")
h = h[~opens].copy()
assert len(h) == 47_912

h["hours"] = (h["closed"] - h["created"]).dt.total_seconds() / 3600
print(f"negative durations: {(h.hours < 0).sum()} | "
      f"closed dates after 2025-12-31 (implausible, kept): {(h.closed > '2025-12-31').sum()}")

table = (h.groupby("Borough")["hours"]
           .agg(closed_cases="count", median_hours="median", mean_hours="mean",
                p90_hours=lambda s: s.quantile(0.90))
           .sort_values("median_hours"))
print("\nmedian hours to close, fastest first:")
print(table.round(1).to_string())

city_median = h["hours"].median()
print(f"\ncitywide median: {city_median:.1f} h")

# Sensitivity: the two absurd 2026 Closed Dates sit in Manhattan; do they move its median?
no_typo = h[h.closed <= "2025-12-31"]
print("Manhattan median with both 2026 dates: "
      f"{h.loc[h.Borough == 'MANHATTAN', 'hours'].median():.2f} h | without: "
      f"{no_typo.loc[no_typo.Borough == 'MANHATTAN', 'hours'].median():.2f} h")

# ---------------------------------------------------------------- verification
# Second route: export one borough to CSV, then statistics.median on a plain list.
q = h[h.Borough == "QUEENS"][["Borough", "Created Date", "Closed Date", "hours"]]
q.to_csv(HERE / "heat_queens_closed.csv", index=False, quoting=csv.QUOTE_MINIMAL)
with open(HERE / "heat_queens_closed.csv", newline="") as f:
    plain = [float(row["hours"]) for row in csv.DictReader(f)]
print(f"\nQUEENS: {len(plain):,} rows exported to heat_queens_closed.csv")
print(f"  statistics.median(plain list) = {statistics.median(plain):.6f} h")
print(f"  groupby median                = {table.loc['QUEENS', 'median_hours']:.6f} h")
print(f"  same number: {statistics.median(plain) == table.loc['QUEENS', 'median_hours']}")

# ---------------------------------------------------------------- figure
fig, ax = plt.subplots(figsize=(9.5, 5.6))
order = table.sort_values("median_hours")          # fastest at top
y = range(len(order))
ax.barh(list(y), order.median_hours, color="#3b6ea5", height=0.6)
ax.axvline(city_median, color="#c0392b", linestyle="--", linewidth=1.2)
ax.text(city_median + 0.5, len(order) - 0.62, f"citywide median {city_median:.1f} h",
        color="#c0392b", fontsize=9, va="top")

ax.set_yticks(list(y))
ax.set_yticklabels(order.index)
ax.set_xlim(0, order.median_hours.max() * 1.28)
for i, row in enumerate(order.itertuples()):
    ax.text(row.median_hours + 0.6, i,
            f"{row.median_hours:,.1f} h   (mean {row.mean_hours:.1f}, n={row.closed_cases:,})",
            va="center", fontsize=9,
            bbox=dict(facecolor="white", edgecolor="none", pad=1.2, alpha=.85))
ax.invert_yaxis()

ax.set_xlabel("Median hours from complaint created to closed", labelpad=8)
ax.set_ylabel("Borough", labelpad=8)
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.xaxis.grid(True, alpha=.3)
ax.set_axisbelow(True)

ax.set_title("The same job, five speeds\n"
             "HEAT/HOT WATER cases (HPD), median hours to close, Nov 2025",
             fontsize=14, fontweight="bold", loc="left", pad=14)
fig.text(0.01, 0.032,
         f"Closed cases only; {int(opens.sum())} open cases dropped (no Closed Date). "
         "Bars = median hours; means are shown in parentheses because a handful of cases stayed open for weeks.",
         fontsize=7.5, color="#444")
fig.text(0.01, 0.008,
         "Source: NYC 311 Service Requests, nyc-311-2025-november.csv. "
         "Same complaint type and same agency in every bar, so the gap is not a difference in the work.",
         fontsize=7, color="#777")
fig.tight_layout(rect=[0, 0.055, 1, 1])
fig.savefig(HERE / "fig-same-job.png", dpi=200)
print("\nWrote fig-same-job.png")
