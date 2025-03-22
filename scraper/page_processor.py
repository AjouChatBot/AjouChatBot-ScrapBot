# scraper/page_processor.py
import time
from selenium.webdriver.common.by import By
from utils.config import PAGE_LOAD_DELAY, VISIT_JSON
from utils.file_manager import save_json
from utils.db_manager import insert_visit

def process_page(driver, url, parent, queue, visit_mapping):
    """
    Selenium을 이용하여 지정된 URL을 렌더링한 후, 페이지 내의 링크와 onClick 이벤트가 있는 요소를 추출하여 queue에 추가합니다.
    방문한 URL과 부모 URL의 매핑 정보는 visit.json에 저장하고, MySQL DB의 scrap_data 테이블에도 삽입합니다.
    """
    try:
        driver.get(url)
        time.sleep(PAGE_LOAD_DELAY)
        
        # 방문 정보 저장 (이미 기록된 경우 건너뜁니다)
        if url not in visit_mapping:
            visit_mapping[url] = parent
            save_json(VISIT_JSON, visit_mapping)
            # MySQL DB에 방문 정보 삽입
            insert_visit(url, parent)
        
        # <a> 태그 추출
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                queue.append({"type": "link", "url": href, "parent": url})
        
        # onClick 이벤트가 등록된 요소 추출 (XPath 사용)
        elements = driver.find_elements(By.XPATH, '//*[@onclick]')
        for elem in elements:
            onclick = elem.get_attribute("onclick")
            identifier = elem.get_attribute("outerHTML")
            queue.append({"type": "event", "onClick": onclick, "identifier": identifier, "parent": url})
    except Exception as e:
        print(f"페이지 처리 중 오류 발생 (URL: {url}): {e}")