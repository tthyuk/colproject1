import streamlit as st
import pandas as pd
import plotly.express as px
import json

# --- 1. 초기 설정 ---
st.set_page_config(layout="wide")

MAPBOX_TOKEN = "YOUR_MAPBOX_ACCESS_TOKEN"  # <--- 여기에 본인의 토큰을 붙여넣으세요!
if MAPBOX_TOKEN == "YOUR_MAPBOX_ACCESS_TOKEN" or not MAPBOX_TOKEN:
    st.warning("Mapbox 접근 토큰을 입력해야 지도가 표시됩니다.")
px.set_mapbox_access_token(MAPBOX_TOKEN)

# --- 2. 데이터 로딩 및 전처리 ---
@st.cache_data
def load_data():
    """모든 데이터 소스를 로드하고 기본 전처리를 수행합니다."""
    try:
        # 데이터 타입(dtype)을 문자열로 지정하여 병합 오류 방지
        dtype_spec = {'행정동_코드': str}
        store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr', dtype=dtype_spec)
        pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr', dtype=dtype_spec)
        sales_df = pd.read_csv('서울시 상권분석서비스(추정매출-행정동).csv', encoding='euc-kr', dtype=dtype_spec)
        
        # [수정] 새로운 위치 정보 파일(csvjson.json) 로드
        with open('csvjson.json', 'r', encoding='utf-8-sig') as f:
            location_data = json.load(f)

    except FileNotFoundError as e:
        st.error(f"데이터 파일을 찾을 수 없습니다: {e.filename}. 모든 파일이 올바른 위치에 있는지 확인해주세요.")
        return None, None
    except Exception as e:
        st.error(f"데이터 로딩 중 오류 발생: {e}")
        return None, None

    # 커피 업종 필터링
    coffee_store_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]
    coffee_sales_df = sales_df[sales_df["서비스_업종_코드_명"] == "커피-음료"]
    
    # 유동인구 데이터 집계
    pop_agg_df = pop_df.groupby(['기준_년분기_코드', '행정동_코드', '행정동_코드_명'])['총_유동인구_수'].sum().reset_index()

    # 위치 정보 전처리
    location_df = pd.DataFrame(location_data)
    # 깨진 컬럼명을 올바른 이름으로 변경
    location_df.rename(columns={
        '읍면동/구': '행정동_코드_명',
        '위도': 'lat',
        '경도': 'lon'
    }, inplace=True)
    # 필요한 컬럼만 선택하고, 중복된 행정동 이름이 있을 경우 첫 번째 값만 사용
    location_df = location_df[['행정동_코드_명', 'lat', 'lon']].drop_duplicates('행정동_코드_명').reset_index(drop=True)
    # '종로1·2·3·4가동'과 같은 이름 차이를 맞춰줌
    location_df['행정동_코드_명'] = location_df['행정동_코드_명'].str.replace('·', '·')
    
    return coffee_store_df, pop_agg_df, coffee_sales_df, location_df, pop_df

# 데이터 로드
all_data = load_data()
if all_data[0] is None:
    st.stop()
coffee_df, pop_agg_df, sales_df, location_df, original_pop_df = all_data

# --- 3. 사이드바 UI ---
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

# 데이터 병합 (행정동 '이름'을 기준으로)
merged_df = pd.merge(coffee_quarter_df, pop_agg_quarter_df, on=merge_keys, how='inner')
merged_df = pd.merge(merged_df, sales_quarter_df, on=merge_keys, how='inner')
# [수정] 행정동 '이름'으로 위치 정보 병합
merged_df = pd.merge(merged_df, location_df, on='행정동_코드_명', how='left')


# 행정동 검색 및 선택
st.sidebar.divider()
full_dong_list = sorted(merged_df['행정동_코드_명'].unique())
search_term = st.sidebar.text_input("행정동 검색", placeholder="예: 역삼, 신사, 명동")
filtered_dong_list = [dong for dong in full_dong_list if search_term in dong] if search_term else full_dong_list
display_list = ["전체"] + filtered_dong_list
selected_dong = st.sidebar.selectbox("행정동을 선택하세요", display_list, help="찾고 싶은 동 이름을 검색창에 입력하세요.")


# --- 4. 메인 화면 UI ---
# 4-1. 전체 분석 화면
if selected_dong == "전체":
    st.title("☕ 커피-음료 업종 전체 동향 분석")
    st.subheader(f"📈 전체 행정동 비교 분석 (기준: {format_quarter(selected_quarter)})")
    
    if not merged_df.empty:
        merged_df['점포당_매출액'] = merged_df['당월_매출_금액'] / merged_df['점포_수'].replace(0, 1)
        
        tab1, tab2 = st.tabs(["📊 종합 비교", "🏆 순위 비교"])
        with tab1:
            col1, col2 = st.columns(2)
            col1.plotly_chart(px.scatter(merged_df, x="총_유동인구_수", y="점포_수", title="유동인구 vs 점포 수", hover_name="행정동_코드_명"), use_container_width=True)
            col2.plotly_chart(px.scatter(merged_df, x="점포_수", y="당월_매출_금액", title="점포 수 vs 매출액", hover_name="행정동_코드_명"), use_container_width=True)
        with tab2:
            col1, col2, col3 = st.columns(3)
            for col, metric, label in zip([col1, col2, col3], ['점포_수', '당월_매출_금액', '점포당_매출액'], ['점포 수', '매출액', '점포당 매출액']):
                col.subheader(f"{label} 상위 15")
                df_sorted = merged_df.sort_values(metric, ascending=False).head(15)
                col.dataframe(df_sorted[['행정동_코드_명', metric]].style.format({metric: '{:,.0f}'}), use_container_width=True)
    else:
        st.warning("분석할 데이터가 없습니다.")

# 4-2. 상세 분석 화면
else:
    st.title(f"🔍 {selected_dong} 상세 분석")
    st.subheader(f"(기준: {format_quarter(selected_quarter)})")
    
    dong_data = merged_df[merged_df['행정동_코드_명'] == selected_dong].iloc[0]
    dong_pop_data = pop_quarter_df[pop_quarter_df['행정동_코드_명'] == selected_dong]

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("⭐ 주요 지표")
        st.metric("☕ 점포 수", f"{int(dong_data['점포_수'])}개")
        st.metric("🚶 총 유동인구", f"{int(dong_data['총_유동인구_수']):,}명")
        st.metric("💰 총 매출액", f"{dong_data['당월_매출_금액']:,.0f} 원")
        sales_per_store = dong_data['당월_매출_금액'] / dong_data['점포_수'] if dong_data['점포_수'] > 0 else 0
        st.metric("🏪 점포당 매출액", f"{sales_per_store:,.0f} 원")

    with col2:
        st.subheader("📍 위치 정보")
        dong_map_df = merged_df[merged_df['행정동_코드_명'] == selected_dong]
        
        if not dong_map_df.empty and not dong_map_df['lat'].isnull().all():
            fig_map = px.scatter_mapbox(dong_map_df, lat="lat", lon="lon",
                                        mapbox_style="open-street-map", zoom=13, size=[20],
                                        hover_name='행정동_코드_명', text='행정동_코드_명')
            fig_map.update_traces(textposition='top center')
            fig_map.update_layout(margin={"r":0,"t":20,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("해당 행정동의 위치(좌표) 정보가 없습니다.")

    st.divider()

    st.subheader("📊 유동인구 vs 매출 비교 분석")
    # (이하 상세 분석 탭 코드는 이전과 동일)
    tab_age, tab_gender, tab_time, tab_day = st.tabs(["연령대별", "성별", "시간대별", "요일별"])
    # ... 탭 코드 ...
