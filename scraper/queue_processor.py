# scraper/queue_processor.py
from collections import deque
from scraper.page_processor import process_page
from scraper.event_processor import process_event
from utils.file_manager import process_file_download, load_json
from utils.config import FILE_EXTENSIONS, VISIT_JSON, FILELIST_JSON

def is_file_download(url):
    """
    URL의 확장자를 기준으로 파일 다운로드 대상인지 판단합니다.
    """
    for ext in FILE_EXTENSIONS:
        if url.lower().endswith(ext):
            return True
    return False

def process_queue(driver, start_url):
    """
    큐를 이용하여 onClick 이벤트와 링크 항목을 우선순위에 따라 처리합니다.
    파일 다운로드인 경우 별도로 처리합니다.
    """
    queue = deque()
    queue.append({"type": "link", "url": start_url, "parent": None})
    
    visit_mapping = load_json(VISIT_JSON)
    filelist = load_json(FILELIST_JSON)
    
    while queue:
        # 이벤트 항목 우선 처리
        event_found = False
        for idx, item in enumerate(queue):
            if item["type"] == "event":
                event_found = True
                event_item = queue[idx]
                del queue[idx]
                process_event(driver, event_item, queue)
                break
        if event_found:
            continue
        
        # 링크 항목 처리
        item = queue.popleft()
        if item["type"] == "link":
            url = item["url"]
            parent = item.get("parent")
            if is_file_download(url):
                filelist = process_file_download(url, parent, filelist)
            else:
                process_page(driver, url, parent, queue, visit_mapping)