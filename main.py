import folium
from streamlit_folium import st_folium

# ==========================================
# 6. 메인 화면 - Folium 지도 그리기
# ==========================================
if df_filtered.empty:
    st.info("⚠️ 조건에 맞는 매장이 하나도 없습니다.")
else:
    # 지도 중심 위치 계산
    if use_radius_search and center_lat:
        map_center = [center_lat, center_lon]
        zoom_level = 13
    else:
        map_center = [df_filtered["위도"].mean(), df_filtered["경도"].mean()]
        zoom_level = 11

    # 깔끔한 지도 생성 (CartoDB Positron 배경 사용)
    m = folium.Map(
        location=map_center,
        zoom_start=zoom_level,
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
    )

    # 매장 위치에 마커 추가
    for _, row in df_filtered.iterrows():
        is_cafe = row["상권업종소분류명"] == "카페"
        icon_color = "orange" if is_cafe else "blue"
        icon_name = "coffee" if is_cafe else "shopping-cart"

        # 마커 추가
        folium.Marker(
            location=[row["위도"], row["경도"]],
            popup=f"<b>{row['상호명']}</b><br>{row['상권업종소분류명']}",
            tooltip=f"{row['상호명']} ({row['상권업종소분류명']})",
            icon=folium.Icon(color=icon_color, icon=icon_name, prefix="fa")
        ).add_to(m)

    # Streamlit에 지도 출력
    st_folium(m, width="100%", height=550)
