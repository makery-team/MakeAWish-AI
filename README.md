# 🎂 MakeAWish-AI MVP 개발 보고서

## 1. 프로젝트 개요
* **목표**: 원본 케이크 이미지, 마스크 이미지, 자연어 프롬프트를 결합하여 케이크의 특정 부분을 자연스럽게 수정하는 인페인팅 기능 구현.
* **핵심 가치**: 수작업 화풍 및 레터링 질감을 그대로 유지하는 고퀄리티 합성물 생성.

## 2. 기술 스택 (Final Stack)
* **Backend Framework**: FastAPI (Uvicorn)
* **AI Engine**: Google Gemini 3.1 Flash Image (코드명: 나노 바나나 2)
* **Client Library**: `google-genai` (신형 SDK 1.0+)
* **Monitoring & Tracing**: LangSmith (`@traceable`)
* **Environment Management**: `python-dotenv` (.env)

## 3. 프로젝트 배경 및 히스토리 (The Journey)


| 단계 | 시도 내용 | 결과 및 한계 (Pain Point) |
| :--- | :--- | :--- |
| **기존** | SD 1.5 + ControlNet + IP-Adapter | 화풍 보존은 성공했으나, **이미지 퀄리티 저하 및 깨짐 현상** 발생. |
| **1차 수정** | LLM(프롬프트 생성) + LangSmith 모니터링 | 자연어 이해도는 높였으나, **프롬프트와 ControlNet의 충돌**로 화풍 붕괴. |
| **2차 수정** | SDXL 모델 교체 + Diffusers 라이브러리 | 로컬(RTX 4060) 구동 시 **장당 6~7분 소요**, 상용화 불가능한 속도와 처참한 결과물. |
| **3차 수정** | **상용 API (Gemini 3.1 Flash) 도입** | 갤럭시 AI 등 대기업 사례 분석 후 결단. **속도, 퀄리티, 비용 효율성 모두 확보.** |


### SDK 마이그레이션 (구형 → 신형)
* **이슈**: 구형 `google-generativeai` 사용 시 `404 Not Found` 또는 모델 경로 오류 발생.
* **해결**: 최신 문법을 지원하는 신형 SDK `google-genai`로 마이그레이션 완료. (`client = genai.Client()` 구조 도입)

### 쿼터(Quota) 및 과금 체계 확보
* **이슈**: 무료 티어 사용 시 `429 RESOURCE_EXHAUSTED` (Limit: 0) 에러로 사용 불가.
* **해결**: 결제 수단 등록을 통해 **Tier 1(Paid)** 등급으로 업그레이드. Google Cloud 300달러(약 42만 원) 무료 크레딧을 방패막이로 확보하여 과금 부담 없이 고성능 모델 권한 획득.


### 핵심 프롬프트 엔지니어링 전략
케이크 인페인팅의 퀄리티를 결정짓는 핵심 시스템 지시어(System Prompt)를 다음과 같이 고정했습니다.
> "You are an expert custom cake decorator AI. Edit ONLY the masked area. CRITICAL: You MUST maintain the exact detailed buttercream icing texture, pastel color tone, and cake decoration style of the original image."



## 4. 실행 및 테스트 가이드

### 서버 실행 (Backend)
```bash
uvicorn main:app --reload
```

### 테스트 방법 (Client Simulation)
1. `img/original1.png` (원본), `img/mask1.png` (마스크) 준비.
2. (선택사항) 참고하고 싶은 이미지(`reference.png`)를 루트 폴더에 준비.
3. `client_test.py` 실행하여 JSON 데이터 통신 확인.
4. 결과물 `server_result.png` 자동 생성 및 화풍 유지 여부 검토.


## 4. 최종 결과물 및 성능 지표

* **생성 속도**: 로컬 7분 ➡️ **API 기반 약 3~5초 (약 100배 개선)**
* **이미지 품질**: 저해상도 깨짐 현상 해결, 원본 케이크의 파스텔톤 및 크림 질감 99% 일치.
* **멀티모달 지원**: 참고 사진(`reference`) 속 인물이나 사물의 특징을 케이크의 화풍에 맞춰 자연스럽게 합성 가능.
* **자연어 대응**: \"안경 낀 남자 모습으로 바꿔줘\" 등 복잡한 요청도 맥락에 맞게 정확히 합성.

