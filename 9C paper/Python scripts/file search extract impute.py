# Script to:
# - Read all FR Y-9C CSVs in a directory
# - Extract a specific MDRM's value per quarter
# - Build a monthly time series with linear interpolation
# - Mark original quarter data vs imputed values

import os
import pandas as pd

# -------- CONFIGURE THESE --------
data_dir = "C:\\Venkat\\learning\\9C-Paper\\9C paper\\MT csv\\"   # change this
target_mdrm = "BHDM1766"                  # MDRM you care about
date_col = "Report Date"                  # column that holds the report date label
value_col = "Value"                       # the numeric value column, adjust to your schema
mdrm_col = "ItemName"                         # MDRM code column (e.g. BHCK0081/BHCK0395)
desc_col = "Description"                  # MDRM description column
# ---------------------------------

# Collect per-quarter data for the target MDRM
records = []

for fname in os.listdir(data_dir):
    fpath = os.path.join(data_dir, fname)
    if not fname.lower().endswith(".csv"):
        continue

    try:
        df = pd.read_csv(fpath, dtype=str)
    except Exception as e:
        print("Skipping file (load error):", fname, e)
        continue

    # Try a few common header variants if needed
    cols_lower = {c.lower(): c for c in df.columns}
    mdrm_c = cols_lower.get(mdrm_col.lower(), mdrm_col)
    desc_c = cols_lower.get(desc_col.lower(), desc_col)

    # Find the numeric report date in the file (e.g. 20200930)
    # Often it is a row where MDRM or description equals "Report Date"
    # or a line with ID_RSSD, etc. Here we try a generic approach:
    report_date_value = None
    # If there is an explicit column for report date, use it
    if date_col in df.columns:
        # assume a single value in that column
        report_date_value = df[date_col].dropna().astype(str).iloc[0]
    else:
        # search rows whose MDRM or description looks like a report date key
        mask_report = df[mdrm_c].str.contains("report date", case=False, na=False) | \
                      df[desc_c].str.contains("report date", case=False, na=False)
        if mask_report.any():
            # assume the value is in the "Value" column if present, else third column
            val_c = value_col if value_col in df.columns else df.columns[-1]
            report_date_value = df.loc[mask_report, val_c].dropna().astype(str).iloc[0]
        else:
            # fallback: try to parse anything that looks like YYYYMMDD in whole file
            for col in df.columns:
                for v in df[col].dropna().astype(str):
                    if len(v) == 8 and v.isdigit():
                        report_date_value = v
                        break
                if report_date_value is not None:
                    break

    if report_date_value is None:
        print("Could not determine report date for", fname, "- skipping")
        continue

    # Parse report date to a proper datetime (YYYYMMDD)
    try:
        report_date = pd.to_datetime(report_date_value, format="%Y%m%d")
    except Exception:
        # Try to parse flexibly
        report_date = pd.to_datetime(report_date_value, errors="coerce")
    if pd.isna(report_date):
        print("Invalid report date in", fname, "value:", report_date_value)
        continue

    # Filter to the target MDRM
    mdrm_mask = df[mdrm_c].astype(str).str.strip().eq(target_mdrm)
    if not mdrm_mask.any():
        # No such MDRM in this file
        continue

    row = df.loc[mdrm_mask].iloc[0]

    desc_val = row[desc_c]

    # Determine which column is numeric value
    if value_col in df.columns:
        val_raw = row[value_col]
    else:
        # fallback: last column in the file
        val_raw = row.iloc[-1]

    # Convert to numeric
    val_num = pd.to_numeric(str(val_raw).replace(",", ""), errors="coerce")
    if pd.isna(val_num):
        print("Non-numeric value for", target_mdrm, "in", fname, ":", val_raw)
        continue

    records.append({
        "Period": report_date,
        "MDRM Name": target_mdrm,
        "MDRM Description": desc_val,
        "Value": val_num,
        "Remark": "Quarterly data"
    })

# Build quarterly DataFrame
if not records:
    raise ValueError("No records found for MDRM " + target_mdrm)

quarter_df = pd.DataFrame(records).sort_values("Period").reset_index(drop=True)

print("Quarterly data head:")
print(quarter_df.head())

# Now construct a monthly date index from min to max quarter dates (end of month)
start = quarter_df["Period"].min()
end = quarter_df["Period"].max()

# We want monthly end dates
monthly_index = pd.date_range(start=start, end=end, freq="M")

# Reindex to monthly, using Period as index
ts = quarter_df.set_index("Period")["Value"]
ts_monthly = ts.reindex(monthly_index)

# Linear interpolation for missing months
ts_interp = ts_monthly.interpolate(method="linear")

# Build final DataFrame
final = pd.DataFrame({
    "Period": ts_interp.index,
    "MDRM Name": target_mdrm,
    "MDRM Description": quarter_df["MDRM Description"].iloc[0],  # assume fixed description
    "Value": ts_interp.values
})

# Mark remarks: if date is one of the original quarter-end dates -> Quarterly data, else Imputed
original_dates = set(quarter_df["Period"])
final["Remark"] = final["Period"].apply(
    lambda d: "Quarterly data" if d in original_dates else "Imputed"
)

# Format Period as YYYY-MM-DD string
final["Period"] = final["Period"].dt.strftime("%Y-%m-%d")

print("\nFinal monthly series head:")
print(final.head(12))

# Optionally save to CSV
out_path = os.path.join(data_dir, "mdrm_" + target_mdrm + "_monthly_imputed.csv")
final.to_csv(out_path, index=False)
print("\nSaved output to:", out_path)