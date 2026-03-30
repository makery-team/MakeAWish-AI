import base64
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# Gemini API 호출용 Python SDK
from google import genai
from PIL import Image
from dotenv import load_dotenv

# 1. 환경 변수 로드
load_dotenv()

# 2. SDK 클라이언트 초기화 (자동으로 .env의 GEMINI_API_KEY 사용)
client = genai.Client()

app = FastAPI(title="MakeAWish-AI Real-time Inpainting Server")

# 데이터 형식


class InpaintRequest(BaseModel):  # noqa
    image_b64: str            # 원본 이미지 (data:image/png;base64,...)
    mask_b64: str             # 마스크 이미지 (data:image/png;base64,...)
    prompt: str               # 사용자 요청
    reference_image_b64: str = None  # (선택) 참고할 사진 (인물, 캐릭터 등)

# Base64 문자열을 PIL 이미지로 바꾸는 헬퍼 함수


def b64_to_pil(b64_str):  # noqa
    if not b64_str:
        return None
    if "base64," in b64_str:
        b64_str = b64_str.split("base64,")[1]
    img_data = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(img_data))


# PIL 이미지를 다시 Base64로 바꾸는 헬퍼 함수
def pil_to_b64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


@app.post("/api/inpaint")
async def generate_cake(request: InpaintRequest):
    print(f"📥 요청 수신: {request.prompt}")

    try:
        # 3. Base64 ➡️ PIL 변환
        original_img = b64_to_pil(request.image_b64)
        mask_img = b64_to_pil(request.mask_b64)
        reference_img = b64_to_pil(request.reference_image_b64)

        # 4. 화풍 보존 및 참고 이미지 반영을 위한 시스템 프롬프트 합성
        if reference_img:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: You are an expert cake decorator. "
                "Modify ONLY the masked area of the cake. "
                "Draw the character or person from the 'Reference Image' onto the masked area. "
                "CRITICAL: The style MUST be a buttercream icing texture, hand-painted art style, "
                "and use pastel colors to perfectly match the original cake's aesthetic. "
                "Do NOT use realistic photo styles; it MUST look like it was drawn with cake cream."
            )
            contents = [final_prompt, original_img, mask_img, reference_img]
        else:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: You are an expert cake decorator. "
                "Modify ONLY the masked area. "
                "Keep the buttercream icing texture and pastel art style "
                "perfectly identical to the original cake."
            )
            contents = [final_prompt, original_img, mask_img]

        # 5. 제미나이 3.1 플래시 호출
        response = client.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=contents
        )

        # 6. 결과물 처리
        for part in response.parts:
            if part.inline_data is not None:
                # inline_data를 그대로 보내 이미지 객체 save 호환성 이슈를 피한다.
                result_b64 = base64.b64encode(
                    part.inline_data.data
                ).decode("utf-8")
                mime_type = part.inline_data.mime_type or "image/png"

                print("✅ 인페인팅 성공! 결과를 반환합니다.")
                return {
                    "result_image": f"data:{mime_type};base64,{result_b64}"
                }

        raise HTTPException(status_code=500, detail="이미지 생성 실패")

    except Exception as e:
        print(f"❌ 서버 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def health():
    return {"status": "alive", "engine": "Gemini 3.1 Flash Image"}
