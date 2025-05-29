# utils/config.py
# 프로젝트 설정 값을 정의합니다.

import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 시작 URL (필요에 따라 변경)
# START_URL = "https://ajou.ac.kr/kr/guide/sitemap.do"
# START_URL = "https://www.ajou.ac.kr/researcher"
# START_URL = "https://ajou.ac.kr/dorm/index.do"
START_URL = os.environ.get("START_URL", "https://ajou.ac.kr/kr/ajou/notice.do")
START_KEY = os.environ.get("START_KEY", "introduction")  # scraplist.json에서 사용할 키 값

# Chrome Headless 모드 옵션
CHROME_HEADLESS_OPTIONS = [
    "--headless",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1920,1080",
]

# 페이지 로딩 및 이벤트 실행 후 대기 시간 (초)
PAGE_LOAD_DELAY = float(os.environ.get("PAGE_LOAD_DELAY", "0.1"))

# 파일 다운로드 대상 확장자 목록
FILE_EXTENSIONS = ['.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']

# 다운로드 파일 저장 폴더
# FILES_DIR = "./files"
FILES_DIR = os.environ.get("FILES_DIR", "/data/files")

# JSON 파일 경로
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILELIST_JSON = os.path.join(BASE_DIR, "data", "filelist.json")
VISIT_JSON = os.path.join(BASE_DIR, "data", "visit.json")
CAT_MAPPING_JSON = os.path.join(BASE_DIR, "data", "cat_mapping.json")
SCRAPLIST_JSON = os.path.join(BASE_DIR, "data", "scraplist.json")

# Redis 설정
REDIS_CONFIG = {
    "host": os.environ.get("REDIS_HOST", "localhost"),
    "port": int(os.environ.get("REDIS_PORT", 6379)),
    "password": os.environ.get("REDIS_PASSWORD", ""),
    "db": int(os.environ.get("REDIS_DB", 0))
}

# MySQL 데이터베이스 설정
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "your_username"),
    "password": os.environ.get("MYSQL_PASSWORD", "your_password"),
    "database": os.environ.get("MYSQL_DATABASE", "amate")
}