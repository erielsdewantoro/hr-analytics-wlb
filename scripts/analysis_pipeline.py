# %% [markdown]
# # Analisis Work-Life Balance dan Attrition Karyawan
#
# **Judul:** Analisis Work-Life Balance Karyawan: Pengaruh Overtime,
# Kepuasan Kerja, dan Demografi terhadap Risiko Attrition
#
# Script ini disusun untuk dijalankan di VS Code menggunakan Python.
# Letakkan HR_Analytics_Encoded.csv di data/raw/ pada root project.
#
# Catatan konteks:
# - Industri/perusahaan dan periode pengamatan tidak tersedia pada file.
# - Attrition diperlakukan sebagai status keluar (`Yes`) pada dataset.
# - Angka attrition rate adalah proporsi pada dataset, bukan turnover tahunan.
# - Encoding kategorikal diasumsikan mengikuti pemetaan dataset HR Analytics
#   yang umum digunakan. Periksa kembali pemetaan jika sumber data berbeda.

# %% [markdown]
# ## BAB 1 — BUSINESS UNDERSTANDING & SETUP
#
# ### Konteks bisnis
# Analisis ditujukan untuk membantu HR memahami distribusi work-life balance,
# membandingkan kondisi antar-departemen dan job level, serta mengevaluasi
# keterkaitan overtime, kepuasan, dan attrition.
#
# **Audiens:** HR Manager, HR Analyst, dan manajemen.
#
# **Pertanyaan bisnis utama:**
# 1. Bagaimana distribusi WLB karyawan?
# 2. Apakah WLB berbeda antar-departemen dan job level?
# 3. Apakah karyawan yang overtime memiliki WLB lebih rendah?
# 4. Bagaimana WLB berkaitan dengan kepuasan kerja dan lingkungan kerja?
# 5. Bagaimana attrition rate pada kelompok WLB, overtime, dan demografi?
# 6. Kelompok mana yang perlu menjadi prioritas pemeriksaan HR?
#
# ### Import library dan konfigurasi

# %%
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from scipy.stats import chi2_contingency, mannwhitneyu

warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_theme(style="whitegrid", palette="Set2")

# File input dan folder output
BASE_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
PROJECT_DIR = BASE_DIR.parent if BASE_DIR.name == "scripts" else BASE_DIR
INPUT_FILE = PROJECT_DIR / "data" / "raw" / "HR_Analytics_Encoded.csv"
PROCESSED_DATA_FILE = PROJECT_DIR / "data" / "clean_data.csv"
OUTPUT_DIR = PROJECT_DIR / "output_hr_analytics"
CHART_DIR = OUTPUT_DIR / "charts"
OUTPUT_DIR.mkdir(exist_ok=True)
CHART_DIR.mkdir(exist_ok=True)

# Konfigurasi kolom utama
TARGET_COL = "Attrition"
WLB_COL = "WorkLifeBalance"
OVERTIME_COL = "OverTime"

NUMERIC_COLS = [
    "Age", "MonthlyIncome", "YearsAtCompany", "JobLevel",
    "WorkLifeBalance", "JobSatisfaction", "EnvironmentSatisfaction"
]
CATEGORICAL_COLS = [
    "Department", "Gender", "OverTime", "Attrition"
]
SATISFACTION_COLS = ["JobSatisfaction", "EnvironmentSatisfaction"]

# Pemetaan kode kategorikal pada dataset HR Analytics yang umum.
# Jika dokumentasi sumber data berbeda, sesuaikan mapping ini.
CATEGORY_MAPS = {
    "Attrition": {0: "No", 1: "Yes"},
    "OverTime": {0: "No", 1: "Yes"},
    # The provided encoded file maps 0 to Male and 1 to Female.
    "Gender": {0: "Male", 1: "Female"},
    "Department": {
        0: "Human Resources",
        1: "Research & Development",
        2: "Sales",
    },
}

SATISFACTION_MAP = {
    1: "Low",
    2: "Medium",
    3: "High",
    4: "Very High",
}
WLB_SCALE_MAP = {
    1: "Bad",
    2: "Good",
    3: "Better",
    4: "Best",
}

# Rentang valid berdasarkan definisi skala pada dataset.
VALID_RANGES = {
    "WorkLifeBalance": (1, 4),
    "JobSatisfaction": (1, 4),
    "EnvironmentSatisfaction": (1, 4),
    "JobLevel": (1, 5),
    "Age": (18, 100),
    "YearsAtCompany": (0, 60),
    "MonthlyIncome": (0, None),
}

# Load data
if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"File tidak ditemukan: {INPUT_FILE}\n"
        "Letakkan CSV di folder script atau ubah INPUT_FILE."
    )

df_raw = pd.read_csv(INPUT_FILE)
df = df_raw.copy()

print("\n=== BAB 1 | DATASET AWAL ===")
print(f"Ukuran dataset: {df.shape[0]:,} baris x {df.shape[1]} kolom")
print("\nLima baris pertama:")
print(df.head())
print("\nInformasi tipe data:")
df.info()
print("\nStatistik deskriptif:")
print(df.describe(include="all").T)

# %% [markdown]
# ### Ringkasan Insight Bisnis
# File yang dianalisis berisi 1.470 baris dan 36 kolom. Dataset menyediakan
# atribut demografi, pekerjaan, kepuasan, WLB, overtime, dan status attrition.
# Karena periode pengamatan dan identitas perusahaan tidak tersedia, hasil
# harus dibaca sebagai gambaran dataset, bukan tren dari waktu ke waktu.

# %% [markdown]
# ## BAB 2 — DATA PROFILING & CLEANING
#
# Tahap ini memeriksa kualitas data, menstandarkan encoding, dan membuat
# variabel turunan. Missing value numerik diisi median dan kategorikal diisi
# modus sebagai fallback. Nilai di luar rentang logis pada skala utama
# diubah menjadi missing sebelum imputasi. Outlier numerik hanya ditandai,
# tidak otomatis dihapus, karena nilai ekstrem seperti masa kerja atau gaji
# dapat merupakan kondisi karyawan yang valid.

# %%
print("\n=== BAB 2 | PROFILING AWAL ===")
print("\nTipe data:")
print(df.dtypes)
print("\nMissing values:")
print(df.isna().sum().sort_values(ascending=False))
print(f"\nDuplikat seluruh baris: {df.duplicated().sum():,}")

if "EmployeeNumber" in df.columns:
    print(
        "EmployeeNumber duplikat:",
        df["EmployeeNumber"].duplicated().sum()
    )

# Hilangkan kolom indeks ekspor dan kolom konstan/tidak informatif.
drop_candidates = ["Unnamed: 0", "EmployeeCount", "Over18", "StandardHours"]
drop_cols = [col for col in drop_candidates if col in df.columns]
df = df.drop(columns=drop_cols)

# Hapus duplikat baris penuh. EmployeeNumber dipertahankan sebagai identifier.
df = df.drop_duplicates().copy()

# Konversi kolom yang seharusnya numerik.
numeric_candidates = [
    col for col in NUMERIC_COLS
    + ["EmployeeNumber", "TotalWorkingYears", "DailyRate", "HourlyRate",
       "MonthlyRate", "DistanceFromHome", "NumCompaniesWorked",
       "YearsInCurrentRole", "YearsSinceLastPromotion",
       "YearsWithCurrManager", "TrainingTimesLastYear",
       "PercentSalaryHike", "PerformanceRating", "Education",
       "JobInvolvement", "RelationshipSatisfaction", "StockOptionLevel",
       "BusinessTravel", "EducationField", "JobRole", "MaritalStatus"]
    if col in df.columns
]
for col in numeric_candidates:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Validasi rentang kolom utama.
invalid_counts = {}
for col, (lower, upper) in VALID_RANGES.items():
    if col not in df.columns:
        continue
    invalid = df[col].notna() & (df[col] < lower)
    if upper is not None:
        invalid |= df[col].notna() & (df[col] > upper)
    invalid_counts[col] = int(invalid.sum())
    df.loc[invalid, col] = np.nan

print("\nJumlah nilai di luar rentang yang ditangani:")
print(pd.Series(invalid_counts, name="invalid_count"))

# Standarisasi kategori: decode angka, rapikan teks bila sudah berbentuk string.
for col, mapping in CATEGORY_MAPS.items():
    if col not in df.columns:
        continue
    numeric_version = pd.to_numeric(df[col], errors="coerce")
    decoded = numeric_version.map(mapping)
    # Jika sumber sudah berupa teks, pertahankan teks yang sudah dinormalisasi.
    text_values = df[col].astype("string").str.strip()
    df[col] = decoded.where(decoded.notna(), text_values)
    df[col] = df[col].replace({"<NA>": np.nan, "": np.nan})

# Imputasi fallback: median untuk numerik, modus untuk kategorikal.
for col in df.columns:
    if df[col].isna().any():
        if pd.api.types.is_numeric_dtype(df[col]):
            median_value = df[col].median()
            df[col] = df[col].fillna(median_value)
        else:
            mode_values = df[col].mode(dropna=True)
            fill_value = mode_values.iloc[0] if not mode_values.empty else "Unknown"
            df[col] = df[col].fillna(fill_value)

# Label skala WLB dan kepuasan. Skor numerik asli tetap dipertahankan.
if WLB_COL in df.columns:
    df["WLB_Scale_Label"] = df[WLB_COL].map(WLB_SCALE_MAP)
for col in SATISFACTION_COLS:
    if col in df.columns:
        df[f"{col}_Label"] = df[col].map(SATISFACTION_MAP)

# Kategori analitis WLB: skor 1-2 rendah, 3 sedang, 4 tinggi.
# Pengelompokan ini adalah keputusan analitis, bukan kategori asli dataset.
if WLB_COL in df.columns:
    df["WLB_Category"] = pd.cut(
        df[WLB_COL],
        bins=[0, 2, 3, 4],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    ).astype("string")

# Kategori kepuasan: skor 1-2 rendah, 3 sedang, 4 tinggi.
for col in SATISFACTION_COLS:
    if col in df.columns:
        df[f"{col}_Category"] = pd.cut(
            df[col],
            bins=[0, 2, 3, 4],
            labels=["Low", "Medium", "High"],
            include_lowest=True,
        ).astype("string")

# Kelompok umur.
if "Age" in df.columns:
    df["Age_Group"] = pd.cut(
        df["Age"],
        bins=[17, 25, 35, 45, np.inf],
        labels=["18-25", "26-35", "36-45", "46+"],
        include_lowest=True,
    ).astype("string")

# Kelompok pendapatan berdasarkan kuartil aktual.
if "MonthlyIncome" in df.columns:
    try:
        df["Income_Group"] = pd.qcut(
            df["MonthlyIncome"],
            q=4,
            labels=["Q1 - Lower", "Q2 - Lower Middle",
                    "Q3 - Upper Middle", "Q4 - Upper"],
            duplicates="drop",
        ).astype("string")
    except ValueError:
        df["Income_Group"] = "Not classified"

# Kelompok masa kerja.
if "YearsAtCompany" in df.columns:
    df["Tenure_Group"] = pd.cut(
        df["YearsAtCompany"],
        bins=[-1, 2, 5, 10, np.inf],
        labels=["0-2 years", "3-5 years", "6-10 years", "10+ years"],
        include_lowest=True,
    ).astype("string")

# Outlier screening menggunakan IQR. Tidak dilakukan penghapusan otomatis.
outlier_rows = []
for col in ["Age", "MonthlyIncome", "YearsAtCompany"]:
    if col not in df.columns:
        continue
    q1, q3 = df[col].quantile([0.25, 0.75])
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    count = int(((df[col] < lower_bound) | (df[col] > upper_bound)).sum())
    outlier_rows.append({
        "column": col,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "outlier_count": count,
    })
outlier_report = pd.DataFrame(outlier_rows)
outlier_report.to_csv(OUTPUT_DIR / "outlier_report.csv", index=False)

print("\n=== RINGKASAN SEBELUM DAN SESUDAH CLEANING ===")
print(f"Baris sebelum: {len(df_raw):,} | sesudah: {len(df):,}")
print(f"Kolom sebelum: {df_raw.shape[1]} | sesudah: {df.shape[1]}")
print(f"Missing values tersisa: {int(df.isna().sum().sum())}")
print("\nOutlier screening (IQR):")
print(outlier_report.to_string(index=False))
print("\nPreview setelah cleaning:")
print(df.head())

# %% [markdown]
# ### Ringkasan Insight Bisnis
# Dataset awal tidak memiliki missing value dan tidak memiliki duplikat baris
# penuh berdasarkan pemeriksaan awal. Kolom indeks ekspor dan kolom konstan
# dihapus karena tidak memberi informasi analitis. Encoding kategori diubah
# menjadi label agar mudah dibaca di Tableau dan Streamlit.
#
# Outlier tidak otomatis dibuang. Karyawan dengan gaji atau masa kerja tinggi
# belum tentu salah input. Kategori WLB Low/Medium/High dibuat untuk
# mempermudah segmentasi; skor aslinya tetap disimpan agar informasi tidak
# hilang. Kelompok pendapatan menggunakan kuartil dataset, sehingga batasnya
# dapat berubah jika data diperbarui.

# %% [markdown]
# ## BAB 3 — EXPLORATORY DATA ANALYSIS (EDA) & VISUALISASI STATISTIK
#
# Visualisasi disimpan sebagai PNG pada folder `output_hr_analytics/charts`.
# Attrition rate dihitung sebagai jumlah `Attrition = Yes` dibagi jumlah
# karyawan pada kelompok terkait.

# %%
print("\n=== BAB 3 | EDA ===")

def attrition_rate_table(data, group_cols):
    """Menghasilkan jumlah karyawan, jumlah attrition, dan attrition rate."""
    result = (
        data.groupby(group_cols, observed=False)
        .agg(
            employee_count=(TARGET_COL, "size"),
            attrition_count=(TARGET_COL, lambda x: (x == "Yes").sum()),
        )
        .reset_index()
    )
    result["attrition_rate_pct"] = (
        result["attrition_count"] / result["employee_count"] * 100
    )
    return result

def save_barplot(data, x, y, title, xlabel, ylabel, filename,
                 order=None, rotate=0):
    """Menyimpan bar chart dengan label nilai."""
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.barplot(data=data, x=x, y=y, order=order, ax=ax, errorbar=None, color="steelblue")
    ax.set_title(title, fontsize=13, weight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=rotate)
    for container in ax.containers:
        ax.bar_label(container, fmt="%.1f", padding=3)
    fig.tight_layout()
    fig.savefig(CHART_DIR / filename, dpi=160, bbox_inches="tight")
    plt.show()
    plt.close(fig)

# Distribusi WLB
wlb_dist = (
    df["WLB_Category"].value_counts()
    .reindex(["Low", "Medium", "High"])
    .rename_axis("WLB_Category")
    .reset_index(name="employee_count")
)
print("\nDistribusi WLB:")
print(wlb_dist)

fig, ax = plt.subplots(figsize=(8, 5))
sns.barplot(
    data=wlb_dist, x="WLB_Category", y="employee_count",
    order=["Low", "Medium", "High"], ax=ax, errorbar=None, color="steelblue"
)
ax.set_title("Distribusi Work-Life Balance Karyawan")
ax.set_xlabel("Kategori Work-Life Balance")
ax.set_ylabel("Jumlah karyawan")
for container in ax.containers:
    ax.bar_label(container, padding=3)
fig.tight_layout()
fig.savefig(CHART_DIR / "01_wlb_distribution.png", dpi=160)
plt.show()
plt.close(fig)

# Rata-rata WLB per departemen dan job level
wlb_department = (
    df.groupby("Department", observed=False)
    .agg(
        employee_count=(WLB_COL, "size"),
        average_wlb=(WLB_COL, "mean"),
        median_wlb=(WLB_COL, "median"),
    ).reset_index()
)
wlb_joblevel = (
    df.groupby("JobLevel", observed=False)
    .agg(
        employee_count=(WLB_COL, "size"),
        average_wlb=(WLB_COL, "mean"),
        median_wlb=(WLB_COL, "median"),
    ).reset_index()
)
print("\nRata-rata WLB per department:")
print(wlb_department.round(2).to_string(index=False))
print("\nRata-rata WLB per job level:")
print(wlb_joblevel.round(2).to_string(index=False))

save_barplot(
    wlb_department, "Department", "average_wlb",
    "Rata-rata WLB berdasarkan Departemen",
    "Departemen", "Rata-rata skor WLB (1-4)",
    "02_wlb_by_department.png", rotate=15
)
save_barplot(
    wlb_joblevel, "JobLevel", "average_wlb",
    "Rata-rata WLB berdasarkan Job Level",
    "Job level", "Rata-rata skor WLB (1-4)",
    "03_wlb_by_joblevel.png"
)

# WLB berdasarkan overtime
wlb_overtime = (
    df.groupby(OVERTIME_COL, observed=False)
    .agg(
        employee_count=(WLB_COL, "size"),
        average_wlb=(WLB_COL, "mean"),
        median_wlb=(WLB_COL, "median"),
    ).reset_index()
)
print("\nWLB berdasarkan overtime:")
print(wlb_overtime.round(2).to_string(index=False))
save_barplot(
    wlb_overtime, OVERTIME_COL, "average_wlb",
    "Perbandingan WLB berdasarkan Status Overtime",
    "Overtime", "Rata-rata skor WLB (1-4)",
    "04_wlb_by_overtime.png"
)

# WLB vs kepuasan kerja dan lingkungan kerja
satisfaction_by_wlb = (
    df.groupby("WLB_Category", observed=False)
    .agg(
        employee_count=(WLB_COL, "size"),
        average_job_satisfaction=("JobSatisfaction", "mean"),
        average_environment_satisfaction=("EnvironmentSatisfaction", "mean"),
    ).reset_index()
)
print("\nKepuasan berdasarkan WLB:")
print(satisfaction_by_wlb.round(2).to_string(index=False))

satisfaction_long = satisfaction_by_wlb.melt(
    id_vars="WLB_Category",
    value_vars=[
        "average_job_satisfaction",
        "average_environment_satisfaction",
    ],
    var_name="satisfaction_type",
    value_name="average_score",
)
fig, ax = plt.subplots(figsize=(9, 5))
sns.barplot(
    data=satisfaction_long, x="WLB_Category",
    y="average_score", hue="satisfaction_type",
    order=["Low", "Medium", "High"], ax=ax
)
ax.set_title("Kepuasan Kerja dan Lingkungan Kerja menurut Kategori WLB")
ax.set_xlabel("Kategori WLB")
ax.set_ylabel("Rata-rata skor (1-4)")
ax.legend(
    title="Jenis kepuasan",
    labels=["Job Satisfaction", "Environment Satisfaction"]
)
fig.tight_layout()
fig.savefig(CHART_DIR / "05_satisfaction_by_wlb.png", dpi=160)
plt.show()
plt.close(fig)

# Attrition rate pada seluruh segmen yang diminta
segment_columns = [
    "WLB_Category", OVERTIME_COL, "Department", "JobLevel",
    "Age_Group", "Income_Group", "Tenure_Group"
]
attrition_tables = {}
for col in segment_columns:
    table = attrition_rate_table(df, [col])
    attrition_tables[col] = table
    print(f"\nAttrition rate berdasarkan {col}:")
    print(table.round(2).to_string(index=False))

# Chart attrition per WLB dan overtime
attrition_wlb = attrition_tables["WLB_Category"]
save_barplot(
    attrition_wlb, "WLB_Category", "attrition_rate_pct",
    "Attrition Rate berdasarkan Work-Life Balance",
    "Kategori WLB", "Attrition rate (%)",
    "06_attrition_by_wlb.png",
    order=["Low", "Medium", "High"]
)

attrition_ot = attrition_tables[OVERTIME_COL]
save_barplot(
    attrition_ot, OVERTIME_COL, "attrition_rate_pct",
    "Attrition Rate berdasarkan Overtime",
    "Overtime", "Attrition rate (%)",
    "07_attrition_by_overtime.png"
)

# %% [markdown]
# ### Ringkasan Insight Bisnis
# Bab ini menghasilkan gambaran distribusi WLB, perbandingan WLB berdasarkan
# departemen dan job level, perbedaan kelompok overtime, serta attrition rate
# pada berbagai segmen. Angka aktual dicetak ketika script dijalankan.
# HR sebaiknya membandingkan rate bersama jumlah karyawan pada setiap segmen:
# persentase tinggi dari kelompok yang sangat kecil perlu ditafsirkan hati-hati.

# %% [markdown]
# ## BAB 4 — FEATURE ENGINEERING / INSIGHTS EXTRACTION
#
# Tabel agregat dibuat agar dapat langsung digunakan sebagai sumber data
# Tableau atau Streamlit. Uji chi-square mengevaluasi asosiasi antarvariabel
# kategorikal. Mann-Whitney membandingkan distribusi skor WLB antara dua
# kelompok overtime. Hasil uji bukan bukti sebab-akibat.

# %%
print("\n=== BAB 4 | INSIGHTS EXTRACTION ===")

# Tabel agregat lintas dimensi
attrition_department_wlb = attrition_rate_table(
    df, ["Department", "WLB_Category"]
)
attrition_overtime_wlb = attrition_rate_table(
    df, [OVERTIME_COL, "WLB_Category"]
)

# Profil kepuasan berdasarkan WLB
satisfaction_wlb_export = (
    df.groupby("WLB_Category", observed=False)
    .agg(
        employee_count=(TARGET_COL, "size"),
        average_job_satisfaction=("JobSatisfaction", "mean"),
        average_environment_satisfaction=("EnvironmentSatisfaction", "mean"),
        attrition_rate_pct=(TARGET_COL, lambda x: (x == "Yes").mean() * 100),
    ).reset_index()
)

# Profil risiko tinggi: WLB rendah + overtime + kepuasan kerja rendah.
# Definisi operasional ini merupakan segmentasi untuk pemeriksaan HR,
# bukan model prediksi atau label risiko yang tervalidasi.
high_risk_mask = (
    (df["WLB_Category"] == "Low")
    & (df[OVERTIME_COL] == "Yes")
    & (df["JobSatisfaction"] <= 2)
)
high_risk_profile = df.loc[high_risk_mask].copy()
if not high_risk_profile.empty:
    high_risk_summary = pd.DataFrame([{
        "segment": "Low WLB + Overtime Yes + Job Satisfaction 1-2",
        "employee_count": len(high_risk_profile),
        "attrition_count": (high_risk_profile[TARGET_COL] == "Yes").sum(),
        "attrition_rate_pct": (
            (high_risk_profile[TARGET_COL] == "Yes").mean() * 100
        ),
        "average_age": high_risk_profile["Age"].mean(),
        "average_monthly_income": high_risk_profile["MonthlyIncome"].mean(),
        "average_tenure": high_risk_profile["YearsAtCompany"].mean(),
    }])
else:
    high_risk_summary = pd.DataFrame([{
        "segment": "Low WLB + Overtime Yes + Job Satisfaction 1-2",
        "employee_count": 0,
        "attrition_count": 0,
        "attrition_rate_pct": np.nan,
        "average_age": np.nan,
        "average_monthly_income": np.nan,
        "average_tenure": np.nan,
    }])

print("\nProfil kelompok prioritas pemeriksaan HR:")
print(high_risk_summary.round(2).to_string(index=False))

# Uji chi-square untuk asosiasi kategori.
def run_chi_square(data, col_a, col_b):
    contingency = pd.crosstab(data[col_a], data[col_b])
    if contingency.shape[0] < 2 or contingency.shape[1] < 2:
        return {
            "variable_1": col_a, "variable_2": col_b,
            "chi2": np.nan, "dof": np.nan, "p_value": np.nan,
            "cramers_v": np.nan, "interpretation": "Tidak cukup kategori"
        }
    chi2, p_value, dof, _ = chi2_contingency(contingency)
    n = contingency.to_numpy().sum()
    min_dim = min(contingency.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 and n > 0 else np.nan
    return {
        "variable_1": col_a,
        "variable_2": col_b,
        "chi2": chi2,
        "dof": dof,
        "p_value": p_value,
        "cramers_v": cramers_v,
        "interpretation": (
            "Ada asosiasi statistik (p < 0.05)"
            if p_value < 0.05 else
            "Belum ada bukti asosiasi statistik (p >= 0.05)"
        ),
    }

chi_square_pairs = [
    ("WLB_Category", TARGET_COL),
    (OVERTIME_COL, TARGET_COL),
    ("WLB_Category", OVERTIME_COL),
    ("Department", TARGET_COL),
    ("Age_Group", TARGET_COL),
    ("Tenure_Group", TARGET_COL),
]
chi_square_results = pd.DataFrame([
    run_chi_square(df, a, b) for a, b in chi_square_pairs
])
print("\nHasil uji chi-square:")
print(chi_square_results.round(4).to_string(index=False))

# Mann-Whitney U untuk skor WLB overtime yes vs no.
ot_yes = df.loc[df[OVERTIME_COL] == "Yes", WLB_COL]
ot_no = df.loc[df[OVERTIME_COL] == "No", WLB_COL]
if len(ot_yes) and len(ot_no):
    u_stat, mw_p = mannwhitneyu(ot_yes, ot_no, alternative="two-sided")
    mann_whitney_result = pd.DataFrame([{
        "comparison": "WLB: Overtime Yes vs No",
        "median_overtime_yes": ot_yes.median(),
        "median_overtime_no": ot_no.median(),
        "u_statistic": u_stat,
        "p_value": mw_p,
        "interpretation": (
            "Distribusi WLB berbeda secara statistik (p < 0.05)"
            if mw_p < 0.05 else
            "Belum ada bukti perbedaan distribusi WLB (p >= 0.05)"
        ),
    }])
else:
    mann_whitney_result = pd.DataFrame()

print("\nHasil Mann-Whitney:")
print(mann_whitney_result.round(4).to_string(index=False))

# Key findings yang dihitung otomatis dari dataset.
def safe_rate(group):
    return (group[TARGET_COL] == "Yes").mean() * 100 if len(group) else np.nan

findings = []
overall_attrition = safe_rate(df)
findings.append(
    f"Attrition rate keseluruhan pada dataset adalah {overall_attrition:.2f}% "
    f"({(df[TARGET_COL] == 'Yes').sum()} dari {len(df)} karyawan)."
)

for category in ["Low", "Medium", "High"]:
    subset = df[df["WLB_Category"] == category]
    if len(subset):
        findings.append(
            f"Kelompok WLB {category}: {len(subset)} karyawan, "
            f"attrition rate {safe_rate(subset):.2f}%."
        )

if len(ot_yes) and len(ot_no):
    findings.append(
        f"Rata-rata WLB overtime Yes = {ot_yes.mean():.2f}, "
        f"sedangkan overtime No = {ot_no.mean():.2f}."
    )

if not wlb_department.empty:
    lowest_dept = wlb_department.loc[wlb_department["average_wlb"].idxmin()]
    highest_dept = wlb_department.loc[wlb_department["average_wlb"].idxmax()]
    findings.append(
        f"Rata-rata WLB terendah terdapat pada {lowest_dept['Department']} "
        f"({lowest_dept['average_wlb']:.2f}); tertinggi pada "
        f"{highest_dept['Department']} ({highest_dept['average_wlb']:.2f})."
    )

if not wlb_joblevel.empty:
    lowest_level = wlb_joblevel.loc[wlb_joblevel["average_wlb"].idxmin()]
    findings.append(
        f"Job level dengan rata-rata WLB terendah adalah "
        f"{int(lowest_level['JobLevel'])} ({lowest_level['average_wlb']:.2f})."
    )

if len(high_risk_profile):
    findings.append(
        f"Segmen WLB rendah + overtime + kepuasan kerja rendah berisi "
        f"{len(high_risk_profile)} karyawan; attrition rate "
        f"{safe_rate(high_risk_profile):.2f}%."
    )
else:
    findings.append(
        "Tidak ditemukan karyawan yang memenuhi definisi segmen prioritas "
        "WLB rendah + overtime + kepuasan kerja rendah."
    )

if not chi_square_results.empty:
    significant = chi_square_results.loc[
        chi_square_results["p_value"] < 0.05, ["variable_1", "variable_2"]
    ]
    if len(significant):
        pairs = [
            f"{row.variable_1} dengan {row.variable_2}"
            for row in significant.itertuples()
        ]
        findings.append(
            "Uji chi-square menemukan asosiasi statistik pada: "
            + "; ".join(pairs) + "."
        )
    else:
        findings.append(
            "Uji chi-square pada pasangan variabel yang diperiksa belum "
            "menemukan asosiasi statistik pada taraf 5%."
        )

print("\n=== KEY FINDINGS OTOMATIS ===")
for number, finding in enumerate(findings[:10], start=1):
    print(f"{number}. {finding}")

print("\n=== REKOMENDASI BISNIS UNTUK HR ===")
recommendations = [
    "Audit distribusi beban kerja dan frekuensi overtime per departemen.",
    "Tinjau kelompok WLB rendah bersama data absensi, workload, dan exit interview jika tersedia.",
    "Evaluasi pola penjadwalan dan kebutuhan kapasitas pada tim dengan overtime tinggi.",
    "Gunakan survei pulse untuk menggali penyebab kepuasan kerja dan lingkungan kerja rendah.",
    "Prioritaskan percakapan retensi secara manusiawi; jangan menjadikan segmentasi ini dasar keputusan otomatis terhadap individu.",
    "Pantau perubahan indikator secara berkala dengan data bertanggal agar tren dapat dianalisis.",
]
for item in recommendations:
    print(f"- {item}")

# %% [markdown]
# ### Ringkasan Insight Bisnis
# Gunakan hasil agregasi dan pengujian untuk menentukan kelompok yang perlu
# ditinjau lebih lanjut, bukan untuk memberi label permanen kepada karyawan.
# Jika kelompok WLB rendah juga menunjukkan attrition rate lebih tinggi,
# HR dapat memeriksa beban kerja, jadwal lembur, dukungan atasan, dan faktor
# lingkungan kerja. Jika uji statistik signifikan, artinya terdapat asosiasi
# dalam data; bukan berarti WLB atau overtime terbukti menyebabkan resign.
#
# Rekomendasi operasional perlu divalidasi bersama HR dan manajer unit,
# terutama dengan informasi tambahan seperti jam lembur aktual, absensi,
# hasil exit interview, dan data historis bertanggal.

# %% [markdown]
# ## BAB 5 — EKSPOR DATA BERSIH
#
# Dataset final berisi kolom sumber yang relevan setelah cleaning, label
# kategori yang sudah didekode, serta fitur turunan. Tabel agregat diekspor
# terpisah agar mudah digunakan sebagai data source Tableau/Streamlit.

# %%
print("\n=== BAB 5 | EKSPOR ===")

# Kolom sumber yang dipertahankan setelah kolom teknis dibuang.
# Kolom lain dari file sumber tetap dipertahankan untuk eksplorasi lanjutan.
clean_data = df.copy()

exports = {
    "clean_data.csv": clean_data,
    "agg_wlb_department.csv": wlb_department,
    "agg_wlb_joblevel.csv": wlb_joblevel,
    "agg_wlb_overtime.csv": wlb_overtime,
    "agg_attrition_wlb.csv": attrition_tables["WLB_Category"],
    "agg_attrition_overtime.csv": attrition_tables[OVERTIME_COL],
    "agg_attrition_department.csv": attrition_tables["Department"],
    "agg_attrition_joblevel.csv": attrition_tables["JobLevel"],
    "agg_attrition_age_group.csv": attrition_tables["Age_Group"],
    "agg_attrition_income_group.csv": attrition_tables["Income_Group"],
    "agg_attrition_tenure_group.csv": attrition_tables["Tenure_Group"],
    "agg_attrition_department_wlb.csv": attrition_department_wlb,
    "agg_attrition_overtime_wlb.csv": attrition_overtime_wlb,
    "agg_satisfaction_by_wlb.csv": satisfaction_wlb_export,
    "high_risk_profile.csv": high_risk_profile,
    "high_risk_summary.csv": high_risk_summary,
    "chi_square_results.csv": chi_square_results,
    "mann_whitney_result.csv": mann_whitney_result,
    "key_findings.txt": None,
}

for filename, table in exports.items():
    output_path = (
        PROCESSED_DATA_FILE if filename == "clean_data.csv"
        else OUTPUT_DIR / filename
    )
    if filename == "key_findings.txt":
        output_path.write_text(
            "\n".join(
                f"{i}. {finding}" for i, finding in enumerate(findings, 1)
            ) + "\n",
            encoding="utf-8",
        )
    else:
        table.to_csv(output_path, index=False)

print(f"Dataset final: {PROCESSED_DATA_FILE}")
print(f"Jumlah baris final: {len(clean_data):,}")
print(f"Jumlah kolom final: {clean_data.shape[1]}")
print("\nDaftar kolom clean_data.csv:")
for col in clean_data.columns:
    print(f"- {col}")

print("\nPreview clean_data.csv:")
print(clean_data.head(10).to_string(index=False))

print("\nFile output:")
for path in sorted(OUTPUT_DIR.iterdir()):
    if path.is_file():
        print(f"- {path.name}")

# %% [markdown]
# ### Ringkasan Insight Bisnis
# File `clean_data.csv` menjadi sumber data utama untuk dashboard karena
# menyimpan data karyawan yang telah dibersihkan, label kategori, dan fitur
# turunan. File agregat digunakan untuk visualisasi KPI dan perbandingan
# segmen. `high_risk_profile.csv` hanya untuk kebutuhan pemeriksaan internal
# yang terbatas dan harus diperlakukan sebagai data personal karyawan.
#
# ## Rekomendasi visualisasi Tableau
# 1. **KPI cards:** jumlah karyawan, jumlah attrition, attrition rate, rata-rata WLB.
# 2. **WLB distribution:** bar chart Low/Medium/High.
# 3. **WLB by Department:** horizontal bar chart dengan jumlah karyawan sebagai tooltip.
# 4. **WLB by Job Level:** bar chart atau heatmap.
# 5. **Overtime vs WLB:** side-by-side bar chart atau stacked bar.
# 6. **Attrition by WLB:** bar chart attrition rate dengan employee count sebagai tooltip.
# 7. **Department x WLB:** heatmap attrition rate per departemen dan kategori WLB.
# 8. **Satisfaction by WLB:** grouped bar chart untuk Job Satisfaction dan Environment Satisfaction.
# 9. **Demographic segmentation:** filter Age Group, Income Group, dan Tenure Group.
# 10. **HR priority segment:** tabel ringkasan kelompok prioritas dengan akses terbatas.
#
# **Keterbatasan:** dataset tidak memiliki tanggal snapshot/keluar, jam lembur
# aktual, alasan resign, maupun variabel workload. Karena itu, dashboard ini
# cocok untuk analisis deskriptif dan asosiasi, bukan prediksi attrition
# individual atau kesimpulan kausal.
