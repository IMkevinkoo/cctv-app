import pandas as pd
import folium
from folium.plugins import MarkerCluster
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import streamlit as st
import tempfile
import os

st.set_page_config(layout="wide")
st.title("📹 사건 주변 CCTV 찾기 시스템")
st.markdown("사건 발생지 주소를 입력하면 주변 CCTV를 거리 기준으로 추천합니다.")

uploaded_file = st.file_uploader("📁 CCTV 엑셀 파일 업로드", type=["xlsx"])
address = st.text_input("📍 사건 발생지 주소를 입력하세요")
radius = st.slider("📏 반경 거리 설정 (미터)", min_value=50, max_value=1000, value=200, step=50)

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # 위경도 필수 컬럼 확인
    if 'WGS84위도' not in df.columns or 'WGS84경도' not in df.columns:
        st.error("❌ 'WGS84위도'와 'WGS84경도' 컬럼이 필요합니다.")
    else:
        # 위경도 float 변환
        df = df.dropna(subset=['WGS84위도', 'WGS84경도'])
        df['위도'] = df['WGS84위도'].astype(float)
        df['경도'] = df['WGS84경도'].astype(float)

        if address and st.button("🔍 CCTV 찾기"):
            geolocator = Nominatim(user_agent="crime-cctv-locator")
            location = geolocator.geocode(address)

            if location is None:
                st.error("❌ 주소를 찾을 수 없습니다.")
            else:
                사건위치 = (location.latitude, location.longitude)

                # 거리 계산
                df['거리(m)'] = df.apply(
                    lambda row: geodesic((row['위도'], row['경도']), 사건위치).meters,
                    axis=1
                )

                반경내_CCTV = df[df['거리(m)'] <= radius].copy()
                반경내_CCTV = 반경내_CCTV.sort_values(by='거리(m)')

                if 반경내_CCTV.empty:
                    st.warning(f"반경 {radius}m 이내 CCTV가 없습니다.")
                else:
                    st.success(f"✅ 반경 {radius}m 이내 CCTV {len(반경내_CCTV)}대 발견!")

                    # 표 출력
                    cols_to_show = ['번호', '소재지도로명주소', '거리(m)']
                    st.dataframe(반경내_CCTV[cols_to_show])

                    # 지도 시각화
                    m = folium.Map(location=사건위치, zoom_start=16)
                    folium.Marker(
                        사건위치,
                        tooltip="📍 사건 발생 위치",
                        icon=folium.Icon(color='red')
                    ).add_to(m)

                    cluster = MarkerCluster().add_to(m)
                    for _, row in 반경내_CCTV.iterrows():
                        tooltip = f"{row['소재지도로명주소']} ({row['거리(m)']:.1f}m)" \
                            if pd.notnull(row['소재지도로명주소']) \
                            else f"CCTV {row['번호']} ({row['거리(m)']:.1f}m)"

                        folium.Marker(
                            location=[row['위도'], row['경도']],
                            tooltip=tooltip,
                            icon=folium.Icon(icon="video-camera", prefix="fa", color="blue")
                        ).add_to(cluster)

                    # 지도 렌더링
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.html') as tmpfile:
                        m.save(tmpfile.name)
                        st.components.v1.html(open(tmpfile.name, 'r', encoding='utf-8').read(), height=600)
                        os.unlink(tmpfile.name)
else:
    st.warning("⬆ 먼저 CCTV 엑셀 파일을 업로드해 주세요.")
