"""
Marketing Dashboard
실행: streamlit run dashboard/app.py
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from pygwalker.api.streamlit import StreamlitRenderer

from loader import (DATA_DIR, appsflyer_signature, channel_signature,
                    join_data, load_appsflyer, load_channel)

st.set_page_config(page_title="마케팅 대시보드", layout="wide", page_icon="📊")

st.markdown("""
<style>
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .metric-label { color: #9ca3af; font-size: 13px; margin-bottom: 4px; }
    .metric-value { color: #f9fafb; font-size: 28px; font-weight: 700; }
    .metric-sub   { color: #6b7280; font-size: 12px; margin-top: 2px; }
    [data-testid="stSidebar"] { background: #111827; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def _load_channel(sig):
    return load_channel(sig)


@st.cache_data
def _load_appsflyer(sig):
    return load_appsflyer(sig)


def fmt_num(v):
    return f"{v:,.0f}"


def fmt_roas(v):
    return f"{v*100:,.0f}%"


# 숫자 컬럼 포맷 스펙 — st.dataframe style.format()용
NUM_FMT = "{:,.0f}"
PCT_FMT = "{:.2f}%"
ROAS_FMT = "{:,.0f}%"  # ratio * 100 으로 저장된 컬럼용


ch_sig = channel_signature()
af_sig = appsflyer_signature()

raw_ch = _load_channel(ch_sig) if ch_sig else pd.DataFrame()
raw_af = _load_appsflyer(af_sig) if af_sig else pd.DataFrame()

if raw_ch.empty and raw_af.empty:
    st.warning("폴더에 데이터 파일이 없어. `*_channel.csv` 또는 `*_appsflyer.csv` 파일을 추가해줘.")
    st.stop()

df_all = join_data(raw_ch, raw_af)

# ── 사이드바 필터 ──────────────────────────────────────
with st.sidebar:
    st.title("마케팅 대시보드")
    st.caption(f"데이터 폴더: `{DATA_DIR.name}`")
    st.divider()

    channels = sorted(df_all["채널"].dropna().unique().tolist())
    sel_channels = st.multiselect("채널", channels, default=channels)

    min_date = df_all["일"].min().date()
    max_date = df_all["일"].max().date()
    if min_date == max_date:
        st.info(f"데이터 기간: {min_date}")
        sel_dates = (min_date, max_date)
    else:
        sel_dates = st.date_input("기간", value=(min_date, max_date),
                                  min_value=min_date, max_value=max_date)
        if len(sel_dates) != 2:
            st.stop()

    campaigns = sorted(df_all["캠페인"].dropna().unique().tolist())
    sel_campaigns = st.multiselect("캠페인 (선택 안 하면 전체)", campaigns)

    st.divider()
    st.caption(f"채널 파일 {len(ch_sig)}개 · 앱스 파일 {len(af_sig)}개")

# ── 데이터 필터 적용 ───────────────────────────────────
df = df_all[
    df_all["채널"].isin(sel_channels) &
    (df_all["일"].dt.date >= sel_dates[0]) &
    (df_all["일"].dt.date <= sel_dates[1])
]
if sel_campaigns:
    df = df[df["캠페인"].isin(sel_campaigns)]

if df.empty:
    st.warning("선택한 조건에 맞는 데이터가 없어.")
    st.stop()

# ── KPI 카드 ──────────────────────────────────────────
total_cost     = df["비용"].sum()
total_imp      = df["노출"].sum()
total_click    = df["클릭"].sum()
total_purchase = df["구매"].sum()
total_rev      = df["구매매출"].sum()
avg_ctr        = total_click / total_imp if total_imp > 0 else 0
avg_roas       = total_rev / total_cost if total_cost > 0 else 0
avg_cpc        = total_cost / total_click if total_click > 0 else 0

cols = st.columns(7)
kpis = [
    ("총비용",  fmt_num(total_cost),          "원"),
    ("노출",    fmt_num(total_imp),            "회"),
    ("클릭",    fmt_num(total_click),          "회"),
    ("CTR",     f"{avg_ctr*100:.2f}%",         "클릭/노출"),
    ("CPC",     fmt_num(avg_cpc),              "원"),
    ("구매",    fmt_num(total_purchase),       "건"),
    ("ROAS",    fmt_roas(avg_roas),            "매출/비용"),
]
for col, (label, value, sub) in zip(cols, kpis):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 탭 ────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs(["채널 비교", "캠페인", "소재", "앱스 대조", "고급 탐색"])

# ── Tab 1 : 채널 비교 ─────────────────────────────────
with tab1:
    by_ch = df.groupby("채널", as_index=False).agg(
        비용=("비용", "sum"),
        노출=("노출", "sum"),
        클릭=("클릭", "sum"),
        구매=("구매", "sum"),
        구매매출=("구매매출", "sum"),
    )
    by_ch["CTR(%)"]  = (by_ch["클릭"] / by_ch["노출"] * 100).round(2)
    by_ch["ROAS(%)"] = (by_ch["구매매출"] / by_ch["비용"] * 100).round(0)
    by_ch["CPC"]     = (by_ch["비용"] / by_ch["클릭"]).round(0)

    metric = st.radio("지표 선택", ["ROAS(%)", "비용", "클릭", "구매", "CTR(%)"],
                      horizontal=True, key="ch_metric")

    c1, c2 = st.columns([3, 2])
    with c1:
        fig = px.bar(by_ch.sort_values(metric), x="채널", y=metric,
                     color="채널", text_auto=".0f",
                     color_discrete_sequence=px.colors.qualitative.Pastel,
                     title=f"채널별 {metric}")
        fig.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)",
                          paper_bgcolor="rgba(0,0,0,0)", font_color="#d1d5db")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.dataframe(
            by_ch[["채널", "비용", "클릭", "구매", "CTR(%)", "ROAS(%)", "CPC"]]
            .sort_values("비용", ascending=False)
            .set_index("채널")
            .style.format({
                "비용": NUM_FMT, "클릭": NUM_FMT, "구매": NUM_FMT,
                "CTR(%)": PCT_FMT, "ROAS(%)": ROAS_FMT, "CPC": NUM_FMT,
            }),
            use_container_width=True,
        )

# ── Tab 2 : 캠페인 ────────────────────────────────────
with tab2:
    grp_col = st.radio("분석 단위", ["캠페인", "그룹"], horizontal=True)
    by_cmp = df.groupby(grp_col, as_index=False).agg(
        비용=("비용", "sum"), 노출=("노출", "sum"), 클릭=("클릭", "sum"),
        구매=("구매", "sum"), 구매매출=("구매매출", "sum"),
    )
    by_cmp["ROAS(%)"] = (by_cmp["구매매출"] / by_cmp["비용"] * 100).round(0)
    by_cmp["CPC"]     = (by_cmp["비용"] / by_cmp["클릭"]).round(0)

    sort_by = st.selectbox("정렬 기준", ["비용", "ROAS(%)", "구매"], key="cmp_sort")
    top_n   = st.slider("상위 N개", 5, 30, 15, key="cmp_topn")

    top = by_cmp.nlargest(top_n, sort_by)
    fig = px.bar(top.sort_values(sort_by), y=grp_col, x=sort_by,
                 orientation="h", color="ROAS(%)",
                 color_continuous_scale="RdYlGn",
                 title=f"{grp_col}별 {sort_by} TOP {top_n}")
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="#d1d5db", height=max(350, top_n * 28))
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        by_cmp.sort_values(sort_by, ascending=False).set_index(grp_col)
        .style.format({
            "비용": NUM_FMT, "노출": NUM_FMT, "클릭": NUM_FMT,
            "구매": NUM_FMT, "구매매출": NUM_FMT,
            "ROAS(%)": ROAS_FMT, "CPC": NUM_FMT,
        }),
        use_container_width=True,
    )

# ── Tab 3 : 소재 ─────────────────────────────────────
with tab3:
    by_cr = df.groupby(["소재", "채널"], as_index=False).agg(
        비용=("비용", "sum"), 노출=("노출", "sum"), 클릭=("클릭", "sum"),
        구매=("구매", "sum"), 구매매출=("구매매출", "sum"),
    )
    by_cr["ROAS(%)"] = (by_cr["구매매출"] / by_cr["비용"] * 100).round(0)
    by_cr["CPC"]     = (by_cr["비용"] / by_cr["클릭"]).round(0)

    cr_sort = st.selectbox("정렬 기준", ["비용", "ROAS(%)", "구매"], key="cr_sort")
    cr_n    = st.slider("상위 N개", 5, 30, 15, key="cr_n")

    top_cr = by_cr.nlargest(cr_n, cr_sort)
    fig = px.scatter(top_cr, x="비용", y="ROAS(%)", size="구매",
                     color="채널", hover_name="소재", text="소재",
                     color_discrete_sequence=px.colors.qualitative.Pastel,
                     title=f"소재별 비용 vs ROAS (버블 크기 = 구매)")
    fig.update_traces(textposition="top center", textfont_size=9)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      font_color="#d1d5db")
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        by_cr.sort_values(cr_sort, ascending=False).set_index("소재")
        .style.format({
            "비용": NUM_FMT, "노출": NUM_FMT, "클릭": NUM_FMT,
            "구매": NUM_FMT, "구매매출": NUM_FMT,
            "ROAS(%)": ROAS_FMT, "CPC": NUM_FMT,
        }),
        use_container_width=True,
    )

# ── Tab 4 : 앱스플라이어 대조 ─────────────────────────
with tab4:
    st.subheader("채널 데이터 vs 앱스플라이어 어트리뷰션 비교")
    st.caption("클릭·구매 수치 차이 = 트래킹 갭 (뷰어블 임프레션, 다중기기, 어트리뷰션 윈도우 등)")

    by_ch2 = df.groupby("채널", as_index=False).agg(
        클릭_채널=("클릭", "sum"),
        클릭_af=("클릭_af", "sum"),
        구매_채널=("구매", "sum"),
        구매_af=("구매_af", "sum"),
    )
    by_ch2["클릭_갭(%)"] = ((by_ch2["클릭_채널"] - by_ch2["클릭_af"]) / by_ch2["클릭_채널"] * 100).round(1)
    by_ch2["구매_갭(%)"] = ((by_ch2["구매_채널"] - by_ch2["구매_af"]) / by_ch2["구매_채널"] * 100).round(1)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            by_ch2.melt(id_vars="채널", value_vars=["클릭_채널", "클릭_af"],
                        var_name="출처", value_name="클릭"),
            x="채널", y="클릭", color="출처", barmode="group",
            title="클릭 수: 채널 vs 앱스플라이어",
            color_discrete_sequence=["#60a5fa", "#34d399"],
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font_color="#d1d5db")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.bar(
            by_ch2.melt(id_vars="채널", value_vars=["구매_채널", "구매_af"],
                        var_name="출처", value_name="구매"),
            x="채널", y="구매", color="출처", barmode="group",
            title="구매 수: 채널 vs 앱스플라이어",
            color_discrete_sequence=["#60a5fa", "#34d399"],
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          font_color="#d1d5db")
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        by_ch2.set_index("채널")
        .style.format({
            "클릭_채널": NUM_FMT, "클릭_af": NUM_FMT,
            "구매_채널": NUM_FMT, "구매_af": NUM_FMT,
            "클릭_갭(%)": "{:.1f}%", "구매_갭(%)": "{:.1f}%",
        }),
        use_container_width=True,
    )

# ── Tab 5 : 고급 탐색 (pygwalker) ─────────────────────
with tab5:
    st.caption("컬럼을 X·Y축, 색깔, 필터에 끌어다 놓으면 차트가 만들어짐. 설정은 자동 저장.")
    config_path = DATA_DIR / "dashboard" / "pyg_config.json"
    renderer = StreamlitRenderer(df_all, spec=str(config_path), spec_io_mode="rw")
    renderer.explorer()
