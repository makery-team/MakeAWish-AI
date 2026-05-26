import base64
import io
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# Gemini API 호출용 Python SDK
from google import genai
from PIL import Image
from dotenv import load_dotenv

# 1. 환경 변수 로드 (.env 파일에 GEMINI_API_KEY가 있어야 함)
load_dotenv()

CHAT_MODEL = "gemini-3.5-flash"
IMAGE_MODEL = "gemini-3.1-flash-image-preview"

# 2. SDK 클라이언트 초기화
client = genai.Client()

app = FastAPI(title="MakeAWish-AI Server")


# --- 서버 시작 이벤트 (모델 워밍업) ---
@app.on_event("startup")
async def startup_event():
    """서버 시작 시 모델을 미리 로드하여 첫 요청 시간 단축"""
    print("🔥 모델 워밍업 시작...")
    try:
        # 간단한 테스트 요청으로 모델 로드
        client.models.generate_content(
            model=CHAT_MODEL,
            contents=["Hello, warmup test"]
        )
        print("✅ 모델 워밍업 완료!")
    except Exception as e:
        print(f"⚠️ 워밍업 중 에러 (무시됨): {e}")


# --- 데이터 모델 정의 ---


class InpaintRequest(BaseModel):
    """이미지 편집(인페인팅) 요청 데이터 모델"""
    image_b64: str            # 원본 이미지 (Base64)
    mask_b64: str             # 편집할 영역을 표시한 마스크 이미지 (Base64)
    prompt: str               # 편집 요청 사항 (예: "여기에 하트 그려줘")
    reference_image_b64: str = None  # (선택) 참고용 이미지 (Base64)


class ChatRequest(BaseModel):
    """통합 채팅 요청 데이터 모델"""
    messages: list            # 이전 대화 내역 [{role: "user", content: "..."}, ...]
    current_message: str      # 현재 사용자가 보낸 메시지
    schema_json: dict = None  # (선택) 가게별 주문서 양식 (슬롯 필링용)


# --- 헬퍼 함수 ---

def b64_to_pil(b64_str):
    """Base64 문자열을 PIL 이미지 객체로 변환"""
    if not b64_str:
        return None
    if "base64," in b64_str:
        b64_str = b64_str.split("base64,")[1]
    img_data = base64.b64decode(b64_str)
    return Image.open(io.BytesIO(img_data))


def pil_to_b64(img):
    """PIL 이미지 객체를 Base64 문자열로 변환"""
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


# --- API 엔드포인트 ---

@app.post("/api/ai/chat")
async def chat_handler(request: ChatRequest):
    """
    [통합 채팅 API]
    사용자의 메시지를 분석하여 의도(Action)를 분류하고 적절한 응답을 반환합니다.

    1. SIMPLE_CHAT: 일상적인 인사나 단순 질문
    2. PORTFOLIO_LIST: 케이크 검색 및 추천 (태그 추출 포함)
    3. EDIT_IMAGE: 사용자가 이미지 편집(에디터) 진입을 원할 때
    4. SHOW_SCHEMA: 주문서 작성 중 추가 정보가 필요할 때
    5. CONFIRM_SLOTS: 모든 주문 정보 수집 완료 후 확인 단계
    6. ORDER_SUMMARY: 주문 내역 요약 및 가격 문의
    """
    print(f"💬 통합 채팅 요청 수신: {request.current_message}")
    try:
        # AI에게 부여할 페르소나와 처리 지침 (System Prompt)
        system_prompt = (
            "You are a professional and friendly assistant for a custom cake shop 'MakeAWish'. "
            "Analyze the user's message and current context to determine the most appropriate 'actionType'. "
            "\n\n### Action Types 설명:"
            "\n1. 'SIMPLE_CHAT': 인사, 단순 질문, 혹은 가벼운 대화"
            "\n2. 'PORTFOLIO_LIST': 사용자가 케이크를 찾거나 추천을 요청할 때. 검색 태그를 'data.tags'에 추출하세요."
            "\n3. 'EDIT_IMAGE': 사용자가 디자인 수정, 이미지 편집, 혹은 에디터 사용 의사를 보일 때"
            "\n4. 'SHOW_SCHEMA': 주문 진행 중(schema_json 존재 시) 비어있는 항목을 채우기 위해 질문이 필요할 때"
            "\n5. 'CONFIRM_SLOTS': 모든 필수 주문 정보가 수집되었을 때. 모든 정보를 'data.extracted_slots'에 포함하세요."
            "\n6. 'ORDER_SUMMARY': When the user asks for the status of their order or price information. Inform them that the shop owner will review the order and provide the final price."
            "\n\n### 응답 형식 (반드시 JSON 형식을 지킬 것):"
            "\n{"
            "\n  'actionType': '위의 6가지 타입 중 하나',"
            "\n  'message': '사용자에게 보내는 친절한 한국어 답변',"
            "\n  'data': {"
            "\n    'tags': ['빨강', '생일'] (PORTFOLIO_LIST인 경우만),"
            "\n    'extracted_slots': { '항목': '값' } (SHOW_SCHEMA, CONFIRM_SLOTS인 경우만),"
            "\n    'status': 'IN_PROGRESS' 또는 'COMPLETED' (주문 관련 시)"
            "\n  } 또는 데이터가 없으면 null"
            "\n}"
        )

        # 가게의 주문서 양식이 제공된 경우 프롬프트에 추가
        if request.schema_json:
            system_prompt += f"\n\n[현재 주문서 양식]: {json.dumps(request.schema_json, ensure_ascii=False)}"

        # 대화 맥락 구성을 위해 이전 내역과 현재 메시지 결합
        history = "\n".join(
            [f"{m.get('role')}: {m.get('content')}" for m in request.messages])
        user_input = f"--- 이전 대화 내역 ---\n{history}\n\n--- 사용자의 현재 메시지 ---\n{request.current_message}"

        # 최신 Gemini 모델 호출
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=[system_prompt, user_input],
            config={
                "response_mime_type": "application/json"
            }
        )

        # AI의 JSON 응답을 파싱하여 반환
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ 채팅 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai/inpaint")
async def generate_cake(request: InpaintRequest):
    """
    [이미지 편집(인페인팅) API]
    원본 이미지의 마스킹된 영역을 사용자의 프롬프트에 맞춰 수정합니다.
    """
    print(f"🎨 이미지 편집 요청 수신: {request.prompt}")

    try:
        # Base64 데이터를 이미지 객체로 변환
        original_img = b64_to_pil(request.image_b64)
        mask_img = b64_to_pil(request.mask_b64)
        reference_img = b64_to_pil(request.reference_image_b64)

        # 참고 사진 유무에 따른 프롬프트 구성
        if reference_img:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: 당신은 숙련된 케이크 데코레이터입니다. "
                "마스크된 영역(masked area)만 수정하세요. "
                "참고 사진(Reference Image)에 있는 인물이나 캐릭터를 마스크 영역에 그리세요. "
                "중요: 기존 케이크의 질감(버터크림 아이싱), 화풍, 파스텔 톤 색감을 완벽하게 유지해야 합니다. "
                "실사 사진처럼 만들지 말고, 케이크 크림으로 그린 듯한 느낌을 주어야 합니다."
            )
            contents = [final_prompt, original_img,
                        mask_img, reference_img]
        else:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: 당신은 숙련된 케이크 데코레이터입니다. "
                "마스크된 영역만 수정하세요. "
                "기존 케이크의 크림 질감과 파스텔 아트 스타일을 완벽하게 유지하여 자연스럽게 합성하세요."
            )
            contents = [final_prompt, original_img, mask_img]

        # 이미지 생성 전용 모델 호출
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents
        )

        # 생성된 결과 이미지(바이너리)를 추출하여 Base64로 반환
        for part in response.parts:
            if part.inline_data is not None:
                result_b64 = base64.b64encode(
                    part.inline_data.data
                ).decode("utf-8")
                mime_type = part.inline_data.mime_type or "image/png"

                print("✅ 이미지 편집 성공!")
                return {
                    "actionType": "INPAINTING_RESULT",
                    "result_image": f"data:{mime_type};base64,{result_b64}"
                }

        raise HTTPException(status_code=500, detail="이미지 생성에 실패했습니다.")

    except Exception as e:
        print(f"❌ 이미지 편집 에러: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def health():
    """서버 상태 확인용"""
    return {"status": "alive", "engine": CHAT_MODEL, "image_engine": IMAGE_MODEL}
