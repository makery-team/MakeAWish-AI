# 🎂 MakeAWish-AI MVP 개발 보고서

## 1. 프로젝트 개요

* **목표**: 원본 케이크 이미지와 자연어를 결합한 인페인팅 기능 및 대화형 주문 자동화 시스템 구축.
* **핵심 가치**: 수작업 화풍 보존 기술과 AI 점원을 통한 끊김 없는(Seamless) 커스텀 케이크 주문 경험 제공.

## 2. 기술 스택 (System Architecture)

### 🧩 3-Tier 분리 아키텍처

* **Frontend**: React Native (TypeScript) - 멀티 엔트리 홈 화면 및 공통 AI 캔버스 에디터.
* **Backend (Orchestrator)**: Spring Boot (Java) - 비즈니스 로직, 데이터베이스(JPA), AI 서비스 연동.
* **AI Server (Brain)**: FastAPI (Python) - Gemini 기반 이미지 생성 및 자연어 분석.

### 🛠 파트별 상세 스택

* **AI Engine**: Google Gemini 3.1 Flash Lite (NLU) & 3.1 Flash Image (Inpainting) (2026 Preview Edition)
* **API Framework**: FastAPI, Spring Boot
* **Database**: PostgreSQL (JSONB 활용), AWS S3 (이미지 저장)
* **Monitoring**: LangSmith (AI 추적)

## 3. 프로젝트 배경 및 히스토리 (The Journey)

| 단계 | 시도 내용 | 결과 및 한계 (Pain Point) |
| :--- | :--- | :--- |
| **기존** | SD 1.5 + ControlNet | 화풍 보존은 성공했으나, **이미지 퀄리티 저하** 발생. |
| **1차 수정** | 로컬 GPU(RTX 4060) 기반 생성 | 장당 **6~7분 소요**, 실서비스 불가능한 속도. |
| **2차 수정** | **상용 API (Gemini) 도입** | **속도(3~5초), 퀄리티, 비용 효율성 모두 확보.** |
| **현재** | **통합 API 및 대화형 로직** | 파편화된 API를 `/chat`으로 통합하고 **대화형 커머스**로 확장. |

## 4. 핵심 기능 (Key Features)

### 🔍 통합 텍스트 대화 API (`/api/ai/chat`)

* 모든 텍스트 기반 인터랙션을 하나의 엔드포인트에서 처리하며, AI가 의도를 분석하여 `actionType`을 결정합니다.
* **PORTFOLIO_LIST**: 검색 태그 추출 및 디자인 추천.
* **SHOW_SCHEMA / CONFIRM_SLOTS**: 주문서 양식(Schema) 기반 슬롯 필링.
* **SIMPLE_CHAT**: 일반 안내 및 안내.
* **ORDER_SUMMARY**: 최종 주문 검토 (사장님 확인 대기).

### 🎨 공통 AI 캔버스 에디터 (`/api/ai/inpaint`)

* 브러시 마스킹과 자연어 프롬프트를 결합한 정밀 수정 지원.
* 기존 케이크의 질감과 화풍을 99% 유지하며 수정 부위만 자연스럽게 합성.

## 5. 실행 및 테스트 가이드

### AI 서버 설정 및 실행 (FastAPI)

1. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```

2. **환경 변수 설정**:
   * `.env.example` 파일을 복사하여 `.env` 파일을 생성하고 `GEMINI_API_KEY`를 입력합니다.

3. **서버 실행**:
   ```bash
   uvicorn main:app --reload
   ```

### 🧪 클라이언트 테스트 가이드 (팀원용)

서버가 실행 중인 상태에서 `client_test.py`를 사용하여 전체 기능을 검증할 수 있습니다.

1. **테스트 실행**:
   ```bash
   python client_test.py
   ```

2. **테스트 항목**:
   * **채팅 통합 테스트**: 인사, 검색, 에디터 진입 의사, 주문 슬롯 필링 등의 시나리오 자동 검증.
   * **인페인팅 테스트**: `img/original.png`를 수정하여 **`server_result.png`** 결과물 생성.

3. **결과 확인**:
   * 터미널의 `✅ 응답 성공` 로그와 `server_result.png` 이미지 파일을 확인하세요.

### 상세 가이드 문서

* **API 명세**: [AI_SERVER_API_SPEC.md](./documents/AI_SERVER_API_SPEC.md)
* **시퀀스 다이어그램**: [CONVERSATIONAL_ORDER_FLOW.md](./documents/CONVERSATIONAL_ORDER_FLOW.md)

---
*최종 업데이트: 2026-05-07*
