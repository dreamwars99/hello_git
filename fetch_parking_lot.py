from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os
import streamlit as st
import requests
import time

class KaKaoLocalAPI:
    def __init__(self, api_key):
        
        load_dotenv() # 환경변수 load
        self.api_key = api_key        
            
    
    def search_parking_category(self, x : float, y : float, radius : float =500):
        """
        주어진 x, y좌표를 중심으로 반경 radius미터 내의 주차장 검색
        Args:
            x(float) : 경도(longitude)
            y(float) : 위도(latitude)
        Returns:
            list : 주차장 정보 딕셔너리의 리스트. 실패 시 빈 리스트 반환
        
        By LeeSeunghyeok
        """
        if not self.api_key:
            print("오류: KAKAO API KEY 환경 변수를 찾을 수 없습니다.")
            return []
        
        url = "https://dapi.kakao.com/v2/local/search/category.json"
        
        headers = {
            "Authorization": f'{self.api_key}',
        }
        
        params = {
            "category_group_code": "PK6",
            "x": x,
            "y": y,
            "radius": radius,
            "sort": "distance"
        }
        
        try:
            response = requests.get(url=url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            documents = data.get("documents", [])
            parking_areas = []
            for place in documents:
                name = place.get("place_name")
                address = place.get("road_address_name") or place.get("address_name")
                latitude_str = place.get("y")
                longitude_str = place.get("x")
                distance = place.get("distance")
                url = place.get("place_url")
                try:
                    latitude = float(latitude_str) if latitude_str else None
                    longitude = float(longitude_str) if longitude_str else None
                except (ValueError, TypeError):
                    latitude = None
                    longitude = None
                    print(f"좌표 변환 실패 - {name}")
                if name and latitude is not None and longitude is not None:
                    parking_lot = {
                        'name': name,
                        'address': address,
                        'y': latitude,
                        'x': longitude,
                        'distance': distance,
                        'url' : url
                    }
                    parking_areas.append(parking_lot)
            print("✅ 주차장 검색 완료")
            return parking_areas
        except requests.exceptions.RequestException as e:
            print(f"API 요청 실패: {e}")
            return []
        except Exception as e:
            print(f"데이터 처리 오류: {e}")
            return []
        
    def get_coordinates(self, query : str):
        '''
        주어진 query(주소 또는 키워드)를 기반으로 위치 x,y좌표 출력
        Args:
            query(str) : 주소(Address) 또는 키워드(Keyword)
            
        Returns:
            x(float) : 경도(longitude)
            y(float) : 위도(latitude)
        
        By KangYungu
        '''
        url_address = "https://dapi.kakao.com/v2/local/search/address.json"
        url_keyword = "https://dapi.kakao.com/v2/local/search/keyword.json"
        
        headers = {"Authorization": f"{self.api_key}"}
        params = {"query": query}

        response = requests.get(url_address, headers=headers, params=params)
        rescode = response.status_code # 응답코드
        
        if rescode == 200: # 정상적으로 응답을 받았을 경우
            data = response.json()
            if data['documents']:
                doc = data['documents'][0]

                return doc['x'], doc['y'] # x(경도), y(위도) 반환
        
        response = requests.get(url_keyword, headers=headers, params=params)
        rescode = response.status_code
        
        if rescode == 200:
            data = response.json()
            if data['documents']:
                doc = data['documents'][0]
                print("✅ 목적지 검색 완료")
                return doc['x'], doc['y'] # x(경도), y(위도) 반환
            else:
                print("검색 결과가 없습니다.")
        else:
            print("Error Code:", rescode)
            
            return 0

    def scrape_parking_fee(self, url):
        
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")  # 이미지 불러오지 않기
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

            driver.get(url)
            time.sleep(2)

            result = ""

            try:
                parking_info = driver.find_element(By.CSS_SELECTOR, 'div.cont_parking').text
                result += "주차정보:\n" + parking_info + "\n\n"
            except:
                result += "주차정보를 찾을 수 없습니다.\n\n"

            try:
                fee_info = driver.find_element(By.CSS_SELECTOR, 'div.group_cont table.tbl_comm').text
                lines = fee_info.split('\n')
                unique_lines = []
                for line in lines:
                    if line not in unique_lines:
                        unique_lines.append(line)
                fee_info = "\n".join(unique_lines)
                result += "현장요금:\n" + fee_info
            except:
                result += "요금 정보를 찾을 수 없습니다."

            driver.quit()
            return result.strip()

        except Exception as e:
            print(f"크롤링 에러: {e}")
            return "요금 정보 조회 실패"