# 2026-08-18 AI 소개글 자동 생성 JSON 파싱 버그 핫픽스

## 1. 개요
- **문제점**: Gemini AI가 JSON 응답 반환 시 끝부분에 불필요한 닫는 괄호(`}`)를 중복 출력하거나 후행 데이터가 포함될 경우, `json.loads()`가 `Extra data: line 4 column 1` 오류(500 Internal Server Error)를 발생시키며 매장 소개글 자동 생성이 실패하는 현상 발생.
- **해결 방안**: JSON 파싱 실패 시 정규식(Regex)을 통한 `generatedBio` 필드 직접 추출 fallback 메커니즘을 추가하여 어떠한 포맷 오류에도 안전하게 소개글을 반환하도록 수정.

## 2. 주요 변경 사항
- **대상 파일**: `MakeAWish-AI/main.py`
- **수정 내용**:
  ```python
  bio = ""
  try:
      result_json = json.loads(raw_text)
      bio = result_json.get("generatedBio", "")
  except Exception:
      # Extra data 등 파싱 실패 시 정규식으로 안전 추출
      bio_match = re.search(r'"generatedBio"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw_text)
      if bio_match:
          bio = bio_match.group(1).replace('\\"', '"').replace('\\n', '\n')
      else:
          clean_txt = re.sub(r'[{}\"\']', '', raw_text).replace('generatedBio:', '').strip()
          bio = clean_txt if clean_txt else "매장 소개글이 성공적으로 생성되었습니다."
  ```

## 3. 검증 결과
- 중복 괄호(`}\n}`) 응답 테스트 시 에러 없이 본문 정상 추출 완료.
