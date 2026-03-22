import requests
import base64
import os
import time

# 1. 서버 주소
URL = "http://127.0.0.1:8000/api/inpaint"
REQUEST_TIMEOUT = (10, 180)  # (connect timeout, read timeout)


def image_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run_test():
    print("🎨 프론트엔드 시뮬레이션 시작...")

    # 2. 로컬에 있는 이미지 읽어서 Base64로 자동 변환
    try:
        img_b64 = image_to_b64("original.png")
        mask_b64 = image_to_b64("mask.png")
    except FileNotFoundError:
        print("❌ 에러: original.png와 mask.png 파일이 폴더에 있어야 합니다!")
        return

    # 3. 서버에 보낼 데이터 (JSON)
    payload = {
        "image_b64": f"data:image/png;base64,{img_b64}",
        "mask_b64": f"data:image/png;base64,{mask_b64}",
        "prompt": "안경을 낀 남자 모습으로 바꿔줘"
    }

    print("📡 서버로 요청 보내는 중... (제미나이가 열심히 그리는 중)")

    # 4. 서버 호출
    started = time.time()
    try:
        response = requests.post(URL, json=payload, timeout=REQUEST_TIMEOUT)
    except requests.exceptions.ConnectTimeout:
        print("❌ 연결 타임아웃: 서버(uvicorn)가 실행 중인지 확인하세요.")
        return
    except requests.exceptions.ReadTimeout:
        print("❌ 응답 타임아웃: 이미지 생성이 오래 걸렸습니다. 잠시 후 다시 시도하세요.")
        return
    except requests.exceptions.ConnectionError:
        print("❌ 연결 실패: http://127.0.0.1:8000 서버에 접속할 수 없습니다.")
        return
    except requests.exceptions.RequestException as e:
        print(f"❌ 요청 실패: {e}")
        return

    elapsed = time.time() - started

    if response.status_code == 200:
        print(f"✅ 서버 응답 성공! ({elapsed:.1f}s)")
        result_data = response.json()["result_image"]

        # 5. 결과 Base64를 다시 이미지 파일로 저장
        header, encoded = result_data.split(",", 1)
        with open("server_result.png", "wb") as f:
            f.write(base64.b64decode(encoded))

        print("🎉 대성공! 결과가 'server_result.png'로 저장되었습니다.")
        os.startfile("server_result.png")  # 윈도우라면 바로 사진 띄우기
    else:
        print(f"❌ 서버 응답 실패 ({response.status_code}): {response.text}")


if __name__ == "__main__":
    run_test()
