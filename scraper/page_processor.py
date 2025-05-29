import time
import re
import os
from typing import Optional
import requests
from datetime import datetime
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils.config import PAGE_LOAD_DELAY, VISIT_JSON, FILES_DIR, FILELIST_JSON
from utils.file_manager import save_json, save_content, load_json
from utils.db_manager import save_log
from utils.url_manager import adjust_url
from utils.queue_manager import RedisQueueManager
from utils.url_matcher import get_categories_for_url

CREATED_BY_FIND_REGEX = re.compile('(([0-9]{2}|[0-9]{4})[-\.][0-9]{1,2}[-\.][0-9]{1,2})')

def is_valid_url(url: str) -> bool:
    """URL이 유효한지 검증합니다."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def is_in_search_scope(url: str) -> bool:
    """현재 URL이 탐색영역 내에 있는 url인지 판단합니다."""
    if not is_valid_url(url):
        return False
        
    result = True
    
    # 영역제한: 아주대학교
    result = result and ("ajou.ac.kr" in url)

    # 영역제한: 공지사항
    # result = result and ("notice" in url)

    # 영역제한: 공홈 - 생활정보
    # result = result and ("life" in url)

    # 영역제한: 기숙사 홈페이지
    # result = result and ("dorm" in url)

    return result

def wait_for_page_load(driver, timeout=10):
    """페이지 로딩이 완료될 때까지 대기합니다."""
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script('return document.readyState') == 'complete'
        )
    except TimeoutException:
        print("페이지 로딩 시간 초과")
        raise

def process_image(url: str, parent_url: str, queue_manager: RedisQueueManager) -> Optional[int]:
    """
    이미지 URL을 다운로드하고 파일 및 DB에 저장합니다.
    성공 시 content_id를 반환합니다.
    """
    if queue_manager.is_visited(url) or queue_manager.is_processing(url):
        print(f"ㄴ이미 처리 중이거나 방문한 이미지: {url}")
        return None

    print(f"ㄴ이미지 처리 시작: {url}")
    queue_manager.mark_as_processing(url)

    try:
        r = requests.get(url, stream=True, timeout=10)
        r.raise_for_status() # HTTP 오류 발생 시 예외 발생

        content_type = r.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            print(f"ㄴURL은 이미지가 아닙니다: {url} (Content-Type: {content_type})")
            return None

        # 파일 이름 및 확장자 추출
        org_filename = os.path.basename(urlparse(url).path)
        if not org_filename:
             org_filename = "downloaded_image"
        org_filename, org_ext = os.path.splitext(org_filename)
        org_ext = org_ext.lstrip(".")

        # DB에 메타데이터 저장 (data 컬럼은 비워둠)
        # data_type 2는 이미지로 가정 (필요시 config에 정의)
        log_id = save_log(url, org_filename + "." + org_ext, datetime.now().strftime("%Y-%m-%d"), data_type=2) # data_type=2 (이미지)
        content_id = save_content(data="", category=None, log_id=log_id, data_type=2, org_filename=org_filename, org_ext=org_ext) # data 컬럼은 비워둠

        if not content_id:
            print(f"ㄴ이미지 메타데이터 DB 저장 실패: {url}")
            return None

        # 파일을 ./files/{content_id}.{ext} 형식으로 저장
        filepath = os.path.join(FILES_DIR, f"{content_id}.{org_ext}")
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # filelist.json 업데이트
        # filelist = load_json(FILELIST_JSON)
        # filelist[url] = {
        #     "parent": parent_url,
        #     "filename": org_filename,
        #     "ext": org_ext,
        #     "log_id": log_id
        # }
        # save_json(FILELIST_JSON, filelist)

        # visit.json 업데이트
        # visit_data = load_json(VISIT_JSON)
        # visit_data[url] = {
        #     "visited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        #     "type": "image",
        #     "parent": parent_url,
        #     "filename": org_filename,
        #     "ext": org_ext,
        #     "log_id": log_id
        # }
        # save_json(VISIT_JSON, visit_data)

        print(f"ㄴ이미지 다운로드 및 저장 완료: {filepath} (출처: {url})")

        queue_manager.mark_as_visited(url) # 방문 상태로 표시
        return content_id

    except requests.exceptions.RequestException as e:
        print(f"ㄴ이미지 다운로드 요청 오류 (URL: {url}): {e}")
    except Exception as e:
        print(f"ㄴ이미지 처리 중 오류 발생 (URL: {url}): {e}")
    finally:
        queue_manager.mark_as_visited(url) # 실패하더라도 재처리 방지

    return None

def process_page(driver, url: str, queue_manager: RedisQueueManager) -> None:
    """
    Selenium을 이용하여 지정된 URL을 렌더링한 후, 페이지 내의 링크, onClick 이벤트, 이미지를 추출하여 queue 또는 파일로 처리합니다.
    """
    print(f"페이지 처리: {url}")
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            url = adjust_url(url)
            if not is_valid_url(url):
                print(f"ㄴ유효하지 않은 URL: {url}")
                return

            # 페이지 조회
            driver.get(url)
            wait_for_page_load(driver)
            time.sleep(PAGE_LOAD_DELAY)

            # 최초접속인 경우에만 데이터 저장
            if not queue_manager.is_visited(url):
                print(f"ㄴ페이지 정보 저장: {url}")

                # 페이지 내 정보저장
                content_area = None
                try:
                    content_area = driver.find_element(By.CLASS_NAME, "content")
                except NoSuchElementException:
                    try:
                        content_area = driver.find_element(By.TAG_NAME, "body")
                    except NoSuchElementException:
                        print(f"ㄴ컨텐츠 영역을 찾을 수 없음: {url}")
                        return

                data = content_area.get_attribute("outerHTML")
                title = driver.title
                
                dates_list = CREATED_BY_FIND_REGEX.findall(data)
                created_at = dates_list[0][0] if dates_list else datetime.now().strftime("%Y-%m-%d")
                print(f"ㄴ생성일: {created_at}")

                # URL에 해당하는 모든 카테고리 가져오기
                categories = get_categories_for_url(url)
                log_id = save_log(url, title, created_at, 0)
                for category in categories:
                    content_id = save_content(data, category, log_id)

            # 페이지 내 이미지 찾기 및 처리
            process_images(driver, url, queue_manager)

            # 다음 접속정보 탐색
            process_links(driver, url, queue_manager)
            process_onclick_events(driver, url, queue_manager)
            
            # 성공적으로 처리되면 종료
            return

        except TimeoutException as e:
            print(f"ㄴ페이지 로딩 시간 초과 (URL: {url}): {e}")
        except WebDriverException as e:
            print(f"ㄴ웹드라이버 오류 (URL: {url}): {e}")
        except Exception as e:
            print(f"ㄴ페이지 처리 중 오류 발생 (URL: {url}): {e}")
        
        if attempt < max_retries - 1:
            print(f"ㄴ재시도 중... ({attempt + 1}/{max_retries})")
            time.sleep(retry_delay)
        else:
            print(f"ㄴ최대 재시도 횟수 초과 (URL: {url})")

def process_links(driver, parent_url: str, queue_manager: RedisQueueManager) -> None:
    """
    페이지 내의 링크를 처리합니다.
    파일 다운로드 URL의 경우 여기서 처리되지 않음 (큐에 넣지 않고 바로 is_file_download에서 처리)
    """
    try:
        anchors = driver.find_elements(By.TAG_NAME, "a")
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                href = adjust_url(href)
                if is_in_search_scope(href) and not queue_manager.is_visited(href):
                    queue_manager.push({
                        "type": "link",
                        "url": href,
                        "parent": parent_url
                    })
    except Exception as e:
        print(f"링크 처리 중 오류 발생: {e}")

def process_onclick_events(driver, parent_url: str, queue_manager: RedisQueueManager) -> None:
    """
    onClick 이벤트가 있는 요소를 처리합니다.
    """
    try:
        elements = driver.find_elements(By.XPATH, '//*[@onclick]')
        for elem in elements:
            onclick = elem.get_attribute("onclick")
            identifier = elem.get_attribute("outerHTML")

            if onclick:
                onclick = adjust_url(onclick)
                if is_in_search_scope(onclick) and not queue_manager.is_visited(onclick):
                    queue_manager.push({
                        "type": "event",
                        "url": onclick,
                        "onClick": onclick,
                        "identifier": identifier,
                        "parent": parent_url
                    })
    except Exception as e:
        print(f"onClick 이벤트 처리 중 오류 발생: {e}")

def process_images(driver, parent_url: str, queue_manager: RedisQueueManager) -> None:
    """
    페이지 내의 이미지를 찾아 처리합니다.
    """
    try:
        images = driver.find_elements(By.TAG_NAME, "img")
        for img in images:
            src = img.get_attribute("src")
            if src:
                image_url = adjust_url(src) # URL 정규화 함수 사용
                if is_valid_url(image_url) and is_in_search_scope(image_url):
                    # 이미지는 큐에 넣지 않고 바로 다운로드 처리
                    process_image(image_url, parent_url, queue_manager)
    except Exception as e:
        print(f"ㄴ이미지 추출 중 오류 발생: {e}")