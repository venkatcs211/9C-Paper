import marimo

__generated_with = "0.17.7"
app = marimo.App(width="medium")


@app.cell
def _(mo):
    mo.md(r"""
    ## Script to extract Quarterly values of FR Y-9C and impute values in between for month ends
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    Imports below

    **Purpose** copy pasted from Julius AI

    Script to:
    1. Read all FR Y-9C CSVs in a directory
    1. Extract a specific MDRM's value per quarter
    1. Build a monthly time series with linear interpolation
    1.  Mark original quarter data vs imputed values
    """)
    return


@app.cell
def _():
    import marimo as mo
    import os
    import pandas as pd
    from pathlib import Path
    return Path, mo, os, pd


@app.cell
def _(mo):
    mo.md(r"""
    Script copy pasted from Julius AI
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    The following variables will have to be configured

    1. data_dir - The path where all the files are in
    1. target_mdrm - The MDRM for which values are to be extracted and values imputed as well
    """)
    return


@app.cell
def _(Path, mo):
    # --- 1. UI Element (The browser) ---
    file_browser = mo.ui.file_browser(
        initial_path=Path("."),
        multiple=False
    )
    return (file_browser,)


@app.cell
def _(mo):
    mo.md(r"""
    Displaying folder below to ensure separation between creation code cell and display code cell
    """)
    return


@app.cell
def _(Path, file_browser):
    # --- 2. Reactive Logic ---
    # This block runs every time file_browser.path changes
    selected_path_value = str(file_browser.path)

    final_folder_path = None
    if selected_path_value:
        p = Path(selected_path_value) # Ensure we are working with a Path object
        if p.is_dir():
            final_folder_path = p
        else:
            final_folder_path = p.parent
    return (final_folder_path,)


@app.cell
def _(mo):
    # --- 3. Output area for button actions ---
    output_area = mo.md("")
    return (output_area,)


@app.cell
def _(final_folder_path, output_area):
    # --- 4. Button Action Handler ---
    def handle_button_click(v):
        # This function captures the value of final_folder_path when clicked
        if final_folder_path:
            output_area.md(
                f'<div style="padding: 10px; background-color: #e0ffe0; border: 1px solid green;">'
                f'✅ **Action performed** on folder: <code>{final_folder_path}</code>'
                f'</div>'
            )
        else:
             output_area.md('<div style="padding: 10px; background-color: #ffe0e0;">❌ Error: No folder selected.</div>')
    return (handle_button_click,)


@app.cell
def _(final_folder_path, handle_button_click, mo):
    # --- 5. Button Definition ---

    # The button label dynamically updates
    button_label = f"Process Folder: {final_folder_path.name if final_folder_path else 'None Selected'}"

    process_button = mo.ui.button(
        label=button_label,
        on_click=handle_button_click,
        kind="primary",
        disabled=final_folder_path is None # Disable if nothing is selected
    )
    return (process_button,)


@app.cell
def _(file_browser, final_folder_path, mo, output_area, process_button):
    # --- 6. Layout all the UI elements ---
    mo.vstack([
        mo.md("## Select a Folder to Process"),
        file_browser,
        mo.md(f"**Currently Selected Path:** `{final_folder_path}`"),
        process_button,
        mo.md("---"),
        output_area # This is where the button output goes
    ])
    return


@app.cell
def _(os, pd):

    # -------- CONFIGURE THESE --------
    data_dir = "/path/to/your/fry9c/folder"   # change this
    target_mdrm = "BHCK0081"                  # MDRM you care about
    date_col = "Report Date"                  # column that holds the report date label
    value_col = "Value"                       # the numeric value column, adjust to your schema
    mdrm_col = "MDRM"                         # MDRM code column (e.g. BHCK0081/BHCK0395)
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
    return


if __name__ == "__main__":
    app.run()
