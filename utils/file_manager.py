# utils/file_manager.py
import os
import json
import re
import requests
from utils.config import FILES_DIR, FILELIST_JSON, VISIT_JSON
from utils.db_manager import save_content
from datetime import datetime

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

def process_file_download(url, parent, filelist, log_id=None):
    """
    파일 다운로드 응답인 경우, 파일을 FILES_DIR 폴더에 저장하고 filelist.json을 업데이트합니다.
    """
    # if url in filelist:
    #     return filelist
    try:
        r = requests.get(url, stream=True)
        content_disposition = r.headers.get("Content-Disposition", "")

        if r.status_code == 200:

            org_filename = None
            if "filename=" in content_disposition:
                filename_match = re.search(r'filename="?([^\";]+)"?', content_disposition)
                if filename_match:
                    org_filename = filename_match.group(1)
            
            if not org_filename:
                org_filename = os.path.basename(url.split("?")[0])
            
            org_filename, org_ext = os.path.splitext(org_filename)
            org_ext = org_ext.lstrip(".")

            content_id = save_content("", org_filename, org_ext, org_filename=org_filename, org_ext=org_ext)
            filepath = os.path.join(FILES_DIR, content_id)

            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            
            # filelist[url] = {
            #     "parent": parent, 
            #     "filename": org_filename,
            #     "ext": org_ext,
            #     "log_id": log_id
            # }
            # save_json(FILELIST_JSON, filelist)

            # visit.json 업데이트
            # visit_data = load_json(VISIT_JSON)
            # visit_data[url] = {
            #     "visited_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            #     "type": "file",
            #     "parent": parent,
            #     "filename": org_filename,
            #     "ext": org_ext,
            #     "log_id": log_id
            # }
            # save_json(VISIT_JSON, visit_data)

            print(f"파일 다운로드 완료: {content_id} (출처: {url})")
    except Exception as e:
        print(f"파일 다운로드 중 오류 발생 (URL: {url}): {e}")
    # return filelist