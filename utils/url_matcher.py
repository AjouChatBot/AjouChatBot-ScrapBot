import json
import re
from typing import Dict, List, Optional
from utils.config import CAT_MAPPING_JSON

def load_category_mapping() -> Dict[str, List[str]]:
    """카테고리 매핑 파일을 로드합니다."""
    try:
        with open(CAT_MAPPING_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"경고: {CAT_MAPPING_JSON} 파일을 찾을 수 없습니다.")
        return {}
    except json.JSONDecodeError:
        print(f"경고: {CAT_MAPPING_JSON} 파일의 JSON 형식이 올바르지 않습니다.")
        return {}

def pattern_to_regex(pattern: str) -> str:
    """URL 패턴을 정규식으로 변환합니다."""
    # 특수문자 escape 후, '*'만 '.*'로 변환
    regex = re.escape(pattern)
    regex = regex.replace(r'\*', '.*')
    return f"^{regex}"  # 끝에 $ 제거로 prefix 매칭

def get_categories_for_url(url: str):
    """URL에 일치하는 모든 카테고리 리스트와 매칭 결과를 반환합니다."""
    mapping = load_category_mapping()
    matched_categories = []
    match_results = []
    all_patterns = []
    for category, patterns in mapping.items():
        for pattern in patterns:
            regex = pattern_to_regex(pattern)
            is_match = bool(re.match(regex, url))
            match_results.append('[0]' if is_match else '[-]')
            all_patterns.append((category, pattern))
            if is_match:
                matched_categories.append(category)
    # 결과 한 줄로 출력
    print('ㄴ', ' '.join(match_results))
    if len(match_results) > 0:
        print('ㄴ-', ' '.join(matched_categories))
        
    return matched_categories 