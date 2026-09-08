import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="편의점 & 카페 지도 시각화", layout="wide")
st.title("\U0001f4cd 편의점 & 카페 분포 지도 (반경 검색 포함)")

# 실제 CSV(store.csv) 열 이름 및 값 매핑 — 다운로드한 파일에 맞게 조정하세요
STORE_NAME_COL = "상호명"
LAT_COL = "위도"
LON_COL = "경도"
CATEGORY_COL = "상권업종소분류명"
SIDO_COL = "시도명"

NAME_CONVENIENCE = "편의점"
NAME_CAFE = "카페"

@st.cache_data
def load_data():
    try:
        df = pd.read_csv("store.csv")
    except FileNotFoundError:
        df = pd.read_csv("store_filtered.csv")

    filtered_df = df[df[CATEGORY_COL].isin([NAME_CONVENIENCE, NAME_CAFE])].copy()

    filtered_df[LAT_COL] = pd.to_numeric(filtered_df[LAT_COL], errors="coerce")
    filtered_df[LON_COL] = pd.to_numeric(filtered_df[LON_COL], errors="coerce")
    filtered_df = filtered_df.dropna(subset=[LAT_COL, LON_COL])
    return filtered_df

try:
    df = load_data()
except Exception as e:
    st.error(f"\u26a0\ufe0f 데이터 파일을 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()

st.sidebar.header("\U0001f50d 검색 설정")
sido_list = sorted(df[SIDO_COL].dropna().unique())
selected_sido = st.sidebar.selectbox("1\ufe0f\u20e3 지역(시/도) 선택", sido_list)

view_df = df[df[SIDO_COL] == selected_sido].copy()

st.sidebar.markdown("---")
use_radius = st.sidebar.checkbox("2\ufe0f\u20e3 반경 검색 사용하기 (특정 매장 기준)")

if use_radius and not view_df.empty:
    store_names = sorted(view_df[STORE_NAME_COL].dropna().unique())
    center_store = st.sidebar.selectbox("기준 매장 선택", store_names)
    radius_km = st.sidebar.slider("검색 반경 (km)", min_value=0.5, max_value=10.0, value=3.0, step=0.5)

    center_row = view_df[view_df[STORE_NAME_COL] == center_store].iloc[0]
    center_lat = center_row[LAT_COL]
    center_lon = center_row[LON_COL]

    def calc_distance(lat1, lon1, lat2, lon2):
        # 하버사인 공식: 지구가 둥글다는 것을 감안해 두 좌표 사이의 실제 거리(km)를 계산
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
        c = 2 * np.arcsin(np.sqrt(a))
        return 6371 * c

    view_df["거리(km)"] = calc_distance(center_lat, center_lon, view_df[LAT_COL], view_df[LON_COL])
    view_df = view_df[view_df["거리(km)"] <= radius_km]

subhead_text = f"\U0001f4ca {selected_sido} 업종별 현황"
if use_radius:
    subhead_text += f" (기준 매장 반경 {radius_km}km 이내)"
st.subheader(subhead_text)

conv_count = (view_df[CATEGORY_COL] == NAME_CONVENIENCE).sum()
cafe_count = (view_df[CATEGORY_COL] == NAME_CAFE).sum()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="\U0001f3ea 편의점 수", value=f"{conv_count:,}개")
with col2:
    st.metric(label="\u2615 카페 수", value=f"{cafe_count:,}개")
with col3:
    st.metric(label="\U0001f4cc 전체 매장 수", value=f"{(conv_count + cafe_count):,}개")

st.divider()

if not view_df.empty:
    if use_radius:
        center_dict = {"lat": center_lat, "lon": center_lon}
        zoom_level = 13
    else:
        center_dict = {"lat": view_df[LAT_COL].mean(), "lon": view_df[LON_COL].mean()}
        zoom_level = 11

    color_map = {NAME_CONVENIENCE: "#1f77b4", NAME_CAFE: "#ff7f0e"}

    hover_info = {LAT_COL: False, LON_COL: False, CATEGORY_COL: True}
    if use_radius:
        hover_info["거리(km)"] = ":.2f"

    # 최신 Plotly(scatter_map) / 구버전(scatter_mapbox) 모두 호환되게 분기 처리
    if hasattr(px, "scatter_map"):
        fig = px.scatter_map(
            view_df, lat=LAT_COL, lon=LON_COL, color=CATEGORY_COL,
            color_discrete_map=color_map, hover_name=STORE_NAME_COL,
            hover_data=hover_info, zoom=zoom_level, center=center_dict,
            map_style="open-street-map", height=650,
        )
    else:
        fig = px.scatter_mapbox(
            view_df, lat=LAT_COL, lon=LON_COL, color=CATEGORY_COL,
            color_discrete_map=color_map, hover_name=STORE_NAME_COL,
            hover_data=hover_info, zoom=zoom_level, center=center_dict,
            mapbox_style="open-street-map", height=650,
        )

    fig.update_layout(
        margin={"r": 0, "t": 10, "l": 0, "b": 0},
        legend_title_text="업종 구분",
        legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.01),
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("선택한 조건에 맞는 매장 데이터가 없습니다.")
