"""
Topic: BIOSENS Dashboard
Lasted Edited By: Elinor Hunt
Date Last Edited: 11/12/2026

Run: streamlit run BIOSENS_Dashboard.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st


st.set_page_config(page_title="BIOSENS | Skills landscape", page_icon="🧬", layout="wide")

DATA_FILE = Path(__file__).resolve().parent / "BIOSENS Skills Data.xlsx"

st.markdown(
    """<style>
    .block-container {padding-top:2rem;max-width:1450px}
    h1 {letter-spacing:-.04em}
    div[data-testid="stMetric"] {background:white;border:1px solid #e3ebe9;
        border-radius:12px;padding:16px}
    div[data-testid="stMetricValue"] {color:#0d766e}
    .skill {display:flex;justify-content:space-between;align-items:center;gap:12px;
        padding:9px 12px;border-bottom:1px solid #edf2ef;font-size:14px}
    .skill-index {color:#93a4a0;min-width:25px}
    .skill-name {flex:1}
    .skill-state {font-size:12px;font-weight:650;white-space:nowrap}
    .shared {color:#137a6d}.entered {color:#b76b30}.departed {color:#627ba4}
    </style>""",
    unsafe_allow_html=True,
)


def read_data(file):
    """Keep all source positions; normalize only outer whitespace in names."""
    df = pd.read_excel(file, sheet_name="Skills Data")
    df.columns = [str(c).strip() for c in df.columns]
    required = ["Region", "Year", "NAICS", "Industry"]
    skill_columns = [f"Skill {i}" for i in range(1, 11)]
    missing = [c for c in required + skill_columns if c not in df.columns]
    if missing:
        raise ValueError("Missing columns: " + ", ".join(missing))
    df = df.dropna(subset=required).copy()
    for col in ("Region", "Industry"):
        df[col] = df[col].astype(str).str.strip()
    df["NAICS"] = df["NAICS"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["Year"] = pd.to_numeric(df["Year"], errors="raise").astype(int)
    for col in skill_columns:
        df[col] = df[col].map(lambda v: str(v).strip() if pd.notna(v) else "")
    if df.duplicated(["Region", "NAICS", "Year"]).any():
        raise ValueError("Each region, NAICS industry, and year must have only one row.")
    return df, skill_columns


def names(row, columns):
    return [row[c] for c in columns if row[c]]


def skill_list(skills, other, year):
    from html import escape

    for position, skill in enumerate(skills, start=1):
        if skill in other:
            label, style = "In both", "shared"
        elif year == 2025:
            label, style = "Entered", "entered"
        else:
            label, style = "Departed", "departed"
        st.markdown(
            f'<div class="skill"><span class="skill-index">{position:02d}</span>'
            f'<span class="skill-name">{escape(skill)}</span>'
            f'<span class="skill-state {style}">{label}</span></div>',
            unsafe_allow_html=True,
        )
    if not skills:
        st.info("No skills listed for this year.")


st.title("Biotechnology Skills Landscape")
st.caption("Compare in-demand skills across time · 2019 vs 2025")
if not DATA_FILE.exists():
    st.error(f"Excel file not found: {DATA_FILE.name}")
    st.info(
        "Put BIOSENS Skills Data(1).xlsx in the same folder as this Python file, "
        "then refresh the app. The filenames must match exactly."
    )
    st.stop()

try:
    df, skill_cols = read_data(DATA_FILE)
except (ValueError, KeyError, OSError) as exc:
    st.error(f"Could not read the workbook: {exc}")
    st.stop()

years = sorted(df["Year"].unique().tolist())
if years != [2019, 2025]:
    st.error(f"Expected years 2019 and 2025; found {years}.")
    st.stop()

regions = df["Region"].drop_duplicates().tolist()
industries = df[["NAICS", "Industry"]].drop_duplicates().sort_values("Industry")
industry_names = dict(zip(industries["NAICS"], industries["Industry"]))
lookup = {
    (row["Region"], row["NAICS"], row["Year"]): names(row, skill_cols)
    for row in df.to_dict("records")
}


def comparison(region, naics):
    a = lookup.get((region, naics, 2019), [])
    b = lookup.get((region, naics, 2025), [])
    shared = len(set(a) & set(b))
    return a, b, shared


compare_tab, overview_tab = st.tabs(
    ["Industry comparison", "Change overview"]
)

with compare_tab:
    c1, c2 = st.columns([1, 2.4])
    with c1:
        region = st.selectbox("Geography", regions, index=regions.index("Maine") if "Maine" in regions else 0)
    with c2:
        code_options = industries["NAICS"].tolist()
        naics = st.selectbox(
            "Industry", code_options,
            format_func=lambda code: f"{industry_names[code]} · {code}",
            index=code_options.index("334516") if "334516" in code_options else 0,
        )
    earlier, later, common = comparison(region, naics)
    st.subheader(industry_names[naics])
    st.caption(f"NAICS {naics} · {region}")
    a, b, c = st.columns(3)
    a.metric("In both years", common)
    b.metric("In 2025 only", len(set(later) - set(earlier)))
    c.metric("In 2019 only", len(set(earlier) - set(later)))
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown(f"### 2019 · {len(earlier)} listed")
        skill_list(earlier, later, 2019)
    with right:
        st.markdown(f"### 2025 · {len(later)} listed")
        skill_list(later, earlier, 2025)

with overview_tab:
    st.subheader("Where did lists change most?")
    st.caption(
        "Each cell shows how many skill names appear in both years for that industry and geography. "
        "LOWER NUMBERS mean GREATER CHANGE in list membership."
    )
    matrix_rows = []
    for code, industry in industries.itertuples(index=False, name=None):
        entry = {"Industry · NAICS": f"{industry} · {code}"}
        for place in regions:
            entry[place] = comparison(place, code)[2]
        matrix_rows.append(entry)
    matrix = pd.DataFrame(matrix_rows).set_index("Industry · NAICS")
    st.dataframe(
        matrix.style.background_gradient(cmap="GnBu", vmin=0, vmax=10).format("{:.0f}"),
        use_container_width=True,
        height=700,
    )
    st.caption("Tip: use the Industry comparison tab to see the specific skills behind a cell.")

# with explorer_tab:
#     st.subheader("Where does a skill appear?")
#     st.caption("Search skill names exactly as written in the workbook; similar labels remain separate.")
#     all_skills = sorted({s for values in lookup.values() for s in values}, key=str.casefold)
#     default = all_skills.index("Biology") if "Biology" in all_skills else 0
#     chosen = st.selectbox("Find a skill", all_skills, index=default)
#     occurrences = df[df[skill_cols].eq(chosen).any(axis=1)].copy()
#     cards = st.columns(len(regions))
#     for col, place in zip(cards, regions):
#         subset = occurrences[occurrences["Region"] == place]
#         current = (subset["Year"] == 2025).sum()
#         past = (subset["Year"] == 2019).sum()
#         with col:
#             st.metric(place, f"{current} / {len(industries)}")
#             st.caption(f"2025 industries · {past} in 2019")
#     st.markdown(f"**{len(occurrences)} lists containing “{chosen}”**")
#     st.dataframe(
#         occurrences[["Industry", "Region", "Year", "NAICS"]]
#         .sort_values(["Industry", "Region", "Year"])
#         .reset_index(drop=True),
#         hide_index=True,
#         use_container_width=True,
#     )

