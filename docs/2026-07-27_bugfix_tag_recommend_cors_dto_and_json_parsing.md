# [Issue #4 Fix] AI 태그 추천 API CORS, Spring Boot Java DTO 호환 및 JSON 파싱 강건성 개선

## 1. 문제 배경 (Background & Cause)
백엔드(Spring Boot Java) 서버 및 프론트엔드와 AI 포트폴리오 태그 추천 API(`/api/ai/portfolios/tags/recommend`)를 연동하는 과정에서 총 5가지 유형의 에러 및 연동 불일치 문제가 확인되었습니다.

1. **`405 Method Not Allowed` 에러**:
   - 프론트엔드에서 API 호출 시 브라우저가 사전 검사(Preflight)로 보내는 `OPTIONS` 요청에 대응하는 CORS 미들웨어가 누락되어 호출이 차단됨.
2. **`404 Not Found` 에러**:
   - 백엔드(Spring Boot) 배포 서버(`43.202.27.154`)에서 AI 서버 호출 시 `/api/ai/generate-tags` 엔드포인트를 호출하여 경로가 불일치함.
3. **`400 Bad Request` 에러**:
   - 요청 바디 필드명이 카멜케이스(`imageUrl`, `imageB64`, `prompt` 등)로 오거나 이미지 URL 다운로드 중 예외 발생 시 검증 예외가 발생함.
4. **`500 Internal Server Error (JSONDecodeError)` 에러**:
   - AI(Gemini) 시스템 프롬프트의 JSON 예시가 싱글 쿼트(`'`)로 작성되어, 모델 응답 끝에 불법적인 트레일링 콤마(예: `["태그1", "태그2", ]`)가 발생함. 이로 인해 파이썬 `json.loads()`가 `line 9 column 4` 문법 오류를 발생시키며 500 에러로 크래시됨.
5. **백엔드 DTO 매핑 시 `None (null)` 반환 문제**:
   - 통신은 `200 OK`로 성공하였으나, Python 서버가 스네이크케이스(`recommended_tags`) 키만 응답함.
   - Java Spring Boot의 Jackson JSON 파서가 카멜케이스 변수명(`recommendedTags` 또는 `tags`)을 매핑하지 못해 DTO 속성 값이 `null`로 할당됨.

---

## 2. 해결 방안 및 적용된 로직 (Applied Solution & Logic)

### 1) CORS 미들웨어 적용 (`405 Method Not Allowed` 방지)
- FastAPI 앱 상단에 `CORSMiddleware` 전역 설정을 추가하여 모든 오리진(`*`), 메서드, 헤더에 대한 교차 출처 통신 및 `OPTIONS` 요청을 허용했습니다.

### 2) 엔드포인트 별칭(Alias) 라우트 지원 (`404 Not Found` 방지)
- 백엔드 코드 수정 없이도 동작하도록 기존 함수에 `@app.post("/api/ai/generate-tags")` 데코레이터를 추가 등록하여 두 주소 모두 지원합니다.

### 3) 요청 DTO 필드 호환 및 예외 강화 (`400 Bad Request` 방지)
- `TagRecommendationRequest` 모델에 카멜케이스(`imageUrl`, `imageB64`)와 텍스트 단독 속성(`text`, `prompt`)을 선택 속성으로 추가했습니다.
- 이미지 URL 다운로드 중 예외가 발생하더라도 설명문 텍스트가 존재하면 서버 예외 대신 텍스트 기반 태그 추출로 자동 대체되도록 예외 처리를 보강했습니다.

### 4) 엄격한 JSON 프롬프트 및 파싱 폴백 (`500 Internal Server Error` 방지)
- 시스템 프롬프트 예시를 표준 더블 쿼트(`"`) JSON 양식으로 교체하고, 마크다운 코드 블록 및 끝 쉼표를 제거하는 정규식 보정 로직(`re.sub(r",\s*([\]}])", r"\1", raw_text)`)을 적용했습니다.
- 만에 하나 JSON 파싱이 실패하더라도 500 에러가 아닌 기본 추천 태그(`["커스텀케이크", "주문제작", "레터링케이크"]`)를 반환하는 `try-except` 폴백을 구성했습니다.

### 5) Java DTO 4중 속성 동시 응답 (`None / null` 바인딩 원천 차단)
- `TagRecommendationResponse` 모델에 4가지 별칭 필드를 선언하고, 동일한 태그 목록을 매칭하여 반환합니다.
- 백엔드 DTO 필드명에 구애받지 않고 **`recommended_tags`**, **`recommendedTags`**, **`tags`**, **`tagList`** 4개 키가 모두 포함되어 100% 매핑에 성공합니다.

---

## 3. 응답 명세 및 Postman 테스트 가이드

### 1) 요청 URL 및 Headers
- **HTTP Method**: `POST`
- **URL**:
  - `https://makeawish-ai.onrender.com/api/ai/generate-tags` (백엔드 호환)
  - `https://makeawish-ai.onrender.com/api/ai/portfolios/tags/recommend` (표준)
- **Headers**:
  - `Content-Type: application/json`

### 2) Request Body 예시
```json
{
  "imageUrl": "https://raw.githubusercontent.com/makery-team/MakeAWish-AI/main/img/original.png",
  "prompt": "파스텔톤 분홍색 딸기 생크림 케이크, 생일 축하 문구 포함"
}
```

### 3) Response JSON 구조
```json
{
  "recommended_tags": [
    "생일축하",
    "파스텔톤",
    "딸기케이크",
    "생크림",
    "레터링케이크"
  ],
  "recommendedTags": [
    "생일축하",
    "파스텔톤",
    "딸기케이크",
    "생크림",
    "레터링케이크"
  ],
  "tags": [
    "생일축하",
    "파스텔톤",
    "딸기케이크",
    "생크림",
    "레터링케이크"
  ],
  "tagList": [
    "생일축하",
    "파스텔톤",
    "딸기케이크",
    "생크림",
    "레터링케이크"
  ]
}
```
