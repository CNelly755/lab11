"""Answers to the lab11 questions about the NYC 311 November 2025 file.

Run:  python3 lab11_answers.py
"""

import pandas as pd

FILE = "nyc-311-2025-november(1).csv.gz"
READ = dict(compression="gzip", encoding="utf-8", encoding_errors="replace")
COLS = ["Problem (formerly Complaint Type)", "Created Date", "Closed Date", "Status"]

# Total width from the header alone; then load just the columns we need.
n_cols = pd.read_csv(FILE, nrows=0, **READ).shape[1]
df = pd.read_csv(FILE, usecols=COLS, dtype=str, **READ)

print(f"Rows: {len(df):,}")
print(f"Columns: {n_cols:,}")
print(f"Distinct Problem values: {df[COLS[0]].nunique():,}")

created = pd.to_datetime(df["Created Date"], format="%m/%d/%Y %I:%M:%S %p")
print(f"Earliest Created Date: {created.min():%Y-%m-%d %H:%M:%S}")
print(f"Latest Created Date:   {created.max():%Y-%m-%d %H:%M:%S}")

no_closed = df["Closed Date"].isna()
print(f"Rows with no Closed Date: {int(no_closed.sum()):,}")
print("Status values among those rows:")
print(df.loc[no_closed, "Status"].value_counts(dropna=False).to_string())
