# [Issue #3 Fix] AI API 예외 처리 구조 개선 (`HTTPException` 400 에러 유지) 및 독스트링 정리

## 1. 문제 배경 (Background & Cause)
`/api/ai/portfolios/tags/recommend`, `/api/ai/stores/profile-suggest`, `/api/ai/stores/generate-bio` 3개의 신규 AI API 핸들러 내부에 아래와 같은 예외 처리 버그와 문서 표기 문제가 있었습니다.

1. **HTTP 400 Bad Request 에러가 500 에러로 덮어씌워지는 버그**:
   - 예: `if not input_img and not request.description: raise HTTPException(status_code=400, ...)`
   - 사용자가 필수 파라미터를 누락하여 `HTTPException(400)`을 발생시키거나, `load_image()` 내부에서 이미지 URL 로드 실패로 `HTTPException(400)`을 발생시켰을 때, 아래에 선언된 `except Exception as e:` 블록이 파이썬의 예외 계층 구조상 `HTTPException`까지 함께 포획합니다.
   - 그 결과, 사용자의 잘못된 입력(400 Bad Request)이 모두 서버 내부 오류(`500 Internal Server Error`)로 응답되는 심각한 오류 응답 왜곡이 발생했습니다.
2. **독스트링 숫자 표기 오류**:
   - `suggest_profile_improvement`의 독스트링: `1. [(AI) 프로필 개선 제안 API]`
   - `generate_store_bio`의 독스트링: `2. [(AI) 소개글 자동 생성 API]`
   - 불필요한 기획서 순번 번호가 그대로 복사되어 들어가 있어 API 문서 일관성이 저하되었습니다.

---

## 2. 해결 방안 및 적용된 로직 (Applied Solution & Logic)
1. **HTTPException 개별 예외 전파 로직(`raise`) 추가**:
   - 3개 API의 `try...except` 구문에서 `except Exception as e:` 상단에 **`except HTTPException as http_exc: raise http_exc`** 블록을 선행 배치했습니다.
   - 이를 통해 FastAPI의 `HTTPException`(상태 코드 400, 404 등)은 중간에 포획되어 500으로 변질되지 않고 클라이언트에게 정상적인 상태 코드와 메시지로 전송됩니다.
2. **독스트링 클린업**:
   - 불필요한 번호 접두사(`1. `, `2. `)를 삭제하고 `[(AI) 프로필 개선 제안 API]`, `[(AI) 소개글 자동 생성 API]`로 깔끔하게 통일했습니다.

---

## 3. 변경 사항 비교 (Before & After)

### [Before]
```python
try:
    if not input_img and not request.description:
        raise HTTPException(status_code=400, detail="...")
    ...
except Exception as e:
    # ❌ 400 HTTPException까지 여기서 잡혀서 무조건 status_code=500으로 응답됨!
    raise HTTPException(status_code=500, detail=f"태그 추천 처리 실패: {str(e)}")
```

### [After]
```python
try:
    if not input_img and not request.description:
        raise HTTPException(status_code=400, detail="...")
    ...
except HTTPException as http_exc:
    # ✅ 400 등 의도적으로 발생시킨 HTTP 예외는 있는 그대로 클라이언트에 전파
    raise http_exc
except Exception as e:
    # ✅ 그 외의 진짜 서버 내부/외부 API 호출 에러만 500 에러로 변환
    print(f"❌ 태그 추천 처리 중 에러 발생: {e}")
    raise HTTPException(status_code=500, detail=f"태그 추천 처리 실패: {str(e)}")
```

---

## 4. 검증 내역 (Verification)
- `python -m py_compile main.py` 명령어를 통해 예외 처리 구문 수정 및 독스트링 변경 후의 파이썬 문법 무결성을 검증했습니다.
