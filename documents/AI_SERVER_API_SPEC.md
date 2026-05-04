# 🤖 MakeAWish AI Server API Specification

본 문서는 AI 서버(Python/FastAPI)와 백엔드 서버(Spring Boot) 간의 통신을 위한 API 명세서입니다.

---

## 1. 태그 추출 (Tag Extraction)

사용자의 자연어 검색 쿼리에서 데이터베이스 검색에 필요한 핵심 키워드를 추출합니다.

- **Endpoint**: `POST /api/ai/tags`
- **Description**: 사용자의 의도(색상, 상황, 대상, 스타일 등)를 분석하여 태그 리스트를 반환합니다.

### Request Body

```json
{
  "query": "엄마 생신에 어울리는 빨간 케이크 찾아줘"
}
```

### Response Body

```json
{
  "tags": ["red", "birthday", "mother"]
}
```

---

## 2. 이미지 인페인팅 (Image Inpainting)

원본 이미지의 특정 영역을 마스킹하고, 프롬프트에 따라 해당 영역을 수정합니다.

- **Endpoint**: `POST /api/ai/inpaint`
- **Description**: 원본 이미지, 마스크 이미지, 프롬프트를 입력받아 수정된 이미지를 생성합니다.

### Request Body

```json
{
  "image_b64": "data:image/png;base64,...",
  "mask_b64": "data:image/png;base64,...",
  "prompt": "중앙에 'Happy Birthday' 문구를 필기체로 적어줘",
  "reference_image_b64": "data:image/png;base64,..." (선택 사항)
}
```

### Response Body

```json
{
  "result_image": "data:image/png;base64,..."
}
```

> **Note**: 백엔드(Spring)는 이 결과를 받아 S3에 업로드한 후 프론트엔드에 URL을 전달합니다.

---

## 3. 대화형 주문 슬롯 필링 (Order Slot Filling)

사용자와의 대화 내역을 분석하여 주문서 항목을 채우고, 부족한 정보에 대한 다음 질문을 생성합니다.

- **Endpoint**: `POST /api/ai/order-filling`
- **Description**: 주문서 스키마와 대화 내역을 바탕으로 정보를 추출하고 상태를 관리합니다.

### Request Body

```json
{
  "schema_json": {
    "flavor": "string (초코, 바닐라, 딸기 중 선택)",
    "size": "string (1호, 2호, 3호 중 선택)",
    "pickup_date": "string (YYYY-MM-DD)",
    "message": "string (케이크 위 문구)"
  },
  "messages": [
    { "role": "user", "content": "케이크 주문하고 싶어요." },
    { "role": "assistant", "content": "안녕하세요! 어떤 맛으로 준비해드릴까요?" }
  ],
  "current_message": "초코맛으로 해주세요."
}
```

### Response Body

```json
{
  "extracted_slots": {
    "flavor": "초코"
  },
  "next_question": "사이즈는 몇 호로 제작해드릴까요?",
  "status": "IN_PROGRESS"
}
```

#### Status Enum

- `IN_PROGRESS`: 아직 채워지지 않은 필수 항목이 있어 추가 질문이 필요한 상태
- `COMPLETED`: 모든 필수 항목이 수집되어 주문 확인 단계로 넘어갈 수 있는 상태

---

## 공통 사항

- **Content-Type**: `application/json`
- **Error Response**:

  ```json
  {
    "detail": "에러 메시지 내용"
  }
  ```

- **Base64 Format**: 이미지는 `data:image/png;base64,...` 형식을 표준으로 사용합니다.
