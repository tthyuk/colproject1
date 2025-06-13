import streamlit as st
import pandas as pd
import plotly.express as px
from scipy.stats import pearsonr

# 페이지 레이아웃을 넓게 사용하도록 설정
st.set_page_config(layout="wide")

# --- 데이터 로딩 (캐싱 사용) ---
@st.cache_data
def load_data():
    """데이터 파일을 로드하고, 커피점포 데이터와 원본 유동인구 데이터를 반환합니다."""
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    except FileNotFoundError:
        st.error("데이터 파일을 찾을 수 없습니다. '.csv' 파일들이 현재 디렉토리에 있는지 확인해주세요.")
        return None, None
    
    coffee_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    return coffee_df, pop_df

coffee_df, pop_df = load_data()

if coffee_df is None or pop_df is None:
    st.stop()

# --- 데이터 전처리: 전체 분석용 데이터 생성 ---
pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()


# --- 사이드바: 사용자 입력 ---
st.sidebar.title("🔍 분석 조건 설정")

def format_quarter(quarter_code):
    year = str(quarter_code)[:4]
    quarter = str(quarter_code)[-1]
    return f"{year}년 {quarter}분기"

available_quarters = sorted(coffee_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox(
    "분기를 선택하세요",
    available_quarters,
    format_func=format_quarter
)

# --- 선택된 분기에 대한 데이터 필터링 ---
coffee_quarter_df = coffee_df[coffee_df['기준_년분기_코드'] == selected_quarter]
pop_agg_quarter_df = pop_agg_df[pop_agg_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = pop_df[pop_df['기준_년분기_코드'] == selected_quarter]

merged_df = pd.merge(
    coffee_quarter_df, 
    pop_agg_quarter_df, 
    on=["행정동_코드", "행정동_코드_명"],
    suffixes=('_점포', '_유동인구')
)

dong_list = ["전체"] + sorted(merged_df['행정동_코드_명'].unique())
selected_dong = st.sidebar.selectbox("행정동을 선택하세요 (상세 분석)", dong_list)

# --- UI 분기: 전체 vs 상세 ---

if selected_dong == "전체":
    # --- 1. 전체 행정동 분석 화면 ---
    st.title("☕ 커피-음료 업종 전체 동향 분석")
    st.subheader(f"📈 행정동별 점포 수 vs 유동 인구 수 (기준: {format_quarter(selected_quarter)})")
    
    # (이전과 동일한 전체 분석 코드)
    if not merged_df.empty:
        merged_df['점포_수_per_10k_pop'] = (merged_df['점포_수'] / merged_df['총_유동인구_수'].replace(0, 1)) * 10000
        corr, p_value = pearsonr(merged_df["총_유동인구_수"], merged_df["점포_수"])
        
        st.markdown(f"**피어슨 상관계수:** `{corr:.3f}` (p-value: `{p_value:.3f}`)")
        if p_value < 0.05: st.markdown("💡 *p-value가 0.05 미만이므로, 두 변수 간의 상관관계는 통계적으로 유의미합니다.*")
        else: st.markdown("⚠️ *p-value가 0.05 이상이므로, 두 변수 간의 상관관계를 신뢰하기 어렵습니다.*")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("유동인구 대비 점포 수 분포")
            fig = px.scatter(merged_df, x="총_유동인구_수", y="점포_수", hover_name="행정동_코드_명", size='점포_수', color='점포_수')
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("유동인구 1만명 당 점포 수")
            df_sorted = merged_df.sort_values(by="점포_수_per_10k_pop", ascending=False).head(15)
            fig = px.bar(df_sorted, x="행정동_코드_명", y="점포_수_per_10k_pop", title="유동인구 대비 점포 밀집도 상위 15개 지역")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("🏙️ 행정동별 커피-음료 점포 수 상위 15개 지역")
        fig = px.bar(merged_df.sort_values(by="점포_수", ascending=False).head(15), x="행정동_코드_명", y="점포_수")
        st.plotly_chart(fig, use_container_width=True)
        
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
    per_pop_val = dong_store_data['점포_수'] / dong_store_data['총_유동인구_수'] * 10000 if dong_store_data['총_유동인구_수'] > 0 else 0
    col3.metric("👨‍👩‍👧‍👦 1만명 당 점포 수", f"{per_pop_val:.2f}개")
    
    st.divider()
    
    st.subheader("📊 유동인구 상세 분석")

    # --- [수정된 부분] 정확한 컬럼명을 직접 사용하여 데이터 집계 ---
    # 연령대
    age_cols = {
        '연령대_10_유동인구_수': '10대', '연령대_20_유동인구_수': '20대',
        '연령대_30_유동인구_수': '30대', '연령대_40_유동인구_수': '40대',
        '연령대_50_유동인구_수': '50대', '연령대_60_이상_유동인구_수': '60대 이상'
    }
    age_pop = dong_pop_data[list(age_cols.keys())].sum().rename(index=age_cols)
    age_df = age_pop.reset_index(name='유동인구').rename(columns={'index':'연령대'})

    # 성별
    gender_cols = {'남성_유동인구_수': '남성', '여성_유동인구_수': '여성'}
    gender_pop = dong_pop_data[list(gender_cols.keys())].sum().rename(index=gender_cols)
    gender_df = gender_pop.reset_index(name='유동인구').rename(columns={'index':'성별'})

    # 시간대
    time_cols = {
        '시간대_00_06_유동인구_수': '00-06시', '시간대_06_11_유동인구_수': '06-11시',
        '시간대_11_14_유동인구_수': '11-14시', '시간대_14_17_유동인구_수': '14-17시',
        '시간대_17_21_유동인구_수': '17-21시', '시간대_21_24_유동인구_수': '21-24시'
    }
    time_pop = dong_pop_data[list(time_cols.keys())].sum().rename(index=time_cols)
    time_df = time_pop.reset_index(name='유동인구').rename(columns={'index':'시간대'})

    # [추가된 부분] 요일
    day_cols = {
        '월요일_유동인구_수': '월', '화요일_유동인구_수': '화', '수요일_유동인구_수': '수',
        '목요일_유동인구_수': '목', '금요일_유동인구_수': '금', '토요일_유동인구_수': '토',
        '일요일_유동인구_수': '일'
    }
    day_pop = dong_pop_data[list(day_cols.keys())].sum().rename(index=day_cols)
    day_df = day_pop.reset_index(name='유동인구').rename(columns={'index':'요일'})
    # 요일 순서 정렬을 위해 Categorical 타입으로 변환
    day_order = ['월', '화', '수', '목', '금', '토', '일']
    day_df['요일'] = pd.Categorical(day_df['요일'], categories=day_order, ordered=True)
    day_df = day_df.sort_values('요일')

    # --- 상세 분석 시각화 (2x2 그리드로 재배치) ---
    col1, col2 = st.columns(2)
    with col1:
        fig_age = px.bar(age_df, x='연령대', y='유동인구', text='유동인구', title="연령대별 유동인구 분포")
        fig_age.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_age, use_container_width=True)
        
        fig_gender = px.pie(gender_df, names='성별', values='유동인구', hole=0.4, title="성별 유동인구 비율")
        st.plotly_chart(fig_gender, use_container_width=True)
    
    with col2:
        fig_time = px.line(time_df, x='시간대', y='유동인구', markers=True, text='유동인구', title="시간대별 유동인구 변화")
        fig_time.update_traces(texttemplate='%{text:,.0f}', textposition='top center')
        st.plotly_chart(fig_time, use_container_width=True)
        
        fig_day = px.bar(day_df, x='요일', y='유동인구', text='유동인구', title="요일별 유동인구 분포")
        fig_day.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_day, use_container_width=True)
