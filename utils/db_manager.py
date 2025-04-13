# utils/db_manager.py
from datetime import datetime
import re
import mysql.connector
from utils.config import MYSQL_CONFIG

def get_connection():
    return mysql.connector.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"]
    )

def is_visited(url: str) -> bool:
    """
    주어진 URL에 대한 접속이력이 있는지 확인합니다
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM scrap_data WHERE url=%s"

        cursor.execute(query, (url))
        row = cursor.fetchone()

        return row is None
    
    except Exception as e:
        print(f"DB 삽입 중 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()
    
def save_content(data: str, filename: str = None, ext: str = None) -> str:
    """
    데이터를 저장하고 content_id를 return합니다
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        if (filename and ext):
            query = "INSERT INTO contents (data_type, data, org_file_name, org_file_ext) VALUES (1, %s, %s, %s)"
            cursor.execute(query, (data, filename, ext))

        else:
            query = "INSERT INTO contents (data) VALUES (%s)"
            cursor.execute(query, (data,))

        conn.commit()

        return str(cursor.lastrowid)

    except Exception as e:
        print(f"DB 삽입 중 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()

def save_log(scrap_url, url_title, created_at, content_id, data_type = 0):
    """
    방문한 URL과 부모 정보를 MySQL DB의 scrap_info 테이블에 삽입합니다.
    """
    conn = get_connection()
    cursor = conn.cursor()

    created_at = re.sub(r"\.", "-", created_at)
    created_at = datetime.strptime(created_at, '%Y-%m-%d').strftime('%Y-%m-%d %H:%M:%S')

    try:
        if content_id is None:
            query = "INSERT INTO scrap_info (scrap_url, url_title, created_at, data_type) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (scrap_url, url_title, created_at, data_type))
        else:
            query = "INSERT INTO scrap_info (scrap_url, url_title, created_at, content_id, data_type) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (scrap_url, url_title, created_at, content_id, data_type))
            
        conn.commit()
        
    except Exception as e:
        print(f"DB 삽입 중 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()