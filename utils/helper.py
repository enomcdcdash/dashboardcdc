import pandas as pd
from utils.data_loader import load_availability_vs_penalty_data

def prepare_penalty_table(df: pd.DataFrame, format_percent: bool = False) -> pd.DataFrame:
    df = df.copy()

    # Ensure date column is datetime
    df["Periode Tagihan (Awal)"] = pd.to_datetime(df["Periode Tagihan (Awal)"], errors="coerce")
    df["Month"] = df["Periode Tagihan (Awal)"].dt.strftime("%B-%Y")

    # Ensure numeric for calculations
    df["Availability"] = pd.to_numeric(df["Availability"], errors="coerce")
    df["Target Availability (%)"] = pd.to_numeric(df["Target Availability (%)"], errors="coerce")

    # Gap Ava
    df["Gap Ava"] = df["Availability"] - df["Target Availability (%)"]

    # Achievement
    df["Achievement"] = df["Gap Ava"].apply(lambda x: "Achieved" if pd.notna(x) and x >= 0 else "Not Achieved")

    # Band classification
    def get_band(row):
        ava = row["Availability"]
        if pd.isna(ava):
            return None
        ava_pct = ava * 100
        cls = str(row.get("Class Site", "")).strip().lower()

        # Diamond & Platinum
        if "diamond" in cls or "platinum" in cls:
            if 99.4 <= ava_pct <= 100:
                return "Ach"
            elif 99.0 <= ava_pct < 99.4:
                return "A"
            elif 98.0 <= ava_pct < 99.0:
                return "B"
            elif 97.0 <= ava_pct < 98.0:
                return "C"
            else:
                return "D"

        # Gold
        if "gold" in cls:
            if 99.0 <= ava_pct <= 100:
                return "Ach"
            elif 98.5 <= ava_pct < 99.0:
                return "E"
            elif 98.0 <= ava_pct < 98.5:
                return "F"
            elif 97.0 <= ava_pct < 98.0:
                return "G"
            else:
                return "H"

        # Silver & Bronze
        if "silver" in cls or "bronze" in cls:
            if 97.5 <= ava_pct <= 100:
                return "Ach"
            elif 97.0 <= ava_pct < 97.5:
                return "I"
            elif 96.5 <= ava_pct < 97.0:
                return "J"
            elif 95.0 <= ava_pct < 96.5:
                return "K"
            else:
                return "L"

        return None

    df["Band"] = df.apply(get_band, axis=1)

    # Prepare for penalty calculation
    df["Month_sort"] = df["Periode Tagihan (Awal)"]
    df["Year"] = df["Month_sort"].dt.year
    df = df.sort_values(["Site Id", "Year", "Month_sort"])

    # Penalty Ke calculation (reset each year)
    def calc_penalty_ke(group):
        penalty_list = []
        counter = 0
        for _, row in group.iterrows():
            if row["Achievement"] == "Achieved":
                counter = 0
            else:
                counter = min(counter + 1, 3)
            penalty_list.append(counter)
        group["Penalty Ke"] = penalty_list
        return group

    df = df.groupby(["Site Id", "Year"], group_keys=False).apply(calc_penalty_ke)

    # Prosentase Penalty mapping
    penalty_map = {
        "A1": 5, "A2": 10, "A3": 15,
        "B1": 10, "B2": 15, "B3": 20,
        "C1": 15, "C2": 20, "C3": 25,
        "D1": 25, "D2": 30, "D3": 35,
        "E1": 5, "E2": 10, "E3": 15,
        "F1": 10, "F2": 15, "F3": 20,
        "G1": 15, "G2": 20, "G3": 25,
        "H1": 25, "H2": 30, "H3": 35,
        "I1": 5, "I2": 10, "I3": 15,
        "J1": 10, "J2": 15, "J3": 20,
        "K1": 15, "K2": 20, "K3": 25,
        "L1": 25, "L2": 30, "L3": 35
    }

    # Combine Band + Penalty Ke into key
    df["Band_PenaltyKe"] = df["Band"].astype(str) + df["Penalty Ke"].astype(str)

    # Map to penalty percentage, default to 0 if not found
    df["Prosentase Penalty"] = (
        df["Band_PenaltyKe"]
        .map(penalty_map)
        .fillna(0)               # replace NaN with 0
        .astype(int)              # ensure integer formatting
        .astype(str) + "%"        # add percentage sign
    )

    # Sort final table
    df = df.sort_values(
        by=["Regional TI", "Site Id", "Year", "Month_sort"],
        ascending=[True, True, True, True]
    )

    # Drop helper cols
    df = df.drop(columns=["Month_sort", "Year", "Band_PenaltyKe"])

    # Format Nilai Penalty as Rupiah
    df["Nilai Penalty"] = df["Nilai Penalty"].apply(lambda x: f"Rp {x:,.0f}".replace(",", "."))

    # Select & reorder
    display_df = df[
        [
            "Month",
            "Regional TI",
            "Site Id",
            "Class Site",
            "Site Name",
            "Target Availability (%)",
            "Availability",
            "Gap Ava",
            "Achievement",
            "Band",
            "Penalty Ke",
            "Prosentase Penalty",
            "Nilai Penalty"
        ]
    ].copy()

    # Optional percentage formatting for only numeric percentage columns
    if format_percent:
        for c in ["Target Availability (%)", "Availability", "Gap Ava"]:
            display_df[c] = (display_df[c] * 100).round(2)

    return display_df


def render_html_table_with_scroll(df, max_height=400):
    # Convert dataframe to HTML manually with special formatting
    header_html = "".join(f"<th>{col}</th>" for col in df.columns)
    rows_html = ""
    for _, row in df.iterrows():
        row_html = ""
        for col, val in zip(df.columns, row):
            cell_val = val
            # Base styles applied to the <td>
            td_style = "font-weight:bold;"

            # Text style inside the cell (optional, can be empty or simple)
            span_style = ""

            # Format Nilai Penalty
            if col == "Nilai Penalty":
                try:
                    num_val = float(str(val).replace("Rp", "").replace(".", "").replace(",", "."))
                except:
                    num_val = 0
                color = "green" if num_val == 0 else "red"
                cell_val = f"Rp {num_val:,.0f}".replace(",", ".")
                span_style = f"color:{color}; font-size:14px; font-weight:bold;"

            # Format Gap Ava background color on <td>
            elif col == "Gap Ava":
                try:
                    gap_val = float(str(val).replace("%", "").strip())
                except:
                    gap_val = 0

                if gap_val >= 0:
                    td_style += "background-color:#d4edda; color:#155724;"  # light green bg, dark green text
                else:
                    td_style += "background-color:#f8d7da; color:#721c24;"  # light red bg, dark red text

            # Compose the cell HTML
            if span_style:
                cell_html = f'<span style="{span_style}">{cell_val}</span>'
            else:
                cell_html = str(cell_val)

            row_html += f'<td style="{td_style}">{cell_html}</td>'

        rows_html += f"<tr>{row_html}</tr>"

    table_html = f"""
    <div class="scroll-table">
        <table>
            <thead>
                <tr>{header_html}</tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    """

    # CSS styling
    style = f"""
    <style>
    .scroll-table {{
        max-height: {max_height}px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 8px;
        background-color: #fff;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        font-size: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .scroll-table table {{
        width: 100%;
        border-collapse: collapse;
    }}
    .scroll-table thead th {{
        position: sticky;
        top: 0;
        background-color: #4a90e2;
        color: white;
        font-weight: 600;
        padding: 8px;
        text-align: center;
    }}
    .scroll-table tbody td {{
        padding: 8px;
        text-align: center;
        border-bottom: 1px solid #ddd;
    }}
    .scroll-table tbody tr:nth-child(even) {{
        background-color: #f9f9f9;
    }}
    .scroll-table tbody tr:hover {{
        background-color: #e6f3ff;
    }}
    </style>
    """

    return style + table_html
