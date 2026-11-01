"""
    streamlit run app.py
"""

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------
# Konfigurasi halaman
# ---------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Analisis Customer Churn — Telco",
    layout="wide",
    initial_sidebar_state="expanded",
)

CHURN_COLORS = {"Yes": "#E63946", "No": "#2E86AB"}
TENURE_ORDER = ["0-12 bulan", "13-24 bulan", "25-48 bulan", "49-60 bulan", "60+ bulan"]
SERVICE_COLS = [
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies",
]


# ---------------------------------------------------------------
# Load data (hasil Action A langkah 1-5 dari notebook Colab)
# ---------------------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_excel(path)
    # Jaga-jaga kalau file mentah (belum di-clean) yang di-load,
    # kolom hasil feature engineering dibuat ulang di sini.
    if "TotalCharges" in df.columns and df["TotalCharges"].dtype == object:
        df["TotalCharges"] = pd.to_numeric(
            df["TotalCharges"].replace(" ", pd.NA), errors="coerce"
        ).fillna(0)
    if df["SeniorCitizen"].dtype != object:
        df["SeniorCitizen"] = df["SeniorCitizen"].map({0: "No", 1: "Yes"})
    if "TenureGroup" not in df.columns:
        def tenure_group(t):
            if t <= 12:
                return "0-12 bulan"
            elif t <= 24:
                return "13-24 bulan"
            elif t <= 48:
                return "25-48 bulan"
            elif t <= 60:
                return "49-60 bulan"
            return "60+ bulan"
        df["TenureGroup"] = df["tenure"].apply(tenure_group)
    if "JumlahLayananTambahan" not in df.columns:
        df["JumlahLayananTambahan"] = df[SERVICE_COLS].apply(
            lambda row: sum(row == "Yes"), axis=1
        )
    if "SegmenKeluarga" not in df.columns:
        def segmen_keluarga(row):
            if row["Partner"] == "Yes" and row["Dependents"] == "Yes":
                return "Berpasangan + Tanggungan"
            elif row["Partner"] == "Yes":
                return "Berpasangan saja"
            elif row["Dependents"] == "Yes":
                return "Tanggungan saja"
            return "Lajang tanpa Tanggungan"
        df["SegmenKeluarga"] = df.apply(segmen_keluarga, axis=1)
    return df


df_raw = load_data("data/telco_churn_clean.xlsx")

# ---------------------------------------------------------------
# Sidebar — Filter interaktif global (setara "Apply to Worksheets: All")
# ---------------------------------------------------------------
st.sidebar.header("Filter Dashboard")

contract_sel = st.sidebar.multiselect(
    "Contract", sorted(df_raw["Contract"].unique()), default=list(df_raw["Contract"].unique())
)
internet_sel = st.sidebar.multiselect(
    "Internet Service", sorted(df_raw["InternetService"].unique()),
    default=list(df_raw["InternetService"].unique()),
)
tenure_sel = st.sidebar.multiselect(
    "Tenure Group", TENURE_ORDER, default=TENURE_ORDER
)

df = df_raw[
    df_raw["Contract"].isin(contract_sel)
    & df_raw["InternetService"].isin(internet_sel)
    & df_raw["TenureGroup"].isin(tenure_sel)
].copy()

if df.empty:
    st.warning("Tidak ada data untuk kombinasi filter ini. Ubah filter di sidebar.")
    st.stop()

# ---------------------------------------------------------------
# Header + Sheet 1: KPI Card Churn Rate
# ---------------------------------------------------------------
st.title("Dashboard Analisis Customer Churn — Telco")

jumlah_pelanggan = df["customerID"].nunique()
churn_rate = (df["Churn"] == "Yes").mean() * 100
avg_tenure = df["tenure"].mean()
avg_monthly = df["MonthlyCharges"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Churn Rate Keseluruhan", f"{churn_rate:.1f}%")
k2.metric("Jumlah Pelanggan", f"{jumlah_pelanggan:,}")
k3.metric("Rata-rata Tenure", f"{avg_tenure:.1f} bulan")
k4.metric("Rata-rata Tagihan Bulanan", f"${avg_monthly:.2f}")

donut = df["Churn"].value_counts().reset_index()
donut.columns = ["Churn", "Jumlah"]
fig_donut = px.pie(
    donut, names="Churn", values="Jumlah", hole=0.55,
    color="Churn", color_discrete_map=CHURN_COLORS,
    title="Proporsi Pelanggan Churn vs Loyal",
)
st.plotly_chart(fig_donut, width="stretch")

st.divider()

# ---------------------------------------------------------------
# Sheet 2 & 3: Churn by Tenure | Churn by Internet Service
# ---------------------------------------------------------------
col2, col3 = st.columns(2)

with col2:
    st.subheader("Churn by Tenure")
    tenure_churn = (
        df.groupby("TenureGroup")["Churn"]
        .apply(lambda x: (x == "Yes").mean() * 100)
        .reindex(TENURE_ORDER)
        .reset_index(name="Churn Rate")
    )
    fig_tenure = px.bar(
        tenure_churn, x="TenureGroup", y="Churn Rate", text_auto=".1f",
        color_discrete_sequence=["#E63946"],
    )
    fig_tenure.update_yaxes(title="Churn Rate (%)")
    st.plotly_chart(fig_tenure, width="stretch")

with col3:
    st.subheader("Churn by Internet Service")
    net_churn = (
        df.groupby("InternetService")["Churn"]
        .apply(lambda x: (x == "Yes").mean() * 100)
        .reset_index(name="Churn Rate")
    )
    fig_net = px.bar(
        net_churn, x="InternetService", y="Churn Rate", text_auto=".1f",
        color_discrete_sequence=["#E63946"],
    )
    fig_net.update_yaxes(title="Churn Rate (%)")
    st.plotly_chart(fig_net, width="stretch")

# Parameter selector (setara bagian E di panduan Tableau)
st.subheader("Churn Rate per Layanan Tambahan (dinamis)")
layanan_pilih = st.selectbox("Pilih layanan", SERVICE_COLS)
layanan_churn = (
    df.groupby(layanan_pilih)["Churn"]
    .apply(lambda x: (x == "Yes").mean() * 100)
    .reset_index(name="Churn Rate")
)
fig_layanan = px.bar(
    layanan_churn, x=layanan_pilih, y="Churn Rate", text_auto=".1f",
    color_discrete_sequence=["#E63946"],
)
st.plotly_chart(fig_layanan, width="stretch")

st.divider()

# ---------------------------------------------------------------
# Sheet 4 & 5: Segmentasi Demografi | Churn vs Jumlah Layanan
# ---------------------------------------------------------------
col4, col5 = st.columns(2)

with col4:
    st.subheader("Segmentasi Demografi")
    seg = df.groupby(["SegmenKeluarga", "Churn"])["customerID"].nunique().reset_index(name="Jumlah")
    fig_seg = px.bar(
        seg, y="SegmenKeluarga", x="Jumlah", color="Churn", orientation="h",
        color_discrete_map=CHURN_COLORS, barmode="stack",
    )
    st.plotly_chart(fig_seg, width="stretch")

    senior = df.groupby(["SeniorCitizen", "Churn"])["customerID"].nunique().reset_index(name="Jumlah")
    fig_senior = px.bar(
        senior, x="SeniorCitizen", y="Jumlah", color="Churn",
        color_discrete_map=CHURN_COLORS, barmode="stack",
        title="Senior Citizen vs Non-Senior",
    )
    st.plotly_chart(fig_senior, width="stretch")

with col5:
    st.subheader("Churn vs Jumlah Layanan Tambahan")
    jml_layanan = (
        df.groupby("JumlahLayananTambahan")["Churn"]
        .apply(lambda x: (x == "Yes").mean() * 100)
        .reset_index(name="Churn Rate")
    )
    fig_jml = px.line(
        jml_layanan, x="JumlahLayananTambahan", y="Churn Rate", markers=True,
        color_discrete_sequence=["#E63946"],
    )
    fig_jml.update_yaxes(title="Churn Rate (%)")
    st.plotly_chart(fig_jml, width="stretch")

st.divider()

# ---------------------------------------------------------------
# Sheet 6 & 7: Scatter pola rentan churn | Heatmap Contract x Payment
# ---------------------------------------------------------------
col6, col7 = st.columns(2)

with col6:
    st.subheader("Pola Pelanggan Rentan Churn")
    fig_scatter = px.scatter(
        df, x="tenure", y="MonthlyCharges", color="Churn",
        color_discrete_map=CHURN_COLORS, opacity=0.6,
        hover_data=["customerID"],
    )
    st.plotly_chart(fig_scatter, width="stretch")
    st.caption(
        "Klaster pelanggan dengan tenure rendah + tagihan bulanan tinggi "
        "paling rentan churn."
    )

with col7:
    st.subheader("Churn by Contract & Payment Method")
    heat = (
        df.groupby(["Contract", "PaymentMethod"])
        .agg(ChurnRate=("Churn", lambda x: (x == "Yes").mean() * 100),
             JumlahPelanggan=("customerID", "nunique"))
        .reset_index()
    )
    fig_heat = px.density_heatmap(
        heat, x="Contract", y="PaymentMethod", z="ChurnRate",
        color_continuous_scale="Reds", text_auto=".1f",
    )
    st.plotly_chart(fig_heat, width="stretch")
    st.caption(
        "Kontrak Month-to-month + pembayaran Electronic check biasanya "
        "menunjukkan churn rate tertinggi."
    )

st.divider()

# ---------------------------------------------------------------
# Insight & Rekomendasi
# ---------------------------------------------------------------
st.subheader("Insight Utama & Rekomendasi Strategi")
st.markdown(
    """
- **Pelanggan dengan kontrak Month-to-month dan tenure < 12 bulan** memiliki churn rate tertinggi.
- **Pelanggan tanpa layanan Online Security & Tech Support** cenderung lebih rentan churn dibanding yang berlangganan.

**Rekomendasi:**
- Tawarkan insentif migrasi ke kontrak 1–2 tahun bagi pelanggan Month-to-month.
- Bundling gratis Online Security/Tech Support untuk pelanggan baru guna menekan churn di 12 bulan pertama.
"""
)
