import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pyproj import Proj, transform

# --- 1. 초기 설정 ---
st.set_page_config(layout="wide")

MAPBOX_TOKEN = "YOUR_MAPBOX_ACCESS_TOKEN"  # <--- 여기에 본인의 토큰을 붙여넣으세요!
if MAPBOX_TOKEN == "YOUR_MAPBOX_ACCESS_TOKEN":
    st.warning("Mapbox 접근 토큰을 입력해야 지도가 표시됩니다.")
px.set_mapbox_access_token(MAPBOX_TOKEN)

# --- 2. 함수 정의 ---
def convert_coords(x, y):
    try:
        proj_in = Proj(init='epsg:5179')
        proj_out = Proj(init='epsg:4326')
        lon, lat = transform(proj_in, proj_out, x, y)
        return lat, lon
    except Exception:
        return None, None

@st.cache_data
def load_data():
    """데이터를 로드하고, 모든 '행정동_코드' 타입을 문자열로 통일합니다."""
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr', dtype={'행정동_코드': str})
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr', dtype={'행정동_코드': str})
        sales_df = pd.read_csv('서울시 상권분석서비스(추정매출-행정동).csv', encoding='euc-kr', dtype={'행정동_코드': str})
        with open('서울시 상권분석서비스(영역-행정동).json', 'r', encoding='utf-8') as f:
            area_json_data = json.load(f)
    except FileNotFoundError as e:
        st.error(f"데이터 파일을 찾을 수 없습니다: {e.filename}. 모든 파일이 올바른 위치에 있는지 확인해주세요.")
        return None, None, None, None, None

    coffee_store_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    coffee_sales_df = sales_df[sales_df["서비스_업종_코드_명"] == "커피-음료"]
    pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()
    
    area_df = pd.DataFrame(area_json_data['DATA']).rename(columns={'adstrd_cd': '행정동_코드'})
    area_df['행정동_코드'] = area_df['행정동_코드'].astype(str)
    area_df[['lat', 'lon']] = area_df.apply(lambda row: pd.Series(convert_coords(row['xcnts_value'], row['ydnts_value'])), axis=1)
    
    return coffee_store_df, pop_agg_df, coffee_sales_df, area_df, pop_df

# --- 3. 데이터 로드 및 전처리 ---
coffee_df, pop_agg_df, sales_df, area_df, original_pop_df = load_data()
if coffee_df is None: st.stop()

# --- 4. 사이드바 UI ---
st.sidebar.title("🔍 분석 조건 설정")
def format_quarter(quarter_code):
    year, quarter = str(quarter_code)[:4], str(quarter_code)[-1]
    return f"{year}년 {quarter}분기"
available_quarters = sorted(coffee_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox("분기를 선택하세요", available_quarters, format_func=format_quarter)

# 분기별 데이터 필터링 및 병합
merge_keys = ['행정동_코드', '행정동_코드_명']
coffee_quarter_df = coffee_df[coffee_df['기준_년분기_코드'] == selected_quarter]
pop_agg_quarter_df = pop_agg_df[pop_agg_df['기준_년분기_코드'] == selected_quarter]
sales_quarter_df = sales_df[sales_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = original_pop_df[original_pop_df['기준_년분기_코드'] == selected_quarter]

merged_df = pd.merge(coffee_quarter_df, pop_agg_quarter_df, on=merge_keys, how='inner')
merged_df = pd.merge(merged_df, sales_quarter_df, on=merge_keys, how='inner')
merged_df = pd.merge(merged_df, area_df[['행정동_코드', 'lat', 'lon']], on='행정동_코드', how='left')

# 행정동 검색 및 선택
st.sidebar.divider()
full_dong_list = sorted(merged_df['행정동_코드_명'].unique())
search_term = st.sidebar.text_input("행정동 검색", placeholder="예: 역삼, 신사, 명동")
filtered_dong_list = [dong for dong in full_dong_list if search_term in dong] if search_term else full_dong_list
display_list = ["전체"] + filtered_dong_list
selected_dong = st.sidebar.selectbox("행정동을 선택하세요", display_list, help="찾고 싶은 동 이름을 검색창에 입력하세요.")


# --- 5. 메인 화면 UI ---

# 5-1. 전체 분석 화면
if selected_dong == "전체":
    st.title("☕ 커피-음료 업종 전체 동향 분석")
    st.subheader(f"📈 전체 행정동 비교 분석 (기준: {format_quarter(selected_quarter)})")
    
    # [수정] 지도 관련 코드 전체 삭제
    if not merged_df.empty:
        merged_df['점포당_매출액'] = merged_df['당월_매출_금액'] / merged_df['점포_수'].replace(0, 1)
        
        tab1, tab2 = st.tabs(["📊 종합 비교", "🏆 순위 비교"])
        with tab1:
            col1, col2 = st.columns(2)
            col1.plotly_chart(px.scatter(merged_df, x="총_유동인구_수", y="점포_수", title="유동인구 vs 점포 수", hover_name="행정동_코드_명"), use_container_width=True)
            col2.plotly_chart(px.scatter(merged_df, x="점포_수", y="당월_매출_금액", title="점포 수 vs 매출액", hover_name="행정동_코드_명"), use_container_width=True)
        with tab2:
            col1, col2, col3 = st.columns(3)
            for col, metric, label in zip(
                [col1, col2, col3], 
                ['점포_수', '당월_매출_금액', '점포당_매출액'], 
                ['점포 수', '매출액', '점포당 매출액']
            ):
                col.subheader(f"{label} 상위 15")
                df_sorted = merged_df.sort_values(metric, ascending=False).head(15)
                col.dataframe(df_sorted[['행정동_코드_명', metric]].style.format({metric: '{:,.0f}'}), use_container_width=True)
    else:
        st.warning("분석할 데이터가 없습니다.")

# 5-2. 상세 분석 화면
else:
    st.title(f"🔍 {selected_dong} 상세 분석")
    st.subheader(f"(기준: {format_quarter(selected_quarter)})")
    
    dong_data = merged_df[merged_df['행정동_코드_명'] == selected_dong].iloc[0]
    dong_pop_data = pop_quarter_df[pop_quarter_df['행정동_코드_명'] == selected_dong]

    # [수정] 2단 레이아웃으로 지표와 지도 함께 표시
    col1, col2 = st.columns([1, 2]) # 왼쪽 1, 오른쪽 2 비율로 공간 할당

    with col1:
        st.subheader("⭐ 주요 지표")
        st.metric("☕ 점포 수", f"{int(dong_data['점포_수'])}개")
        st.metric("🚶 총 유동인구", f"{int(dong_data['총_유동인구_수']):,}명")
        st.metric("💰 총 매출액", f"{dong_data['당월_매출_금액']:,.0f} 원")
        sales_per_store = dong_data['당월_매출_금액'] / dong_data['점포_수'] if dong_data['점포_수'] > 0 else 0
        st.metric("🏪 점포당 매출액", f"{sales_per_store:,.0f} 원")

    with col2:
        # [추가] 선택된 행정동만 표시하는 지도
        st.subheader("📍 위치 정보")
        dong_map_df = merged_df[merged_df['행정동_코드_명'] == selected_dong]
        
        if not dong_map_df.empty and not dong_map_df['lat'].isnull().all():
            fig_map = px.scatter_mapbox(
                dong_map_df,
                lat="lat", lon="lon",
                mapbox_style="open-street-map", # 배경 지도 스타일
                zoom=13, # 동네 수준으로 확대
                size=[20], # 점 크기 고정
                hover_name='행정동_코드_명'
            )
            fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("해당 행정동의 위치(좌표) 정보가 없습니다.")

    st.divider()

    st.subheader("📊 유동인구 vs 매출 비교 분석")
    # (이하 상세 분석 탭 코드는 이전과 동일)
    tab_age, tab_gender, tab_time, tab_day = st.tabs(["연령대별", "성별", "시간대별", "요일별"])
    # ... 탭 코드 ...
