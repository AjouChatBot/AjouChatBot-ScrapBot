# scraper/queue_processor.py
import requests
from collections import deque
from scraper.page_processor import process_page
from scraper.event_processor import process_event
from utils.file_manager import process_file_download, load_json, save_json
from utils.config import FILE_EXTENSIONS, VISIT_JSON, FILELIST_JSON, PAGE_LOAD_DELAY, START_KEY, SCRAPLIST_JSON
from selenium.webdriver.chrome.webdriver import WebDriver
from utils.queue_manager import RedisQueueManager
import time
import traceback
from datetime import datetime

def is_file_download(url):
    """
    URL응답에 따라 파일응답인지 여부를 판단합니다
    """
    try:
        response = requests.head(url, allow_redirects=True, timeout=5)
        content_type = response.headers.get("Content-Type", "").lower()

        # HTML이 아닌 경우 = 파일 응답으로 간주
        if not content_type.startswith("text/html") and not content_type.startswith("application/xhtml+xml"):
            return True
        return False
    except requests.RequestException as e:
        print(f"[에러] 요청 실패: {e}")
        return False    

def process_queue(driver: WebDriver, start_url: str) -> None:
    """
    큐를 이용하여 onClick 이벤트와 링크 항목을 우선순위에 따라 처리합니다.
    파일 다운로드인 경우 별도로 처리합니다.
    """
    try:
        queue_manager = RedisQueueManager()
        print(f"큐 초기화: {queue_manager.get_queue_length(START_KEY)}")
        
        # scraplist.json에서 START_KEY에 해당하는 URL 목록을 가져옵니다
        scraplist = load_json(SCRAPLIST_JSON)
        if START_KEY in scraplist:
            urls = scraplist[START_KEY]
            print(f"START_KEY '{START_KEY}'에 해당하는 URL 목록을 큐에 추가합니다.")
            for url in urls:
                if not queue_manager.is_visited(url, START_KEY):
                    queue_manager.push({"type": "page", "url": url}, START_KEY)
        
        # 시작 URL을 큐에 추가
        print(f"시작 URL 확인: {queue_manager.is_visited(start_url, START_KEY)}")
        if not queue_manager.is_visited(start_url, START_KEY):
            queue_manager.push({"type": "page", "url": start_url}, START_KEY)
        
        print(f"큐 확인: {queue_manager.get_queue_length(START_KEY)}")

        while True:
            try:
                # 큐에서 다음 작업 가져오기
                item = queue_manager.pop(START_KEY)
                if not item:
                    # 큐가 비어있고 처리 중인 작업이 없으면 종료
                    if queue_manager.get_queue_length(START_KEY) == 0:
                        print("큐가 비어있어 종료합니다.")
                        break
                    print("큐가 비어있어 대기합니다...")
                    time.sleep(PAGE_LOAD_DELAY)
                    continue
                
                url = item.get("url")
                print(f"처리할 URL: {url}")
                
                if not url:
                    print("URL이 없어 다음 항목으로 넘어갑니다.")
                    continue

                if queue_manager.is_visited(url, START_KEY):
                    print(f"이미 방문한 URL: {url}")
                    continue

                if queue_manager.is_processing(url, START_KEY):
                    print(f"이미 처리 중인 URL: {url}")
                    continue

                print(f"URL 처리 시작: {url}")
                queue_manager.mark_as_processing(url, START_KEY)
                
                try:
                    # 파일 다운로드인 경우 별도 처리
                    if is_file_download(url):
                        print(f"파일 다운로드 처리: {url}")
                        parent_url = item.get("parent", "")
                        log_id = item.get("log_id")
                        process_file_download(url, parent_url, None, log_id)
                        queue_manager.mark_as_visited(url, START_KEY)
                    else:
                        process_page(driver, url, queue_manager)
                        print(f"URL 처리 완료: {url}")
                        queue_manager.mark_as_visited(url, START_KEY)
                except Exception as e:
                    print(f"URL 처리 중 오류 발생: {url}")
                    print(f"오류 내용: {str(e)}")
                    print("스택 트레이스:")
                    print(traceback.format_exc())
                    # 에러 발생 시 다시 큐에 추가
                    queue_manager.push(item, START_KEY)
                finally:
                    # 처리 중 상태 해제
                    if queue_manager.is_processing(url, START_KEY):
                        print(f"처리 중 상태 해제: {url}")
                        queue_manager.mark_as_visited(url, START_KEY)
                    time.sleep(PAGE_LOAD_DELAY)
            except Exception as e:
                print(f"큐 처리 중 오류 발생: {str(e)}")
                print("스택 트레이스:")
                print(traceback.format_exc())
                time.sleep(PAGE_LOAD_DELAY)
    except Exception as e:
        print(f"전체 프로세스 오류 발생: {str(e)}")
        print("스택 트레이스:")
        print(traceback.format_exc())