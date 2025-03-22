# main.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from utils.config import CHROME_HEADLESS_OPTIONS, START_URL
from utils.file_manager import initialize_files
from scraper.queue_processor import process_queue

def create_driver():
    chrome_options = Options()
    for arg in CHROME_HEADLESS_OPTIONS:
        chrome_options.add_argument(arg)
    driver = webdriver.Chrome(options=chrome_options)
    return driver

if __name__ == "__main__":
    # 필요한 디렉토리와 JSON 파일들을 초기화합니다.
    initialize_files()
    
    driver = create_driver()
    try:
        process_queue(driver, START_URL)
    finally:
        driver.quit()