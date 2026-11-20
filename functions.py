"""Pemrosesan data, KPI, agregasi, insight otomatis, dan helper chart.

Semua fungsi menerima DataFrame yang SUDAH difilter (kecuali load_data dan
validate_schema), sehingga KPI, chart, insight, dan download selalu konsisten.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- #
# Konstanta
# --------------------------------------------------------------------------- #
NAVY, BG, CARD = "#14283F", "#F5F7FA", "#FFFFFF"
SLATE, LOW, MEDIUM, HIGH, TEXT = "#8495AA", "#D94B61", "#E6AE45", "#269B83", "#243B53"
FONT = "Inter, Manrope, sans-serif"
CATEGORY_COLORS = {"Low": LOW, "Medium": MEDIUM, "High": HIGH}
MIN_N = 30  # di bawah ini sampel dianggap kecil

ORDERS: dict[str, list] = {
    "WLB_Category": ["Low", "Medium", "High"],
    "JobSatisfaction_Category": ["Low", "Medium", "High"],
    "EnvironmentSatisfaction_Category": ["Low", "Medium", "High"],
    "Age_Group": ["18-25", "26-35", "36-45", "46+"],
    "Income_Group": ["Q1 - Lower", "Q2 - Lower Middle", "Q3 - Upper Middle", "Q4 - Upper"],
    "Tenure_Group": ["0-2 years", "3-5 years", "6-10 years", "10+ years"],
    "Department": ["Research & Development", "Sales", "Human Resources"],
    "OverTime": ["No", "Yes"],
    "Gender": ["Female", "Male"],
    "JobLevel": [1, 2, 3, 4, 5],
}

REQUIRED_COLUMNS = [
    "EmployeeNumber", "Attrition", "Department", "Gender", "JobLevel", "OverTime",
    "WorkLifeBalance", "JobSatisfaction", "EnvironmentSatisfaction",
    "WLB_Category", "JobSatisfaction_Category", "EnvironmentSatisfaction_Category",
    "Age_Group", "Income_Group", "Tenure_Group",
]
# Field numerik yang sebenarnya ordinal/kategorikal.
ORDINAL_COLUMNS = ["JobLevel", "WorkLifeBalance", "JobSatisfaction", "EnvironmentSatisfaction"]
FILTER_COLUMNS = {
    "Department": "Department", "JobLevel": "Job Level", "Gender": "Gender",
    "Age_Group": "Age Group", "OverTime": "OverTime", "Income_Group": "Income Group",
    "Tenure_Group": "Tenure Group", "WLB_Category": "WLB Category",
}


class DataValidationError(Exception):
    """Dataset tidak ditemukan atau tidak memenuhi skema minimum."""


# --------------------------------------------------------------------------- #
# Format
# --------------------------------------------------------------------------- #
def fmt_int(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{int(x):,}"


def fmt_pct(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.2f}%"


def fmt_score(x) -> str:
    return "–" if x is None or pd.isna(x) else f"{x:.2f}"


def fmt_label(v) -> str:
    if isinstance(v, tuple):
        return " | ".join(fmt_label(i) for i in v)
    if isinstance(v, (int, np.integer)):
        return f"Level {int(v)}"
    return str(v)


def safe_div(num, den) -> float:
    return float(num) / float(den) if den else np.nan


# --------------------------------------------------------------------------- #
# Loading & validasi
# --------------------------------------------------------------------------- #
def validate_schema(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(
            "Kolom wajib tidak ditemukan di dataset: " + ", ".join(missing)
        )


@st.cache_data(show_spinner=False)
def load_data(path: str, mtime: float = 0.0) -> tuple[pd.DataFrame, list[str]]:
    """Load CSV sekali (di-cache). `mtime` memaksa reload jika file berubah."""
    p = Path(path)
    if not p.exists():
        raise DataValidationError(f"File dataset tidak ditemukan: {p}")
    df = pd.read_csv(p)
    validate_schema(df)
    notes: list[str] = []

    for col in ORDINAL_COLUMNS:
        before = df[col].isna().sum()
        num = pd.to_numeric(df[col], errors="coerce")
        invalid = int(num.isna().sum() - before)
        if invalid:
            notes.append(f"{invalid} nilai tidak valid pada {col} dikonversi menjadi NULL.")
        if ((num.dropna() % 1) != 0).any():
            notes.append(f"{col} berisi nilai non-integer; tipe float dipertahankan.")
            df[col] = num
        else:
            df[col] = num.astype("Int64")  # float 3.0 -> 3 (nilai tidak berubah)

    for col, allowed in (("Attrition", {"Yes", "No"}), ("OverTime", {"Yes", "No"})):
        bad = int((~df[col].isin(allowed)).sum())
        if bad:
            notes.append(f"{bad} baris {col} bernilai di luar Yes/No (tetap dipertahankan).")
    return df, notes


def data_quality(df: pd.DataFrame) -> dict:
    return {
        "rows": len(df),
        "columns": df.shape[1],
        "missing_total": int(df.isna().sum().sum()),
        "duplicate_employee": int(df["EmployeeNumber"].duplicated().sum()),
    }


def column_options(df: pd.DataFrame, col: str) -> list:
    vals = list(df[col].dropna().unique())
    known = [v for v in ORDERS.get(col, []) if v in vals]
    return known + sorted((v for v in vals if v not in known), key=str)


def ordered_categories(df: pd.DataFrame, col: str) -> list:
    """Urutan kategori baku + kategori tak dikenal agar tidak hilang diam-diam."""
    base = list(ORDERS.get(col, []))
    extra = [v for v in df[col].dropna().unique() if v not in base]
    return base + sorted(extra, key=str)


# --------------------------------------------------------------------------- #
# Filtering
# --------------------------------------------------------------------------- #
def apply_filters(df: pd.DataFrame, selections: dict, options: dict) -> pd.DataFrame:
    """Terapkan filter gabungan. Filter yang memilih semua opsi dilewati
    sehingga baris dengan NULL tidak terbuang saat kondisi default (All)."""
    mask = pd.Series(True, index=df.index)
    for col, sel in selections.items():
        if sel is None or set(sel) == set(options[col]):
            continue
        mask &= df[col].isin(sel)
    return df[mask]


def filter_context(selections: dict, options: dict) -> str:
    parts = []
    for col, label in FILTER_COLUMNS.items():
        sel = selections.get(col)
        if sel is None or set(sel) == set(options[col]):
            continue
        shown = ", ".join(fmt_label(v) if col == "JobLevel" else str(v) for v in sel) or "(kosong)"
        parts.append(f"{label}: {shown}")
    return "; ".join(parts) if parts else "All (tanpa filter)"


# --------------------------------------------------------------------------- #
# KPI & agregasi
# --------------------------------------------------------------------------- #
def _uniq(df: pd.DataFrame, mask: pd.Series | None = None) -> int:
    return int((df if mask is None else df[mask])["EmployeeNumber"].nunique())


def compute_kpis(df: pd.DataFrame) -> dict:
    n = _uniq(df)
    low = _uniq(df, df["WLB_Category"] == "Low")
    attr = _uniq(df, df["Attrition"] == "Yes")
    ot = _uniq(df, df["OverTime"] == "Yes")
    return {
        "total_employees": n,
        "avg_wlb": df["WorkLifeBalance"].mean() if n else np.nan,
        "low_wlb_count": low,
        "low_wlb_pct": safe_div(low, n) * 100,
        "attrition_count": attr,
        "attrition_rate": safe_div(attr, n) * 100,
        "overtime_count": ot,
        "overtime_pct": safe_div(ot, n) * 100,
        "avg_job_sat": df["JobSatisfaction"].mean() if n else np.nan,
        "avg_env_sat": df["EnvironmentSatisfaction"].mean() if n else np.nan,
    }


def attrition_flag(df: pd.DataFrame) -> pd.Series:
    return df["Attrition"] == "Yes"


def low_wlb_flag(df: pd.DataFrame) -> pd.Series:
    return df["WLB_Category"] == "Low"


def rate_table(df: pd.DataFrame, by, flag: pd.Series, order=None) -> pd.DataFrame:
    """Employees, Events (karyawan unik dengan flag True), Rate (%) per grup.
    Kategori tanpa observasi tetap ditampilkan (Employees = 0, Rate = NaN)."""
    keys = by if isinstance(by, list) else [by]
    tmp = df[keys].copy()
    tmp["EmployeeNumber"] = df["EmployeeNumber"]
    tmp["_f"] = flag.reindex(df.index).fillna(False).astype(bool)
    emp = tmp.groupby(keys, observed=True)["EmployeeNumber"].nunique()
    ev = tmp[tmp["_f"]].groupby(keys, observed=True)["EmployeeNumber"].nunique()
    out = pd.DataFrame({"Employees": emp, "Events": ev})
    if order is not None:
        out = out.reindex(order)
    out = out.fillna(0).astype({"Employees": int, "Events": int})
    out["Rate"] = np.where(
        out["Employees"] > 0, out["Events"] / out["Employees"].replace(0, np.nan) * 100, np.nan
    )
    return out


def mean_table(df: pd.DataFrame, by: str, value: str, order=None) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    out = pd.DataFrame({"Employees": g["EmployeeNumber"].nunique(), "Mean": g[value].mean()})
    if order is not None:
        out = out.reindex(order)
    out["Employees"] = out["Employees"].fillna(0).astype(int)
    return out


def composition(df: pd.DataFrame, by: str, cat: str):
    """Komposisi % kategori `cat` di dalam setiap grup `by` (tiap baris = 100%)."""
    by_order, cat_order = ordered_categories(df, by), ordered_categories(df, cat)
    ct = pd.crosstab(df[by], df[cat]).reindex(index=by_order, columns=cat_order, fill_value=0)
    n = ct.sum(axis=1)
    pct = ct.div(n.replace(0, np.nan), axis=0) * 100
    return pct, ct, n


def rate_matrix(df: pd.DataFrame, row: str, col: str, flag: pd.Series):
    rows, cols = ordered_categories(df, row), ordered_categories(df, col)
    idx = pd.MultiIndex.from_product([rows, cols])
    t = rate_table(df, [row, col], flag, order=idx)
    return tuple(t[k].unstack().reindex(index=rows, columns=cols) for k in ("Rate", "Employees", "Events"))


# --------------------------------------------------------------------------- #
# Insight otomatis
# --------------------------------------------------------------------------- #
def _insight(text: str, warn: bool = False) -> dict:
    return {"text": text, "warn": bool(warn)}


def _extreme(tbl: pd.DataFrame, col: str, kind: str):
    t = tbl[(tbl["Employees"] > 0) & tbl[col].notna()]
    if len(t) < 2:
        return None, t
    target = t[col].max() if kind == "max" else t[col].min()
    return t[t[col].round(2) == round(float(target), 2)], t


def _extreme_insight(tbl, what, kind="max", event_noun="karyawan", col="Rate", vfmt=fmt_pct, count_note=False):
    top, t = _extreme(tbl, col, kind)
    if top is None:
        return _insight(
            f"{what}: perbandingan tidak tersedia karena hanya ada satu kelompok dengan data pada filter saat ini."
        )
    word = "tertinggi" if kind == "max" else "terendah"
    names = " dan ".join(fmt_label(i) for i in top.index)
    val = vfmt(top[col].iloc[0])
    sizes = "; ".join(
        f"{fmt_label(i)}: n = {fmt_int(r.Employees)}"
        + (f", {fmt_int(r.Events)} {event_noun}" if "Events" in tbl else "")
        for i, r in top.iterrows()
    )
    tie = " (seri)" if len(top) > 1 else ""
    text = f"{what} {word}: {names}{tie} sebesar {val} ({sizes})."
    small = bool((top["Employees"] < MIN_N).any())
    if count_note and "Events" in tbl and t["Events"].max() > 0:
        big = t[t["Events"] == t["Events"].max()]
        if set(big.index) != set(top.index):
            text += (
                f" Jumlah terbesar (bukan rate) ada di {' dan '.join(fmt_label(i) for i in big.index)} "
                f"dengan {fmt_int(big['Events'].iloc[0])} {event_noun}."
            )
    if small:
        text += f" ⚠ Ukuran sampel kecil (n < {MIN_N}); interpretasikan dengan hati-hati."
    return _insight(text, small)


def wlb_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    low = low_wlb_flag(df)
    dept_low = rate_table(df, "Department", low, ordered_categories(df, "Department"))
    dept_mean = mean_table(df, "Department", "WorkLifeBalance", ordered_categories(df, "Department"))
    lvl_low = rate_table(df, "JobLevel", low, ordered_categories(df, "JobLevel"))
    combo = rate_table(df, ["Department", "JobLevel"], low)
    return [
        _extreme_insight(dept_mean, "Department dengan rata-rata WLB", "min", col="Mean", vfmt=fmt_score),
        _extreme_insight(dept_low, "Department dengan Low WLB rate", "max", "Low WLB", count_note=True),
        _extreme_insight(lvl_low, "Job Level dengan Low WLB rate", "max", "Low WLB", count_note=True),
        _extreme_insight(combo, "Kombinasi Department | Job Level dengan Low WLB rate", "max", "Low WLB", count_note=True),
    ]


def overtime_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    order = ordered_categories(df, "OverTime")
    t = rate_table(df, "OverTime", attrition_flag(df), order)
    m = mean_table(df, "OverTime", "WorkLifeBalance", order)
    if not {"Yes", "No"} <= set(t.index) or (t.loc[["Yes", "No"], "Employees"] == 0).any():
        have = " dan ".join(str(i) for i in t.index[t["Employees"] > 0])
        return [_insight(f"Perbandingan overtime vs non-overtime tidak tersedia: filter saat ini hanya memuat OverTime = {have}.")]
    y, n = t.loc["Yes"], t.loc["No"]
    out = [
        _insight(f"Attrition rate karyawan overtime {fmt_pct(y.Rate)} (n = {fmt_int(y.Employees)}; {fmt_int(y.Events)} attrition).", y.Employees < MIN_N),
        _insight(f"Attrition rate karyawan non-overtime {fmt_pct(n.Rate)} (n = {fmt_int(n.Employees)}; {fmt_int(n.Events)} attrition).", n.Employees < MIN_N),
    ]
    ratio = f"; rasio {y.Rate / n.Rate:.2f}×" if n.Rate > 0 else "; rasio tidak dapat dihitung karena rate non-overtime = 0"
    out.append(_insight(
        f"Selisih attrition rate overtime terhadap non-overtime: {y.Rate - n.Rate:+.2f} percentage points{ratio}. "
        "Ini perbedaan deskriptif, bukan bukti sebab-akibat.",
        min(y.Employees, n.Employees) < MIN_N,
    ))
    out.append(_insight(
        f"Rata-rata WLB overtime {fmt_score(m.loc['Yes', 'Mean'])} vs non-overtime {fmt_score(m.loc['No', 'Mean'])} "
        f"(selisih {m.loc['Yes', 'Mean'] - m.loc['No', 'Mean']:+.2f} poin pada skala 1–4)."
    ))
    return out


def satisfaction_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    a = attrition_flag(df)
    jc, ec = "JobSatisfaction_Category", "EnvironmentSatisfaction_Category"
    job = rate_table(df, jc, a, ordered_categories(df, jc))
    env = rate_table(df, ec, a, ordered_categories(df, ec))
    combo = rate_table(df, [ec, jc], a)
    combo.index = pd.MultiIndex.from_tuples([(f"Env {e}", f"Job {j}") for e, j in combo.index])
    return [
        _extreme_insight(job, "Kategori Job Satisfaction dengan attrition rate", "max", "attrition", count_note=True),
        _extreme_insight(env, "Kategori Environment Satisfaction dengan attrition rate", "max", "attrition", count_note=True),
        _extreme_insight(combo, "Kombinasi kepuasan (Environment | Job) dengan attrition rate", "max", "attrition", count_note=True),
    ]


def attrition_insights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    a = attrition_flag(df)
    out = []
    for col, what in (("Department", "Department"), ("Age_Group", "Age Group"),
                      ("Income_Group", "Income Group"), ("Tenure_Group", "Tenure Group")):
        out.append(_extreme_insight(rate_table(df, col, a, ordered_categories(df, col)),
                                    f"{what} dengan attrition rate", "max", "attrition", count_note=True))
    return out


def overview_highlights(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    k = compute_kpis(df)
    out = [_insight(
        f"{fmt_pct(k['low_wlb_pct'])} karyawan berada pada kategori Low WLB "
        f"({fmt_int(k['low_wlb_count'])} dari {fmt_int(k['total_employees'])})."
    )]
    out.append(_extreme_insight(
        rate_table(df, "Department", attrition_flag(df), ordered_categories(df, "Department")),
        "Department dengan attrition rate", "max", "attrition", count_note=True))
    order = ordered_categories(df, "OverTime")
    m = mean_table(df, "OverTime", "WorkLifeBalance", order)
    if {"Yes", "No"} <= set(m.index) and (m.loc[["Yes", "No"], "Employees"] > 0).all():
        out.append(_insight(
            f"Rata-rata WLB karyawan overtime {fmt_score(m.loc['Yes', 'Mean'])} vs "
            f"{fmt_score(m.loc['No', 'Mean'])} pada non-overtime "
            f"(selisih {m.loc['Yes', 'Mean'] - m.loc['No', 'Mean']:+.2f} poin)."))
    else:
        out.append(_insight("Perbandingan rata-rata WLB overtime vs non-overtime tidak tersedia pada filter saat ini."))
    return out


# --------------------------------------------------------------------------- #
# Insight summary untuk download
# --------------------------------------------------------------------------- #
def build_insight_summary(df: pd.DataFrame, context: str) -> pd.DataFrame:
    rows: list[dict] = []

    def add(metric, category, value, unit, emp, ev=None):
        rows.append({
            "Metric": metric, "Category": category,
            "Value": None if value is None or pd.isna(value) else round(float(value), 2),
            "Unit": unit, "Employee Count": int(emp),
            "Attrition Count": None if ev is None else int(ev), "Filter Context": context,
        })

    k = compute_kpis(df)
    n, ac = k["total_employees"], k["attrition_count"]
    add("Total Employees", "Overall", n, "employees", n, ac)
    add("Average WLB", "Overall", k["avg_wlb"], "score 1-4", n, ac)
    add("Low WLB Percentage", "Overall", k["low_wlb_pct"], "%", n, ac)
    add("Attrition Rate", "Overall", k["attrition_rate"], "%", n, ac)
    add("Overtime Percentage", "Overall", k["overtime_pct"], "%", n, ac)
    add("Average Job Satisfaction", "Overall", k["avg_job_sat"], "score 1-4", n, ac)
    add("Average Environment Satisfaction", "Overall", k["avg_env_sat"], "score 1-4", n, ac)
    if df.empty:
        return pd.DataFrame(rows)

    a, lo = attrition_flag(df), low_wlb_flag(df)

    def lab(col, idx):
        return fmt_label(idx) if col == "JobLevel" else idx

    for col, label in (("WLB_Category", "WLB Category"), ("Department", "Department"), ("JobLevel", "Job Level"),
                       ("Age_Group", "Age Group"), ("Income_Group", "Income Group"), ("Tenure_Group", "Tenure Group"),
                       ("JobSatisfaction_Category", "Job Satisfaction"),
                       ("EnvironmentSatisfaction_Category", "Environment Satisfaction"), ("OverTime", "OverTime")):
        t = rate_table(df, col, a, ordered_categories(df, col))
        for idx, r in t.iterrows():
            add(f"Attrition Rate by {label}", lab(col, idx), r.Rate, "%", r.Employees, r.Events)
    for col, label in (("Department", "Department"), ("JobLevel", "Job Level")):
        order = ordered_categories(df, col)
        t, att = rate_table(df, col, lo, order), rate_table(df, col, a, order)
        for idx, r in t.iterrows():
            add(f"Low WLB Rate by {label}", lab(col, idx), r.Rate, "%", r.Employees, att.loc[idx, "Events"])
    for col in ("Department", "OverTime"):
        order = ordered_categories(df, col)
        m, att = mean_table(df, col, "WorkLifeBalance", order), rate_table(df, col, a, order)
        for idx, r in m.iterrows():
            add(f"Average WLB by {col}", idx, r.Mean, "score 1-4", r.Employees, att.loc[idx, "Events"])
    t = rate_table(df, ["EnvironmentSatisfaction_Category", "JobSatisfaction_Category"], a)
    for (e, j), r in t.iterrows():
        if r.Employees:
            add("Attrition Rate by Satisfaction Combination", f"Env {e} | Job {j}", r.Rate, "%", r.Employees, r.Events)
    for section in (overview_highlights, wlb_insights, overtime_insights, satisfaction_insights, attrition_insights):
        for ins in section(df):
            rows.append({"Metric": "Automated Insight", "Category": ins["text"], "Value": None, "Unit": "text",
                         "Employee Count": n, "Attrition Count": ac, "Filter Context": context})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Chart helpers (Plotly)
# --------------------------------------------------------------------------- #
def _layout(fig: go.Figure, title: str = "", height: int = 360) -> go.Figure:
    """Judul Plotly opsional. Di app.py judul dirender sebagai HTML di dalam card."""
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=NAVY, family=FONT)) if title else None,
        font=dict(family=FONT, color=TEXT, size=12),
        paper_bgcolor="white", plot_bgcolor="white", height=height,
        margin=dict(l=10, r=10, t=64 if title else 40, b=10),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, size=12, color=TEXT)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, title_text=""),
    )
    fig.update_xaxes(showgrid=False, linecolor="#D8DEE6", automargin=True)
    fig.update_yaxes(gridcolor="#EEF1F5", zeroline=False, automargin=True)
    return fig


def _tick_labels(index, employees) -> list[str]:
    return [f"{fmt_label(i)}<br><span style='font-size:10px;color:{SLATE}'>n = {int(n):,}</span>"
            for i, n in zip(index, employees)]


def bar_rate(tbl, title, *, x_title, y_title="Attrition rate (%)", event_label="Attrition",
             color_map: bool = False, reference: float | None = None, height: int = 360) -> go.Figure:
    rate = tbl["Rate"]
    mx = rate.max()
    if color_map:
        colors = [CATEGORY_COLORS.get(str(i), SLATE) for i in tbl.index]
    else:
        colors = [LOW if pd.notna(r) and r == mx else SLATE for r in rate]
    text = [fmt_pct(r) if pd.notna(r) else "n = 0" for r in rate]
    fig = go.Figure(go.Bar(
        x=_tick_labels(tbl.index, tbl["Employees"]), y=rate.fillna(0), marker_color=colors, text=text,
        textposition="outside", cliponaxis=False,
        customdata=np.column_stack([tbl["Employees"], tbl["Events"]]),
        hovertemplate=("<b>%{x}</b><br>Rate: %{y:.2f}%<br>Employees: %{customdata[0]:,}"
                       f"<br>{event_label}: %{{customdata[1]:,}}<extra></extra>"),
    ))
    top = max(float(mx) if pd.notna(mx) else 0.0, reference if reference is not None and pd.notna(reference) else 0.0)
    fig.update_yaxes(range=[0, max(top * 1.25, 5)], ticksuffix="%", title_text=y_title)
    fig.update_xaxes(title_text=x_title, type="category")
    if reference is not None and pd.notna(reference):
        fig.add_hline(y=reference, line_dash="dot", line_color=NAVY, line_width=1,
                      annotation_text=f"Overall {fmt_pct(reference)}", annotation_position="top left",
                      annotation_font=dict(size=10, color=NAVY))
    return _layout(fig, title, height)


def bar_count(tbl, title, *, x_title, y_title="Jumlah karyawan", color_map=True, height=360) -> go.Figure:
    emp = tbl["Employees"]
    colors = [CATEGORY_COLORS.get(str(i), SLATE) if color_map else SLATE for i in tbl.index]
    total = int(emp.sum())
    fig = go.Figure(go.Bar(
        x=[fmt_label(i) for i in tbl.index], y=emp, marker_color=colors,
        text=[fmt_int(v) for v in emp], textposition="outside", cliponaxis=False,
        customdata=[safe_div(v, total) * 100 if total else np.nan for v in emp],
        hovertemplate="<b>%{x}</b><br>Employees: %{y:,}<br>Porsi: %{customdata:.2f}%<extra></extra>",
    ))
    fig.update_yaxes(range=[0, max(float(emp.max()) * 1.2, 5)], title_text=y_title)
    fig.update_xaxes(title_text=x_title, type="category")
    return _layout(fig, title, height)


def bar_mean(tbl, title, *, x_title, y_title="Average WLB (skala 1–4)", height=360) -> go.Figure:
    m = tbl["Mean"]
    has_many = int((tbl["Employees"] > 0).sum()) > 1
    mn = m.min()
    colors = [LOW if has_many and pd.notna(v) and v == mn else SLATE for v in m]
    fig = go.Figure(go.Bar(
        x=_tick_labels(tbl.index, tbl["Employees"]), y=m.fillna(0), marker_color=colors,
        text=[fmt_score(v) if pd.notna(v) else "n = 0" for v in m], textposition="outside", cliponaxis=False,
        customdata=tbl["Employees"],
        hovertemplate="<b>%{x}</b><br>Average WLB: %{y:.2f}<br>Employees: %{customdata:,}<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 4.4], title_text=y_title, dtick=1)
    fig.update_xaxes(title_text=x_title, type="category")
    return _layout(fig, title, height)


def stacked_100(pct, counts, n, title, *, x_title, height=360) -> go.Figure:
    fig = go.Figure()
    xs = _tick_labels(n.index, n.values)
    for cat in pct.columns:
        vals = pct[cat]
        fig.add_bar(
            name=str(cat), x=xs, y=vals.fillna(0), marker_color=CATEGORY_COLORS.get(str(cat), SLATE),
            text=[fmt_pct(v) if pd.notna(v) and v >= 4 else "" for v in vals], textposition="inside",
            textfont=dict(color=NAVY if cat == "Medium" else "white", size=11),
            customdata=counts[cat],
            hovertemplate=f"<b>%{{x}}</b><br>{cat}: %{{y:.2f}}%<br>Employees: %{{customdata:,}}<extra></extra>",
        )
    fig.update_layout(barmode="stack")
    fig.update_yaxes(range=[0, 100], ticksuffix="%", title_text="Komposisi (%)")
    fig.update_xaxes(title_text=x_title, type="category")
    return _layout(fig, title, height)


def heatmap(rate: pd.DataFrame, emp: pd.DataFrame, ev: pd.DataFrame, title: str, *, x_title: str, y_title: str,
            event_label="Attrition", height=360) -> go.Figure:
    rl = [fmt_label(i) for i in rate.index]
    cl = [fmt_label(i) for i in rate.columns]
    z = rate.to_numpy(dtype=float)
    e = emp.to_numpy()
    zmax = float(np.nanmax(z)) if np.isfinite(z).any() else 1.0
    zmax = zmax if zmax > 0 else 1.0
    fig = go.Figure(go.Heatmap(
        z=z, x=cl, y=rl, customdata=np.dstack([e, ev.to_numpy()]), zmin=0, zmax=zmax, xgap=2, ygap=2,
        colorscale=[[0, "#EEF1F5"], [1, LOW]], showscale=False, hoverongaps=False,
        hovertemplate=("<b>%{y} × %{x}</b><br>Rate: %{z:.2f}%<br>Employees: %{customdata[0]:,}"
                       f"<br>{event_label}: %{{customdata[1]:,}}<extra></extra>"),
    ))
    for i, r in enumerate(rl):
        for j, c in enumerate(cl):
            v = z[i, j]
            if np.isnan(v):
                label, color = "–<br><span style='font-size:9px'>tanpa data</span>", SLATE
            else:
                label = f"{v:.2f}%<br><span style='font-size:10px'>n = {int(e[i, j]):,}</span>"
                color = "white" if v / zmax > 0.62 else NAVY
            fig.add_annotation(x=c, y=r, text=label, showarrow=False, font=dict(color=color, size=12, family=FONT))
    fig.update_xaxes(title_text=x_title, side="top", type="category")
    fig.update_yaxes(title_text=y_title, autorange="reversed", type="category")
    fig = _layout(fig, title, height)
    fig.update_layout(margin=dict(l=10, r=10, t=110 if title else 84, b=10))
    return fig