import math
import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ==========================================
# 1. 페이지 기본 설정 및 제목
# ==========================================
st.set_page_config(
    page_title="편의점 & 카페 지도 탐색기", page_icon="📍", layout="wide"
)

st.title("📍 편의점 및 카페 위치 탐색기")
st.caption("지역별 매장 위치 및 업종별 필터, 반경 내 검색 기능을 제공합니다.")


# ==========================================
# 2. 데이터 불러오기 및 전처리 함수
# ==========================================
@st.cache_data
def load_data():
    file_path = "store.csv"
    if not os.path.exists(file_path):
        if os.path.exists("store_filtered.csv"):
            file_path = "store_filtered.csv"
        else:
            st.error(
                "데이터 파일(store.csv 또는 store_filtered.csv)을 찾을 수 없습니다."
            )
            return None

    df = pd.read_csv(file_path)

    # 위도, 경도 숫자형 변환 및 결측치 제거
    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")
    df = df.dropna(subset=["위도", "경도"])

    # 편의점과 카페만 필터링
    target_categories = ["편의점", "카페"]
    df = df[df["상권업종소분류명"].isin(target_categories)].copy()

    return df


df_raw = load_data()

if df_raw is not None and not df_raw.empty:

    # ==========================================
    # 3. 하버사인(Haversine) 거리 계산 함수
    # ==========================================
    def haversine_distance(lat1, lon1, lat2, lon2):
        """두 지점의 위도, 경도를 바탕으로 대권 거리(km)를 계산합니다."""
        R = 6371.0  # 지구 반지름 (km)

        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    # ==========================================
    # 4. 사이드바 설정 (지역, 업종, 지도 스타일 & 반경 검색)
    # ==========================================
    st.sidebar.header("🔍 검색 필터 설정")

    # 1) 지역(시/도) 선택
    sido_list = sorted(df_raw["시도명"].dropna().unique())
    selected_sido = st.sidebar.selectbox("지역(시/도) 선택", sido_list)

    # 선택된 지역 데이터 일차 필터링
    df_filtered = df_raw[df_raw["시도명"] == selected_sido].copy()

    # 2) 업종별 구분/필터링 선택
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏷️ 업종 선택")
    selected_categories = st.sidebar.multiselect(
        "표시할 업종을 선택하세요",
        options=["편의점", "카페"],
        default=["편의점", "카페"],  # 기본값: 둘 다 선택
    )

    # 선택된 업종으로 2차 필터링
    df_filtered = df_filtered[
        df_filtered["상권업종소분류명"].isin(selected_categories)
    ].copy()

    # 3) 지도 테마 / 스타일 선택 (강추: CartoDB Positron)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 지도 테마 선택")
    style_option = st.sidebar.selectbox(
        "지도 디자인 테마",
        ["밝고 깔끔함 (CartoDB)", "다크 모드 (Dark Matter)", "기본 지도 (OpenStreetMap)"],
        index=0,  # 기본값: CartoDB Positron (강추 스타일)
    )

    # 선택한 메뉴에 맞게 지도 스타일 매핑
    style_map = {
        "밝고 깔끔함 (CartoDB)": "carto-positron",
        "다크 모드 (Dark Matter)": "carto-darkmatter",
        "기본 지도 (OpenStreetMap)": "open-street-map",
    }
    chosen_style = style_map[style_option]

    # 4) 반경 검색 옵션
    st.sidebar.markdown("---")
    use_radius_search = st.sidebar.checkbox("🎯 반경 검색 사용하기")

    center_lat = None
    center_lon = None
    radius_km = None
    selected_store_name = ""

    if use_radius_search:
        st.sidebar.subheader("반경 검색 조건")

        # 기준 매장 선택 드롭다운 (지역 내 모든 매장 기준)
        raw_sido_stores = df_raw[df_raw["시도명"] == selected_sido]
        store_options = raw_sido_stores["상호명"].dropna().unique()

        if len(store_options) > 0:
            selected_store_name = st.sidebar.selectbox(
                "기준 매장 선택", store_options
            )

            # 선택한 매장의 위도/경도 가져오기
            selected_store = raw_sido_stores[
                raw_sido_stores["상호명"] == selected_store_name
            ].iloc[0]
            center_lat = selected_store["위도"]
            center_lon = selected_store["경도"]

            # 반경 설정 슬라이더 (0.5km ~ 10.0km)
            radius_km = st.sidebar.slider(
                "검색 반경 (km)",
                min_value=0.5,
                max_value=10.0,
                value=2.0,
                step=0.5,
            )

            # 기준 위치로부터의 거리 계산 및 반경 내 필터링
            df_filtered["거리_km"] = df_filtered.apply(
                lambda row: haversine_distance(
                    center_lat, center_lon, row["위도"], row["경도"]
                ),
                axis=1,
            )
            df_filtered = df_filtered[
                df_filtered["거리_km"] <= radius_km
            ].copy()
        else:
            st.sidebar.warning("선택한 지역에 매장이 없습니다.")

    # ==========================================
    # 5. 메인 화면 - 지표 카드(Metric) 출력
    # ==========================================
    if use_radius_search and selected_store_name:
        st.subheader(
            f"📍 기준 매장('{selected_store_name}') 반경 {radius_km} km 이내"
        )

    # 매장 수 집계
    convenience_count = len(df_filtered[df_filtered["상권업종소분류명"] == "편의점"])
    cafe_count = len(df_filtered[df_filtered["상권업종소분류명"] == "카페"])
    total_count = len(df_filtered)

    # 3개 컬럼에 지표 표시
    col1, col2, col3 = st.columns(3)
    col1.metric("🏪 편의점 수", f"{convenience_count:,} 개")
    col2.metric("☕ 카페 수", f"{cafe_count:,} 개")
    col3.metric("🏢 전체 매장 수", f"{total_count:,} 개")

    st.markdown("---")

    # ==========================================
    # 6. 메인 화면 - Plotly 지도 그리기
    # ==========================================
    if df_filtered.empty:
        st.info("⚠️ 조건에 맞는 매장이 하나도 없습니다. 업종 필터나 지역 설정을 확인해 주세요.")
    else:
        # 비주얼이 향상된 컬러 매핑 (편의점: 파란색계열, 카페: 시그니처 주황색계열)
        color_map = {"편의점": "#2B5C8F", "카페": "#E05A47"}

        # Plotly 최신/구버전 호환성 분기 처리
        is_latest_plotly = hasattr(px, "scatter_map")

        if is_latest_plotly:
            fig = px.scatter_map(
                df_filtered,
                lat="위도",
                lon="경도",
                color="상권업종소분류명",
                hover_name="상호명",
                hover_data={"상권업종소분류명": True, "위도": False, "경도": False},
                color_discrete_map=color_map,
                zoom=12.5 if use_radius_search else 10.5,
                center=(
                    {"lat": center_lat, "lon": center_lon}
                    if (use_radius_search and center_lat)
                    else None
                ),
            )
            fig.update_layout(
                map_style=chosen_style,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
            )
        else:
            fig = px.scatter_mapbox(
                df_filtered,
                lat="위도",
                lon="경도",
                color="상권업종소분류명",
                hover_name="상호명",
                hover_data={"상권업종소분류명": True, "위도": False, "경도": False},
                color_discrete_map=color_map,
                zoom=12.5 if use_radius_search else 10.5,
                center=(
                    {"lat": center_lat, "lon": center_lon}
                    if (use_radius_search and center_lat)
                    else None
                ),
            )
            fig.update_layout(
                mapbox_style=chosen_style,
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
            )

        # 마커(점) 스타일링: 크기 조절 및 테두리/투명도 효과 부여
        fig.update_traces(
            marker=dict(
                size=11,
                opacity=0.85,
            )
        )

        # 범례(Legend) 스타일 모던화
        fig.update_layout(
            legend_title_text="업종 구분",
            legend=dict(
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="rgba(0, 0, 0, 0.1)",
                borderwidth=1,
            ),
        )

        # Streamlit 화면에 지도 출력
        st.plotly_chart(fig, use_container_width=True)
