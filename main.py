import os
import sys
import signal
import atexit
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.config import CHROME_HEADLESS_OPTIONS, START_URL, START_KEY
from utils.file_manager import initialize_files
from scraper.queue_processor import process_queue
from utils.queue_manager import RedisQueueManager

def create_driver():
    """Chrome WebDriver를 생성하고 반환합니다."""
    chrome_options = Options()
    for option in CHROME_HEADLESS_OPTIONS:
        chrome_options.add_argument(option)
    return webdriver.Chrome(options=chrome_options)

def cleanup(queue_manager):
    """프로그램 종료 시 Redis 상태를 임시 파일로 저장합니다."""
    print("프로그램 종료 중... Redis 상태를 저장합니다.")
    queue_manager.save_state_to_temp(START_KEY)
    print("상태 저장 완료")

if __name__ == "__main__":
    # 필요한 디렉토리와 JSON 파일들을 초기화합니다.
    initialize_files()
    
    # Redis 큐 매니저 초기화
    queue_manager = RedisQueueManager()
    
    # 종료 시 cleanup 함수 실행 등록
    atexit.register(cleanup, queue_manager)
    
    # 상태 복원 로딩을 담당할 스크래퍼인지 확인하고 복원 시도
    if queue_manager.is_first_scraper_for_loading():
        print("상태 복원 담당 스크래퍼입니다. 임시 파일에서 상태를 불러옵니다.")
        if queue_manager.load_state_from_temp(START_KEY):
            print("이전 스크래핑 상태 복원 성공.")
            # 복원 완료 후 임시 파일 삭제 및 락 해제
            queue_manager.delete_temp_file()
            queue_manager.release_load_lock()
        else:
            print("이전 스크래핑 상태 복원 실패 또는 파일 없음. 새로운 스크래핑을 시작합니다.")
            # 복원 실패 시 락 해제
            queue_manager.release_load_lock()
            # 새로운 스크래핑 시작이므로 Redis 데이터 초기화 (선택 사항, 필요에 따라)
            # queue_manager.clear(START_KEY)
    elif os.path.exists(f"{queue_manager.temp_file}.{START_KEY}") and not queue_manager.is_redis_empty(START_KEY):
         # 임시 파일은 있지만 Redis에 데이터가 이미 있는 경우 (다른 스크래퍼가 이미 복원했거나 작업 중)
         print("임시 파일이 존재하지만 Redis에 이미 데이터가 있습니다. 복원하지 않고 시작합니다.")
    else:
        # 임시 파일이 없거나, 있더라도 첫 번째 로딩 스크래퍼가 아닌 경우
        print("첫 번째 로딩 스크래퍼가 아니거나 임시 파일이 없습니다. 새로운 스크래핑을 시작합니다.")
        # 완전히 새로운 시작인 경우 Redis 데이터를 초기화 (선택 사항, 필요에 따라)
        # queue_manager.clear(START_KEY)

    driver = create_driver()
    try:
        # process_queue 함수는 Redis 큐를 사용하여 상태를 공유하며 병렬 실행 가능
        process_queue(driver, START_URL)
    finally:
        driver.quit()