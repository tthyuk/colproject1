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

# 커피-음료 업종 필터링
coffee_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]

# 병합
merged = pd.merge(coffee_df, pop_df, on=["기준_년분기_코드", "행정동_코드", "행정동_코드_명"])

# 최신 분기 기준
latest_quarter = merged["기준_년분기_코드"].max()
merged_latest = merged[merged["기준_년분기_코드"] == latest_quarter]

st.title("☕ 커피-음료 업종 분석 대시보드")
st.subheader(f"📈 행정동별 점포 수 vs 유동 인구 수 (기준 분기: {latest_quarter})")

# 상관관계 계산
if not merged_latest.empty:
    corr, _ = pearsonr(merged_latest["총_유동인구_수"], merged_latest["점포_수"])
    st.markdown(f"**피어슨 상관계수:** {corr:.3f} (점포 수 vs 유동 인구 수)")

    # 산점도 시각화
    fig_scatter = px.scatter(
        merged_latest,
        x="총_유동인구_수",
        y="점포_수",
        text="행정동_코드_명",
        labels={"총_유동인구_수": "총 유동 인구 수", "점포_수": "커피-음료 점포 수"},
        title="유동 인구 수 대비 커피-음료 점포 수 분포"
    )
    fig_scatter.update_traces(textposition="top center")
    st.plotly_chart(fig_scatter, use_container_width=True)

    # 바 차트: 행정동별 점포 수
    st.subheader("🏙 행정동별 커피-음료 점포 수 상위 지역")
    top_stores = merged_latest.sort_values(by="점포_수", ascending=False).head(15)
    fig_bar = px.bar(top_stores, x="행정동_코드_명", y="점포_수", title="커피-음료 점포 수 상위 15개 지역")
    st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.warning("데이터가 부족합니다.")
