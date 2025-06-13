# (이하 상세 분석 코드는 이전과 동일)
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
