import requests
import base64
import os
import time
import json

# 1. 서버 주소
BASE_URL = "http://127.0.0.1:8000/api/ai"
REQUEST_TIMEOUT = (30, 300)  # (connect timeout, read timeout)
MAX_RETRIES = 3


def retry_request(method, url, max_retries=MAX_RETRIES, **kwargs):
    """요청 재시도 로직"""
    for attempt in range(max_retries):
        try:
            if method == "post":
                return requests.post(url, timeout=REQUEST_TIMEOUT, **kwargs)
            else:
                return requests.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        except (requests.ConnectionError, requests.Timeout, KeyboardInterrupt) as e:
            if attempt == max_retries - 1:
                raise
            print(f"⚠️ 재시도 {attempt + 1}/{max_retries - 1}...")
            time.sleep(2)


def image_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def test_chat(message, schema=None):
    print(f"\n💬 채팅 테스트: '{message}'")
    url = f"{BASE_URL}/chat"
    payload = {
        "messages": [],
        "current_message": message
    }
    if schema:
        payload["schema_json"] = schema

    response = retry_request("post", url, json=payload)
    if response.status_code == 200:
        print(
            f"✅ 응답 성공: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 응답 실패: {response.text}")


def test_inpaint():
    print("\n🎨 인페인팅 테스트 시작 (비동기 방식)...")
    url = f"{BASE_URL}/inpaint"

    ORIGINAL_PATH = "img/original.png"
    MASK_PATH = "img/mask.png"

    try:
        img_b64 = image_to_b64(ORIGINAL_PATH)
        mask_b64 = image_to_b64(MASK_PATH)
    except FileNotFoundError:
        print(f"❌ 에러: 이미지 파일이 필요합니다. (img 폴더에 original.png, mask.png를 넣어주세요)")
        return

    # 이제 task_id가 필수로 들어갑니다.
    payload = {
        "task_id": 9999,
        "image_b64": f"data:image/png;base64,{img_b64}",
        "mask_b64": f"data:image/png;base64,{mask_b64}",
        "prompt": "중앙에 '안녕하세요'라고 적어줘"
    }

    response = retry_request("post", url, json=payload)

    if response.status_code == 202:
        print(f"✅ 인페인팅 백그라운드 작업 접수 성공! (상태 코드: 202)")
        print(f"응답 데이터: {response.json()}")
        print("백엔드 서버의 콘솔 로그를 확인해서 웹훅이 정상적으로 도착하는지 확인해 보세요!")
    else:
        print(f"❌ 인페인팅 접수 실패: {response.text}")


if __name__ == "__main__":
    # 1. 단순 인사
    test_chat("안녕하세요!")

    # 2. 디자인 검색
    test_chat("엄마 생신에 어울리는 화사한 케이크 보여줘")

    # 3. 이미지 편집 의사 표시
    test_chat("이 케이크 사진 좀 수정하고 싶어요")

    # 4. 주문 슬롯 필링
    cake_schema = {
        "flavor": "초코, 바닐라, 딸기 중 선택",
        "size": "1호, 2호, 3호 중 선택",
        "pickup_date": "YYYY-MM-DD"
    }
    test_chat("초코맛 1호로 주문할게요", schema=cake_schema)

    # 5. 인페인팅 테스트 실행
    test_inpaint()
