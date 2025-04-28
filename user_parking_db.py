import pandas as pd
import mysql.connector
import datetime, os

class Parking_db:
    '''
    사용자로부터 받은 목적지와 그 목적지 주변의 주차장 정보를 parkinglog_db(데이터베이스)의
    tbl_user와 tbl_parking에 저장하여 관리하는 class
    
    By LeeWonJeeHui
    '''
    def __init__(self, host, user, password, database, port=3306):
        try:
            self.db_connection = mysql.connector.connect(
                host = host,
                user = user,
                password = password,
                database = database,
                port = port
            )
        except mysql.connector.errors.ProgrammingError:
            self.create_parkinglot_db()
            self.db_connection = mysql.connector.connect(
                host = host,
                user = user,
                password = password,
                database = database,
                port = port
            )
        self.cursor = self.db_connection.cursor()
        
    
    def create_parkinglot_db(self):
        db_connection = mysql.connector.connect(
            host = 'localhost',
            user = 'root',
            password = 'ha231546'
        )
        cursor = db_connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS parkinglot_db")
        cursor.execute("USE parkinglot_db")
        
        db_connection.commit()
        print("✅ parkinglot_db 데이터베이스 생성 완료")
    
    def create_tbl_parking(self):
        create_tbl_parking_query = """
        CREATE TABLE IF NOT EXISTS tbl_parking (
            id INT AUTO_INCREMENT PRIMARY KEY, # ID, PK 
            name TEXT, # 주차장 이름
            address TEXT, # 주차장 주소
            x DOUBLE, # 경도
            y DOUBLE, # 위도
            distance INT, # 목적지와의 거리
            url TEXT, # 상세 정보 링크
            timestamp TEXT # 생성 시간
        );
        """
        self.cursor.execute(create_tbl_parking_query)
        print("✅ tbl_parking 테이블 생성 완료")
    
    def delete_tbl_parking(self):
        self.cursor.execute("DROP TABLE IF EXISTS tbl_parking")
        self.db_connection.commit()
        
    
    def create_tbl_user(self):
        create_tbl_user_query = """
        CREATE TABLE IF NOT EXISTS tbl_user (
            id INT AUTO_INCREMENT PRIMARY KEY, # ID, PK
            destination TEXT, # 목적지(주소 또는 키워드)
            timestamp TEXT # 생성 시간
        );
        """
        self.cursor.execute(create_tbl_user_query)
        print("✅ tbl_user 테이블 생성 완료")
        
    def insert_data_to_tbl(self, parking_data, user_data): # user_data의 타입 확인 필요
        insert_parking_query = """
        INSERT INTO tbl_parking (name, address, x, y, distance, url, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        insert_user_query = """
        INSERT INTO tbl_user (destination, timestamp)
        VALUES (%s, %s)
        """
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.cursor.execute("DELETE FROM tbl_parking")
        for row in parking_data:
            data = (
                str(row['name']),
                str(row['address']),
                float(row['x']),
                float(row['y']),
                float(row['distance']),
                str(row['url']),
                str(now)
            )
            self.cursor.execute(insert_parking_query, data)
        
        if user_data is not None:
            destination_data = (user_data, now)
            self.cursor.execute(insert_user_query, destination_data)
        
        self.db_connection.commit()
        
    
    def get_parking_data(self):
        df = pd.read_sql("SELECT * FROM tbl_parking ORDER BY distance asc", self.db_connection)
        self.db_connection.close()
        
        return df
        
    def close(self):
        self.cursor.close()
        self.db_connection.close()
        print("✅ DB 연결 종료")
    
    
            
    
    