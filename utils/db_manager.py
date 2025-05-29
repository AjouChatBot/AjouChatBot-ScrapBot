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
    
def save_log(scrap_url, url_title, created_at, data_type = 0):
    """
    방문한 URL과 부모 정보를 MySQL DB의 scrap_info 테이블에 삽입하고, log_id를 반환합니다.
    """
    conn = get_connection()
    cursor = conn.cursor()

    created_at = re.sub(r"\.", "-", created_at)
    created_at = datetime.strptime(created_at, '%Y-%m-%d').strftime('%Y-%m-%d %H:%M:%S')

    try:
        query = "INSERT INTO scrap_info (scrap_url, url_title, created_at, data_type) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (scrap_url, url_title, created_at, data_type))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"DB 삽입 중 오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def save_content(data: str, category: str = None, log_id: int = None, data_type: int = 0, org_filename: str = None, org_ext: str = None) -> int:
    """
    본문(HTML 등) 데이터를 content 테이블에 저장하고 id를 반환합니다.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO contents (
                data_type, data, created_at, category, log_id, org_file_name, org_file_ext
            ) VALUES (%s, %s, NOW(), %s, %s, %s, %s)
        """
        cursor.execute(sql, (data_type, data, category, log_id, org_filename, org_ext))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"콘텐츠 저장 중 오류 발생: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()