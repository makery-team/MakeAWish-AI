import requests
import base64
import os
import time
import json

# 1. 서버 주소
BASE_URL = "http://127.0.0.1:8000/api/ai"
REQUEST_TIMEOUT = (10, 180)  # (connect timeout, read timeout)


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

    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code == 200:
        print(
            f"✅ 응답 성공: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 응답 실패: {response.text}")


def test_inpaint():
    print("\n🎨 인페인팅 테스트 시작...")
    url = f"{BASE_URL}/inpaint"

    ORIGINAL_PATH = "img/original.png"
    MASK_PATH = "img/mask.png"

    try:
        img_b64 = image_to_b64(ORIGINAL_PATH)
        mask_b64 = image_to_b64(MASK_PATH)
    except FileNotFoundError:
        print(f"❌ 에러: 이미지 파일이 필요합니다.")
        return

    payload = {
        "image_b64": f"data:image/png;base64,{img_b64}",
        "mask_b64": f"data:image/png;base64,{mask_b64}",
        "prompt": "중앙에 'Happy'라고 적어줘"
    }

    started = time.time()
    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    elapsed = time.time() - started

    if response.status_code == 200:
        print(f"✅ 인페인팅 성공! ({elapsed:.1f}s)")
        result_data = response.json()
        print(f"결과 actionType: {result_data.get('actionType')}")

        # 이미지 데이터 추출 및 저장
        img_data_str = result_data.get("result_image")
        if img_data_str and "," in img_data_str:
            header, encoded = img_data_str.split(",", 1)
            with open("server_result.png", "wb") as f:
                f.write(base64.b64decode(encoded))
            print("🎉 결과가 'server_result.png'로 저장되었습니다.")
    else:
        print(f"❌ 인페인팅 실패: {response.text}")


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
