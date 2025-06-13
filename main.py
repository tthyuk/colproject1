import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import pearsonr

# 데이터 불러오기
@st.cache_data
def load_data():
    store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
    pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    return store_df, pop_df

store_df, pop_df = load_data()

# 앱 제목
st.title("서울시 상권 분석 대시보드")

# 기능 선택
tab = st.sidebar.selectbox("분석 항목 선택", ["업종 vs 유동인구 상관관계", "지역별 개업/폐업 현황", "유동인구 상위 지역"])

# 1. 업종 vs 유동인구 상관관계
if tab == "업종 vs 유동인구 상관관계":
    selected_industry = st.selectbox("업종 선택", store_df["서비스_업종_코드_명"].unique())

    filtered_store = store_df[store_df["서비스_업종_코드_명"] == selected_industry]
    merged = pd.merge(filtered_store, pop_df, on=["기준_년분기_코드", "행정동_코드", "행정동_코드_명"])

    if not merged.empty:
        corr, _ = pearsonr(merged["점포_수"], merged["총_유동인구_수"])
        st.write(f"**피어슨 상관계수 (점포 수 vs 유동 인구 수):** {corr:.3f}")

        fig = px.scatter(merged, x="총_유동인구_수", y="점포_수", hover_name="행정동_코드_명",
                         title=f"{selected_industry} 업종 - 점포 수 vs 유동 인구 수")
        st.plotly_chart(fig)
    else:
        st.warning("해당 업종의 데이터가 없습니다.")

# 2. 지역별 개업/폐업 현황
elif tab == "지역별 개업/폐업 현황":
    region = st.selectbox("행정동 선택", store_df["행정동_코드_명"].unique())
    region_data = store_df[store_df["행정동_코드_명"] == region]

    if not region_data.empty:
        fig = px.bar(region_data, x="서비스_업종_코드_명", y=["개업_점포_수", "폐업_점포_수"],
                     barmode="group", title=f"{region} 업종별 개업/폐업 현황")
        st.plotly_chart(fig)
    else:
        st.warning("선택한 지역에 데이터가 없습니다.")

# 3. 유동인구 상위 지역
elif tab == "유동인구 상위 지역":
    top_n = st.slider("상위 지역 수", 5, 30, 10)
    latest_quarter = pop_df["기준_년분기_코드"].max()
    top_regions = pop_df[pop_df["기준_년분기_코드"] == latest_quarter].nlargest(top_n, "총_유동인구_수")

    fig = px.bar(top_regions, x="행정동_코드_명", y="총_유동인구_수",
                 title=f"{latest_quarter} 유동인구 상위 {top_n}개 지역")
    st.plotly_chart(fig)
