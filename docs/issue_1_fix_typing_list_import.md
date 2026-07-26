# [Issue #1 Fix] AI 포트폴리오 및 프로필 개선 API의 `List` 임포트 누락 수정 및 타입 표기 통일

## 1. 문제 배경 (Background & Cause)
`feature/ai-portfolio-tag-recommendation` 브랜치에서 신규로 추가된 AI 기능의 Pydantic 데이터 모델 중, 아래 모델들에서 `typing.List`를 사용하고 있었습니다.
- `TagRecommendationResponse`: `recommended_tags: List[str]`
- `StoreProfileSuggestResponse`: `suggestions: List[str]`

하지만 `main.py` 상단의 임포트문(`line 49`)에는 `from typing import Optional`만 정의되어 있었으며, **`List`를 임포트하지 않았습니다.**
이로 인해 파이썬 모듈 로드 또는 Pydantic 모델 파싱 시 **`NameError: name 'List' is not defined`** 런타임 예외가 발생할 위험이 있었습니다.
또한, `ReviewSummaryRequest`, `ReviewSummaryResponse` 모델은 소문자 `list[str]`을 혼용하고 있어 전체 코드베이스의 타입 힌트 컨벤션 일관성이 저하되었습니다.

---

## 2. 해결 방안 및 적용된 로직 (Applied Solution & Logic)
1. **typing 모듈 임포트 보완**:
   - `from typing import Optional, List`로 수정하여 `List` 타입을 명시적으로 임포트했습니다.
2. **Pydantic 데이터 모델 타입 통일**:
   - 기존에 소문자 `list[str]`로 선언되었던 `ReviewSummaryRequest`, `ReviewSummaryResponse`의 속성들을 표준 `List[str]` 표기법으로 일관되게 통일했습니다.

---

## 3. 변경 사항 비교 (Before & After)

### [Before]
```python
# line 49
from typing import Optional

...

class TagRecommendationResponse(BaseModel):
    recommended_tags: List[str]  # ❌ NameError 발생 가능

class ReviewSummaryRequest(BaseModel):
    reviews: list[str]           # ❌ 혼용된 타입 표기

class ReviewSummaryResponse(BaseModel):
    summary: str
    positive_points: list[str]
    negative_points: list[str]
```

### [After]
```python
# line 49
from typing import Optional, List

...

class TagRecommendationResponse(BaseModel):
    recommended_tags: List[str]  # ✅ List 임포트 완료

class ReviewSummaryRequest(BaseModel):
    reviews: List[str]           # ✅ List[str]로 일관성 통일

class ReviewSummaryResponse(BaseModel):
    summary: str
    positive_points: List[str]
    negative_points: List[str]
```

---

## 4. 검증 내역 (Verification)
- `python -m py_compile main.py` 명령어를 통해 문법 및 임포트 오류 없이 파싱 완료됨을 검증했습니다.
