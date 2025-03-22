# utils/file_manager.py
import os
import json
import requests
from utils.config import FILES_DIR, FILELIST_JSON, VISIT_JSON

def initialize_files():
    """
    필요한 디렉토리와 JSON 파일(filelist.json, visit.json)을 초기화합니다.
    """
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
    
    for filename in [FILELIST_JSON, VISIT_JSON]:
        if not os.path.exists(filename):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def process_file_download(url, parent, filelist):
    """
    파일 다운로드 응답인 경우, 파일을 FILES_DIR 폴더에 저장하고 filelist.json을 업데이트합니다.
    """
    if url in filelist:
        return filelist
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            local_filename = url.split("/")[-1]
            filepath = os.path.join(FILES_DIR, local_filename)
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            filelist[url] = {"parent": parent, "filename": local_filename}
            save_json(FILELIST_JSON, filelist)
            print(f"파일 다운로드 완료: {local_filename} (출처: {url})")
    except Exception as e:
        print(f"파일 다운로드 중 오류 발생 (URL: {url}): {e}")
    return filelist