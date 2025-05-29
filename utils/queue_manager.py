import json
import redis
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv
import time
from redis.exceptions import ConnectionError, RedisError
from utils.config import REDIS_CONFIG

load_dotenv()

class RedisQueueManager:
    def __init__(self, max_retries=3, retry_delay=1):
        self.redis_client = redis.Redis(
            host=REDIS_CONFIG["host"],
            port=REDIS_CONFIG["port"],
            password=REDIS_CONFIG["password"],
            db=REDIS_CONFIG["db"],
            decode_responses=True
        )
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.queue_key_prefix = "url_queue:"  # 큐 키 접두사
        self.processing_key_prefix = "processing_urls:"  # 처리 중인 URL 키 접두사
        self.visited_key_prefix = "visited_urls:"  # 방문한 URL 키 접두사
        self.temp_file = "temp_state"
        self.load_lock_key = "redis_load_lock"
        self.load_lock_timeout = 60 # 초 단위 락 타임아웃
        self._connect()

    def _connect(self):
        """Redis 서버에 연결을 시도합니다."""
        retries = 0
        while retries < self.max_retries:
            try:
                self.redis_client.ping()
                return
            except (ConnectionError, RedisError) as e:
                retries += 1
                if retries == self.max_retries:
                    raise Exception(f"Redis 연결 실패: {str(e)}")
                print(f"Redis 연결 재시도 {retries}/{self.max_retries}")
                time.sleep(self.retry_delay)

    def _execute_with_retry(self, operation):
        """Redis 작업을 재시도 로직과 함께 실행합니다."""
        retries = 0
        while retries < self.max_retries:
            try:
                return operation()
            except (ConnectionError, RedisError) as e:
                retries += 1
                if retries == self.max_retries:
                    raise Exception(f"Redis 작업 실패: {str(e)}")
                print(f"Redis 작업 재시도 {retries}/{self.max_retries}")
                time.sleep(self.retry_delay)
                self._connect()  # 재연결 시도

    def _get_queue_key(self, key: str) -> str:
        """키에 해당하는 큐 키를 반환합니다."""
        return f"{self.queue_key_prefix}{key}"

    def _get_processing_key(self, key: str) -> str:
        """키에 해당하는 처리 중인 URL 키를 반환합니다."""
        return f"{self.processing_key_prefix}{key}"

    def _get_visited_key(self, key: str) -> str:
        """키에 해당하는 방문한 URL 키를 반환합니다."""
        return f"{self.visited_key_prefix}{key}"

    def push(self, item: Dict[str, Any], key: str) -> None:
        """특정 키의 큐에 새로운 항목을 추가합니다."""
        def _push():
            self.redis_client.rpush(self._get_queue_key(key), json.dumps(item))
        self._execute_with_retry(_push)

    def pop(self, key: str) -> Optional[Dict[str, Any]]:
        """특정 키의 큐에서 항목을 가져옵니다."""
        def _pop():
            item = self.redis_client.lpop(self._get_queue_key(key))
            return json.loads(item) if item else None
        return self._execute_with_retry(_pop)

    def mark_as_processing(self, url: str, key: str) -> None:
        """URL을 특정 키의 처리 중인 상태로 표시합니다."""
        def _mark():
            self.redis_client.sadd(self._get_processing_key(key), url)
        self._execute_with_retry(_mark)

    def mark_as_visited(self, url: str, key: str) -> None:
        """URL을 특정 키의 방문 완료 상태로 표시합니다."""
        def _mark():
            self.redis_client.sadd(self._get_visited_key(key), url)
            self.redis_client.srem(self._get_processing_key(key), url)
        self._execute_with_retry(_mark)

    def is_visited(self, url: str, key: str) -> bool:
        """URL이 특정 키에서 이미 방문되었는지 확인합니다."""
        def _check():
            return self.redis_client.sismember(self._get_visited_key(key), url)
        return self._execute_with_retry(_check)

    def is_processing(self, url: str, key: str) -> bool:
        """URL이 특정 키에서 현재 처리 중인지 확인합니다."""
        def _check():
            return self.redis_client.sismember(self._get_processing_key(key), url)
        return self._execute_with_retry(_check)

    def get_queue_length(self, key: str) -> int:
        """특정 키의 현재 큐 길이를 반환합니다."""
        def _get_length():
            return self.redis_client.llen(self._get_queue_key(key))
        return self._execute_with_retry(_get_length)

    def clear(self, key: str) -> None:
        """특정 키의 모든 큐 데이터를 초기화합니다."""
        def _clear():
            self.redis_client.delete(self._get_queue_key(key))
            self.redis_client.delete(self._get_processing_key(key))
            self.redis_client.delete(self._get_visited_key(key))
        self._execute_with_retry(_clear)

    def clear_all(self):
        """Redis의 모든 데이터를 초기화합니다."""
        try:
            self.redis_client.flushall()
            print("Redis 데이터가 초기화되었습니다.")
        except Exception as e:
            print(f"Redis 초기화 중 오류 발생: {e}")
            raise

    def save_state_to_temp(self, key: str) -> None:
        """특정 키의 현재 Redis 상태를 임시 파일로 저장합니다."""
        try:
            state = {
                "queue": [json.loads(item) for item in self.redis_client.lrange(self._get_queue_key(key), 0, -1)],
                "processing": list(self.redis_client.smembers(self._get_processing_key(key))),
                "visited": list(self.redis_client.smembers(self._get_visited_key(key)))
            }
            with open(f"{self.temp_file}.{key}", 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print(f"Redis 상태가 {self.temp_file}.{key}에 저장되었습니다.")
        except Exception as e:
            print(f"Redis 상태 저장 중 오류 발생: {e}")

    def load_state_from_temp(self, key: str) -> bool:
        """특정 키의 임시 파일에서 Redis 상태를 불러옵니다."""
        temp_file = f"{self.temp_file}.{key}"
        if not os.path.exists(temp_file):
            print(f"임시 파일 {temp_file}가 존재하지 않습니다.")
            return False

        try:
            with open(temp_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # 기존 데이터 초기화
            self.clear(key)

            # 큐 데이터 복원
            if state.get("queue"):
                self.redis_client.rpush(self._get_queue_key(key), *[json.dumps(item) for item in state["queue"]])

            # 처리 중인 URL 복원
            if state.get("processing"):
                self.redis_client.sadd(self._get_processing_key(key), *state["processing"])

            # 방문한 URL 복원
            if state.get("visited"):
                self.redis_client.sadd(self._get_visited_key(key), *state["visited"])

            print(f"Redis 상태가 {temp_file}에서 복원되었습니다.")
            return True
        except Exception as e:
            print(f"Redis 상태 복원 중 오류 발생: {e}")
            return False

    def is_redis_empty(self, key: str) -> bool:
        """특정 키의 Redis 큐, 처리 중, 방문 완료 상태가 모두 비어있는지 확인합니다."""
        try:
            queue_len = self.redis_client.llen(self._get_queue_key(key))
            processing_count = self.redis_client.scard(self._get_processing_key(key))
            visited_count = self.redis_client.scard(self._get_visited_key(key))
            return queue_len == 0 and processing_count == 0 and visited_count == 0
        except Exception as e:
            print(f"Redis 상태 확인 중 오류 발생: {e}")
            return False

    def acquire_load_lock(self) -> bool:
        """상태 복원을 위한 Redis 락을 획득합니다."""
        try:
            # setnx는 키가 없을 때만 설정하고 True 반환, 이미 있으면 설정하지 않고 False 반환
            return self.redis_client.setnx(self.load_lock_key, os.getpid())
        except Exception as e:
            print(f"상태 복원 락 획득 중 오류 발생: {e}")
            return False

    def release_load_lock(self) -> None:
        """상태 복원을 위한 Redis 락을 해제합니다."""
        try:
            # 락 소유자만 해제하도록 검증 필요 (여기서는 단순 구현)
            # 실제 환경에서는 Lua 스크립트 등으로 원자적으로 구현하는 것이 안전
            if int(self.redis_client.get(self.load_lock_key) or 0) == os.getpid():
                self.redis_client.delete(self.load_lock_key)
        except Exception as e:
            print(f"상태 복원 락 해제 중 오류 발생: {e}")

    def is_first_scraper_for_loading(self) -> bool:
        """상태 복원 로딩을 담당할 첫 번째 스크래퍼인지 확인합니다."""
        try:
            # 임시 파일이 있고 Redis 큐가 비어있을 때만 복원 후보
            if os.path.exists(self.temp_file) and self.is_redis_empty():
                # 락 획득을 시도하여 성공하면 복원 담당
                if self.acquire_load_lock():
                    return True
                else:
                    # 락 획득 실패 -> 다른 스크래퍼가 이미 복원 중
                    print("다른 스크래퍼가 상태 복원 락을 소유하고 있습니다.")
                    return False
            elif os.path.exists(self.temp_file) and not self.is_redis_empty():
                # 임시 파일이 있지만 Redis에 이미 데이터가 있는 경우 (다른 스크래퍼가 이미 복원했거나 작업 중)
                print("임시 파일이 존재하지만 Redis에 이미 데이터가 있습니다. 복원하지 않습니다.")
                # 오래된 임시 파일 삭제 (선택 사항, 비정상 종료 후 재시작 시 중복 복원 방지)
                # os.remove(self.temp_file)
                return False
            else:
                # 임시 파일이 없는 경우 (새로운 시작)
                return False
        except Exception as e:
            print(f"상태 복원 담당 스크래퍼 확인 중 오류 발생: {e}")
            return False # 오류 발생 시 복원 시도 안함

    def delete_temp_file(self) -> None:
        """임시 파일을 삭제합니다."""
        try:
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
                print(f"임시 파일 {self.temp_file}를 삭제했습니다.")
        except Exception as e:
            print(f"임시 파일 삭제 중 오류 발생: {e}")

    def is_first_scraper(self) -> bool:
        """현재 스크래퍼가 첫 번째 스크래퍼인지 확인합니다."""
        try:
            scraper_key = "active_scraper"
            current_pid = os.getpid()

            # 임시 파일 존재 여부 확인
            temp_file_exists = os.path.exists(self.temp_file)

            # active_scraper 키의 존재 및 PID 확인
            stored_pid = self.redis_client.get(scraper_key)

            if stored_pid is None:
                # 키가 없는 경우: 새로운 시작이거나 이전 스크래퍼가 정상/비정상 종료됨
                if temp_file_exists:
                    # 임시 파일이 있으면 상태 복원 시도 (이전 비정상 종료 가정)
                    print("Redis 상태 키가 없지만 임시 파일이 존재합니다. 상태 복원을 시도합니다.")
                    # 여기서 바로 load_state_from_temp 호출하지 않고 main에서 처리
                    # 현재 스크래퍼가 첫 번째로 간주하고 상태 복원 로직으로 넘어감
                    return True
                else:
                    # 임시 파일도 없으면 완전히 새로운 시작
                    print("Redis 상태 키 및 임시 파일이 없습니다. 새로운 스크래핑을 시작합니다.")
                    # 현재 스크래퍼가 첫 번째로 간주
                    return True
            else:
                # 키가 존재하는 경우
                if int(stored_pid) == current_pid:
                    # 키의 PID가 현재 PID와 같으면 재시작된 같은 스크래퍼
                    print(f"동일한 스크래퍼 ({current_pid})가 Redis 키를 소유하고 있습니다.")
                    return True
                else:
                    # 키의 PID가 현재 PID와 다르면 다른 스크래퍼가 실행 중
                    print(f"다른 스크래퍼 ({stored_pid})가 실행 중입니다.")
                    return False

        except Exception as e:
            print(f"스크래퍼 상태 확인 중 오류 발생: {e}")
            # 오류 발생 시 안전하게 True를 반환하여 상태 복원 시도를 막지 않음
            return True

    def set_scraper_active(self):
        """현재 스크래퍼가 활성화되었음을 Redis에 표시합니다."""
        try:
            scraper_key = "active_scraper"
            current_pid = os.getpid()
            self.redis_client.set(scraper_key, str(current_pid), ex=3600) # 1시간 만료 시간 설정
            print(f"스크래퍼 ({current_pid})가 활성화되었습니다.")
        except Exception as e:
            print(f"스크래퍼 활성화 상태 설정 중 오류 발생: {e}")

    def cleanup_scraper_state(self):
        """스크래퍼 종료 시 상태를 정리합니다."""
        try:
            scraper_key = "active_scraper"
            current_pid = os.getpid()

            # 현재 프로세스의 PID와 일치하는 경우에만 키 삭제
            stored_pid = self.redis_client.get(scraper_key)
            if stored_pid is not None and int(stored_pid) == current_pid:
                self.redis_client.delete(scraper_key)
                print(f"스크래퍼 ({current_pid}) 상태 키를 삭제했습니다.")

            # 프로그램 정상 종료 시 임시 파일 삭제
            if os.path.exists(self.temp_file):
                 os.remove(self.temp_file)
                 print(f"임시 파일 {self.temp_file}를 삭제했습니다.")

        except Exception as e:
            print(f"스크래퍼 상태 정리 중 오류 발생: {e}") 