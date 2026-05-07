# 🌊 MakeAWish-AI 대화형 주문 플로우 및 상세 작업 가이드 (Graduation Project Edition)

본 문서는 프론트엔드, Spring 서버, AI 서버 간의 상호작용을 정의한 시퀀스 다이어그램 및 졸업 작품 완성을 위한 최종 기술 명세서입니다.

---

## 1. [v1] 초기 시퀀스 다이어그램 (Concept Model)

```mermaid
sequenceDiagram
    autonumber
    participant U as 사용자 (Frontend)
    participant S as Spring 서버 (Orchestrator)
    participant A as AI 서버 (Python/Gemini)
    participant DB as 데이터베이스 (PostgreSQL/S3)

    Note over U, S: [진입점 A: 탐색 채팅 (Search Chat)]
    U->>S: "엄마 생신에 어울리는 빨간 케이크 찾아줘"
    S->>A: 검색 태그 추출 요청 (extract_tags)
    A-->>S: { "tags": ["red", "birthday", "parent"] }
    S->>DB: 태그 기반 케이크 검색
    DB-->>S: 케이크 카드 리스트 응답

    Note over U, S: [진입점 B: 홈 화면 (Direct Selection)]
    U->>U: 홈 화면에서 케이크 카드 직접 선택

    Note over U, A: [2단계: 편집 또는 주문 선택 (Decision)]
    U->>U: "AI 편집" 버튼 클릭 시 ➡️ [공통 AI 에디터] 이동
    U->>U: "이대로 주문" 버튼 클릭 시 ➡️ [주문 채팅] 이동

    Note over U, A: [별도 흐름: 공통 AI 에디터 (Centralized Editor)]
    U->>U: 마스킹 및 프롬프트 입력
    U->>S: 편집 요청
    S->>A: /api/inpaint 호출
    A-->>S: 결과 이미지 반환
    S-->>U: 수정된 이미지 노출
    U->>U: "이 디자인으로 주문" 클릭 시 ➡️ [주문 채팅] 진입

    Note over U, A: [3단계: 슬롯 필링 주문 (Conversational Ordering)]
    S->>DB: 해당 가게의 주문서 양식(Schema) 로드
    S->>A: [양식 + 대화내역] 분석 및 다음 질문 생성
    A-->>S: { "next_question": "맛은 무엇으로 할까요?", "current_slots": {} }
    S-->>U: 챗봇 질문 전달
    U->>S: "초코맛이요"
    S->>A: 데이터 추출 및 다음 질문 생성
    A-->>S: { "extracted_slots": {"flavor": "초코"}, "next_question": "사이즈는요?" }
    S->>DB: 중간 저장 (Draft Order Update)
    S-->>U: 다음 질문 전달

    Note over U, A: [4단계: 주문 확정]
    A-->>S: { "status": "COMPLETED", "final_order": {...} }
    S-->>U: 주문 완료 안내
    S->>DB: 사장님 앱으로 주문 알림 전송
```

---

## 2. [v2] 통합 및 고도화된 시퀀스 다이어그램 (Implementation Model)

```mermaid
sequenceDiagram
    autonumber
    
    participant F as 사용자 (Frontend)
    participant B as 스프링부트 (Backend)
    participant A as AI (Gemini)
    participant DB as DB (S3/RDBMS)

    Note over F, B: [1단계: 탐색 및 추천]
    F->>B: "엄마 생신에 어울리는 빨간 케이크 찾아줘"
    B->>DB: 사용자 메시지 저장
    B->>A: /api/ai/chat 호출 (의도 분류 및 태그 추출)
    A-->>B: { "actionType": "PORTFOLIO_LIST", "data": {"tags": ["red", "birthday"]} }
    B->>DB: 태그 기반 포트폴리오 검색
    DB-->>B: [ { "id": 10, "url": "..." }, ... ]
    B-->>F: { "message": "추천 디자인입니다!", "actionType": "PORTFOLIO_LIST", "data": [...] }
    B->>DB: 답변 메시지 저장
    Note over F: [UI] 채팅 입력창 일시 비활성화 및 카드 선택 유도
%% 포트폴리오 사진 선택 및 에디터 진입
rect rgb(255, 240, 240)
Note over F, B: [2단계] 디자인 선택 및 편집
F->>F: 카드에서 '수정하기' 클릭 ➡️ [AI 에디터] 이동
F->>F: 마스킹 및 프롬프트 입력 ("하트 그려줘")
F->>B: 편집 요청 (Image, Mask, Prompt)
B->>A: /api/ai/inpaint 호출
A-->>B: { "actionType": "INPAINTING_RESULT", "result_image": "..." }
B->>DB: 편집된 이미지 S3 업로드 및 저장
B-->>F: { "message": "편집 완료!", "actionType": "INPAINTING_RESULT", "data": { "url": "..." } }
F->>F: "이 디자인으로 주문" 클릭 ➡️ [대화형 주문] 진입
end

    Note over F, B: [3단계: 대화형 주문 (Slot-Filling)]
    Note over F: [UI] 채팅창 복귀 및 주문 정보 수집 시작
    B->>DB: 매장별 주문 양식(Schema) 로드
    B->>A: /api/ai/chat 호출 (양식 + 이미지 정보 + 내역)
    A-->>B: { "actionType": "SHOW_SCHEMA", "message": "맛은 무엇으로 할까요?", "data": {...} }
    B->>DB: 답변 저장
    B-->>F: { "message": "맛은 무엇으로 할까요?", "actionType": "SHOW_SCHEMA", "data": { "options": ["초코", "바닐라"] } }
    
    F->>B: "초코맛이요"
    B->>DB: 사용자 메시지 저장
    B->>A: /api/ai/chat 호출 (슬롯 추출 및 다음 질문)
    A-->>B: { "actionType": "SHOW_SCHEMA", "extracted_slots": {"flavor": "초코"}, "message": "사이즈는요?" }
    B->>DB: 답변 저장
    B-->>F: { "message": "사이즈는요?", "actionType": "SHOW_SCHEMA", "data": { "options": ["1호", "2호"] } }

    F->>B: "1호로 할게요"
    B->>DB: 사용자 메시지 저장
    B->>A: /api/ai/chat 호출 (완료 확인 요청)
    A-->>B: { "actionType": "CONFIRM_SLOTS", "extracted_slots": {"flavor": "초코", "size": "1호"}, "status": "COMPLETED" }
    B-->>F: { "message": "초코맛, 1호 맞으신가요?", "actionType": "CONFIRM_SLOTS" }
    F->>B: "네, 맞아요"

    Note over F, B: [4단계: 주문 검토 및 금액 확정]
    B->>DB: 주문 내역 저장 및 사장님 앱으로 알림 전송
    Note over DB: [사장님] 주문서 확인 및 최종 금액 입력
    DB-->>B: 주문 수락 및 최종 금액 반환
    B-->>F: { "message": "사장님이 주문을 수락했습니다! 최종 금액은 45,000원입니다. 결제하시겠습니까?", "actionType": "ORDER_SUMMARY", "data": { "totalPrice": 45000 } }
    
    F->>B: "결제하기" (결제 프로세스 진행)
    B->>DB: 결제 완료 상태 업데이트
    B-->>F: { "message": "결제가 완료되었습니다! 예쁘게 제작해 드릴게요.", "actionType": "ORDER_COMPLETE", "data": { "orderId": 123 } }
```

---

## 3. v1 vs v2 차이점 및 변화 분석

### 🌟 잘 된 점 (Improvements)

- **통합 API 구조 반영**: 모든 텍스트 기반 인터랙션을 `/api/ai/chat` 하나로 처리하여 관리가 용이해짐.
- **데이터 응답 구조화**: `actionType`과 `data` 필드를 도입하여 프론트엔드가 상황에 맞는 UI(버튼, 카드 등)를 동적으로 렌더링할 수 있게 됨.
- **비즈니스 로직의 명확화**: 금액 계산과 같은 핵심 로직을 AI가 아닌 백엔드(Spring)가 담당하게 하여 데이터의 정확성과 신뢰성을 확보함.
- **데이터 영속성 강화**: 매 대화 단계마다 DB 저장을 명시하여 장애 복구 및 대화 맥락 유지 능력을 향상시킴.

### 💡 향후 구현 시 보완점 (Technical Deep Dive)

- **DB 저장소의 이원화**: RDBMS(텍스트 데이터)와 S3(이미지 파일)를 물리적으로 분리하여 저장 및 관리.
- **이미지 영속화 처리**: AI 서버가 생성한 임시 이미지를 서비스 전용 S3 버킷으로 재업로드하여 유효기간 문제 방지.
- **예외 상황 대응(Fallback)**: 사용자의 이탈 답변이나 AI의 인식 오류 시 백엔드에서 선택지를 다시 제시하는 등의 방어적 로직 구현.

---

## 4. 서버별 핵심 역할

### 🛠 Spring 서버 (The Manager)

- **진입점 및 오케스트레이션**: 탐색 채팅, 홈 화면 유입 관리 및 전체 주문 상태 머신 제어.
- **상태 및 데이터 관리**: 사용자가 선택한 케이크 정보 매칭, 가게별 주문서 스키마 보관, AI 추출 데이터의 DB 영속화.
- **파일 서비스**: 생성된 시안을 S3에 업로드하고 URL을 관리.

### 🤖 AI 서버 (The Brain)

- **통합 텍스트 분석**: `/api/ai/chat`을 통한 태그 추출, 슬롯 필링, 의도 분류.
- **이미지 생성 (Inpainting)**: 에디터 페이지에서 이미지 수정 및 결과 반환.

### 📱 프론트엔드 (The Interface)

- **동적 UI 컴포넌트**: `actionType`에 따른 AI 에디터, 주문 채팅창, 결과 카드 등의 유기적 배치.
- **상태 관리**: 채팅 일시 정지 및 카드 선택 유도 등 사용자 인터랙션 관리.

---
*최종 업데이트: 2026-05-07*
