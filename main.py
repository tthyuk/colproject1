import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import pearsonr

st.set_page_config(layout="wide") # 페이지 레이아웃을 넓게 사용

# --- 데이터 로딩 (캐싱 사용) ---
@st.cache_data
def load_data():
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. '서울시 상권분석서비스(점포-행정동).csv'와 '서울시 상권분석서비스(길단위인구-행정동).csv' 파일이 현재 디렉토리에 있는지 확인해주세요.")
        return None, None
    
    # --- [개선점 1] 유동인구 데이터 전처리 ---
    # 길단위인구 데이터를 행정동 단위로 집계 (groupby)
    pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()
    
    return store_df, pop_agg_df

store_df, pop_df = load_data()

# 데이터 로딩 실패 시 앱 중단
if store_df is None or pop_df is None:
    st.stop()

# --- 사이드바: 사용자 입력 ---
st.sidebar.title("🔍 분석 조건 설정")

# 1. 분기 선택
available_quarters = sorted(store_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox("분기를 선택하세요", available_quarters)

# 2. 업종 선택
available_services = sorted(store_df['서비스_업종_코드_명'].unique())
selected_service = st.sidebar.selectbox("서비스 업종을 선택하세요", available_services, index=available_services.index('커피-음료'))

# --- 데이터 필터링 및 병합 ---

# 1. 선택된 업종 필터링
service_df = store_df[store_df["서비스_업종_코드_명"] == selected_service]

# 2. 선택된 분기 데이터 필터링
service_quarter_df = service_df[service_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = pop_df[pop_df['기준_년분기_코드'] == selected_quarter]

# 3. 데이터 병합 (행정동 코드를 기준으로)
# how='inner'는 양쪽 데이터에 모두 존재하는 행정동만 남김
merged_df = pd.merge(
    service_quarter_df, 
    pop_quarter_df, 
    on=["행정동_코드", "행정동_코드_명"],
    suffixes=('_점포', '_유동인구') # 중복되는 컬럼명 처리
)

# --- 대시보드 UI ---
st.title(f"☕ {selected_service} 업종 분석 대시보드")
st.subheader(f"📈 행정동별 점포 수 vs 유동 인구 수 (기준: {selected_quarter}년 {selected_quarter%10}분기)")

if not merged_df.empty:
    # --- [개선점 4] 새로운 분석 지표 추가 ---
    # 유동인구 1만명 당 점포 수 계산 (0으로 나누는 오류 방지)
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
        # --- [개선점 2] 시각화 가독성 향상 (hover_name 사용) ---
        st.subheader("유동인구 대비 점포 수 분포")
        fig_scatter = px.scatter(
            merged_df,
            x="총_유동인구_수",
            y="점포_수",
            hover_name="행정동_코드_명", # 마우스를 올리면 행정동 이름 표시
            labels={"총_유동인구_수": "총 유동 인구 수", "점포_수": f"{selected_service} 점포 수"},
            size='점포_수', # 점포 수에 따라 원 크기 조절
            color='점포_수', # 점포 수에 따라 색상 조절
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

    st.subheader(f"🏙️ 행정동별 {selected_service} 점포 수 상위 15개 지역")
    top_stores = merged_df.sort_values(by="점포_수", ascending=False).head(15)
    fig_bar = px.bar(
        top_stores, 
        x="행정동_코드_명", 
        y="점포_수", 
        title=f"{selected_service} 점포 수 상위 15개 지역",
        labels={"행정동_코드_명": "행정동", "점포_수": "점포 수"}
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("데이터 확인")
    st.dataframe(merged_df[['행정동_코드_명', '점포_수', '총_유동인구_수', '점포_수_per_10k_pop']].sort_values(by='점포_수', ascending=False))

else:
    st.warning("선택하신 조건에 해당하는 데이터가 없습니다. 다른 분기나 업종을 선택해주세요.")
