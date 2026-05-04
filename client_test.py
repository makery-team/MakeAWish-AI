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


def test_tags():
    print("\n🔍 1. 태그 추출 테스트 시작...")
    url = f"{BASE_URL}/tags"
    payload = {"query": "엄마 생신에 어울리는 빨간 케이크 찾아줘"}
    
    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code == 200:
        print(f"✅ 태그 추출 성공: {response.json()}")
    else:
        print(f"❌ 태그 추출 실패: {response.text}")


def test_order_filling():
    print("\n💬 2. 슬롯 필링 테스트 시작...")
    url = f"{BASE_URL}/order-filling"
    payload = {
        "schema_json": {
            "flavor": "string (초코, 바닐라 중 선택)",
            "size": "string (1호, 2호 중 선택)"
        },
        "messages": [
            {"role": "user", "content": "케이크 주문할게요"}
        ],
        "current_message": "초코맛으로 해주세요"
    }
    
    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if response.status_code == 200:
        print(f"✅ 슬롯 필링 성공: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ 슬롯 필링 실패: {response.text}")


def test_inpaint():
    print("\n🎨 3. 인페인팅 테스트 시작...")
    url = f"{BASE_URL}/inpaint"

    ORIGINAL_PATH = "img/original.png"
    MASK_PATH = "img/mask.png"
    REFERENCE_PATH = "img/reference.png"

    try:
        img_b64 = image_to_b64(ORIGINAL_PATH)
        mask_b64 = image_to_b64(MASK_PATH)
    except FileNotFoundError:
        print(f"❌ 에러: {ORIGINAL_PATH}와 {MASK_PATH} 파일이 있어야 합니다!")
        return

    payload = {
        "image_b64": f"data:image/png;base64,{img_b64}",
        "mask_b64": f"data:image/png;base64,{mask_b64}",
        "prompt": "중앙에 'Happy'라고 적어줘"
    }

    if os.path.exists(REFERENCE_PATH):
        ref_b64 = image_to_b64(REFERENCE_PATH)
        payload["reference_image_b64"] = f"data:image/png;base64,{ref_b64}"

    started = time.time()
    response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    elapsed = time.time() - started

    if response.status_code == 200:
        print(f"✅ 인페인팅 성공! ({elapsed:.1f}s)")
        result_data = response.json()["result_image"]
        header, encoded = result_data.split(",", 1)
        with open("server_result.png", "wb") as f:
            f.write(base64.b64decode(encoded))
        print("🎉 결과가 'server_result.png'로 저장되었습니다.")
    else:
        print(f"❌ 인페인팅 실패: {response.text}")


if __name__ == "__main__":
    test_tags()
    test_order_filling()
    # test_inpaint() # 이미지는 시간이 오래 걸리므로 필요시 주석 해제
