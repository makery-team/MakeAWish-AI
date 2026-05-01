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

* **AI Engine**: Google Gemini 2.0 Flash (NLU) & 3.1 Flash Image (Inpainting)
* **API Framework**: FastAPI, Spring Boot
* **Database**: PostgreSQL (JSONB 활용), AWS S3 (이미지 저장)
* **Monitoring**: LangSmith (AI 추적)

## 3. 프로젝트 배경 및 히스토리 (The Journey)

| 단계 | 시도 내용 | 결과 및 한계 (Pain Point) |
| :--- | :--- | :--- |
| **기존** | SD 1.5 + ControlNet | 화풍 보존은 성공했으나, **이미지 퀄리티 저하** 발생. |
| **1차 수정** | 로컬 GPU(RTX 4060) 기반 생성 | 장당 **6~7분 소요**, 실서비스 불가능한 속도. |
| **2차 수정** | **상용 API (Gemini) 도입** | **속도(3~5초), 퀄리티, 비용 효율성 모두 확보.** |
| **현재** | **3-Tier 분리 및 대화형 로직** | 단순 이미지 생성을 넘어 **대화형 커머스(Conversational Commerce)**로 확장. |

## 4. 핵심 기능 (Key Features)

### 🔍 대화형 케이크 탐색 (AI Discovery)

- 사용자의 자연어 입력("엄마 생신에 어울리는 빨간 케이크")에서 핵심 태그를 추출하여 DB 검색 연동.
* **Endpoint**: `POST /api/ai/tags`

### 🎨 공통 AI 캔버스 에디터 (Centralized Editor)

- 홈 화면, 채팅 리스트 등 어디서든 진입 가능한 통합 이미지 수정 인터페이스.
* 브러시 마스킹과 자연어 프롬프트를 결합한 정밀 수정 지원.
* **Endpoint**: `POST /api/inpaint`

### 💬 슬롯 필링 기반 주문 자동화 (AI Slot-Filling)

- AI 점원이 가게별로 상이한 주문서 양식(Schema)을 파악하여 부족한 정보를 대화로 수집.
* 텍스트 대화만으로 최종 주문 JSON 데이터 완성.
* **Endpoint**: `POST /api/ai/order-filling`

## 5. 실행 및 테스트 가이드

### AI 서버 실행 (FastAPI)

```bash
uvicorn main:app --reload
```

### 아키텍처 및 상세 작업 가이드

- 상세 시퀀스 다이어그램 및 파트별 상세 Task는 [CONVERSATIONAL_ORDER_FLOW.md](./documents/CONVERSATIONAL_ORDER_FLOW.md) 참조.

## 6. 최종 성능 지표

* **생성 속도**: 로컬 7분 ➡️ **API 기반 약 3~5초 (약 100배 개선)**
* **이미지 품질**: 원본 케이크의 파스텔톤 및 크림 질감 99% 일치.
* **확장성**: 3-Tier 분리를 통해 서버별 독립적 확장(Scalability) 가능.
* **자동화**: AI 점원을 통한 주문 누락 방지 및 주문서 작성 시간 단축.

---
*최종 업데이트: 2026-05-01*
