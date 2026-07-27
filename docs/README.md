# 📚 MakeAWish AI (FastAPI) 기술 문서 및 이슈 분석 리포트 색인 (Documentation Index)

이 디렉토리(`docs/`)는 MakeAWish-AI 마이크로서비스 프로젝트의 버그 수정, 인터페이스 명세 및 가이드 문서를 관리합니다.  
누구나 문서 이름만 보고도 어떤 내용인지 한눈에 파악할 수 있도록 **표준 문서 네이밍 규칙**을 준수합니다.

---

## 📐 문서 네이밍 규칙 (`YYYY-MM-DD_[분류]_[직관적_주제].md`)

```
예시: 2026-07-26_bugfix_http_exception_handling_and_tag_recommend.md
       (날짜)       (분류: 버그수정)      (주제: HTTP 예외 처리 및 태그 추천 버그 해결)
```

---

## 📋 문서 목록 (Index)

### 🐞 버그 수정 및 이슈 분석 (`bugfix_`)
| 작성일자 | 문서명 | 핵심 주제 및 해결 내용 |
| :---: | :--- | :--- |
| **2026-07-26** | [`2026-07-26_bugfix_http_exception_handling_and_tag_recommend.md`](./2026-07-26_bugfix_http_exception_handling_and_tag_recommend.md) | **AI 태그 추천 및 프로필 개선 API HTTP 예외 방어 로직 수정**<br>• `HTTPException` 발생 시 500 에러로 중복 래핑되던 문제 해결 |
| **2026-07-25** | [`2026-07-25_bugfix_review_summary_api_serialization.md`](./2026-07-25_bugfix_review_summary_api_serialization.md) | **AI 리뷰 요약 API(`ReviewSummaryRequest`) Pydantic 직렬화 오류 수정**<br>• 요청 바디 형식 불일치로 인한 422 Unprocessable Entity 해결 |
| **2026-07-25** | [`2026-07-25_bugfix_portfolio_list_type_import.md`](./2026-07-25_bugfix_portfolio_list_type_import.md) | **AI 포트폴리오 API의 `typing.List` 임포트 누락 및 스키마 명세 일관성 개선** |
