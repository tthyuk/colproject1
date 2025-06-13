import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------
# 데이터 불러오기
# ---------------------
@st.cache_data
def load_data():
    store_df = pd.read_csv('서울시 상권분석서비스(점포-행정동).csv', encoding='euc-kr')
    pop_df = pd.read_csv('서울시 상권분석서비스(길단위인구-행정동).csv', encoding='euc-kr')
    return store_df, pop_df

store_df, pop_df = load_data()

# ---------------------
# 최신 분기 필터링
# ---------------------
latest_quarter = pop_df["기준_년분기_코드"].max()
store_df = store_df[store_df["기준_년분기_코드"] == latest_quarter]
pop_df = pop_df[pop_df["기준_년분기_코드"] == latest_quarter]

# ---------------------
# 커피-음료 업종 필터링
# ---------------------
store_df = store_df[store_df["서비스_업종_코드_명"] == "커피-음료"]

# ---------------------
# 사이드바 UI 설정
# ---------------------
st.sidebar.header("🔍 조건 선택")

# 행정동 리스트
dongs = sorted(pop_df["행정동_코드_명"].unique())
selected_dong = st.sidebar.selectbox("행정동 선택", dongs)

# 시간대 매핑
time_options = {
    "00~06시": "유동인구_00_06_시",
    "06~11시": "유동인구_06_11_시",
    "11~14시": "유동인구_11_14_시",
    "14~17시": "유동인구_14_17_시",
    "17~21시": "유동인구_17_21_시",
    "21~24시": "유동인구_21_24_시"
}
selected_time_label = st.sidebar.selectbox("시간대 선택", list(time_options.keys()))
selected_time_col = time_options[selected_time_label]

# ---------------------
# 페이지 제목
# ---------------------
st.title("☕ 커피-음료 업종 유동 인구 분석")
st.markdown(f"**기준 분기:** `{latest_quarter}`")

# ---------------------
# 선택된 행정동 데이터 필터링
# ---------------------
pop_filtered = pop_df[pop_df["행정동_코드_명"] == selected_dong]
store_filtered = store_df[store_df["행정동_코드_명"] == selected_dong]

# ---------------------
# 유동 인구 및 성별 시각화
# ---------------------
st.subheader(f"📍 {selected_dong} - 시간대: {selected_time_label}")

if not pop_filtered.empty:
    male = int(pop_filtered["남성_유동인구_수"].values[0])
    female = int(pop_filtered["여성_유동인구_수"].values[0])
    selected_time = int(pop_filtered[selected_time_col].values[0])

    st.markdown(f"**선택 시간대 총 유동 인구 수:** `{selected_time:,}명`")

    # 성별 유동인구 시각화
    fig_gender = px.bar(
        x=["남성", "여성"],
        y=[male, female],
        labels={"x": "성별", "y": "유동 인구 수"},
        title="성별 유동 인구",
        color_discrete_sequence=["#1f77b4", "#ff7f0e"]
    )
    st.plotly_chart(fig_gender, use_container_width=True)
else:
    st.warning("해당 행정동의 유동 인구 데이터가 없습니다.")

# ---------------------
# 점포 수 정보
# ---------------------
if not store_filtered.empty:
    store_count = store_filtered["점포_수"].sum()
    st.success(f"☕ 해당 행정동의 **커피-음료 점포 수**: `{store_count}개`")
else:
    st.info("해당 행정동에는 커피-음료 업종 점포가 없습니다.")

# ---------------------
# 유동인구 vs 점포 수 비교 (주변 행정동 포함)
# ---------------------
st.subheader("📊 주변 행정동과 비교: 유동 인구 vs 점포 수")

# 병합 및 비교용 테이블 생성
merged = pd.merge(store_df, pop_df, on=["기준_년분기_코드", "행정동_코드", "행정동_코드_명"])
compare_df = merged[["행정동_코드_명", "점포_수", selected_time_col]]
compare_df = compare_df.rename(columns={selected_time_col: "선택_시간대_유동인구_수"})

# 산점도 시각화
fig_compare = px.scatter(
    compare_df,
    x="선택_시간대_유동인구_수",
    y="점포_수",
    text="행정동_코드_명",
    title=f"유동 인구 수 vs 점포 수 (시간대: {selected_time_label})",
    labels={"선택_시간대_유동인구_수": "유동 인구 수", "점포_수": "점포 수"},
    color_discrete_sequence=["#2ca02c"]
)
fig_compare.update_traces(textposition="top center")
st.plotly_chart(fig_compare, use_container_width=True)
