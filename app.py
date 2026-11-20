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
    ("Profil Karyawan", ["Gender", "Age_Group"]),
    ("Pekerjaan", ["Department", "JobLevel", "OverTime", "Tenure_Group"]),
    ("Kompensasi", ["Income_Group"]),
    ("Work-Life Balance", ["WLB_Category"]),
]
assert sorted(c for _, cols in FILTER_GROUPS for c in cols) == sorted(fx.FILTER_COLUMNS)

st.set_page_config(page_title="Dashboard HR — Work-Life Balance Karyawan", page_icon="📊",
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


def insight_card(title: str, insights: list[dict], key: str, caption: str = "Diperbarui otomatis mengikuti filter yang Anda pilih.") -> None:
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
    st.error(f"**Data belum bisa ditampilkan.** {exc}")
    st.info("Pastikan file `data/clean_data.csv` tersedia dan memuat semua kolom yang dibutuhkan.")
    st.stop()
except Exception as exc:  # noqa: BLE001 - tampilkan pesan yang ramah, bukan stack trace
    st.error(f"**Terjadi kendala saat membaca data:** {exc}")
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
    st.markdown("<div class='sidebar-title'>Filter Data</div>", unsafe_allow_html=True)
    st.caption("Semua angka, grafik, rekomendasi, tabel, dan unduhan di halaman ini mengikuti filter berikut.")
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
    st.download_button("⬇ Data hasil filter (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_filtered_data.csv", mime="text/csv", width="stretch",
                       disabled=df.empty)
    st.download_button("⬇ Ringkasan temuan (CSV)", fx.build_insight_summary(df, context).to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_insight_summary.csv", mime="text/csv", width="stretch",
                       disabled=df.empty)

# --------------------------------------------------------------------------- #
# Header & status filter
# --------------------------------------------------------------------------- #
st.markdown(
    "<div class='app-eyebrow'>HR ANALYTICS</div>"
    "<h1 class='app-title'>Work-Life Balance Karyawan: Dari Data ke Keputusan HR</h1>"
    "<div class='app-subtitle'>Lihat bagaimana lembur, kepuasan kerja, dan profil karyawan berkaitan dengan "
    "keputusan karyawan untuk resign. Pola dari data historis karyawan ini disiapkan untuk membantu HR dan "
    "manajemen mengambil keputusan yang lebih tepat.</div>",
    unsafe_allow_html=True,
)
for msg in load_notes:
    st.warning(msg)

total = len(full_df)
st.markdown(
    f"<div class='status-bar'><b>{fx.fmt_int(len(df))}</b> dari {fx.fmt_int(total)} karyawan sedang dianalisis "
    f"({fx.fmt_pct(len(df) / total * 100)}) &nbsp;•&nbsp; Filter aktif: {context}</div>",
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("**Tidak ada karyawan yang cocok dengan filter saat ini.** "
               "Coba longgarkan salah satu filter atau klik *Pilih semua / Reset filter* di sidebar.")
    st.stop()

kpi = fx.compute_kpis(df)
attr, low = fx.attrition_flag(df), fx.low_wlb_flag(df)
overall_attr = kpi["attrition_rate"]
if len(df) < fx.MIN_N:
    st.warning(f"Filter ini hanya mencakup {len(df)} karyawan (kurang dari {fx.MIN_N} orang). Persentase bisa "
               "terlihat naik-turun tajam meski hanya 1–2 orang yang berubah, jadi baca dengan hati-hati.")

tabs = st.tabs(["Ringkasan", "Work-Life Balance", "Lembur & Kepuasan", "Karyawan Keluar", "Eksplorasi Data"])

# =========================================================================== #
# 1. OVERVIEW
# =========================================================================== #
with tabs[0]:
    section_header("Ringkasan Eksekutif",
                   "Potret cepat kondisi karyawan: seberapa seimbang hidup dan kerja mereka, seberapa sering lembur, "
                   "seberapa puas mereka, dan berapa banyak yang akhirnya memilih keluar.")

    sub_heading("Angka Kunci Perusahaan")
    kpi_row([
        ("Total Karyawan", fx.fmt_int(kpi["total_employees"]), "karyawan unik (berdasarkan nomor karyawan)", False),
        ("Rata-rata Skor WLB", fx.fmt_score(kpi["avg_wlb"]), "skala 1–4, makin tinggi makin baik", False),
        ("Karyawan dengan WLB Rendah", fx.fmt_pct(kpi["low_wlb_pct"]), f"{fx.fmt_int(kpi['low_wlb_count'])} karyawan merasa WLB-nya rendah", True),
        ("Tingkat Resign (Attrition)", fx.fmt_pct(kpi["attrition_rate"]), f"{fx.fmt_int(kpi['attrition_count'])} karyawan sudah keluar", True),
    ])
    kpi_row([
        ("Karyawan yang Lembur", fx.fmt_pct(kpi["overtime_pct"]), f"{fx.fmt_int(kpi['overtime_count'])} karyawan bekerja lembur", False),
        ("Rata-rata Kepuasan Kerja", fx.fmt_score(kpi["avg_job_sat"]), "skala 1–4, makin tinggi makin puas", False),
        ("Rata-rata Kepuasan Lingkungan Kerja", fx.fmt_score(kpi["avg_env_sat"]), "skala 1–4, makin tinggi makin puas", False),
    ])

    divider()
    sub_heading("Gambaran Umum & Perbandingan",
                "Garis putus-putus pada grafik tingkat resign = rata-rata seluruh karyawan pada filter ini. "
                "n = jumlah karyawan di tiap kelompok.")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        wlb_dist = fx.rate_table(df, "WLB_Category", low, fx.ordered_categories(df, "WLB_Category"))
        chart_card("Seberapa seimbang hidup dan kerja karyawan kita?",
                   fx.bar_count(wlb_dist, "", x_title="Kategori WLB", height=CH), "ov_wlb_dist")
    with c2:
        chart_card("Apakah karyawan yang lembur punya WLB lebih rendah?",
                   fx.bar_mean(fx.mean_table(df, "OverTime", "WorkLifeBalance", fx.ordered_categories(df, "OverTime")),
                               "", x_title="Status Lembur", height=CH), "ov_wlb_ot")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        chart_card("Apakah karyawan ber-WLB rendah lebih banyak yang resign?",
                   fx.bar_rate(fx.rate_table(df, "WLB_Category", attr, fx.ordered_categories(df, "WLB_Category")), "",
                               x_title="Kategori WLB", color_map=True, reference=overall_attr, height=CH), "ov_attr_wlb")
    with c4:
        chart_card("Departemen mana yang paling banyak kehilangan karyawan?",
                   fx.bar_rate(fx.rate_table(df, "Department", attr, fx.ordered_categories(df, "Department")), "",
                               x_title="Departemen", reference=overall_attr, height=CH), "ov_attr_dept")
    note("Catatan: grafik ini menunjukkan pola dari data historis karyawan untuk membantu pengambilan keputusan. "
         "Pola ini belum tentu berarti lembur adalah penyebab turunnya WLB, atau WLB rendah adalah penyebab "
         "karyawan resign. Pastikan lewat dialog langsung dengan karyawan.")

    divider()
    insight_card("Sorotan Utama untuk Manajemen", fx.overview_highlights(df), "ov_highlights")

# =========================================================================== #
# 2. WLB ANALYSIS
# =========================================================================== #
with tabs[1]:
    section_header("Kondisi Work-Life Balance",
                   "Di mana keseimbangan hidup dan kerja paling terjaga, dan di mana paling terancam: "
                   "per departemen, level jabatan, dan kelompok karyawan.")

    sub_heading("Departemen & Level Jabatan")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_card("Departemen mana yang keseimbangan hidup-kerjanya paling rendah?",
                   fx.bar_mean(fx.mean_table(df, "Department", "WorkLifeBalance", fx.ordered_categories(df, "Department")),
                               "", x_title="Departemen", height=CH), "wlb_avg_dept")
    with c2:
        chart_card("Departemen mana yang paling banyak karyawan ber-WLB rendah?",
                   fx.bar_rate(fx.rate_table(df, "Department", low, fx.ordered_categories(df, "Department")), "",
                               x_title="Departemen", y_title="Karyawan ber-WLB rendah (%)", event_label="Low WLB",
                               reference=kpi["low_wlb_pct"], height=CH), "wlb_low_dept")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        chart_card("Level jabatan mana yang paling banyak karyawan ber-WLB rendah?",
                   fx.bar_rate(fx.rate_table(df, "JobLevel", low, fx.ordered_categories(df, "JobLevel")), "",
                               x_title="Level Jabatan", y_title="Karyawan ber-WLB rendah (%)", event_label="Low WLB",
                               reference=kpi["low_wlb_pct"], height=CH), "wlb_low_level")
    with c4:
        rate, emp, ev = fx.rate_matrix(df, "Department", "JobLevel", low)
        chart_card("Kombinasi departemen dan level jabatan mana yang perlu perhatian khusus?",
                   fx.heatmap(rate, emp, ev, "", x_title="Level Jabatan", y_title="Departemen",
                              event_label="Low WLB", height=CH), "wlb_heat")

    divider()
    sub_heading("Komposisi WLB di Berbagai Kelompok")
    pct, cnt, n = fx.composition(df, "JobLevel", "WLB_Category")
    chart_card("Bagaimana komposisi WLB di tiap level jabatan?",
               fx.stacked_100(pct, cnt, n, "", x_title="Level Jabatan", height=CH), "wlb_comp_level")
    d1, d2 = st.columns(2, gap="medium")
    for col_ui, (col, label, key) in zip((d1, d2), (("Age_Group", "Kelompok Usia", "wlb_age"), ("Tenure_Group", "Masa Kerja", "wlb_tenure"))):
        with col_ui:
            pct, cnt, n = fx.composition(df, col, "WLB_Category")
            chart_card(f"Bagaimana komposisi WLB menurut {label}?",
                       fx.stacked_100(pct, cnt, n, "", x_title=label, height=CH), key)
    pct, cnt, n = fx.composition(df, "Income_Group", "WLB_Category")
    chart_card("Bagaimana komposisi WLB menurut kelompok pendapatan?",
               fx.stacked_100(pct, cnt, n, "", x_title="Kelompok Pendapatan", height=CH), "wlb_income")
    note("Cara membaca kategori WLB: Low (Rendah) = skor 1–2, Medium (Sedang) = skor 3, High (Tinggi) = skor 4. "
         "Label di bawah 4% disembunyikan agar grafik tetap bersih; angka lengkapnya muncul saat kursor diarahkan ke batang.")

    divider()
    insight_card("Temuan Penting: Work-Life Balance", fx.wlb_insights(df), "wlb_focus")

# =========================================================================== #
# 3. OVERTIME & SATISFACTION
# =========================================================================== #
with tabs[2]:
    section_header("Lembur & Kepuasan Kerja",
                   "Apakah karyawan yang lembur cenderung lebih sering resign, kurang puas, dan punya WLB lebih rendah?")

    sub_heading("Pola Lembur")
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        chart_card("Apakah karyawan yang lembur lebih sering resign dibanding yang tidak?",
                   fx.bar_rate(fx.rate_table(df, "OverTime", attr, fx.ordered_categories(df, "OverTime")), "",
                               x_title="Status Lembur", reference=overall_attr, height=CH), "ot_attr")
    with c2:
        chart_card("Berapa rata-rata WLB karyawan yang lembur dan yang tidak?",
                   fx.bar_mean(fx.mean_table(df, "OverTime", "WorkLifeBalance", fx.ordered_categories(df, "OverTime")),
                               "", x_title="Status Lembur", height=CH), "ot_wlb")

    divider()
    sub_heading("Kepuasan Kerja")
    c3, c4 = st.columns(2, gap="medium")
    with c3:
        pct, cnt, n = fx.composition(df, "OverTime", "JobSatisfaction_Category")
        chart_card("Seberapa puas karyawan terhadap pekerjaannya, yang lembur dan yang tidak?",
                   fx.stacked_100(pct, cnt, n, "", x_title="Status Lembur", height=CH), "ot_job")
    with c4:
        pct, cnt, n = fx.composition(df, "OverTime", "EnvironmentSatisfaction_Category")
        chart_card("Seberapa puas karyawan terhadap lingkungan kerjanya, yang lembur dan yang tidak?",
                   fx.stacked_100(pct, cnt, n, "", x_title="Status Lembur", height=CH), "ot_env")
    rate, emp, ev = fx.rate_matrix(df, "EnvironmentSatisfaction_Category", "JobSatisfaction_Category", attr)
    chart_card("Kombinasi kepuasan seperti apa yang paling banyak berujung pada resign?",
               fx.heatmap(rate, emp, ev, "", x_title="Kepuasan Kerja", y_title="Kepuasan Lingkungan Kerja", height=CH), "ot_heat")
    note("Cara membaca kategori kepuasan: Low (Rendah) = skor 1–2, Medium (Sedang) = skor 3, High (Tinggi) = skor 4. "
         "Kotak bertanda “–” berarti tidak ada karyawan pada kombinasi tersebut. Perhatikan jumlah karyawan (n) di tiap kotak: "
         "persentase pada kotak yang isinya sedikit orang bisa terlihat tinggi meski hanya 1–2 orang yang keluar.")

    divider()
    i1, i2 = st.columns(2, gap="medium")
    with i1:
        insight_card("Temuan Penting: Lembur", fx.overtime_insights(df), "ot_focus")
    with i2:
        insight_card("Temuan Penting: Kepuasan", fx.satisfaction_insights(df), "sat_focus")

# =========================================================================== #
# 4. ATTRITION ANALYSIS
# =========================================================================== #
with tabs[3]:
    section_header("Siapa yang Paling Banyak Keluar?",
                   "Profil karyawan yang paling banyak resign. Gunakan sebagai petunjuk arah prioritas program retensi, "
                   "bukan untuk menilai individu tertentu.")
    sub_heading("Tingkat resign per kelompok",
                f"Rata-rata keseluruhan pada filter ini: <b>{fx.fmt_pct(overall_attr)}</b> "
                f"({fx.fmt_int(kpi['attrition_count'])} dari {fx.fmt_int(kpi['total_employees'])} karyawan keluar). "
                "Batang merah menandai kelompok dengan tingkat resign tertinggi (pada grafik berwarna kategori, warna mengikuti kategori).")
    specs = [
        ("WLB_Category", "Kategori WLB", "Apakah WLB rendah diikuti tingkat resign yang lebih tinggi?", True),
        ("Department", "Departemen", "Departemen mana yang paling banyak kehilangan karyawan?", False),
        ("JobLevel", "Level Jabatan", "Di level jabatan mana karyawan paling banyak keluar?", False),
        ("Age_Group", "Kelompok Usia", "Kelompok usia mana yang paling banyak keluar?", False),
        ("Income_Group", "Kelompok Pendapatan", "Kelompok pendapatan mana yang paling banyak keluar?", False),
        ("Tenure_Group", "Masa Kerja", "Pada masa kerja berapa karyawan paling banyak keluar?", False),
        ("JobSatisfaction_Category", "Kepuasan Kerja", "Apakah karyawan yang kurang puas pada pekerjaannya lebih banyak keluar?", True),
        ("EnvironmentSatisfaction_Category", "Kepuasan Lingkungan Kerja", "Apakah karyawan yang kurang puas pada lingkungan kerja lebih banyak keluar?", True),
        ("OverTime", "Status Lembur", "Apakah karyawan yang lembur lebih banyak keluar?", False),
    ]
    for i in range(0, len(specs), 2):
        cols = st.columns(2, gap="medium")
        for col_ui, (col, label, title, cmap) in zip(cols, specs[i:i + 2]):
            with col_ui:
                chart_card(title, fx.bar_rate(fx.rate_table(df, col, attr, fx.ordered_categories(df, col)), "",
                                              x_title=label, color_map=cmap, reference=overall_attr, height=CH), f"attr_{col}")
    rate, emp, ev = fx.rate_matrix(df, "Department", "WLB_Category", attr)
    with cols[1]:  # 9 chart bar -> satu kolom tersisa di baris terakhir untuk heatmap
        chart_card("Tingkat resign: kombinasi departemen dan kategori WLB",
                   fx.heatmap(rate, emp, ev, "", x_title="Kategori WLB", y_title="Departemen", height=CH), "attr_heat")

    with st.expander("Rincian angka: jumlah karyawan dan jumlah yang keluar per kelompok"):
        parts = []
        for col, label, *_ in specs:
            t = fx.rate_table(df, col, attr, fx.ordered_categories(df, col)).reset_index()
            t.columns = ["Kelompok", "Jumlah Karyawan", "Jumlah Resign", "Tingkat Resign (%)"]
            t.insert(0, "Dimensi", label)
            t["Kelompok"] = t["Kelompok"].map(fx.fmt_label)
            parts.append(t)
        st.dataframe(pd.concat(parts, ignore_index=True), hide_index=True, width="stretch",
                     column_config={"Tingkat Resign (%)": st.column_config.NumberColumn(format="%.2f%%"),
                                    "Jumlah Karyawan": st.column_config.NumberColumn(format="%d"),
                                    "Jumlah Resign": st.column_config.NumberColumn(format="%d")})

    divider()
    insight_card("Temuan Penting: Karyawan Keluar", fx.attrition_insights(df), "attr_focus")

# =========================================================================== #
# 5. DATA EXPLORER
# =========================================================================== #
with tabs[4]:
    section_header("Eksplorasi Data", "Telusuri data karyawan sesuai filter dan cek kualitas datanya sebelum dipakai untuk mengambil keputusan.")
    st.info("🔒 **Privasi:** Nomor karyawan (`EmployeeNumber`) disembunyikan secara bawaan. Tampilkan hanya bila "
            "benar-benar perlu, dan jangan bagikan tampilan ini ke publik.")
    sub_heading("Tabel data")
    all_cols = list(df.columns)
    default_cols = [c for c in all_cols if c != "EmployeeNumber"]
    chosen = st.multiselect("Kolom yang ditampilkan", all_cols, default=default_cols, key="explorer_cols")
    query = st.text_input("Cari kata kunci (departemen, jabatan, kelompok usia, dll.)", key="explorer_search")
    view = df
    if query.strip():
        text_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c])]
        m = pd.Series(False, index=df.index)
        for c in text_cols:
            m |= df[c].astype(str).str.contains(query.strip(), case=False, na=False, regex=False)
        view = df[m]
    st.markdown(f"**{fx.fmt_int(len(view))}** baris ditampilkan dari {fx.fmt_int(len(df))} karyawan hasil filter "
                f"(total {fx.fmt_int(total)} karyawan).")
    if chosen:
        st.dataframe(view[chosen], hide_index=True, width="stretch", height=380)
    else:
        st.warning("Pilih minimal satu kolom agar tabel bisa ditampilkan.")
    st.download_button("⬇ Unduh data hasil filter (CSV)", df.to_csv(index=False).encode("utf-8"),
                       file_name="hr_analytics_filtered_data.csv", mime="text/csv", key="dl_explorer")
    st.caption("File unduhan memuat seluruh kolom dari data hasil filter (tanpa pencarian kata kunci), dengan encoding UTF-8.")

    divider()
    sub_heading("Kualitas data")
    q_full, q_f = fx.data_quality(full_df), fx.data_quality(df)
    qc = st.columns(4)
    qc[0].metric("Baris (terfilter / total)", f"{q_f['rows']:,} / {q_full['rows']:,}")
    qc[1].metric("Jumlah kolom", q_full["columns"])
    qc[2].metric("Total data kosong", f"{q_full['missing_total']:,}")
    qc[3].metric("Nomor karyawan ganda", f"{q_full['duplicate_employee']:,}")
    if q_full["duplicate_employee"] == 0 and q_full["missing_total"] == 0:
        st.success("Nomor karyawan unik dan tidak ada data kosong, jadi dataset siap dianalisis.")
    miss = full_df.isna().sum()
    miss = miss[miss > 0].rename("Jumlah Kosong").reset_index().rename(columns={"index": "Kolom"})
    if not miss.empty:
        st.dataframe(miss, hide_index=True, width="stretch")
    with st.expander("Detail tipe data"):
        info = pd.DataFrame({"Kolom": full_df.columns, "Tipe Data": full_df.dtypes.astype(str).values,
                             "Terisi": full_df.notna().sum().values, "Nilai Unik": full_df.nunique().values})
        st.dataframe(info, hide_index=True, width="stretch")
        st.caption("Level jabatan, WLB, kepuasan kerja, dan kepuasan lingkungan kerja berupa skala bertingkat (1–4), "
                   "sehingga dibaca per kategori, bukan sebagai angka rata-rata biasa.")

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


# Template rekomendasi per dimensi demografi / pekerjaan: {g} = kelompok, {r} = rate, {o} = rata-rata keseluruhan
DEMO_RECS = {
    "Age_Group": ("Kelompok usia",
                  "Karyawan **{g}** mencatat tingkat resign **{r}** (rata-rata keseluruhan {o}). Tawarkan jalur karier "
                  "dan pengembangan yang sesuai fase hidup mereka, misalnya mentoring, rotasi tugas, atau pola kerja fleksibel."),
    "Tenure_Group": ("Masa kerja",
                     "Karyawan dengan masa kerja **{g}** paling banyak keluar (**{r}**, rata-rata keseluruhan {o}). "
                     "Perkuat masa awal bergabung (onboarding), jadwalkan obrolan berkala dengan atasan, dan perjelas "
                     "peluang promosi pada fase masa kerja ini."),
    "Income_Group": ("Pendapatan",
                     "Kelompok pendapatan **{g}** mencatat tingkat resign **{r}** (rata-rata keseluruhan {o}). Bandingkan "
                     "gaji mereka dengan standar pasar dan tinjau paket penghargaan secara menyeluruh, misalnya insentif "
                     "kinerja, tunjangan, atau bonus retensi."),
    "JobLevel": ("Level jabatan",
                 "Level jabatan **{g}** mencatat tingkat resign **{r}** (rata-rata keseluruhan {o}). Evaluasi beban dan "
                 "ruang otonomi peran, buka peluang naik level yang jelas, dan siapkan calon pengganti untuk posisi "
                 "yang berisiko kosong."),
    "Department": ("Departemen",
                   "Departemen **{g}** mencatat tingkat resign **{r}** (rata-rata keseluruhan {o}). Gali akar masalahnya "
                   "bersama kepala departemen lewat wawancara keluar (*exit interview*) dan survei singkat, lalu tetapkan "
                   "target penurunan resign tiap kuartal."),
}

divider()
section_header("💡 HR Strategic Recommendations",
               "Saran langkah nyata untuk manajemen, disusun otomatis dari data dan berubah mengikuti filter yang Anda pilih.")
st.caption(f"Dasar penilaian: tingkat resign di atas {ATTR_ALERT_PCT:.0f}% • lembur di atas {OT_ALERT_PCT:.0f}% • "
           f"WLB dianggap rendah bila rata-rata skor di bawah {WLB_LOW_AVG:.2f} atau minimal {WLB_LOW_SHARE_PCT:.0f}% karyawan ber-WLB rendah. "
           f"Kelompok dengan kurang dari {fx.MIN_N} karyawan tidak dijadikan dasar rekomendasi karena persentasenya mudah menyesatkan.")

# ---- 1. Attrition ---------------------------------------------------------- #
st.markdown("##### 1. Menjaga Talenta Tetap Bertahan")
if overall_attr > ATTR_ALERT_PCT:
    by_dept = group_attrition(df, attr, "Department")
    msg = (f"**Tingkat resign {fx.fmt_pct(overall_attr)} sudah melewati batas aman {ATTR_ALERT_PCT:.0f}%**: "
           f"{fx.fmt_int(kpi['attrition_count'])} dari {fx.fmt_int(kpi['total_employees'])} karyawan memilih keluar. "
           "Setiap karyawan yang pergi membawa biaya rekrutmen, pelatihan ulang, dan hilangnya pengetahuan, "
           "jadi ini layak menjadi prioritas manajemen.\n\n")
    if not by_dept.empty:
        top_d = by_dept.index[0]
        msg += (f"- **Mulai dari {fx.fmt_label(top_d)}**, departemen dengan tingkat resign tertinggi "
                f"({fx.fmt_pct(by_dept.iloc[0]['rate'])}, dari {fx.fmt_int(by_dept.iloc[0]['n'])} karyawan). "
                f"Dalam 30 hari ke depan, ajak kepala departemen dan HR berbincang dengan karyawan kunci "
                f"(*stay interview*) untuk memahami apa yang membuat mereka bertahan atau mulai mempertimbangkan pergi.\n")
    by_ot = group_attrition(df, attr, "OverTime")
    if len(by_ot) >= 2:
        msg += (f"- Berdasarkan status lembur, tingkat resign tertinggi ada pada kelompok **{fx.fmt_label(by_ot.index[0])}** "
                f"({fx.fmt_pct(by_ot.iloc[0]['rate'])}), sedangkan terendah pada **{fx.fmt_label(by_ot.index[-1])}** "
                f"({fx.fmt_pct(by_ot.iloc[-1]['rate'])}). Jam kerja adalah salah satu tuas retensi yang bisa langsung Anda atur.\n")
    msg += ("- Tinjau kembali daya saing gaji dan jalur promosi, lalu pantau tingkat resign setiap bulan dengan "
            "target penurunan yang jelas (misalnya turun 2–3 poin persentase dalam dua kuartal).")
    st.info(msg, icon="🎯")
else:
    st.success(f"**Tingkat resign {fx.fmt_pct(overall_attr)} masih di bawah batas {ATTR_ALERT_PCT:.0f}%**, kabar yang baik. "
               "Pertahankan program retensi yang sudah berjalan dan tetap awasi kelompok yang tingkat resign-nya "
               "di atas rata-rata (lihat poin 3).", icon="✅")

# ---- 2. WLB & Overtime ----------------------------------------------------- #
st.markdown("##### 2. Beban Kerja, Lembur & Risiko Kelelahan (Burnout)")
ot_pct, avg_wlb, low_pct = kpi["overtime_pct"], kpi["avg_wlb"], kpi["low_wlb_pct"]
ot_high = ot_pct > OT_ALERT_PCT
wlb_low = (avg_wlb < WLB_LOW_AVG) or (low_pct >= WLB_LOW_SHARE_PCT)
snapshot = (f"Karyawan yang lembur **{fx.fmt_pct(ot_pct)}**, rata-rata skor WLB **{fx.fmt_score(avg_wlb)}** (skala 1–4), "
            f"dan **{fx.fmt_pct(low_pct)}** karyawan ber-WLB rendah.")
by_dept_low = group_attrition(df, low, "Department")
hot_dept = (f" Mulailah dari **{fx.fmt_label(by_dept_low.index[0])}**, tempat "
            f"{fx.fmt_pct(by_dept_low.iloc[0]['rate'])} karyawannya ber-WLB rendah." if not by_dept_low.empty else "")
if ot_high and wlb_low:
    st.info(f"**Waspada risiko burnout.** {snapshot}\n\n"
            "- **Audit beban kerja:** cari tahu tim dan peran mana yang paling sering lembur, lalu telusuri akarnya "
            "(kekurangan orang, pembagian tugas yang timpang, atau tenggat yang tidak realistis).\n"
            "- **Batasi lembur dengan aturan yang jelas:** tetapkan batas lembur per orang, persetujuan atasan, "
            "dan kompensasi yang adil, termasuk cuti pengganti.\n"
            "- **Hadirkan dukungan nyata:** survei kondisi karyawan tiap bulan, akses konseling, dan pelatihan manajer "
            "agar mampu mengenali tanda kelelahan sebelum karyawan memutuskan resign." + hot_dept, icon="🔥")
elif ot_high:
    st.info(f"**Lembur tinggi, tetapi WLB masih terjaga.** {snapshot}\n\n"
            "Ini peringatan dini yang masih bisa dicegah: tinjau ulang beban kerja dan bagi ulang tugas sebelum "
            "kelelahan menggerus WLB dan kepuasan karyawan." + hot_dept, icon="⚠️")
elif wlb_low:
    st.info(f"**WLB rendah, padahal lembur terkendali.** {snapshot}\n\n"
            "Penyebabnya kemungkinan bukan jam lembur. Gali faktor lain: fleksibilitas jadwal dan lokasi kerja, "
            "lamanya perjalanan ke kantor, serta budaya membalas pesan di luar jam kerja. Opsi kerja hibrida atau "
            "jam kerja fleksibel layak dicoba." + hot_dept,
            icon="⚠️")
else:
    st.success(f"**Beban kerja tergolong sehat.** {snapshot}\n\n"
               "Pertahankan kebijakan yang berjalan dan terus pantau lembur serta WLB secara rutin agar kondisi ini tetap terjaga.", icon="✅")

# ---- 3. Demografi / segmen ------------------------------------------------- #
st.markdown("##### 3. Kelompok yang Perlu Perhatian Khusus")
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
        lines.append(f"- **{DEMO_RECS[dim][0]}** ({fx.fmt_int(n)} karyawan): {text}")
    st.info("Kelompok berikut paling jauh melampaui rata-rata tingkat resign pada data yang sedang ditampilkan:\n\n"
            + "\n".join(lines), icon="🧭")
else:
    st.success("Pada filter ini, belum ada kelompok (usia, masa kerja, pendapatan, level jabatan, departemen) yang "
               "tingkat resign-nya menonjol di atas rata-rata, atau jumlah karyawannya terlalu sedikit untuk dibaca "
               "dengan yakin. Pertahankan kebijakan SDM saat ini, atau longgarkan filter untuk melihat gambaran yang lebih luas.", icon="✅")
note("Catatan: rekomendasi ini disusun dari pola data historis karyawan dan berfungsi sebagai arah awal, bukan kepastian "
     "penyebab. Sebelum dijalankan, konfirmasi dulu lewat percakapan langsung, wawancara keluar, atau survei karyawan.")

st.markdown("<div class='app-footer'>Seluruh temuan dibangun dari pola data historis karyawan untuk membantu "
            "pengambilan keputusan. Pola ini menunjukkan keterkaitan, bukan bukti sebab-akibat, dan tidak "
            "dimaksudkan untuk menilai atau memprediksi individu tertentu.</div>", unsafe_allow_html=True)

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
