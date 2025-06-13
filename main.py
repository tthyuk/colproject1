import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import pearsonr

# 페이지 레이아웃을 넓게 사용하도록 설정
st.set_page_config(layout="wide")

# --- 데이터 로딩 (캐싱 사용) ---
@st.cache_data
def load_data():
    """데이터 파일을 로드하고 유동인구 데이터를 행정동별로 집계합니다."""
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. '.csv' 파일들이 현재 디렉토리에 있는지 확인해주세요.")
        return None, None
    
    # 길단위인구 데이터를 행정동 단위로 집계 (groupby)
    pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()
    
    # '커피-음료' 업종 데이터만 미리 필터링
    coffee_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    
    return coffee_df, pop_agg_df

coffee_df, pop_df = load_data()

# 데이터 로딩 실패 시 앱 중단
if coffee_df is None or pop_df is None:
    st.stop()


# --- 사이드바: 사용자 입력 ---
st.sidebar.title("🔍 분석 조건 설정")

# [개선점 2] 분기 코드를 '2024년 3분기' 형태로 변환하는 함수
def format_quarter(quarter_code):
    """(예: 20243 -> '2024년 3분기')"""
    year = str(quarter_code)[:4]
    quarter = str(quarter_code)[-1]
    return f"{year}년 {quarter}분기"

# 분기 선택 (사용자가 보기 편한 형태로)
available_quarters = sorted(coffee_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox(
    "분기를 선택하세요",
    available_quarters,
    format_func=format_quarter # 표시 형식을 지정하는 함수를 연결
)

# --- 데이터 필터링 및 병합 ---
# [개선점 1] 업종 선택 기능 제거, '커피-음료'로 고정
service_name = "커피-음료" 

# 선택된 분기 데이터 필터링
service_quarter_df = coffee_df[coffee_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = pop_df[pop_df['기준_년분기_코드'] == selected_quarter]

# 데이터 병합 (행정동 코드를 기준으로)
merged_df = pd.merge(
    service_quarter_df, 
    pop_quarter_df, 
    on=["행정동_코드", "행정동_코드_명"],
    suffixes=('_점포', '_유동인구')
)

# --- 대시보드 UI ---
st.title(f"☕ {service_name} 업종 분석 대시보드")
st.subheader(f"📈 행정동별 점포 수 vs 유동 인구 수 (기준: {format_quarter(selected_quarter)})") # 제목도 통일된 형식으로 표시

if not merged_df.empty:
    # 유동인구 1만명 당 점포 수 계산
    merged_df['점포_수_per_10k_pop'] = (merged_df['점포_수'] / merged_df['총_유동인구_수']) * 10000
    
    # 상관관계 계산
    corr, p_value = pearsonr(merged_df["총_유동인구_수"], merged_df["점포_수"])
    
    st.markdown(f"**피어슨 상관계수:** `{corr:.3f}` (p-value: `{p_value:.3f}`)")
    if p_value < 0.05:
        st.markdown("💡 *p-value가 0.05 미만이므로, 두 변수 간의 상관관계는 통계적으로 유의미합니다.*")
    else:
        st.markdown("⚠️ *p-value가 0.05 이상이므로, 두 변수 간의 상관관계를 신뢰하기 어렵습니다.*")

    # --- 시각화 ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("유동인구 대비 점포 수 분포")
        fig_scatter = px.scatter(
            merged_df,
            x="총_유동인구_수",
            y="점포_수",
            hover_name="행정동_코드_명",
            labels={"총_유동인구_수": "총 유동 인구 수", "점포_수": f"{service_name} 점포 수"},
            size='점포_수',
            color='점포_수',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        st.subheader("유동인구 1만명 당 점포 수")
        df_sorted_per_pop = merged_df.sort_values(by="점포_수_per_10k_pop", ascending=False).head(15)
        fig_bar_per_pop = px.bar(
            df_sorted_per_pop, 
            x="행정동_코드_명", 
            y="점포_수_per_10k_pop", 
            title="유동인구 대비 점포 밀집도 상위 15개 지역",
            labels={"행정동_코드_명": "행정동", "점포_수_per_10k_pop": "유동인구 1만명 당 점포 수"}
        )
        st.plotly_chart(fig_bar_per_pop, use_container_width=True)

    st.subheader(f"🏙️ 행정동별 {service_name} 점포 수 상위 15개 지역")
    top_stores = merged_df.sort_values(by="점포_수", ascending=False).head(15)
    fig_bar = px.bar(
        top_stores, 
        x="행정동_코드_명", 
        y="점포_수", 
        title=f"{service_name} 점포 수 상위 15개 지역",
        labels={"행정동_코드_명": "행정동", "점포_수": "점포 수"}
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("데이터 확인")
    st.dataframe(merged_df[['행정동_코드_명', '점포_수', '총_유동인구_수', '점포_수_per_10k_pop']].sort_values(by='점포_수', ascending=False))

else:
    st.warning("선택하신 분기에 해당하는 데이터가 없습니다.")
