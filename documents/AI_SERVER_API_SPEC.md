# 🤖 MakeAWish AI Server API Specification

본 문서는 AI 서버(Python/FastAPI)와 백엔드 서버(Spring Boot) 간의 통신을 위한 API 명세서입니다.

---

## 1. 통합 텍스트 대화 (Consolidated Chat)

사용자의 모든 텍스트 입력을 분석하여 의도를 분류하고, 정의된 `actionType`에 따라 응답을 반환합니다.

- **Endpoint**: `POST /api/ai/chat`
- **Description**: 사용자의 쿼리와 대화 내역을 바탕으로 `actionType`을 결정하고 데이터를 처리합니다.

### Request Body

```json
{
  "messages": [
    { "role": "user", "content": "안녕하세요" },
    { "role": "assistant", "content": "안녕하세요! 어떤 케이크를 찾으시나요?" }
  ],
  "current_message": "엄마 생신에 어울리는 빨간 케이크 찾아줘",
  "schema_json": { ... } // (선택) 주문 슬롯 필링이 필요한 경우 전달
}
```

### Response Body Structure

```json
{
  "actionType": "...",
  "message": "사용자에게 전달할 메시지",
  "data": { ... } // actionType에 따라 달라짐
}
```

### Action Types & Data Format

| actionType | 설명 | 프론트엔드 대응 가이드 | data 구조 |
| :--- | :--- | :--- | :--- |
| `SIMPLE_CHAT` | 일반적인 대화 및 안내 | 채팅 메시지 노출 | `null` |
| `PORTFOLIO_LIST` | 케이크 디자인 추천 | 메시지 노출 후 **채팅창 입력 제한**, 하단에 추천 카드 및 [결정/수정] 버튼 노출 | `{ "tags": ["red", "birthday"] }` |
| `EDIT_IMAGE` | 유저가 대화로 수정 의사를 밝힐 때 | (Fallback 용도) 즉시 에디터 페이지로 화면 전환 처리 | `null` |
| `SHOW_SCHEMA` | 주문 정보 수집 중 | 질문 메시지 노출 및 관련 입력 폼(날짜 선택기, 옵션 버튼 등) 활성화 | `{ "extracted_slots": { ... }, "status": "IN_PROGRESS" }` |
| `CONFIRM_SLOTS` | 주문 정보 수집 완료 | 수집된 정보 요약 노출 및 [최종 확인] 버튼 활성화 | `{ "extracted_slots": { ... }, "status": "COMPLETED" }` |
| `ORDER_SUMMARY` | 최종 주문 요약 | 결제 금액 및 주문 정보 최종 확인 카드 노출 | `{ "final_slots": { ... } }` |

---

## 2. 이미지 인페인팅 (Image Inpainting)

원본 이미지의 특정 영역을 마스킹하고, 프롬프트에 따라 해당 영역을 수정합니다.

- **Endpoint**: `POST /api/ai/inpaint`

### Response Body

```json
{
  "actionType": "INPAINTING_RESULT",
  "result_image": "data:image/png;base64,..."
}
```

---

## 공통 사항

- **Content-Type**: `application/json`
- **Base64 Format**: 이미지는 `data:image/png;base64,...` 형식을 표준으로 사용합니다.
