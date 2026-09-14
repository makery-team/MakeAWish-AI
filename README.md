# 🧠 MakeAWish AI Microservice (Conversational Engine & Inpainting)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-v0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=for-the-badge&logo=pydantic&logoColor=white" />
  <img src="https://img.shields.io/badge/Google%20Gemini-1.5%20%2F%20Flash-4285F4?style=for-the-badge&logo=google-gemini&logoColor=white" />
  <img src="https://img.shields.io/badge/Stable%20Diffusion-Inpainting-FFA116?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Uvicorn-ASGI-499848?style=for-the-badge" />
</p>

MakeAWish AI 마이크로서비스 저장소입니다. FastAPI 기반의 비동기 서빙 엔진으로, 매장별 동적 주문서 양식(JSON Schema)을 런타임에 학습하여 대화형 슬롯필링을 수행하고, 케이크 실물 사진의 질감을 유지하며 핑거 마스킹 영역만 합성하는 Gemini 멀티모달 Inpainting 파이프라인을 제공합니다.

---

## 📑 목차 (Table of Contents)
1. [주요 기능 및 파이프라인](#1-주요-기능-및-파이프라인)
2. [기술 스택 및 아키텍처](#2-기술-스택-및-아키텍처)
3. [프로젝트 구조 및 모듈 명세](#3-프로젝트-구조-및-모듈-명세)
4. [핵심 엔지니어링 구현 상세](#4-핵심-엔지니어링-구현-상세)
5. [트러블슈팅 및 결함 해결 사례](#5-트러블슈팅-및-결함-해결-사례)
6. [환경 설정 및 실행 방법](#6-환경-설정-및-실행-방법)

---

## 1. 주요 기능 및 파이프라인

- **런타임 동적 스키마 슬롯필링 (Slot-Filling)**: 매장마다 상이한 옵션(호수, 시트, 크림, 레터링)을 In-Context Learning으로 주입받아 소비자의 자연어 발화에서 주문 필수 슬롯을 정형 JSON으로 추출.
- **실물 질감 보존형 Inpainting 파이프라인**: 사장님의 실제 제작 케이크 사진을 베이스로 상단 마스킹 영역만 국소 재합성하여 실제 제작 가능한 도안을 시각화.
- **비정형 출력 방어 3단계 Fallback 파서**: LLM의 마크다운 백틱이나 끝자리 괄호 중복 오염에도 500 크래시 없이 200 OK로 안전하게 수복하는 파싱 로직.
- **포트폴리오 사진 자동 태그 추출**: 케이크 사진 업로드 시 비전 모델을 통해 검색 태그 자동 추천.

---

## 2. 기술 스택 및 아키텍처

- **Python 3.10+ & FastAPI**: 메인 서버와 분리하여 AI 연산 부하를 격리하고, `async/await` 코루틴 기반으로 비동기 I/O 처리.
- **Pydantic v2**: 초고속 데이터 검증 및 타입 체킹 수행.
- **Google Gemini (gemini-3.5-flash & gemini-3.1-flash-image)**: 언어 이해 및 슬롯 추출에는 저지연 LLM을 사용하고, 이미지 합성에는 Gemini 3.1 Flash 멀티모달 Inpainting 모델 활용.

---

## 3. 프로젝트 구조 및 모듈 명세

```text
MakeAWish-AI/
├── main.py                             # FastAPI 앱 엔트리포인트 및 라우터 등록
├── core/                               # 설정 및 공통 로깅 (pydantic-settings)
├── services/                           # 핵심 AI 비즈니스 파이프라인
│   ├── slot_filler.py                  # Gemini 기반 동적 스키마 슬롯필링 엔진
│   ├── parser.py                       # 3단계 정규식 기반 Fallback JSON 파서
│   ├── inpainter.py                    # Gemini 3.1 Flash Image 국소 영역 인페인팅
│   └── vision_tagger.py                # 케이크 이미지 분석 및 자동 태그 생성기
├── schemas/                            # Pydantic v2 입출력 DTO 명세
├── tests/                              # pytest 단위 및 통합 테스트
├── client_test.py                      # 연동 검증용 테스트 스크립트
└── requirements.txt                    # 의존성 패키지 명세
```

---

## 4. 핵심 엔지니어링 구현 상세

### 4.1 런타임 동적 스키마 슬롯필링 (`main.py`)
백엔드로부터 수신한 매장별 JSON 스키마에서 순수 한글 라벨(`label`) 목록만 필터링하여 Gemini 3.5 Flash 모델의 System Instruction 제약 조건으로 런타임에 동적 주입합니다. 이를 통해 모델 재학습 없이도 매장별 커스텀 질문 항목을 대화에서 100% 자동 추출합니다.

```python
# main.py 발췌: 스키마 라벨 필터링 및 동적 프롬프트 주입
def extract_clean_labels(schema_json: dict) -> list[str]:
    labels = []
    if isinstance(schema_json, dict) and "properties" in schema_json:
        for key, val in schema_json["properties"].items():
            if isinstance(val, dict) and "label" in val:
                labels.append(val["label"])
    return labels

system_instruction = f"""
당신은 맞춤형 케이크 전문 베이커리의 주문 보조 AI입니다.
고객 발화에서 다음 주문 항목만 정확히 추출하여 JSON으로 응답하세요.
[유효 항목]: {extract_clean_labels(custom_schema)}
"""
```

### 4.2 3단계 Fallback JSON 파서 (`services/parser.py`)
LLM 응답에서 마크다운 코드 블록이나 중복 닫는 중괄호(`}}`)로 인한 `JSONDecodeError` 500 에러를 방지하기 위해 3단계 정규식 및 브래킷 밸런싱 파서를 구축했습니다.

```python
# services/parser.py 발췌: 3단계 방어형 파서
def safe_parse_ai_json(raw_text: str) -> dict:
    cleaned = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", raw_text.strip())
    # 1단계: 표준 파싱 시도
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 2단계: 최외각 중괄호 정규식 추출
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 3단계: 브래킷 밸런스 스캐너를 통한 닫는 괄호 보정
    open_count = 0
    valid_end = -1
    for i, char in enumerate(cleaned):
        if char == '{': open_count += 1
        elif char == '}':
            open_count -= 1
            if open_count == 0:
                valid_end = i + 1
                break
    if valid_end != -1:
        return json.loads(cleaned[:valid_end])
    raise ValueError("유효한 JSON 블록을 복구할 수 없습니다.")
```

---

## 5. 트러블슈팅 및 결함 해결 사례

| 문제 현상 | 원인 분석 | 해결 방법 |
| :--- | :--- | :--- |
| **JSON Schema 메타키 오인식** | `$schema`, `required` 같은 시스템 메타 키를 주문 옵션으로 잘못 추출 | 스키마 전처리 파이프라인을 구축하여 순수 옵션 필드만 정제 후 모델 주입 |
| **중복 괄호(`}\n}`) 500 크래시** | LLM이 불완전한 JSON을 반환하여 `JSONDecodeError` 발생 | 3단계 정규식 & 브래킷 카운팅 Fallback 파서를 적용하여 200 OK 복구 |
| **Pydantic v2 직렬화 예외** | Pydantic v2 모델 인스턴스를 FastAPI `JSONResponse`에 직접 전달하여 `TypeError` 발생 | `.model_dump()`를 명시적으로 호출하여 표준 dict로 변환 후 직렬화 |
| **필수값 누락 시 500 에러** | 광범위 try-except로 인해 클라이언트 입력 누락임에도 500 에러 반환 | Pydantic 유효성 검사 및 `HTTPException(status_code=400)` 명시적 분기 처리 |

---

## 6. 환경 설정 및 실행 방법

### 6.1 환경 변수 설정 (`.env`)

```env
GEMINI_API_KEY=your_google_gemini_api_key
PORT=8000
ENVIRONMENT=development
```

### 6.2 실행 명령어

```bash
# 가상환경 활성화 및 패키지 설치
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 서버 실행
uvicorn main:app --reload --port 8000

# 테스트 스크립트 실행
python client_test.py
```
