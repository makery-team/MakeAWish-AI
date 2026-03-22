import os
from google import genai
from google.genai import types
from PIL import Image
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env에서 GEMINI_API_KEY 자동 인식)
load_dotenv()

# 2. 신형 SDK 클라이언트 초기화 (문서와 동일!)
client = genai.Client()

def test_nano_banana_inpainting():
    print("🚀 [최신 SDK] 나노 바나나 2 (Gemini 3.1 Flash Image) 엔진 가동!")

    # 3. 로컬 이미지 로드
    try:
        original_image = Image.open("original.png")
        mask_image = Image.open("mask.png")
        print("✅ 원본 및 마스크 이미지 로드 성공!")
    except FileNotFoundError:
        print("❌ 에러: 'original.png' 또는 'mask.png' 파일이 없습니다!")
        return

    # 4. 프롬프트 엔지니어링 (사장님의 도메인 지식!)
    user_prompt = "이 부분을 귀여운 남자아이 캐릭터로 변경해줘"
    magic_prompt = "detailed buttercream icing texture, cute 2d character drawing, pastel color tone, matching the exact original cake decoration style"
    final_prompt = f"{user_prompt}. {magic_prompt}"

    print("📡 나노 바나나 2 모델로 데이터 전송 중... ")

    # 5. 문서에 나온 방식대로 generate_content 호출
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[
                final_prompt,
                original_image,
                mask_image
            ]
        )

        print("🎉 API 호출 성공! 이미지 추출 중...")
        
        # 6. 문서에 나온 방식대로 응답에서 이미지(inline_data)를 꺼내서 저장
        for i, part in enumerate(response.parts):
            if part.inline_data is not None:
                image = part.as_image()
                filename = f"final_cake_result_{i}.png"
                image.save(filename)
                print(f"👉 대성공! 완성된 이미지가 저장되었습니다: {filename}")
            elif part.text is not None:
                print("💡 제미나이의 코멘트:", part.text)

    except Exception as e:
        print(f"❌ API 호출 실패: {e}")

if __name__ == "__main__":
    test_nano_banana_inpainting()