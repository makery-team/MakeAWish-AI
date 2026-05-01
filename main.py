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

app = FastAPI(title="MakeAWish-AI Server")

# 데이터 형식


class InpaintRequest(BaseModel):  # noqa
    image_b64: str            # 원본 이미지 (data:image/png;base64,...)
    mask_b64: str             # 마스크 이미지 (data:image/png;base64,...)
    prompt: str               # 사용자 요청
    reference_image_b64: str = None  # (선택) 참고할 사진 (인물, 캐릭터 등)


class TagRequest(BaseModel):
    query: str                # 사용자의 검색 질문


class OrderFillRequest(BaseModel):
    schema_json: dict         # 가게의 주문서 양식 (JSON)
    messages: list            # 지금까지의 대화 내역
    current_message: str      # 현재 사용자의 메시지


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


@app.post("/api/ai/tags")
async def extract_tags(request: TagRequest):
    """
    사용자의 검색 쿼리에서 DB 검색용 태그를 추출합니다.
    """
    print(f"🔍 태그 추출 요청: {request.query}")
    try:
        system_prompt = (
            "You are a helpful assistant for a custom cake shop. "
            "Extract search keywords (tags) from the user's query for database searching. "
            "The tags should include colors, occasions (birthday, anniversary, etc.), "
            "styles (cute, elegant, etc.), and target recipients (mom, friend, child, etc.). "
            "Return the tags as a JSON list of strings. "
            "Example Output: ['red', 'birthday', 'mother', 'fancy']"
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash",  # 텍스트 분석에 최적화된 모델 사용
            contents=[system_prompt, request.query],
            config={
                "response_mime_type": "application/json"
            }
        )
        return {"tags": response.text}
    except Exception as e:
        print(f"❌ 태그 추출 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/order-filling")
async def fill_order_slots(request: OrderFillRequest):
    """
    주문서 양식과 대화 내용을 바탕으로 정보를 추출하고 다음 질문을 생성합니다.
    """
    print(f"💬 주문 슬롯 필링 요청: {request.current_message}")
    try:
        system_prompt = (
            f"You are a professional cake shop clerk. Your goal is to fill out the following order schema: {request.schema_json}. "
            "Based on the conversation history and the current user message, identify any missing information in the schema. "
            "If information is provided, extract it into the 'extracted_slots' field. "
            "Then, generate the 'next_question' to ask the user for the next missing information in a natural, friendly tone. "
            "If all information is collected, set 'status' to 'COMPLETED'. Otherwise, set it to 'IN_PROGRESS'. "
            "Return the result as a JSON object with 'extracted_slots', 'next_question', and 'status' fields."
        )

        history = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in request.messages])
        user_input = f"History: {history}\nUser: {request.current_message}"

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[system_prompt, user_input],
            config={
                "response_mime_type": "application/json"
            }
        )
        return response.text
    except Exception as e:
        print(f"❌ 슬롯 필링 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
