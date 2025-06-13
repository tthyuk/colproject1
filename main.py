import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pyproj import Proj, transform # 좌표 변환을 위한 라이브러리

# --- 1. 초기 설정 ---

# 페이지 레이아웃을 넓게 사용하도록 설정
st.set_page_config(layout="wide")

# [필수] Mapbox 접근 토큰을 여기에 입력하세요.
# https://www.mapbox.com/ 에서 무료로 발급받을 수 있습니다.
MAPBOX_TOKEN = "YOUR_MAPBOX_ACCESS_TOKEN"  # <--- 여기에 본인의 토큰을 붙여넣으세요!
if MAPBOX_TOKEN == "YOUR_MAPBOX_ACCESS_TOKEN":
    st.warning("Mapbox 접근 토큰을 입력해야 지도가 표시됩니다.")
px.set_mapbox_access_token(MAPBOX_TOKEN)

# --- 2. 함수 정의 ---

def convert_coords(x, y):
    """TM 좌표계(EPSG:5179)를 WGS84 위도/경도 좌표계(EPSG:4326)로 변환합니다."""
    try:
        # TM 중부원점(Bessel) -> WGS84
        proj_in = Proj(init='epsg:5179')
        proj_out = Proj(init='epsg:4326')
        lon, lat = transform(proj_in, proj_out, x, y)
        return lat, lon
    except:
        return None, None # 변환 실패 시 None 반환

@st.cache_data
def load_data():
    """점포, 유동인구, 매출, 그리고 행정동 좌표 데이터를 로드하고 전처리합니다."""
    try:
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
        sales_df = pd.read_csv('서울시 상권분석서비스(추정매출-행정동).csv', encoding='euc-kr')
        with open('서울시 상권분석서비스(영역-행정동).json', 'r', encoding='utf-8') as f:
            area_json_data = json.load(f)
    except FileNotFoundError as e:
        st.error(f"데이터 파일을 찾을 수 없습니다: {e.filename}. 모든 파일이 올바른 위치에 있는지 확인해주세요.")
        return None, None
    
    # 커피 업종 필터링
    coffee_store_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    coffee_sales_df = sales_df[sales_df["서비스_업종_코드_명"] == "커피-음료"]
    
    # 유동인구 데이터 집계
    pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()
    
    # 좌표 데이터 DataFrame 변환 및 좌표 변환
    area_df = pd.DataFrame(area_json_data['DATA'])
    area_df = area_df.rename(columns={'adstrd_cd': '행정동_코드'})
    area_df[['lat', 'lon']] = area_df.apply(
        lambda row: pd.Series(convert_coords(row['xcnts_value'], row['ydnts_value'])), axis=1
    )

    return coffee_store_df, pop_agg_df, coffee_sales_df, area_df, pop_df

# --- 3. 데이터 로드 및 전처리 ---
coffee_df, pop_agg_df, sales_df, area_df, original_pop_df = load_data()

if coffee_df is None:
    st.stop()

# --- 4. 사이드바 UI ---
st.sidebar.title("🔍 분석 조건 설정")

def format_quarter(quarter_code):
    year, quarter = str(quarter_code)[:4], str(quarter_code)[-1]
    return f"{year}년 {quarter}분기"

available_quarters = sorted(coffee_df['기준_년분기_코드'].unique(), reverse=True)
selected_quarter = st.sidebar.selectbox("분기를 선택하세요", available_quarters, format_func=format_quarter)

# 분기별 데이터 필터링
merge_keys = ['행정동_코드', '행정동_코드_명']
coffee_quarter_df = coffee_df[coffee_df['기준_년분기_코드'] == selected_quarter]
pop_agg_quarter_df = pop_agg_df[pop_agg_df['기준_년분기_코드'] == selected_quarter]
sales_quarter_df = sales_df[sales_df['기준_년분기_코드'] == selected_quarter]
pop_quarter_df = original_pop_df[original_pop_df['기준_년분기_코드'] == selected_quarter]

# 3개 데이터프레임 병합
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
    st.subheader(f"🗺️ 서울시 행정동별 분포 지도 (기준: {format_quarter(selected_quarter)})")
    
    if not merged_df.empty and 'lat' in merged_df.columns:
        merged_df['점포당_매출액'] = merged_df['당월_매출_금액'] / merged_df['점포_수'].replace(0, 1)
        
        map_metric = st.selectbox('지도에 표시할 데이터를 선택하세요', ('점포_수', '당월_매출_금액', '총_유동인구_수', '점포당_매출액'))
        
        fig_map = px.scatter_mapbox(
            merged_df.dropna(subset=['lat', 'lon']),
            lat="lat", lon="lon",
            size=map_metric, color=map_metric,
            color_continuous_scale="Viridis",
            mapbox_style="carto-positron",
            zoom=9.5, center={"lat": 37.5665, "lon": 126.9780},
            opacity=0.7, hover_name='행정동_코드_명',
            hover_data={map_metric: ':,.0f', 'lat':False, 'lon':False}
        )
        fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown("---")
        
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
                col.dataframe(df_sorted[['행정동_코드_명', metric]], use_container_width=True)
    else:
        st.warning("분석할 데이터가 없거나, 지도 좌표 정보가 부족합니다.")

# 5-2. 상세 분석 화면
else:
    st.title(f"🔍 {selected_dong} 상세 분석")
    st.subheader(f"(기준: {format_quarter(selected_quarter)})")
    
    dong_data = merged_df[merged_df['행정동_코드_명'] == selected_dong].iloc[0]
    dong_pop_data = pop_quarter_df[pop_quarter_df['행정동_코드_명'] == selected_dong]

    st.subheader("⭐ 주요 지표")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("☕ 점포 수", f"{int(dong_data['점포_수'])}개")
    col2.metric("🚶 총 유동인구", f"{int(dong_data['총_유동인구_수']):,}명")
    col3.metric("💰 총 매출액", f"{dong_data['당월_매출_금액']:,.0f} 원")
    sales_per_store = dong_data['당월_매출_금액'] / dong_data['점포_수'] if dong_data['점포_수'] > 0 else 0
    col4.metric("🏪 점포당 매출액", f"{sales_per_store:,.0f} 원")
    st.divider()

    st.subheader("📊 유동인구 vs 매출 비교 분석")
    # (이하 상세 분석 탭 코드는 이전과 동일)
    tab_age, tab_gender, tab_time, tab_day = st.tabs(["연령대별", "성별", "시간대별", "요일별"])
    
    def get_grouped_data(prefix, pop_cols, sales_cols):
        pop_data = dong_pop_data[list(pop_cols.keys())].sum().rename(index=pop_cols)
        sales_data = dong_data[list(sales_cols.keys())].rename(index=sales_cols)
        pop_df = pop_data.reset_index(name='유동인구').rename(columns={'index': prefix})
        sales_df = sales_data.reset_index(name='매출액').rename(columns={'index': prefix})
        return pop_df, sales_df
    
    with tab_age:
        pop_cols = {'연령대_10_유동인구_수':'10대', '연령대_20_유동인구_수':'20대', '연령대_30_유동인구_수':'30대', '연령대_40_유동인구_수':'40대', '연령대_50_유동인구_수':'50대', '연령대_60_이상_유동인구_수':'60대+'}
        sales_cols = {'연령대_10_매출_금액':'10대', '연령대_20_매출_금액':'20대', '연령대_30_매출_금액':'30대', '연령대_40_매출_금액':'40대', '연령대_50_매출_금액':'50대', '연령대_60_이상_매출_금액':'60대+'}
        pop_res, sales_res = get_grouped_data('연령대', pop_cols, sales_cols)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(pop_res, x='연령대', y='유동인구', title='연령대별 유동인구'), use_container_width=True)
        c2.plotly_chart(px.bar(sales_res, x='연령대', y='매출액', title='연령대별 매출액'), use_container_width=True)

    with tab_gender:
        pop_cols = {'남성_유동인구_수': '남성', '여성_유동인구_수': '여성'}
        sales_cols = {'남성_매출_금액': '남성', '여성_매출_금액': '여성'}
        pop_res, sales_res = get_grouped_data('성별', pop_cols, sales_cols)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.pie(pop_res, names='성별', values='유동인구', title='성별 유동인구', hole=0.4), use_container_width=True)
        c2.plotly_chart(px.pie(sales_res, names='성별', values='매출액', title='성별 매출액', hole=0.4), use_container_width=True)

    with tab_time:
        pop_cols = {'시간대_00_06_유동인구_수':'00-06시', '시간대_06_11_유동인구_수':'06-11시', '시간대_11_14_유동인구_수':'11-14시', '시간대_14_17_유동인구_수':'14-17시', '시간대_17_21_유동인구_수':'17-21시', '시간대_21_24_유동인구_수':'21-24시'}
        sales_cols = {'시간대_00~06_매출_금액':'00-06시', '시간대_06~11_매출_금액':'06-11시', '시간대_11~14_매출_금액':'11-14시', '시간대_14~17_매출_금액':'14-17시', '시간대_17~21_매출_금액':'17-21시', '시간대_21~24_매출_금액':'21-24시'}
        pop_res, sales_res = get_grouped_data('시간대', pop_cols, sales_cols)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(pop_res, x='시간대', y='유동인구', title='시간대별 유동인구'), use_container_width=True)
        c2.plotly_chart(px.bar(sales_res, x='시간대', y='매출액', title='시간대별 매출액'), use_container_width=True)

    with tab_day:
        pop_cols = {'월요일_유동인구_수':'월', '화요일_유동인구_수':'화', '수요일_유동인구_수':'수', '목요일_유동인구_수':'목', '금요일_유동인구_수':'금', '토요일_유동인구_수':'토', '일요일_유동인구_수':'일'}
        sales_cols = {'월요일_매출_금액':'월', '화요일_매출_금액':'화', '수요일_매출_금액':'수', '목요일_매출_금액':'목', '금요일_매출_금액':'금', '토요일_매출_금액':'토', '일요일_매출_금액':'일'}
        pop_res, sales_res = get_grouped_data('요일', pop_cols, sales_cols)
        day_order = ['월', '화', '수', '목', '금', '토', '일']
        for df in [pop_res, sales_res]:
            df['요일'] = pd.Categorical(df['요일'], categories=day_order, ordered=True)
            df.sort_values('요일', inplace=True)
        c1, c2 = st.columns(2)
        c1.plotly_chart(px.bar(pop_res, x='요일', y='유동인구', title='요일별 유동인구'), use_container_width=True)
        c2.plotly_chart(px.bar(sales_res, x='요일', y='매출액', title='요일별 매출액'), use_container_width=True)
