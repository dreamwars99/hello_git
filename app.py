from streamlit_folium import st_folium
from dotenv import load_dotenv
from fetch_parking_lot import KaKaoLocalAPI
from user_parking_db import Parking_db
from st_aggrid import AgGrid, GridOptionsBuilder
from folium.plugins import BeautifyIcon
import streamlit as st
import folium
import os

class Parkinglot_app:
    def __init__(self):
        
        load_dotenv()
        
        if os.getenv("KAKAO_API_KEY") is not None:
            self.fetcher = KaKaoLocalAPI(os.getenv("KAKAO_API_KEY"))
            
        else:
            st.error("KAKAO_API_KEY 환경변수가 설정되지 않았습니다.")
            return
       
        self.db = Parking_db(
                        os.getenv('DB_HOST'), 
                        os.getenv('DB_USER'), 
                        os.getenv('DB_PASSWORD'), 
                        os.getenv('DB_NAME')) # instanciation 하는 순간 DB와 Table 생성
        
        if 'init' not in st.session_state:
            self.db.create_parkinglot_db()
            self.db.delete_tbl_parking()
            self.db.create_tbl_parking()
            self.db.create_tbl_user()
            print("✅ DB 연결 완료")
            st.session_state['init'] = False

    
    def show_streamlit(self):
        st.set_page_config(page_title="🚗 주변 주차장 탐색기 🚗", layout='wide')
        st.title("🚗 주변 주차장 탐색기 🚗")
        
        address = st.text_input("🔎 목적지 주소를 입력하세요", None)
        col1, _, _ = st.columns([3,3,3])
        with col1:
            radius = st.slider("📏 검색 반경 (미터)", min_value=500, max_value=1000, value=700, step=100)
        
        query_key = f"{address}-{radius}" # 검색 갱신 체크를 위한 key
        
        if st.button("📡 주차장 검색"):
            
            if st.session_state.get("last_query") != query_key: # 이전 검색과 다른 조건일 경우에만 실행
                # try:
                x, y = self.fetcher.get_coordinates(address)
                data = self.fetcher.search_parking_category(x, y, radius)
                self.db.insert_data_to_tbl(parking_data=data, user_data=address)
                print(f"✅ 검색 데이터를 DB에 저장 완료")
                
                st.session_state["center"] = [x, y]
                st.session_state["last_query"] = query_key
                st.success(f"'{address}' 기준 주변 주차장 정보를 불러왔습니다!")
            else:
                st.info("동일한 조건의 검색 결과가 이미 존재합니다!")
        
        df = self.db.get_parking_data()
        
        if not df.empty: # 검색 결과가 있을 경우에만 지도 표시
            st.subheader("🔍 주차장 목록")
            
            gb = GridOptionsBuilder.from_dataframe(df[['name', 'distance']])
            gb.configure_selection('single', use_checkbox=True)
            grid_options = gb.build()
            
            grid_response = AgGrid(
                df[['name', 'distance']],
                gridOptions=grid_options,
                height=400,
                width='100%',
                update_mode = 'SELECTION_CHANGED',
                theme='streamlit'
            )
            
            if grid_response is not None:
                selected = grid_response['selected_rows']
            else:
                selected = []
            
            left, right = st.columns([2, 1])
            
            with left:
                if "center" in st.session_state:
                    center_x, center_y = st.session_state['center'][0], st.session_state['center'][1]
                else:
                    center_y, center_x = float(df.iloc[0]['y']), float(df.iloc[0]['x'])

                m = folium.Map(location=[center_y, center_x], zoom_start = 15) # 지도 생성

                
                folium.Marker(
                    location = [center_y, center_x],
                    popup = folium.Popup(f"<div style='white-space: nowrap;'>📍{address}</div>", max_width=300),
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m) # 내 위치 마커 추가
                
                for idx, row in df.iterrows(): # 주차장명, 상세url 및 마커 추가
                    popup_html = f"<b>{row['name']}</b><br>거리: {row['distance']}m"
                    icon_color = "blue"
                    is_selected = False
                    if selected is not None and row['name'] == selected['name'].values[0]:
                        icon_color = "green"
                        is_selected = True
                    
                    if is_selected:
                        icon = BeautifyIcon(
                            icon_shape = 'marker',
                            border_color = icon_color,
                            border_width = 3,
                            text_color=icon_color,
                            background_color = 'white',
                            spin=True,
                            inner_icon_style='font-size:24px',
                            icon_size=[40,40]
                        )
                    else:
                        icon = BeautifyIcon(
                            icon_shape = 'marker',
                            border_color = icon_color,
                            border_width = 1,
                            text_color=icon_color,
                            icon_size=[20,20]
                        )
                        
                    folium.Marker(
                        location=[float(row['y']), float(row['x'])],
                        popup=folium.Popup(popup_html, max_width=300),
                        icon=icon,
                    ).add_to(m) 
                
                st.subheader("🗺️ 지도에서 보기")
                st_folium(m, width=960, height=540)
            
            with right:
                st.subheader("ℹ️ 선택한 주차장 정보")
                if selected is not None:
                    selected_row = df[df['name'] == selected['name'].values[0]].iloc[0]
                    st.markdown(f'**주차장명**: {selected_row['name']}')
                    st.markdown(f"**주소**: {selected_row['address']}")
                    st.markdown(f"**거리**: {selected_row['distance']}")
                    st.markdown(f"**상세 링크**: [바로가기]({selected_row['url']})")
                    
                    if st.button("📡 상세 정보 가져오기"):
                        fee_info = self.fetcher.scrape_parking_fee(selected_row['url'])
                        st.session_state['fee_info'] = fee_info
                        fee_info = st.session_state['fee_info'].split('\n')
                        
                        parking_info_section = []
                        parking_type_section = []
                        fee_info_section = []
                        section_flag = None

                        for line in fee_info[:-4]:
                            
                            if '주차정보' in line:
                                section_flag = 'parking'
                                continue
                            elif '주차형태' in line:
                                section_flag = 'parking_type'
                                continue
                            elif '현장요금' in line:
                                section_flag = 'fee'
                                continue
                            
                            if section_flag == 'parking':
                                parking_info_section.append(line)
                            elif section_flag == 'parking_type':
                                parking_type_section.append(line)
                            elif section_flag == 'fee':
                                fee_info_section.append(line)
                                
                        st.markdown("### 🅿️ 주차정보")
                        if parking_info_section:
                            for item in parking_info_section:
                                st.markdown(f"- {item}")
                        else:
                            st.markdown("주차정보 없음")
                            
                        st.markdown("### ℹ️ 주차형태")
                        if parking_type_section:
                            for item in parking_type_section:
                                st.markdown(f"- {item}")
                        else:
                            st.markdown("주차형태 없음")

                        st.markdown("### 💸 요금정보")
                        if fee_info_section:
                            for item in fee_info_section:
                                st.markdown(f"- {item}")
                        else:
                            st.markdown("요금 정보 없음")
                else:
                    st.info("표에서 주차장을 선택하세요.")
            
if __name__ == "__main__":
    app = Parkinglot_app()
    app.show_streamlit()