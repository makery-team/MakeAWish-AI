# [Issue #2 Fix] AI 리뷰 요약 API Pydantic 객체 직렬화 오류 수정 및 응답 모델 지정

## 1. 문제 배경 (Background & Cause)
`/api/ai/reviews/summary` 엔드포인트에 다음과 같은 치명적 버그 및 구조적 누락 사항들이 존재했습니다.
1. **Pydantic 모델 인스턴스 직접 직렬화 오류 (`TypeError`)**:
   - `contents = [prompt, f"Reviews: {json.dumps(request, ensure_ascii=False)}"]`
   - `request`는 `ReviewSummaryRequest` 타입의 Pydantic 인스턴스이므로, 파이썬 표준 `json.dumps()`에 직접 전달하면 `TypeError: Object of type ReviewSummaryRequest is not JSON serializable` 예외가 발생합니다.
2. **응답 모델(`response_model`) 누락**:
   - 다른 AI API와 달리 `@app.post(...)` 데코레이터에 `response_model=ReviewSummaryResponse`가 선언되지 않아 Swagger API 명세 및 자동 검증 기능이 누락되었습니다.
3. **예외 처리 및 유효성 검사 미흡**:
   - 빈 리스트(`[]`) 요청에 대한 검증 로직이 없고, API 핸들러 전체를 감싸는 `try...except`가 없어 Gemini API 호출 중 문제 발생 시 500 Unhandled Traceback이 출력되었습니다.

---

## 2. 해결 방안 및 적용된 로직 (Applied Solution & Logic)
1. **직렬화 대상 변경**:
   - `json.dumps(request.reviews, ensure_ascii=False)`로 수정하여 모델 인스턴스가 아닌 내부의 문자열 리스트(`reviews`)를 올바르게 JSON 문자열로 변환했습니다.
2. **FastAPI 응답 모델 명시 및 안전한 래핑**:
   - `@app.post("/api/ai/reviews/summary", response_model=ReviewSummaryResponse)`를 명시하고, 반환 시 `ReviewSummaryResponse(...)` 인스턴스로 안전하게 래핑하여 응답하도록 개선했습니다.
3. **유효성 검사 및 예외 처리 강화**:
   - `if not request.reviews:` 조건을 추가해 빈 배열 요청 시 400 Bad Request(`리뷰 목록은 최소 1개 이상이어야 합니다.`)를 명시적으로 반환합니다.
   - `try...except HTTPException` 및 `except Exception as e:` 블록을 구성하여 서버 내부 오류에 대한 안전한 로깅 및 에러 코드 통일을 구현했습니다.

---

## 3. 변경 사항 비교 (Before & After)

### [Before]
```python
@app.post("/api/ai/reviews/summary")  # ❌ response_model 누락
async def summarize_reviews(request: ReviewSummaryRequest):
    ...
    # ❌ Pydantic 객체를 dumps에 넣어 TypeError 발생
    contents = [prompt, f"Reviews: {json.dumps(request, ensure_ascii=False)}"]
    
    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=contents,
        config={"response_mime_type": "application/json"}
    )
    
    return json.loads(response.text)  # ❌ 예외 처리 없이 raw dict 반환
```

### [After]
```python
@app.post("/api/ai/reviews/summary", response_model=ReviewSummaryResponse)  # ✅ 응답 모델 명시
async def summarize_reviews(request: ReviewSummaryRequest):
    ...
    try:
        if not request.reviews:  # ✅ 빈 리스트 예외 검증
            raise HTTPException(status_code=400, detail="리뷰 목록은 최소 1개 이상이어야 합니다.")

        ...
        # ✅ request.reviews 리스트를 JSON 직렬화
        contents = [prompt, f"Reviews: {json.dumps(request.reviews, ensure_ascii=False)}"]

        response = client.models.generate_content(
            model=CHAT_MODEL,
            contents=contents,
            config={"response_mime_type": "application/json"}
        )

        result_json = json.loads(response.text)
        return ReviewSummaryResponse(
            summary=result_json.get("summary", ""),
            positive_points=result_json.get("positive_points", []),
            negative_points=result_json.get("negative_points", [])
        )
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"❌ 리뷰 요약 처리 중 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=f"리뷰 요약 처리 실패: {str(e)}")
```

---

## 4. 검증 내역 (Verification)
- `python -m py_compile main.py` 명령어를 통해 수정한 리뷰 요약 API의 구문 파싱 및 문법 무결성을 확인했습니다.
