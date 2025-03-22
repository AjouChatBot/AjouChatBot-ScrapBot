# scraper/event_processor.py
import time
from selenium.common.exceptions import NoAlertPresentException
from utils.config import PAGE_LOAD_DELAY

def process_event(driver, event_item, queue):
    """
    onClick 이벤트 코드를 실행한 후, 링크 이동이나 팝업 발생 등으로 인한 페이지 변화를 처리합니다.
    """
    parent = event_item.get("parent")
    onclick_code = event_item.get("onClick")
    try:
        driver.execute_script(onclick_code)
        time.sleep(PAGE_LOAD_DELAY)
        
        new_url = driver.current_url
        if new_url != parent:
            queue.appendleft({"type": "link", "url": new_url, "parent": parent})
        
        try:
            alert = driver.switch_to.alert
            popup_text = alert.text
            print(f"팝업 발생 감지: {popup_text}")
            alert.accept()
            queue.appendleft({"type": "link", "url": driver.current_url, "parent": parent})
        except NoAlertPresentException:
            pass
    except Exception as e:
        print(f"이벤트 처리 중 오류 발생: {e}")