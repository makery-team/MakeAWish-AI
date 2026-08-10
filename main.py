import base64
import io
import json
import re
import requests
import boto3
import uuid
import os
import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
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

# CORS 미들웨어 추가 (OPTIONS 405 에러 및 프론트엔드 통신 해결)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


from datetime import datetime

# --- 데이터 모델 정의 ---


from typing import Optional, List

class InpaintRequest(BaseModel):
    """이미지 편집(인페인팅) 요청 데이터 모델"""
    task_id: int              # 백엔드 작업 식별 ID
    prompt: str               # 편집 요청 사항 (예: "여기에 하트 그려줘")
    
    # 원본 이미지 (URL 우선, 없으면 Base64)
    image_url: Optional[str] = None
    image_b64: Optional[str] = None
    
    # 마스크 이미지 (URL 우선, 없으면 Base64)
    mask_url: Optional[str] = None
    mask_b64: Optional[str] = None
    
    # 참고용 이미지 (URL 우선, 없으면 Base64)
    reference_image_url: Optional[str] = None
    reference_image_b64: Optional[str] = None


class ChatRequest(BaseModel):
    """통합 채팅 요청 데이터 모델"""
    messages: list            # 이전 대화 내역 [{role: "user", content: "..."}, ...]
    current_message: str      # 현재 사용자가 보낸 메시지
    schema_json: Optional[dict] = None  # (선택) 가게별 주문서 양식 (슬롯 필링용)

class TagRecommendationRequest(BaseModel):
    """(AI) 포트폴리오 태그 추천 요청 데이터 모델"""
    image_url: Optional[str] = None     # 포트폴리오 이미지 URL
    imageUrl: Optional[str] = None      # (호환) 카멜케이스 이미지 URL
    image_b64: Optional[str] = None     # 포트폴리오 이미지 Base64
    imageB64: Optional[str] = None      # (호환) 카멜케이스 Base64
    description: Optional[str] = None   # 추가 설명문 (선택)
    text: Optional[str] = None          # (호환) 텍스트 설명
    prompt: Optional[str] = None        # (호환) 프롬프트 설명


class TagRecommendationResponse(BaseModel):
    """(AI) 포트폴리오 태그 추천 응답 데이터 모델 (Spring Boot 백엔드 DTO 호환)"""
    recommended_tags: List[str]         # 파이썬/스네이크 케이스
    recommendedTags: List[str]          # 자바/카멜 케이스 (Spring Boot 호환)
    tags: List[str]                     # 단순 태그 배열 (Spring Boot 호환)
    tagList: List[str]                  # 리스트 형식 호환

class ReviewSummaryRequest(BaseModel):
    reviews: List[str]

class ReviewSummaryResponse(BaseModel):
    summary: str
    positive_points: List[str]
    negative_points: List[str]

class StoreProfileSuggestRequest(BaseModel):
    """(AI) 프로필 개선 제안 요청 데이터 모델"""
    storeName: str
    description: Optional[str] = ""
    notice: Optional[str] = ""
    cautionNotice: Optional[str] = ""


class StoreProfileSuggestResponse(BaseModel):
    """(AI) 프로필 개선 제안 응답 데이터 모델"""
    overallFeedback: str
    suggestions: List[str]


class StoreBioGenerateRequest(BaseModel):
    """(AI) 소개글 자동 생성 요청 데이터 모델"""
    storeName: str
    keywords: Optional[str] = ""
    concept: Optional[str] = ""


class StoreBioGenerateResponse(BaseModel):
    """(AI) 소개글 자동 생성 응답 데이터 모델"""
    generatedBio: str

# --- S3 및 웹훅 설정 ---

s3_client = boto3.client('s3')

def upload_to_s3(img_bytes: bytes, content_type: str = "image/png") -> str:
    """바이트 데이터를 S3에 업로드하고 퍼블릭 URL을 반환합니다."""
    S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "makeawish-bucket")
    file_name = f"ai-generated/{uuid.uuid4().hex}.png"
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=file_name,
            Body=img_bytes,
            ContentType=content_type,
            ACL='public-read'
        )
        region = os.getenv("AWS_REGION", "ap-northeast-2")
        return f"https://{S3_BUCKET_NAME}.s3.{region}.amazonaws.com/{file_name}"
    except Exception as e:
        print(f"❌ S3 업로드 에러: {e}")
        raise e

async def process_and_send_webhook(task_id: int, request: InpaintRequest):
    """실제 이미지 생성 로직을 백그라운드에서 처리하고 웹훅으로 결과를 전송합니다."""
    webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:8080/api/ai-agent/webhook/inpaint")
    try:
        # URL 또는 Base64 데이터를 이미지 객체로 변환
        original_img = load_image(url=request.image_url, b64_str=request.image_b64)
        mask_img = load_image(url=request.mask_url, b64_str=request.mask_b64)
        reference_img = load_image(url=request.reference_image_url, b64_str=request.reference_image_b64)

        if not original_img or not mask_img:
            raise ValueError("원본 이미지와 마스크 이미지는 필수입니다.")

        if reference_img:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: 당신은 숙련된 케이크 데코레이터입니다. "
                "마스크된 영역(masked area)만 수정하세요. "
                "참고 사진(Reference Image)에 있는 인물이나 캐릭터를 마스크 영역에 그리세요. "
                "중요: 기존 케이크의 질감(버터크림 아이싱), 화풍, 파스텔 톤 색감을 완벽하게 유지해야 합니다. "
                "실사 사진처럼 만들지 말고, 케이크 크림으로 그린 듯한 느낌을 주어야 합니다."
            )
            contents = [final_prompt, original_img, mask_img, reference_img]
        else:
            final_prompt = (
                f"User Request: {request.prompt}. "
                "Instruction: 당신은 숙련된 케이크 데코레이터입니다. "
                "마스크된 영역만 수정하세요. "
                "기존 케이크의 크림 질감과 파스텔 아트 스타일을 완벽하게 유지하여 자연스럽게 합성하세요."
            )
            contents = [final_prompt, original_img, mask_img]

        # 모델 호출
        response = client.models.generate_content(model=IMAGE_MODEL, contents=contents)

        result_url = None
        for part in response.parts:
            if part.inline_data is not None:
                print("✅ 이미지 생성 완료, S3 업로드 시작...")
                result_url = upload_to_s3(part.inline_data.data, part.inline_data.mime_type or "image/png")
                break
        
        if not result_url:
            raise ValueError("이미지 생성 결과가 없습니다.")

        print("✅ S3 업로드 완료! 웹훅 전송...")
        payload = {"task_id": task_id, "result_image": result_url, "status": "COMPLETED"}
        async with httpx.AsyncClient() as http_client:
            await http_client.post(webhook_url, json=payload)
            print("✅ 웹훅 전송 성공!")

    except Exception as e:
        print(f"❌ 작업 에러 발생: {e}")
        # 실패 웹훅 전송
        payload = {"task_id": task_id, "result_image": "", "status": "FAILED"}
        try:
            async with httpx.AsyncClient() as http_client:
                await http_client.post(webhook_url, json=payload)
        except Exception:
            pass


# --- 헬퍼 함수 ---

def load_image(url: str = None, b64_str: str = None):
    """URL 또는 Base64 문자열로부터 PIL 이미지 객체를 생성합니다."""
    if url:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"이미지 URL 로드 실패: {e}")
    elif b64_str:
        return b64_to_pil(b64_str)
    return None


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

    1. SIMPLE_CHAT: 일상적인 인사나 단순 질문, 혹은 사용자가 이미지 편집/수정을 요구할 때의 안내
    2. PORTFOLIO_LIST: 케이크 검색 및 추천 (태그 추출 포함)
    3. SHOW_SCHEMA: 주문서 작성 중 추가 정보가 필요할 때
    4. CONFIRM_SLOTS: 모든 주문 정보 수집 완료 후 확인 단계
    5. ORDER_SUMMARY: 주문 내역 요약 및 가격 문의
    """
    print(f"💬 통합 채팅 요청 수신: {request.current_message}")
    try:
        # 현재 날짜(연도) 주입
        now = datetime.now()
        current_date_str = now.strftime('%Y-%m-%d')
        current_year = now.year

        # AI에게 부여할 페르소나와 처리 지침(System Prompt)
        system_prompt = (
            "You are a professional and friendly assistant for a custom cake shop 'MakeAWish'. "
            "Analyze the user's message and current context to determine the most appropriate 'actionType'. "
            "\n\n### Action Types 설명:"
            "\n1. 'SIMPLE_CHAT': 인사, 단순 질문, 가벼운 대화. 만약 사용자가 디자인 수정이나 이미지 편집을 요구하면, '사진 밑의 [시안 편집하기] 버튼을 눌러 직접 수정해 보세요!'라고 안내하세요."
            "\n2. 'PORTFOLIO_LIST': 사용자가 케이크를 찾거나 추천을 요청할 때. 검색 태그를 'data.tags'에 추출하세요."
            "\n3. 'SHOW_SCHEMA': 주문 진행 중 schema_json 존재 시 비어있는 값을 채우기 위해 질문이 필요할 때."
            f"\n4. 'CONFIRM_SLOTS': 모든 필수 주문 정보가 수집되었을 때. 모든 정보를 'data.extracted_slots'에 포함하세요. (반드시 날짜는 '{current_year}'년 기준으로 'YYYY-MM-DD', 시간은 'HH:MM' 형식으로 변환할 것. 오늘 날짜는 {current_date_str} 입니다.)"
            "\n5. 'ORDER_SUMMARY': When the user asks for the status of their order or price information. Inform them that the shop owner will review the order and provide the final price."
            "\n\n### 응답 형식 (반드시 JSON 형식을 지킬 것):"
            "\n{"
            "\n  'actionType': '위의 5가지 타입 중 하나',"
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
            system_prompt += (
                f"\n\n[현재 주문서 양식]: {json.dumps(request.schema_json, ensure_ascii=False)}"
                "\n\n[중요 지침]: 'data.extracted_slots'를 작성할 때, 반드시 [현재 주문서 양식]에 정의된 키(Key) 이름들만 정확히 사용해서 매핑하세요. 절대 임의의 새로운 키(예: '픽업일자', '시간', '케이크 맛' 등)를 만들거나 중복으로 넣지 마세요."
            )

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


@app.post("/api/ai/inpaint", status_code=202)
async def generate_cake(request: InpaintRequest, background_tasks: BackgroundTasks):
    """
    [비동기 이미지 편집(인페인팅) API]
    원본 이미지의 마스킹된 영역을 사용자의 프롬프트에 맞춰 수정합니다.
    작업은 백그라운드에서 진행되며, 완료 시 백엔드의 웹훅을 호출합니다.
    """
    print(f"🎨 이미지 편집 요청 수신 (Task ID: {request.task_id}): {request.prompt}")
    background_tasks.add_task(process_and_send_webhook, request.task_id, request)
    return {"message": "Processing started", "status": "202 Accepted", "task_id": request.task_id}

@app.post("/api/ai/portfolios/tags/recommend", response_model=TagRecommendationResponse)
@app.post("/api/ai/generate-tags", response_model=TagRecommendationResponse)
async def recommend_portfolio_tags(request: TagRecommendationRequest):
    """
    [(AI) 포트폴리오 태그 추천 API]
    이미지(URL 또는 Base64)와 설명을 분석하여 
    커스텀 케이크 포트폴리오에 어울리는 추천 태그 목록(List[str])을 반환합니다.
    """
    url = request.image_url or request.imageUrl
    b64 = request.image_b64 or request.imageB64
    desc = request.description or request.text or request.prompt

    print(f"🏷️ 포트폴리오 태그 추천 요청 수신 (설명: {desc})")
    try:
        # 1. 이미지 로드 (URL 우선, 없으면 Base64)
        input_img = None
        if url or b64:
            try:
                input_img = load_image(url=url, b64_str=b64)
            except Exception as img_err:
                print(f"⚠️ 이미지 로드 실패 (텍스트 설명으로 대체 시도): {img_err}")

        if not input_img and not desc:
            raise HTTPException(status_code=400, detail="이미지(image_url/image_b64) 또는 설명(description) 중 하나는 필수입니다.")

        # 2. AI 분석용 프롬프트 구성 (엄격한 JSON 더블 쿼트 포맷 지정)
        system_prompt = (
            "You are an expert AI tagger for custom cake portfolios. "
            "Analyze the provided image and/or text description of the custom cake. "
            "Extract 3 to 7 concise and relevant Korean tags. "
            "Focus on: Cake category, Color, Design elements, Character, Target recipient, or Anniversary type. "
            'Example tags: ["입체케이크", "강아지", "파스텔톤", "생일축하", "티아라", "레터링케이크"]. '
            "\n\n### Response Format (Strict JSON only with double quotes):"
            '\n{"recommended_tags": ["태그1", "태그2", "태그3"]}'
        )

        contents = [system_prompt]

        # 이미지가 존재하는 경우 멀티모달 입력으로 추가
        if input_img:
            contents.append(input_img)

        # 텍스트 설명이 존재하는 경우 추가
        if desc:
            contents.append(f"Additional Description: {desc}")

        # 3. Gemini 모델 호출 (JSON 응답 모드)
        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config={
                "response_mime_type": "application/json"
            }
        )

        # 4. JSON 파싱 및 예외 안전 처리 (마크다운/트레일링 콤마 보정 후 로드)
        raw_text = response.text.strip()
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            raw_text = match.group(0)

        # 트레일링 콤마(끝 쉼표) 제거 보정
        raw_text = re.sub(r",\s*([\]}])", r"\1", raw_text)

        try:
            result_json = json.loads(raw_text)
            tags = (
                result_json.get("recommended_tags")
                or result_json.get("recommendedTags")
                or result_json.get("tags")
                or result_json.get("tagList")
                or []
            )
            if not tags or not isinstance(tags, list):
                tags = ["커스텀케이크", "주문제작", "레터링케이크"]
            return TagRecommendationResponse(
                recommended_tags=tags,
                recommendedTags=tags,
                tags=tags,
                tagList=tags,
            )
        except Exception as parse_err:
            print(f"⚠️ JSON 파싱 실패 ({parse_err}), raw_text: {raw_text}")
            fallback_tags = ["커스텀케이크", "주문제작", "레터링케이크"]
            return TagRecommendationResponse(
                recommended_tags=fallback_tags,
                recommendedTags=fallback_tags,
                tags=fallback_tags,
                tagList=fallback_tags,
            )

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ 태그 추천 처리 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=f"태그 추천 처리 실패: {str(e)}")

@app.post("/api/ai/reviews/summary", response_model=ReviewSummaryResponse)
async def summarize_reviews(request: ReviewSummaryRequest):
    """
    [(AI) 리뷰 요약 조회 API]
    고객 리뷰 목록(List[str])을 분석하여 종합 요약 및 긍정/개선 포인트를 JSON 형태로 반환합니다.
    """
    print(f"📊 리뷰 요약 요청 수신 (리뷰 수: {len(request.reviews)}개)")
    try:
        if not request.reviews:
            raise HTTPException(status_code=400, detail="리뷰 목록은 최소 1개 이상이어야 합니다.")

        prompt = (
            "You are an AI specialized in analyzing customer reviews for custom cake shops. "
            "Analyze the following list of reviews and generate: "
            "1. Overall summary (2-3 sentences in Korean) "
            "2. Key positive points (bullet points) "
            "3. Key areas for improvement or negative points (bullet points) "
            "\n\n### Response Format (JSON only):"
            "\n{"
            "\n  \"summary\": \"종합 요약문\","
            "\n  \"positive_points\": [\"장점1\", \"장점2\"],"
            "\n  \"negative_points\": [\"아쉬운점1\"]"
            "\n}"
        )

        contents = [prompt, f"Reviews: {json.dumps(request.reviews, ensure_ascii=False)}"]

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config={"response_mime_type": "application/json"}
        )

        result_json = json.loads(response.text)
        return ReviewSummaryResponse(
            summary=result_json.get("summary", ""),
            positive_points=result_json.get("positive_points", []),
            negative_points=result_json.get("negative_points", [])
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ 리뷰 요약 처리 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=f"리뷰 요약 처리 실패: {str(e)}")


@app.post("/api/ai/stores/profile-suggest", response_model=StoreProfileSuggestResponse)
async def suggest_profile_improvement(request: StoreProfileSuggestRequest):
    """
    [(AI) 프로필 개선 제안 API]
    매장의 현재 프로필(소개, 공지사항, 주의사항)을 분석하여 개선점 및 피드백을 제공합니다.
    """
    print(f"💡 프로필 개선 제안 요청 수신 (매장명: {request.storeName})")
    try:
        prompt = (
            "You are a professional marketing and branding consultant for custom cake shops. "
            "Analyze the following shop profile information and provide constructive feedback and actionable suggestions "
            "to make the profile more appealing to customers and improve conversion rates. "
            "\n\n### Profile Information:"
            f"\n- Store Name: {request.storeName}"
            f"\n- Description: {request.description}"
            f"\n- Notice: {request.notice}"
            f"\n- Caution/Order Rules: {request.cautionNotice}"
            "\n\n### Response Format (JSON only in Korean):"
            "\n{"
            "\n  \"overallFeedback\": \"전반적인 피드백 및 평가 (2-3문장)\","
            "\n  \"suggestions\": [\"개선 제안 1\", \"개선 제안 2\", \"개선 제안 3\"]"
            "\n}"
        )

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=[prompt],
            config={"response_mime_type": "application/json"}
        )
        result_json = json.loads(response.text)
        return StoreProfileSuggestResponse(
            overallFeedback=result_json.get("overallFeedback", ""),
            suggestions=result_json.get("suggestions", [])
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ 프로필 개선 제안 처리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"프로필 개선 제안 처리 실패: {str(e)}")


@app.post("/api/ai/stores/generate-bio", response_model=StoreBioGenerateResponse)
async def generate_store_bio(request: StoreBioGenerateRequest):
    """
    [(AI) 소개글 자동 생성 API]
    매장명, 키워드, 컨셉을 기반으로 매력적인 매장 소개문(Bio)을 자동 작성합니다.
    """
    print(f"✍️ 소개글 자동 생성 요청 수신 (매장명: {request.storeName})")
    try:
        prompt = (
            "You are a professional copywriter for custom cake shops. "
            "Generate a charming, polite, and catchy shop introduction bio (2-4 sentences in Korean) "
            "based on the store name, keywords, and concept provided below. "
            "\n\n### Input Data:"
            f"\n- Store Name: {request.storeName}"
            f"\n- Keywords: {request.keywords}"
            f"\n- Concept/Vibe: {request.concept}"
            "\n\n### Response Format (JSON only):"
            "\n{"
            "\n  \"generatedBio\": \"생성된 친절하고 매력적인 매장 소개글 문장\""
            "\n}"
        )

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=[prompt],
            config={"response_mime_type": "application/json"}
        )
        result_json = json.loads(response.text)
        return StoreBioGenerateResponse(
            generatedBio=result_json.get("generatedBio", "")
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ 소개글 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"소개글 생성 실패: {str(e)}")

@app.get("/")
async def health():
    """서버 상태 확인용"""
    return {"status": "alive", "engine": CHAT_MODEL, "image_engine": IMAGE_MODEL}
