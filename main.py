import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import pearsonr

# 페이지 레이아웃을 넓게 사용하도록 설정
st.set_page_config(layout="wide")

# --- 데이터 로딩 (캐싱 사용) ---
@st.cache_data
def load_data():
    """
    데이터 파일을 로드하고, 커피점포 데이터와 원본 유동인구 데이터를 반환합니다.
    상세 분석을 위해 원본 유동인구 데이터가 필요합니다.
    """
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. '.csv' 파일들이 현재 디렉토리에 있는지 확인해주세요.")
        return None, None
    
    # '커피-음료' 업종 데이터만 미리 필터링
    coffee_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    
    return coffee_df, pop_df

coffee_df, pop_df = load_data()

# 데이터 로딩 실패 시 앱 중단
if coffee_df is None or pop_df is None:
    st.stop()

# --- 데이터 전처리: 전체 분석용 데이터 생성 ---
# 길단위인구 데이터를 행정동 단위로 집계
pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()


# --- 사이드바: 사용자 입력 ---
st.sidebar.title("🔍 분석 조건 설정")

# 분기 코드를 '2024년 3분기' 형태로 변환하는 함수
def format_quarter(quarter_code):
    year = str(quarter_code)[:4]
    quarter = str(quarter_code)[-1]
    return f"{year}년 {quarter}분기"

# 분기 선택
available_quarters = sorted(coffee_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox(
    "분기를 선택하세요",
    available_quarters,
    format_func=format_quarter
)

# --- 선택된 분기에 대한 데이터 필터링 ---
coffee_quarter_df = coffee_df[coffee_df['기준_년분기_코드'] == selected_quarter]
pop_agg_quarter_df = pop_agg_df[pop_agg_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = pop_df[pop_df['기준_년분기_코드'] == selected_quarter] # 상세분석용 원본

# 전체 분석용 데이터 병합
merged_df = pd.merge(
    coffee_quarter_df, 
    pop_agg_quarter_df, 
    on=["행정동_코드", "행정동_코드_명"],
    suffixes=('_점포', '_유동인구')
)

# [개선점] 행정동 선택 기능
dong_list = ["전체"] + sorted(merged_df['행정동_코드_명'].unique())
selected_dong = st.sidebar.selectbox("행정동을 선택하세요 (상세 분석)", dong_list)


# --- UI 분기: 전체 vs 상세 ---

if selected_dong == "전체":
    # --- 1. 전체 행정동 분석 화면 ---
    st.title("☕ 커피-음료 업종 전체 동향 분석")
    st.subheader(f"📈 행정동별 점포 수 vs 유동 인구 수 (기준: {format_quarter(selected_quarter)})")
    
    if not merged_df.empty:
        merged_df['점포_수_per_10k_pop'] = (merged_df['점포_수'] / merged_df['총_유동인구_수']) * 10000
        corr, p_value = pearsonr(merged_df["총_유동인구_수"], merged_df["점포_수"])
        
        st.markdown(f"**피어슨 상관계수:** `{corr:.3f}` (p-value: `{p_value:.3f}`)")
        if p_value < 0.05:
            st.markdown("💡 *p-value가 0.05 미만이므로, 두 변수 간의 상관관계는 통계적으로 유의미합니다.*")
        else:
            st.markdown("⚠️ *p-value가 0.05 이상이므로, 두 변수 간의 상관관계를 신뢰하기 어렵습니다.*")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("유동인구 대비 점포 수 분포")
            fig_scatter = px.scatter(
                merged_df, x="총_유동인구_수", y="점포_수", hover_name="행정동_코드_명",
                labels={"총_유동인구_수": "총 유동 인구 수", "점포_수": "커피-음료 점포 수"},
                size='점포_수', color='점포_수', color_continuous_scale='Viridis')
            st.plotly_chart(fig_scatter, use_container_width=True)
        with col2:
            st.subheader("유동인구 1만명 당 점포 수")
            df_sorted = merged_df.sort_values(by="점포_수_per_10k_pop", ascending=False).head(15)
            fig_bar = px.bar(
                df_sorted, x="행정동_코드_명", y="점포_수_per_10k_pop",
                title="유동인구 대비 점포 밀집도 상위 15개 지역",
                labels={"행정동_코드_명": "행정동", "점포_수_per_10k_pop": "유동인구 1만명 당 점포 수"})
            st.plotly_chart(fig_bar, use_container_width=True)

        st.subheader("🏙️ 행정동별 커피-음료 점포 수 상위 15개 지역")
        top_stores = merged_df.sort_values(by="점포_수", ascending=False).head(15)
        fig_bar_top = px.bar(top_stores, x="행정동_코드_명", y="점포_수", title="커피-음료 점포 수 상위 15개 지역")
        st.plotly_chart(fig_bar_top, use_container_width=True)
        
        st.subheader("데이터 확인")
        st.dataframe(merged_df[['행정동_코드_명', '점포_수', '총_유동인구_수', '점포_수_per_10k_pop']].sort_values(by='점포_수', ascending=False))
    else:
        st.warning("선택하신 분기에 해당하는 데이터가 없습니다.")

else:
    # --- 2. 특정 행정동 상세 분석 화면 ---
    st.title(f"🔍 {selected_dong} 상세 분석")
    st.subheader(f"(기준: {format_quarter(selected_quarter)})")

    # 선택된 동의 데이터 추출
    dong_store_data = merged_df[merged_df['행정동_코드_명'] == selected_dong].iloc[0]
    dong_pop_data = pop_quarter_df[pop_quarter_df['행정동_코드_명'] == selected_dong]

    # 주요 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("☕ 커피점포 수", f"{int(dong_store_data['점포_수'])}개")
    col2.metric("🚶 총 유동인구 수", f"{int(dong_store_data['총_유동인구_수']):,}명")
    per_pop_val = dong_store_data['점포_수'] / dong_store_data['총_유동인구_수'] * 10000
    col3.metric("👨‍👩‍👧‍👦 1만명 당 점포 수", f"{per_pop_val:.2f}개")
    
    st.divider()

    # 상세 유동인구 데이터 집계
    # 연령대
    age_cols = {f'연령대_{i}_유동인구_수': f'{i}대' for i in range(10, 70, 10)}
    age_pop = dong_pop_data[age_cols.keys()].sum().rename(index=age_cols)
    age_df = age_pop.reset_index(name='유동인구').rename(columns={'index':'연령대'})

    # 성별
    gender_cols = {'남성_유동인구_수': '남성', '여성_유동인구_수': '여성'}
    gender_pop = dong_pop_data[gender_cols.keys()].sum().rename(index=gender_cols)
    gender_df = gender_pop.reset_index(name='유동인구').rename(columns={'index':'성별'})

    # 시간대
    time_cols = {f'시간대_{h:02d}_{h+x-1:02d}_유동인구_수': f'{h:02d}-{h+x-1:02d}' 
                 for h, x in [(0,6), (6,5), (11,3), (14,3), (17,4), (21,3)]}
    time_pop = dong_pop_data[time_cols.keys()].sum().rename(index=time_cols)
    time_df = time_pop.reset_index(name='유동인구').rename(columns={'index':'시간대'})
    
    # 상세 분석 시각화
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("연령대별 유동인구")
        fig_age = px.bar(age_df, x='연령대', y='유동인구', text='유동인구', title="연령대별 유동인구 분포")
        fig_age.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_age, use_container_width=True)
        
        st.subheader("성별 유동인구")
        fig_gender = px.pie(gender_df, names='성별', values='유동인구', hole=0.4, title="성별 유동인구 비율")
        st.plotly_chart(fig_gender, use_container_width=True)
    
    with col2:
        st.subheader("시간대별 유동인구")
        fig_time = px.line(time_df, x='시간대', y='유동인구', markers=True, text='유동인구', title="시간대별 유동인구 변화")
        fig_time.update_traces(texttemplate='%{text:,.0f}', textposition='top center')
        st.plotly_chart(fig_time, use_container_width=True)
