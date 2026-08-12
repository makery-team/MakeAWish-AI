# 🧠 AI 챗봇 스키마 파싱 및 동적 선택지(Options) 응답 가이드

본 문서는 `MakeAWish-AI` (Python FastAPI 서버)가 백엔드로부터 전달받은 주문서 양식(Schema)을 어떻게 분석하고, 사용자에게 객관식 선택지(`options`)를 제공하는지에 대한 프롬프트 설계 로직을 설명합니다.

## 1. 개요 (Architecture Overview)

소비자 앱에서 케이크를 주문할 때, 매장마다 묻는 정보가 다릅니다(어느 매장은 레터링만 묻고, 어느 매장은 알러지도 물어봄).
이 복잡성을 해결하기 위해 백엔드는 매장의 주문서 JSON을 AI 서버로 넘겨주고, **AI 서버(LLM)가 알아서 대화의 흐름을 통제**합니다.

- **흐름 요약**:
  1. 백엔드에서 `ChatRequest` 객체를 통해 이전 대화 내역(`messages`), 현재 메시지(`current_message`), 그리고 **매장의 주문서 양식(`schema_json`)**을 전달
  2. Gemini 모델은 시스템 프롬프트 지침에 따라 현재 어떤 정보가 누락되었는지 추론
  3. 누락된 정보가 객관식(선택형) 항목이라면, `SHOW_SCHEMA` 액션과 함께 프론트엔드가 렌더링할 수 있도록 `options` 배열을 JSON 형태로 응답
  4. 프론트엔드 앱은 이 `options` 배열을 받아 말풍선 아래 버튼(Chip)들로 예쁘게 그려줌

## 2. 주요 로직 및 코드 설명 (`main.py`)

로직의 핵심은 모델에게 전달하는 **시스템 프롬프트(System Prompt)**에 있습니다. 별도의 하드코딩된 조건문 없이, 모델이 동적으로 JSON을 생성하게 만듭니다.

### 프롬프트 인젝션 로직
```python
system_prompt = (
    # ... 기본 챗봇 페르소나 ...
    "\n\n### Action Types 설명:"
    "\n3. 'SHOW_SCHEMA': 주문 진행 중 schema_json 존재 시 비어있는 값을 채우기 위해 질문이 필요할 때."
    
    "\n\n### 응답 형식 (반드시 JSON 형식을 지킬 것):"
    "\n{"
    "\n  'actionType': '위의 5가지 타입 중 하나',"
    "\n  'message': '사용자에게 보내는 친절한 한국어 답변',"
    "\n  'data': {"
    "\n    'extracted_slots': { '항목': '값' } (SHOW_SCHEMA, CONFIRM_SLOTS인 경우만),"
    "\n    'options': ['선택지1', '선택지2'] (SHOW_SCHEMA 질문에 대해 주문서 양식 상 선택지가 있다면 추가),"
    "\n    'status': 'IN_PROGRESS' 또는 'COMPLETED' (주문 관련 시)"
    "\n  } 또는 데이터가 없으면 null"
    "\n}"
)

# 동적으로 매장별 스키마 주입
if request.schema_json:
    system_prompt += (
        f"\n\n[현재 주문서 양식]: {json.dumps(request.schema_json, ensure_ascii=False)}"
        "\n\n[중요 지침]: 'data.extracted_slots'를 작성할 때, 반드시 [현재 주문서 양식]에 정의된 키(Key) 이름들만 정확히 사용해서 매핑하세요."
    )
```

## 3. 요약 및 주의사항

- 이 구현은 프론트엔드와 백엔드의 커플링(Coupling)을 극도로 낮춰줍니다. 프론트엔드는 AI가 뱉어내는 JSON의 `options` 항목만 화면에 그릴 뿐, 양식이 어떻게 생겼는지는 전혀 알 필요가 없습니다.
- 프롬프트에 명시된 `'options': ['선택지1', '선택지2']` 문장 하나가, 앱에서 화려한 터치 칩(Chip) UI를 만들어내는 핵심 Trigger 역할을 합니다. 프롬프트 수정 시 JSON 키 값(`options`)이 깨지지 않도록 매우 주의해야 합니다.
