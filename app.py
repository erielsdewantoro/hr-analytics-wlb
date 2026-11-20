"""HR Analytics — Work-Life Balance, Overtime, Satisfaction & Attrition (Streamlit)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

import functions as fx

BASE_DIR = Path(__file__).parent
DATA_PATH = BASE_DIR / "data" / "clean_data.csv"
CSS_PATH = BASE_DIR / "assets" / "custom.css"
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}
CH = 360  # tinggi plot seragam untuk semua chart agar card sejajar

# Pengelompokan filter di sidebar (setiap kolom di fx.FILTER_COLUMNS harus muncul tepat sekali)
FILTER_GROUPS = [
    ("Demografi", ["Gender", "Age_Group"]),
    ("Pekerjaan", ["Department", "JobLevel", "OverTime", "Tenure_Group"]),
    ("Kompensasi", ["Income_Group"]),
    ("Work-Life Balance", ["WLB_Category"]),
]
assert sorted(c for _, cols in FILTER_GROUPS for c in cols) == sorted(fx.FILTER_COLUMNS)

st.set_page_config(page_title="HR Analytics — Work-Life Balance", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
if CSS_PATH.exists():
    st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# UI helpers
# --------------------------------------------------------------------------- #
def chart_card(title: str, fig, key: str) -> None:
    """Chart di dalam card bergaya minimalis. Judul = HTML (bisa 2 baris) agar tinggi antar card seragam."""
    with st.container(border=True, key=f"card_{key}"):
        st.markdown(f"<div class='chart-title'>{title}</div>", unsafe_allow_html=True)
        st.plotly_chart(fig, key=key, width="stretch", config=PLOT_CONFIG)


def kpi_row(cards: list[tuple]) -> None:
    """Baris kartu KPI (flexbox). Tiap item: (label, value, sub, alert)."""
    html = "".join(
        f"<div class='kpi-card'><div class='kpi-label'>{label}</div>"
        f"<div class='kpi-value{' alert' if alert else ''}'>{value}</div><div class='kpi-sub'>{sub}</div></div>"
        for label, value, sub, alert in cards
    )
    st.markdown(f"<div class='kpi-row'>{html}</div>", unsafe_allow_html=True)


def section_header(title: str, subtitle: str) -> None:
    st.markdown(f"<h2 class='section-title'>{title}</h2><div class='section-sub'>{subtitle}</div>", unsafe_allow_html=True)


def sub_heading(title: str, caption: str = "") -> None:
    cap = f"<div class='sub-caption'>{caption}</div>" if caption else ""
    st.markdown(f"<h3 class='sub-heading'>{title}</h3>{cap}", unsafe_allow_html=True)


def divider() -> None:
    st.markdown("<hr class='soft-divider'>", unsafe_allow_html=True)


def insight_card(title: str, insights: list[dict], key: str, caption: str = "Dihitung otomatis dari data terfilter.") -> None:
    if not insights:
        return
    items = "".join(f"<li class='{'warn' if i['warn'] else ''}'>{i['text']}</li>" for i in insights)
    with st.container(border=True, key=f"card_{key}"):
        st.markdown(f"<h3 class='sub-heading'>{title}</h3><div class='sub-caption'>{caption}</div>"
                    f"<ul class='insight-list'>{items}</ul>", unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f"<div class='chart-note'>{text}</div>", unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Load data (dengan penanganan error yang jelas)
# --------------------------------------------------------------------------- #
try:
    mtime = DATA_PATH.stat().st_mtime if DATA_PATH.exists() else 0.0
    full_df, load_notes = fx.load_data(str(DATA_PATH), mtime)
except fx.DataValidationError as exc:
    st.error(f"**Dataset tidak dapat dimuat.** {exc}")
    st.info("Pastikan file `data/clean_data.csv` tersedia dan memiliki seluruh kolom wajib.")
    st.stop()
except Exception as exc:  # noqa: BLE001 - tampilkan pesan yang ramah, bukan stack trace
    st.error(f"**Terjadi kesalahan saat membaca dataset:** {exc}")
    st.stop()

options = {col: fx.column_options(full_df, col) for col in fx.FILTER_COLUMNS}

# --------------------------------------------------------------------------- #
# Sidebar — filter global, dikelompokkan
# --------------------------------------------------------------------------- #
for col in fx.FILTER_COLUMNS:
    st.session_state.setdefault(f"f_{col}", list(options[col]))


def reset_filters() -> None:
    for c in fx.FILTER_COLUMNS:
        st.session_state[f"f_{c}"] = list(options[c])


selections: dict[str, list] = {}
with st.sidebar:
    st.markdown("<div class='sidebar-title'>Filter Global</div>", unsafe_allow_html=True)
    st.caption("Semua KPI, chart, insight, tabel, dan unduhan mengikuti filter ini.")
    st.button("Pilih semua / Reset filter", on_click=reset_filters, width="stretch")
    for group, cols in FILTER_GROUPS:
        st.markdown(f"<div class='side-group'>{group}</div>", unsafe_allow_html=True)
        for col in cols:
            selections[col] = st.multiselect(
                fx.FILTER_COLUMNS[col], options[col], key=f"f_{col}",
                format_func=fx.fmt_label if col == "JobLevel" else str,
            )

df = fx.apply_filters(full_df, selections, options)
context = fx.filter_context(selections, options)

with st.sidebar:
    st.markdown("<div class='side-group'>Unduh Data</div>", unsafe_allow_html=True)
    st.download_button("⬇ Filtered dataset (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_filtered_data.csv", mime="text/csv", width="stretch",
                       disabled=df.empty)
    st.download_button("⬇ Insight summary (CSV)", fx.build_insight_summary(df, context).to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_insight_summary.csv", mime="text/csv", width="stretch",
                       disabled=df.empty)

# --------------------------------------------------------------------------- #
# Header & status filter
# --------------------------------------------------------------------------- #
st.markdown(
    "<div class='app-eyebrow'>HR ANALYTICS</div>"
    "<h1 class='app-title'>Analisis Work-Life Balance Karyawan</h1>"
    "<div class='app-subtitle'>Pengaruh overtime, kepuasan kerja, dan demografi terhadap pola attrition — "
    "analisis deskriptif untuk HR dan manajemen.</div>",
    unsafe_allow_html=True,
)
for msg in load_notes:
    st.warning(msg)

total = len(full_df)
st.markdown(
    f"<div class='status-bar'><b>{fx.fmt_int(len(df))}</b> dari {fx.fmt_int(total)} karyawan "
    f"({fx.fmt_pct(len(df) / total * 100)}) &nbsp;•&nbsp; Filter aktif: {context}</div>",
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("**Tidak ada karyawan yang cocok dengan kombinasi filter saat ini.** "
               "Longgarkan salah satu filter atau klik *Pilih semua / Reset filter* di sidebar.")
    st.stop()

kpi = fx.compute_kpis(df)
attr, low = fx.attrition_flag(df), fx.low_wlb_flag(df)
overall_attr = kpi["attrition_rate"]
if len(df) < fx.MIN_N:
    st.warning(f"Ukuran sampel hasil filter kecil (n = {len(df)} < {fx.MIN_N}). Persentase dapat berfluktuasi tajam.")

tabs = st.tabs(["Overview", "WLB Analysis", "Overtime & Satisfaction", "Attrition Analysis", "Data Explorer"])

# =========================================================================== #
# 1. OVERVIEW
# =========================================================================== #
with tabs[0]:
    section_header("Overview", "Gambaran umum kondisi Work-Life Balance, overtime, kepuasan, dan attrition.")

    sub_heading("Ringkasan KPI")
    kpi_row([
        ("Total Employees", fx.fmt_int(kpi["total_employees"]), "karyawan unik (EmployeeNumber)", False),
        ("Average WLB", fx.fmt_score(kpi["avg_wlb"]), "skala 1–4", False),
        ("Low WLB Percentage", fx.fmt_pct(kpi["low_wlb_pct"]), f"{fx.fmt_int(kpi['low_wlb_count'])} karyawan Low WLB", True),
        ("Attrition Rate", fx.fmt_pct(kpi["attrition_rate"]), f"{fx.fmt_int(kpi['attrition_count'])} karyawan attrition", True),
    ])
    kpi_row([
        ("Overtime Percentage", fx.fmt_pct(kpi["overtime_pct"]), f"{fx.fmt_int(kpi['overtime_count'])} karyawan overtime", False),
        ("Average Job Satisfaction", fx.fmt_score(kpi["avg_job_sat"]), "skala 1–4", False),
        ("Average Environment Satisfaction", fx.fmt_score(kpi["avg_env_sat"]), "skala 1–4", False),
    ])

    divider()
    sub_heading("Distribusi & Perbandingan", "Garis putus-putus pada chart attrition = rate keseluruhan data terfilter. n = jumlah karyawan per kelompok.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        wlb_dist = fx.rate_table(df, "WLB_Category", low, fx.ordered_categories(df, "WLB_Category"))
        chart_card("Berapa banyak karyawan di setiap kategori WLB?",
                   fx.bar_count(wlb_dist, "", x_title="WLB Category", height=CH), "ov_wlb_dist")
    with c2:
        chart_card("Apakah rata-rata WLB berbeda menurut status overtime?",
                   fx.bar_mean(fx.mean_table(df, "OverTime", "WorkLifeBalance", fx.ordered_categories(df, "OverTime")),
                               "", x_title="OverTime", height=CH), "ov_wlb_ot")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        chart_card("Bagaimana attrition rate pada tiap kategori WLB?",
                   fx.bar_rate(fx.rate_table(df, "WLB_Category", attr, fx.ordered_categories(df, "WLB_Category")), "",
                               x_title="WLB Category", color_map=True, reference=overall_attr, height=CH), "ov_attr_wlb")
    with c4:
        chart_card("Department mana yang memiliki attrition rate tertinggi?",
                   fx.bar_rate(fx.rate_table(df, "Department", attr, fx.ordered_categories(df, "Department")), "",
                               x_title="Department", reference=overall_attr, height=CH), "ov_attr_dept")
    note("Temuan bersifat deskriptif, bukan bukti bahwa overtime menyebabkan penurunan WLB atau WLB menyebabkan attrition.")

    divider()
    insight_card("Automated Highlights", fx.overview_highlights(df), "ov_highlights")

# =========================================================================== #
# 2. WLB ANALYSIS
# =========================================================================== #
with tabs[1]:
    section_header("WLB Analysis", "Work-Life Balance menurut struktur organisasi dan kelompok demografi.")

    sub_heading("Department & Job Level")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_card("Department mana yang rata-rata WLB-nya paling rendah?",
                   fx.bar_mean(fx.mean_table(df, "Department", "WorkLifeBalance", fx.ordered_categories(df, "Department")),
                               "", x_title="Department", height=CH), "wlb_avg_dept")
    with c2:
        chart_card("Department mana yang proporsi Low WLB-nya paling tinggi?",
                   fx.bar_rate(fx.rate_table(df, "Department", low, fx.ordered_categories(df, "Department")), "",
                               x_title="Department", y_title="Low WLB rate (%)", event_label="Low WLB",
                               reference=kpi["low_wlb_pct"], height=CH), "wlb_low_dept")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        chart_card("Job Level mana yang proporsi Low WLB-nya paling tinggi?",
                   fx.bar_rate(fx.rate_table(df, "JobLevel", low, fx.ordered_categories(df, "JobLevel")), "",
                               x_title="Job Level", y_title="Low WLB rate (%)", event_label="Low WLB",
                               reference=kpi["low_wlb_pct"], height=CH), "wlb_low_level")
    with c4:
        rate, emp, ev = fx.rate_matrix(df, "Department", "JobLevel", low)
        chart_card("Kombinasi Department × Job Level mana yang perlu diperhatikan?",
                   fx.heatmap(rate, emp, ev, "", x_title="Job Level", y_title="Department",
                              event_label="Low WLB", height=CH), "wlb_heat")

    divider()
    sub_heading("Komposisi WLB")
    pct, cnt, n = fx.composition(df, "JobLevel", "WLB_Category")
    chart_card("Bagaimana komposisi WLB pada tiap Job Level?",
               fx.stacked_100(pct, cnt, n, "", x_title="Job Level", height=CH), "wlb_comp_level")
    d1, d2 = st.columns(2, gap="medium")
    for col_ui, (col, label, key) in zip((d1, d2), (("Age_Group", "Age Group", "wlb_age"), ("Tenure_Group", "Tenure Group", "wlb_tenure"))):
        with col_ui:
            pct, cnt, n = fx.composition(df, col, "WLB_Category")
            chart_card(f"Bagaimana distribusi WLB menurut {label}?",
                       fx.stacked_100(pct, cnt, n, "", x_title=label, height=CH), key)
    pct, cnt, n = fx.composition(df, "Income_Group", "WLB_Category")
    chart_card("Bagaimana distribusi WLB menurut Income Group?",
               fx.stacked_100(pct, cnt, n, "", x_title="Income Group", height=CH), "wlb_income")
    note("Kategori WLB: Low = skor 1–2, Medium = skor 3, High = skor 4. Label di bawah 4% disembunyikan agar tidak bertumpuk; "
         "nilai lengkap ada di tooltip.")

    divider()
    insight_card("Analytical Focus — WLB", fx.wlb_insights(df), "wlb_focus")

# =========================================================================== #
# 3. OVERTIME & SATISFACTION
# =========================================================================== #
with tabs[2]:
    section_header("Overtime & Satisfaction", "Perbedaan overtime, dua dimensi kepuasan kerja, dan pola attrition.")

    sub_heading("Overtime")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_card("Apakah attrition rate berbeda antara karyawan overtime dan non-overtime?",
                   fx.bar_rate(fx.rate_table(df, "OverTime", attr, fx.ordered_categories(df, "OverTime")), "",
                               x_title="OverTime", reference=overall_attr, height=CH), "ot_attr")
    with c2:
        chart_card("Berapa rata-rata WLB menurut status overtime?",
                   fx.bar_mean(fx.mean_table(df, "OverTime", "WorkLifeBalance", fx.ordered_categories(df, "OverTime")),
                               "", x_title="OverTime", height=CH), "ot_wlb")

    divider()
    sub_heading("Kepuasan Kerja")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        pct, cnt, n = fx.composition(df, "OverTime", "JobSatisfaction_Category")
        chart_card("Bagaimana distribusi Job Satisfaction menurut overtime?",
                   fx.stacked_100(pct, cnt, n, "", x_title="OverTime", height=CH), "ot_job")
    with c4:
        pct, cnt, n = fx.composition(df, "OverTime", "EnvironmentSatisfaction_Category")
        chart_card("Bagaimana distribusi Environment Satisfaction menurut overtime?",
                   fx.stacked_100(pct, cnt, n, "", x_title="OverTime", height=CH), "ot_env")
    rate, emp, ev = fx.rate_matrix(df, "EnvironmentSatisfaction_Category", "JobSatisfaction_Category", attr)
    chart_card("Kombinasi kepuasan mana yang memiliki attrition rate tertinggi?",
               fx.heatmap(rate, emp, ev, "", x_title="Job Satisfaction", y_title="Environment Satisfaction", height=CH), "ot_heat")
    note("Kategori kepuasan: Low = skor 1–2, Medium = skor 3, High = skor 4. Sel tanpa observasi ditampilkan sebagai “–”. "
         "Perhatikan n pada tiap sel: rate dari sel kecil mudah berfluktuasi.")

    divider()
    i1, i2 = st.columns(2, gap="medium")
    with i1:
        insight_card("Analytical Focus — Overtime", fx.overtime_insights(df), "ot_focus")
    with i2:
        insight_card("Analytical Focus — Satisfaction", fx.satisfaction_insights(df), "sat_focus")

# =========================================================================== #
# 4. ATTRITION ANALYSIS
# =========================================================================== #
with tabs[3]:
    section_header("Attrition Analysis", "Pola attrition menurut karakteristik karyawan. Pola, bukan prediksi individu.")
    sub_heading("Attrition rate per kelompok",
                f"Baseline data terfilter: <b>{fx.fmt_pct(overall_attr)}</b> "
                f"({fx.fmt_int(kpi['attrition_count'])} dari {fx.fmt_int(kpi['total_employees'])} karyawan). "
                "Batang merah = kelompok dengan rate tertinggi (pada chart berwarna kategori, warna mengikuti kategori).")
    specs = [
        ("WLB_Category", "WLB Category", "Attrition rate menurut kategori WLB", True),
        ("Department", "Department", "Attrition rate menurut Department", False),
        ("JobLevel", "Job Level", "Attrition rate menurut Job Level", False),
        ("Age_Group", "Age Group", "Attrition rate menurut Age Group", False),
        ("Income_Group", "Income Group", "Attrition rate menurut Income Group", False),
        ("Tenure_Group", "Tenure Group", "Attrition rate menurut Tenure Group", False),
        ("JobSatisfaction_Category", "Job Satisfaction", "Attrition rate menurut Job Satisfaction", True),
        ("EnvironmentSatisfaction_Category", "Environment Satisfaction", "Attrition rate menurut Environment Satisfaction", True),
        ("OverTime", "OverTime", "Attrition rate menurut status OverTime", False),
    ]
    for i in range(0, len(specs), 2):
        cols = st.columns(2, gap="medium")
        for col_ui, (col, label, title, cmap) in zip(cols, specs[i:i + 2]):
            with col_ui:
                chart_card(title, fx.bar_rate(fx.rate_table(df, col, attr, fx.ordered_categories(df, col)), "",
                                              x_title=label, color_map=cmap, reference=overall_attr, height=CH), f"attr_{col}")
    rate, emp, ev = fx.rate_matrix(df, "Department", "WLB_Category", attr)
    with cols[1]:  # 9 chart bar -> satu kolom tersisa di baris terakhir untuk heatmap
        chart_card("Attrition rate: Department × kategori WLB",
                   fx.heatmap(rate, emp, ev, "", x_title="WLB Category", y_title="Department", height=CH), "attr_heat")

    with st.expander("Tabel rincian: ukuran sampel dan jumlah attrition per kelompok"):
        parts = []
        for col, label, *_ in specs:
            t = fx.rate_table(df, col, attr, fx.ordered_categories(df, col)).reset_index()
            t.columns = ["Group", "Employees", "Attrition Count", "Attrition Rate (%)"]
            t.insert(0, "Dimension", label)
            t["Group"] = t["Group"].map(fx.fmt_label)
            parts.append(t)
        st.dataframe(pd.concat(parts, ignore_index=True), hide_index=True, width="stretch",
                     column_config={"Attrition Rate (%)": st.column_config.NumberColumn(format="%.2f%%"),
                                    "Employees": st.column_config.NumberColumn(format="%d"),
                                    "Attrition Count": st.column_config.NumberColumn(format="%d")})

    divider()
    insight_card("Analytical Focus — Attrition", fx.attrition_insights(df), "attr_focus")

# =========================================================================== #
# 5. DATA EXPLORER
# =========================================================================== #
with tabs[4]:
    section_header("Data Explorer", "Eksplorasi data terfilter dan ringkasan kualitas data.")
    st.info("🔒 **Privasi:** `EmployeeNumber` disembunyikan secara default. Tampilkan hanya jika diperlukan "
            "dan jangan dibagikan pada tampilan publik.")
    sub_heading("Tabel data")
    all_cols = list(df.columns)
    default_cols = [c for c in all_cols if c != "EmployeeNumber"]
    chosen = st.multiselect("Kolom yang ditampilkan", all_cols, default=default_cols, key="explorer_cols")
    query = st.text_input("Cari teks (Department, JobRole, Age_Group, dll.)", key="explorer_search")
    view = df
    if query.strip():
        text_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
        m = pd.Series(False, index=df.index)
        for c in text_cols:
            m |= df[c].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        view = df[m]
    st.markdown(f"**{fx.fmt_int(len(view))}** records ditampilkan dari {fx.fmt_int(len(df))} hasil filter "
                f"({fx.fmt_int(total)} total).")
    if chosen:
        st.dataframe(view[chosen], hide_index=True, width="stretch", height=380)
    else:
        st.warning("Pilih minimal satu kolom untuk ditampilkan.")
    st.download_button("⬇ Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_filtered_data.csv", mime="text/csv", key="dl_explorer")
    st.caption("File unduhan berisi seluruh kolom pada data hasil filter (tanpa pencarian teks), encoding UTF-8.")

    divider()
    sub_heading("Data quality summary")
    q_full, q_f = fx.data_quality(full_df), fx.data_quality(df)
    qc = st.columns(4)
    qc[0].metric("Rows (filtered / total)", f"{q_f['rows']:,} / {q_full['rows']:,}")
    qc[1].metric("Columns", q_full["columns"])
    qc[2].metric("Missing values (total)", f"{q_full['missing_total']:,}")
    qc[3].metric("Duplicate EmployeeNumber", f"{q_full['duplicate_employee']:,}")
    if q_full["duplicate_employee"] == 0 and q_full["missing_total"] == 0:
        st.success("EmployeeNumber unik dan tidak ada missing value pada dataset.")
    miss = full_df.isna().sum()
    miss = miss[miss > 0].rename("Missing").reset_index().rename(columns={"index": "Column"})
    if not miss.empty:
        st.dataframe(miss, hide_index=True, width="stretch")
    with st.expander("Informasi tipe data"):
        info = pd.DataFrame({"Column": full_df.columns, "Dtype": full_df.dtypes.astype(str).values,
                             "Non-null": full_df.notna().sum().values, "Unique": full_df.nunique().values})
        st.dataframe(info, hide_index=True, width="stretch")
        st.caption("JobLevel, WorkLifeBalance, JobSatisfaction, dan EnvironmentSatisfaction adalah skala ordinal "
                   "sehingga disimpan sebagai integer dan dianalisis per kategori, bukan variabel kontinu.")

# =========================================================================== #
# 💡 HR STRATEGIC RECOMMENDATIONS — dinamis, mengikuti filter global
# =========================================================================== #
ATTR_ALERT_PCT = 15.0      # attrition rate di atas ini -> rekomendasi retensi
OT_ALERT_PCT = 25.0        # persentase overtime di atas ini dianggap tinggi
WLB_LOW_AVG = 2.75         # rata-rata WLB (skala 1-4) di bawah ini dianggap rendah
WLB_LOW_SHARE_PCT = 25.0   # atau proporsi Low WLB di atas ini dianggap tinggi


def group_attrition(frame: pd.DataFrame, flag, col: str) -> pd.DataFrame:
    """Attrition per kelompok (n, rate %), hanya kelompok dengan n >= fx.MIN_N agar tidak menyesatkan."""
    g = (pd.DataFrame({"g": frame[col].to_numpy(), "a": pd.Series(flag).astype(float).to_numpy()})
         .groupby("g", observed=True)["a"].agg(n="size", rate="mean"))
    g["rate"] *= 100
    return g[g["n"] >= fx.MIN_N].sort_values("rate", ascending=False)


# Template rekomendasi per dimensi demografi / pekerjaan: {g} = kelompok, {r} = rate, {o} = baseline
DEMO_RECS = {
    "Age_Group": ("Usia",
                  "Kelompok usia **{g}** mencatat attrition **{r}** (baseline {o}). Rancang jalur karier dan program "
                  "pengembangan yang sesuai fase hidup kelompok ini (mentoring, rotasi, skema kerja fleksibel)."),
    "Tenure_Group": ("Masa kerja",
                     "Karyawan dengan masa kerja **{g}** paling rentan keluar (**{r}**, baseline {o}). Perkuat onboarding, "
                     "check-in berkala (stay interview), dan kejelasan promosi pada titik kritis masa kerja tersebut."),
    "Income_Group": ("Kompensasi",
                     "Kelompok pendapatan **{g}** memiliki attrition **{r}** (baseline {o}). Lakukan benchmark gaji terhadap pasar "
                     "dan tinjau paket total reward (insentif berbasis kinerja, tunjangan, retensi bonus) untuk kelompok ini."),
    "JobLevel": ("Level jabatan",
                 "Job Level **{g}** menunjukkan attrition **{r}** (baseline {o}). Evaluasi beban peran, ruang otonomi, "
                 "dan peluang naik level; siapkan succession plan untuk posisi yang berisiko kosong."),
    "Department": ("Departemen",
                   "Department **{g}** mencatat attrition **{r}** (baseline {o}). Jadwalkan diagnosis akar masalah bersama "
                   "kepala departemen (exit interview, survei pulse) dan tetapkan target penurunan attrition per kuartal."),
}

divider()
section_header("💡 HR Strategic Recommendations",
               "Rekomendasi otomatis untuk manajemen, dihitung ulang dari data sesuai filter global yang aktif.")
st.caption(f"Ambang batas: attrition > {ATTR_ALERT_PCT:.0f}% • overtime > {OT_ALERT_PCT:.0f}% • "
           f"WLB rendah = rata-rata < {WLB_LOW_AVG:.2f} atau proporsi Low WLB ≥ {WLB_LOW_SHARE_PCT:.0f}%. "
           f"Kelompok dengan n < {fx.MIN_N} tidak dijadikan dasar rekomendasi.")

# ---- 1. Attrition ---------------------------------------------------------- #
st.markdown("##### 1. Retensi Karyawan")
if overall_attr > ATTR_ALERT_PCT:
    by_dept = group_attrition(df, attr, "Department")
    msg = (f"**Attrition rate {fx.fmt_pct(overall_attr)}** melampaui ambang {ATTR_ALERT_PCT:.0f}% "
           f"({fx.fmt_int(kpi['attrition_count'])} dari {fx.fmt_int(kpi['total_employees'])} karyawan).\n\n")
    if not by_dept.empty:
        top_d = by_dept.index[0]
        msg += (f"- **Prioritas retensi: {fx.fmt_label(top_d)}** — attrition {fx.fmt_pct(by_dept.iloc[0]['rate'])} "
                f"(n = {fx.fmt_int(by_dept.iloc[0]['n'])}). Bentuk tim retensi lintas fungsi (HR + kepala departemen) "
                f"dan lakukan *stay interview* pada talenta kunci dalam 30 hari.\n")
    by_ot = group_attrition(df, attr, "OverTime")
    if len(by_ot) >= 2:
        msg += (f"- Attrition tertinggi ada pada kelompok OverTime **{fx.fmt_label(by_ot.index[0])}** "
                f"({fx.fmt_pct(by_ot.iloc[0]['rate'])}) vs **{fx.fmt_label(by_ot.index[-1])}** "
                f"({fx.fmt_pct(by_ot.iloc[-1]['rate'])}); jadikan pengelolaan jam kerja bagian dari strategi retensi.\n")
    msg += ("- Tinjau kompetitivitas kompensasi dan jalur promosi, lalu pantau attrition bulanan "
            "sebagai KPI manajemen dengan target penurunan yang terukur.")
    st.info(msg, icon="🎯")
else:
    st.success(f"**Attrition rate {fx.fmt_pct(overall_attr)}** masih di bawah ambang {ATTR_ALERT_PCT:.0f}%. "
               "Pertahankan program retensi yang berjalan dan lanjutkan pemantauan berkala, terutama pada "
               "kelompok dengan rate di atas rata-rata (lihat poin 3).", icon="✅")

# ---- 2. WLB & Overtime ----------------------------------------------------- #
st.markdown("##### 2. Beban Kerja, Overtime & Risiko Burnout")
ot_pct, avg_wlb, low_pct = kpi["overtime_pct"], kpi["avg_wlb"], kpi["low_wlb_pct"]
ot_high = ot_pct > OT_ALERT_PCT
wlb_low = (avg_wlb < WLB_LOW_AVG) or (low_pct >= WLB_LOW_SHARE_PCT)
snapshot = (f"Overtime **{fx.fmt_pct(ot_pct)}**, rata-rata WLB **{fx.fmt_score(avg_wlb)}** (skala 1–4), "
            f"Low WLB **{fx.fmt_pct(low_pct)}**.")
by_dept_low = group_attrition(df, low, "Department")
hot_dept = (f" Fokuskan intervensi awal pada **{fx.fmt_label(by_dept_low.index[0])}** "
            f"(Low WLB {fx.fmt_pct(by_dept_low.iloc[0]['rate'])})." if not by_dept_low.empty else "")
if ot_high and wlb_low:
    st.info(f"**Risiko burnout tinggi.** {snapshot}\n\n"
            "- **Audit beban kerja:** petakan jam lembur per tim/peran, identifikasi penyebab struktural "
            "(kekurangan headcount, distribusi tugas, tenggat tidak realistis).\n"
            "- **Batasi lembur:** tetapkan batas lembur per karyawan, mekanisme persetujuan atasan, dan kompensasi "
            "(waktu pengganti/*time-off in lieu*) yang adil.\n"
            "- **Program anti-burnout:** survei pulse bulanan, jalur konseling/EAP, dan pelatihan manajer untuk "
            "mendeteksi tanda kelelahan sejak dini." + hot_dept, icon="🔥")
elif ot_high:
    st.info(f"**Overtime tinggi, WLB masih terjaga.** {snapshot}\n\n"
            "Ini sinyal dini: lakukan evaluasi beban kerja dan redistribusi tugas sebelum kelelahan menurunkan "
            "WLB dan kepuasan kerja." + hot_dept, icon="⚠️")
elif wlb_low:
    st.info(f"**WLB rendah meski overtime terkendali.** {snapshot}\n\n"
            "Telusuri faktor non-lembur: fleksibilitas jadwal/lokasi kerja, jarak dan waktu komuter, serta budaya "
            "komunikasi di luar jam kerja. Pertimbangkan kebijakan kerja hibrida atau jam kerja fleksibel." + hot_dept,
            icon="⚠️")
else:
    st.success(f"**Kondisi beban kerja sehat.** {snapshot}\n\n"
               "Pertahankan kebijakan yang ada dan jadikan overtime serta WLB sebagai indikator pemantauan rutin.", icon="✅")

# ---- 3. Demografi / segmen ------------------------------------------------- #
st.markdown("##### 3. Rekomendasi Spesifik Segmen")
candidates = []
for dim, (_, template) in DEMO_RECS.items():
    g = group_attrition(df, attr, dim)
    if g.empty:
        continue
    gap = g.iloc[0]["rate"] - overall_attr
    if gap > 0 and len(g) >= 2:  # butuh pembanding; satu kelompok saja bukan temuan segmen
        candidates.append((gap, dim, g.index[0], g.iloc[0]["rate"], g.iloc[0]["n"]))
candidates.sort(reverse=True)
if candidates:
    lines = []
    for gap, dim, grp, rate, n in candidates[:3]:
        text = DEMO_RECS[dim][1].format(g=fx.fmt_label(grp), r=fx.fmt_pct(rate), o=fx.fmt_pct(overall_attr))
        lines.append(f"- **{DEMO_RECS[dim][0]}** (n = {fx.fmt_int(n)}): {text}")
    st.info("Segmen berikut menyimpang paling jauh di atas rata-rata attrition pada data terfilter:\n\n"
            + "\n".join(lines), icon="🧭")
else:
    st.success("Pada filter aktif, tidak ada segmen (usia, masa kerja, pendapatan, level, departemen) yang menonjol "
               "di atas rata-rata attrition, atau jumlah kelompok/sampel belum cukup. Pertahankan kebijakan SDM "
               "saat ini dan longgarkan filter untuk melihat segmen yang lebih luas.", icon="✅")
note("Rekomendasi dibangun dari asosiasi pada data observasional dan bersifat arah kebijakan awal, bukan bukti sebab-akibat. "
     "Validasi dengan data kualitatif (exit interview, survei) sebelum implementasi.")

st.markdown(
    "<div class='app-footer'>Dataset observasional — seluruh temuan menunjukkan asosiasi dan pola, "
    "bukan hubungan sebab-akibat maupun prediksi individu.<br>"
    "Data: <a href='https://github.com/IBM/employee-attrition-aif360' target='_blank' rel='noopener noreferrer'>"
    "IBM HR Analytics Employee Attrition &amp; Performance</a> (ODbL 1.0 / DbCL 1.0). "
    "File encoded: <a href='https://github.com/apoorva2796/DataSet/blob/master/HR_Analytics_Encoded.csv' "
    "target='_blank' rel='noopener noreferrer'>apoorva2796/DataSet</a>.</div>",
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Kredit pembuat (nama + tautan LinkedIn & GitHub)
# --------------------------------------------------------------------------- #
AUTHOR_NAME = "Eriel Setiawan Dewantoro"
LINKEDIN_URL = "https://www.linkedin.com/in/eriel-setiawan-dewantoro/"
GITHUB_URL = "https://github.com/erielsdewantoro"
_ICON_LI = ("<svg viewBox='0 0 24 24' width='18' height='18' fill='currentColor' aria-hidden='true'><path d='M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z'/></svg>")
_ICON_GH = ("<svg viewBox='0 0 24 24' width='18' height='18' fill='currentColor' aria-hidden='true'><path d='M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12'/></svg>")
_LINK_STYLE = "display:inline-flex;align-items:center;gap:6px;color:inherit;text-decoration:none;opacity:.8;"
st.markdown(
    "<div style='text-align:center;margin:4px 0 24px;font-size:.85rem;opacity:.9;'>"
    f"Dibuat oleh <b>{AUTHOR_NAME}</b> &nbsp;•&nbsp; "
    f"<a href='{LINKEDIN_URL}' target='_blank' rel='noopener noreferrer' style='{_LINK_STYLE}'>{_ICON_LI} LinkedIn</a>"
    " &nbsp;&nbsp; "
    f"<a href='{GITHUB_URL}' target='_blank' rel='noopener noreferrer' style='{_LINK_STYLE}'>{_ICON_GH} GitHub</a>"
    "</div>",
    unsafe_allow_html=True,
)
