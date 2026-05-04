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

    rect rgb(240, 240, 240)
    Note over U, S: [진입점 A: 탐색 채팅 (Search Chat)]
    U->>S: "엄마 생신에 어울리는 빨간 케이크 찾아줘"
    S->>A: 검색 태그 추출 요청 (extract_tags)
    A-->>S: { "tags": ["red", "birthday", "parent"] }
    S->>DB: 태그 기반 케이크 검색
    DB-->>S: 케이크 카드 리스트 응답
    end

    rect rgb(255, 240, 240)
    Note over U, S: [진입점 B: 홈 화면 (Direct Selection)]
    U->>U: 홈 화면에서 케이크 카드 직접 선택
    end

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

## 2. [v2] 고도화된 시퀀스 다이어그램 (Implementation Model)

```mermaid
sequenceDiagram
    autonumber
    
    actor User as 사용자 (Frontend)
    participant Backend as 스프링부트 (Backend)
    participant AI as AI (Gemini)
    participant DB as DB (RDBMS/S3)

    %% 1단계: 탐색 및 추천
    rect rgb(245, 245, 245)
    Note over User, DB: [1단계] 탐색 및 추천
    User->>Backend: "엄마 생신에 어울리는 빨간 케이크 찾아줘"
    Backend->>DB: 사용자 메시지 저장
    Backend->>AI: 태그 추출 요청
    AI-->>Backend: { "tags": ["red", "birthday"] }
    Backend->>DB: 태그 기반 포트폴리오 검색
    DB-->>Backend: [{ "id": 10, "url": "..." }, ...]
    Backend-->>User: { "message": "추천 디자인입니다.", "actionType": "PORTFOLIO_LIST", "data": [...] }
    Backend->>DB: 답변 메시지 저장
    end

    %% 포트폴리오 사진 선택
    rect rgb(255, 240, 240)
    Note over User, DB: [포트폴리오 사진 선택]
    User->>User: 홈 화면에서 케이크 선택
    end

    %% 2단계: 서비스 선택
    rect rgb(245, 245, 245)
    Note over User, DB: [2단계] 서비스 선택
    User->>User: 'AI 변환' 또는 '이대로 주문' 선택
    end

    %% 사진 업로드 및 편집
    rect rgb(245, 245, 245)
    Note over User, DB: [사진 편집 & 데이터]
    User->>User: 마스킹 및 프롬프트 입력
    User->>Backend: 편집 요청 (image, mask, prompt)
    Backend->>AI: 인페인팅 요청
    AI-->>Backend: { "resultUrl": "url..." }
    Backend->>DB: 인페인팅된 이미지 저장 (S3 업로드 및 영속화)
    Backend-->>User: { "message": "편집 완료!", "actionType": "INPAINTING_RESULT", "data": {"url": "..."} }
    User->>User: 이 디자인으로 주문 클릭 (대화형 주문 진입)
    end

    %% 3단계: 대화형 주문
    rect rgb(245, 245, 245)
    Note over User, DB: [3단계] 대화형 주문
    Backend->>DB: 상황/문맥 정보 로드
    Backend->>AI: (형식: 문장, 이미지 정보 + 대화내역) 전송
    AI->>AI: 분석 및 정보 추출
    AI-->>Backend: { "next_question": "어떤 품목으로 할까요?", "slots": {...} }
    Backend->>DB: 답변 저장
    Backend-->>User: { "message": "어떤 품목으로 할까요?", "actionType": "SHOW_SCHEMA", "data": { "options": ["스콘", "케이크"] } }
    User->>Backend: "스콘이요!"
    Backend->>DB: 사용자 메시지 저장
    Backend->>AI: 메시지 전달 및 슬롯 추출
    AI->>AI: 다음 질문 찾음
    AI-->>Backend: { "extracted_slots": {"item": "스콘"}, "next_question": "사이즈는요?" }
    Backend->>DB: 답변 저장
    Backend-->>User: { "message": "사이즈는요?", "actionType": "SHOW_SCHEMA", "data": { "options": ["1호", "2호"] } }
    User->>Backend: "1호로 할게요!"
    Backend->>DB: 사용자 메시지 저장
    Backend->>AI: 완료 확인 요청
    AI->>AI: 모든 슬롯 수집 완료
    AI-->>Backend: { "extracted_slots": {"item": "스콘", "size": "1호"}, "status": "CONFIRM_SLOTS" }
    Backend-->>User: { "message": "주문할 1호 스콘 맞으신가요?", "actionType": "CONFIRM_SLOTS" }
    User->>Backend: "네, 맞아요"
    end

    %% 4단계: 금액 계산 및 저장
    rect rgb(245, 245, 245)
    Note over User, DB: [4단계] 금액 계산 & 저장
    Backend->>DB: 가격 정보 조회
    DB-->>Backend: (가격 데이터)
    Backend->>Backend: 최종 금액 계산 (50,000 + 5,000 - 10,000 = 45,000)
    Backend->>DB: 답변 저장
    Backend-->>User: { "message": "최종 45,000원입니다. 주문할까요?", "actionType": "ORDER_SUMMARY", "data": { "totalPrice": 45000 } }
    User->>Backend: "주문 확정 및 결제"
    Backend->>DB: 사용자 메시지 저장
    Backend->>DB: 최종 주문 저장 및 알림 처리
    Backend->>DB: 답변 저장
    Backend-->>User: { "message": "주문 완료!", "actionType": "ORDER_COMPLETE", "data": { "orderId": 123 } }
    end
```

---

## 3. v1 vs v2 차이점 및 변화 분석

### 🌟 잘 된 점 (Improvements)

- **데이터 응답 구조화**: `actionType`과 `data` 필드를 도입하여 프론트엔드가 상황에 맞는 UI(버튼, 카드 등)를 동적으로 렌더링할 수 있게 됨.
- **비즈니스 로직의 명확화**: 금액 계산과 같은 핵심 로직을 AI가 아닌 백엔드(Spring)가 담당하게 하여 데이터의 정확성과 신뢰성을 확보함.
- **데이터 영속성 강화**: 매 대화 단계마다 DB 저장을 명시하여 장애 복구 및 대화 맥락 유지 능력을 향상시킴.

### 💡 향후 구현 시 보완점 (Technical Deep Dive)

- **DB 저장소의 이원화**: RDBMS(텍스트 데이터)와 S3(이미지 파일)를 물리적으로 분리하여 저장 및 관리.
- **이미지 영속화 처리**: AI 서버가 생성한 임시 URL 이미지를 서비스 전용 S3 버킷으로 재업로드하여 유효기간 만료 문제 방지.
- **예외 상황 대응(Fallback)**: 사용자의 이탈 답변이나 AI의 인식 오류 시 백엔드에서 선택지를 다시 제시하는 등의 방어적 로직 구현.
- **컨텍스트 연결**: AI 에디터에서의 작업 결과(이미지 ID 등)를 주문 세션으로 자연스럽게 전달하는 구조 설계.

---

## 4. 서버별 핵심 역할

### 🛠 Spring 서버 (The Manager)

- **진입점 및 오케스트레이션**: 탐색 채팅, 홈 화면 유입 관리 및 전체 주문 상태 머신 제어.
- **상태 및 데이터 관리**: 사용자가 선택한 케이크 정보 매칭, 가게별 주문서 스키마 보관, AI 추출 데이터의 DB 영속화.
- **파일 서비스**: 생성된 시안을 S3에 업로드하고 URL을 관리.

### 🤖 AI 서버 (The Brain)

- **태그 추출 (Tagging)**: 검색 키워드 및 사용자 의도 추출.
- **슬롯 필링 (Slot-filling)**: 대화형 인터페이스를 위한 데이터 추출 및 다음 질문 생성.
- **이미지 생성 (Inpainting)**: 에디터 페이지에서 이미지 수정 및 결과 반환.

### 📱 프론트엔드 (The Interface)

- **멀티 엔트리 홈 화면**: 탐색 채팅과 카드 리스트 그리드 뷰의 유기적 배치.
- **동적 UI 컴포넌트**: `actionType`에 따른 AI 에디터, 주문 채팅창, 결과 카드 등의 전역적 재활용.

---

## 5. 파트별 상세 작업 리스트 (Detailed Task List)

### 🤖 AI 서버 파트 (Python/FastAPI)

1. **검색 엔진 고도화 (`/api/ai/tags`)**
   - [x] 유저 문장에서 `색상`, `상황`, `대상`, `스타일` 키워드를 분리하는 전용 프롬프트 작성.
   - [x] 결과값을 항상 `list` 포맷의 JSON으로 반환하도록 제약 설정.
2. **주문 슬롯 필링 엔진 (`/api/ai/order-filling`)**
   - [x] **Context 관리**: Spring에서 넘어온 대화 내역을 결합하여 문맥을 파악.
   - [x] **필수 항목 체크**: 주문서 JSON(Schema)과 비교하여 비어있는 Key값을 탐색.
   - [x] **질문 생성**: 자연스럽고 친절한 점원 페르소나 적용.
3. **인페인팅 서버 최적화 (`/api/inpaint`)**
   - [ ] Gemini 3.1 Flash의 인페인팅 파라미터 튜닝 및 결과 이미지 품질 고도화.

### 🛠 Spring 서버 파트 (Java/Spring Boot)

1. **데이터베이스(JPA/RDBMS) 설계**
   - [ ] `CakePortfolio`: 이미지 URL, 태그 리스트 저장.
   - [ ] `OrderSchema`: 가게별 커스텀 주문서 양식(JSON) 저장.
   - [ ] `ChatMessage`: 대화 내역 및 주문 진행 상태 저장.
2. **AI 서버 연동 모듈 (WebClient)**
   - [ ] FastAPI 서버와의 비동기 통신 및 예외 처리 로직 구현.
3. **오케스트레이션 로직**
   - [ ] `actionType` 기반의 응답 생성 및 주문 슬롯 실시간 업데이트 로직.
4. **이미지 저장소(S3) 연동**
   - [ ] 외부 이미지를 S3에 업로드하고 영속 URL을 관리하는 파일 서비스.

### 📱 프론트엔드 파트 (TypeScript/React Native)

1. **대화형 UI 개발**
   - [ ] 채팅창 UI 및 AI 추천 결과 가로 스크롤 카드 뷰.
2. **AI 캔버스 에디터 (Centralized Editor)**
   - [ ] 이미지 위 마스킹(그리기) 및 영역 추출 로직 구현.
3. **상태 관리 및 연동**
   - [ ] 주문서 작성 현황 관리 및 Spring 서버 API 연동.

---

## 6. 데이터 흐름 표준 규격 (API Interface)

### A. 검색 태그 추출 (Spring ➡️ AI)

- **Request**: `{ "query": "..." }`
- **Response**: `{ "tags": ["tag1", "tag2"] }`

### B. 슬롯 필링 질문 (Spring ➡️ AI)

- **Request**: `{ "schema_json": {...}, "messages": [...], "current_message": "..." }`
- **Response**: `{ "extracted_slots": {...}, "next_question": "...", "status": "..." }`

### C. 프론트엔드 응답 규격 (Spring ➡️ Frontend)

```json
{
  "message": "질문 내용",
  "actionType": "PORTFOLIO_LIST | SHOW_SCHEMA | CONFIRM_SLOTS | ORDER_SUMMARY | ...",
  "data": { ... }
}
```

---
*최종 업데이트: 2026-05-02*
