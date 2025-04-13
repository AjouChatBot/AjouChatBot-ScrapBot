import time
import re
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from utils.config import PAGE_LOAD_DELAY, VISIT_JSON
from utils.file_manager import save_json
from utils.db_manager import save_log, save_content
from utils.url_manager import adjust_url

CREATED_BY_FIND_REGEX = re.compile('(([0-9]{2}|[0-9]{4})[-\.][0-9]{1,2}[-\.][0-9]{1,2})')

def is_in_search_scope(url: str) -> bool:
    """
    현재 URL이 탐색영역 내에 있는 url인지 판단합니다
    """

    result = True
    
    # 영역제한: 아주대학교
    result = result and ("ajou.ac.kr" in url)

    # 영역제한: 공지사항
    # result = result and ("notice" in url)

    # 영역제한: 공홈 - 생활정보
    # result = result and ("life" in url)

    # 영역제한: 기숙사 홈페이지
    result = result and ("dorm" in url)

    return result

def process_page(driver, url, parent, queue, visit_mapping):
    """
    Selenium을 이용하여 지정된 URL을 렌더링한 후, 페이지 내의 링크와 onClick 이벤트가 있는 요소를 추출하여 queue에 추가합니다.
    방문한 URL과 부모 URL의 매핑 정보는 visit.json에 저장하고, MySQL DB의 scrap_data 테이블에도 삽입합니다.
    """
    try:
        url = adjust_url(url)

        # 페이지 조회 |=================================

        driver.get(url)
        time.sleep(PAGE_LOAD_DELAY)

        # 최초접속인 경우에만 데이터 저장
        if url not in visit_mapping:

            print(f"페이지 정보 저장: {url}")

            # 페이지 내 정보저장

            content_area = None
            try:
                content_area = driver.find_element(By.CLASS_NAME, "content")
            except NoSuchElementException:
                content_area = driver.find_element(By.TAG_NAME, "body")

            if content_area is None:
                return

            data = content_area.text
            title = driver.title
            
            dates_list = CREATED_BY_FIND_REGEX.findall(data)
            created_at = dates_list[0][0] if len(dates_list) > 0 else datetime.now().strftime("%Y-%m-%d")
            print(created_at)

            content_id = save_content(data)
            save_log(url, title, created_at, content_id, 0)

            # 접속기록 로깅
            visit_mapping[url] = parent
            save_json(VISIT_JSON, visit_mapping)

        # 다음 접속정보 탐색 |=================================
        
        # <a> 태그 추출
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                href = adjust_url(href)

                # 검색영역인 링크만 방문
                if not is_in_search_scope(href):
                    continue

                # 이미 접속한 페이지 미방문
                if href in visit_mapping:
                    continue
                
                # print(f"신규URL추가 (href): {href}")
                queue.append({"type": "link", "url": href, "parent": url})
        
        # onClick 이벤트가 등록된 요소 추출 (XPath 사용)
        elements = driver.find_elements(By.XPATH, '//*[@onclick]')
        for elem in elements:
            onclick = elem.get_attribute("onclick")
            identifier = elem.get_attribute("outerHTML")

            onclick = adjust_url(onclick)

            # 검색영역인 링크만 방문
            if not is_in_search_scope(onclick):
                continue

            # 이미 접속한 페이지 미방문
            if onclick in visit_mapping:
                continue

            # print(f"신규URL추가 (onclick): {onclick}")
            queue.append({"type": "event", "onClick": onclick, "identifier": identifier, "parent": url})

    except Exception as e:
        print(f"페이지 처리 중 오류 발생 (URL: {url}): {e}")