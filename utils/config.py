# utils/config.py
# 프로젝트 설정 값을 정의합니다.

# 시작 URL (필요에 따라 변경)
START_URL = "https://www.ajou.ac.kr"

# Chrome Headless 모드 옵션
CHROME_HEADLESS_OPTIONS = [
    '--headless',
    '--disable-gpu'
]

# 페이지 로딩 및 이벤트 실행 후 대기 시간 (초)
PAGE_LOAD_DELAY = 3

# 파일 다운로드 대상 확장자 목록
FILE_EXTENSIONS = ['.pdf', '.zip', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']

# 다운로드 파일 저장 폴더
FILES_DIR = "files"

# JSON 파일 경로
FILELIST_JSON = "filelist.json"
VISIT_JSON = "visit.json"

# MySQL 데이터베이스 설정
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "user": os.environ.get("MYSQL_USER", "your_username"),
    "password": os.environ.get("MYSQL_PASSWORD", "your_password"),
    "database": os.environ.get("MYSQL_DATABASE", "amate")
}