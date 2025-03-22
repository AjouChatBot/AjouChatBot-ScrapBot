# utils/db_manager.py
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

def insert_visit(url, parent):
    """
    방문한 URL과 부모 정보를 MySQL DB의 scrap_data 테이블에 삽입합니다.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "INSERT INTO scrap_data (url, parent) VALUES (%s, %s)"
        cursor.execute(query, (url, parent))
        conn.commit()
    except Exception as e:
        print(f"DB 삽입 중 오류 발생: {e}")
    finally:
        cursor.close()
        conn.close()