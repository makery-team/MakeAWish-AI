# 🎂 MakeAWish-AI 핵심 기술 분석 보고서

본 문서는 `MakeAWish-AI` 프로젝트의 소스 코드에서 발표 및 기술 공유를 위해 추출한 핵심 로직 분석 결과입니다.

---

## 1. 페르소나 기반 프롬프트 엔지니어링 (Persona Prompting)

단순한 이미지 수정을 넘어, AI에게 **전문 케이크 데코레이터**라는 역할을 부여하여 결과물의 일관성을 확보합니다.

```python
# main.py - 시스템 프롬프트 합성 로직
instruction = (
    "Instruction: You are an expert cake decorator. "
    "CRITICAL: The style MUST be a buttercream icing texture, "
    "hand-painted art style, and use pastel colors... "
    "It MUST look like it was drawn with cake cream."
)
```ㄹ
*   **분석**: `CRITICAL` 키워드를 사용하여 AI가 실사 사진이 아닌 '케이크 크림 질감'을 반드시 유지하도록 강제합니다. 이는 서비스의 시각적 정체성을 결정짓는 핵심 설정입니다.

## 2. 정밀 인페인팅 제어 (Masked Area Control)
원본 케이크의 아름다움을 해치지 않고 사용자가 지정한 영역만 정확히 수정하도록 지시합니다.

```python
# main.py - 영역 제한 지시
"Modify ONLY the masked area of the cake."
"Keep the buttercream icing texture and pastel art style perfectly identical to the original cake."
```

* **분석**: `Modify ONLY`라는 명시적 제약을 통해 마스크 외부(원본 케이크 배경)의 손실을 방지하고 자연스러운 합성을 유도합니다.

## 3. 멀티모달 컨텐츠 구성 (Multi-modal Input)

텍스트, 원본 이미지, 마스크 이미지, 참고 이미지를 하나의 컨텍스트로 결합하여 AI에게 전달합니다.

```python
# main.py - 제미나이 입력 데이터 구성
if reference_img:
    contents = [final_prompt, original_img, mask_img, reference_img]
else:
    contents = [final_prompt, original_img, mask_img]

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=contents
)
```

* **분석**: `gemini-3.1-flash` 모델의 멀티모달 능력을 활용하여 복잡한 데이터 구조를 직관적으로 처리합니다. 여러 이미지를 동시에 입력받아 관계를 이해하는 것이 핵심입니다.

## 4. 동적 참고 이미지 반영 (Reference Style Transfer)

사용자가 올린 참고 사진(인물, 캐릭터 등)을 케이크 디자인에 즉석에서 반영합니다.

```python
# main.py - 참고 이미지 활용 프롬프트
"Draw the character or person from the 'Reference Image' onto the masked area."
```

* **분석**: 별도의 미세 조정(Fine-tuning) 없이도 입력된 `reference_image`의 특징을 추출하여 케이크 화풍으로 재해석하는 'Zero-shot' 능력을 활용합니다.

## 5. 효율적인 데이터 파이프라인 (Base64 <-> PIL)

웹(프론트엔드)과 AI 엔진 사이의 데이터 형식 차이를 메우는 유틸리티 로직입니다.

```python
# main.py - 변환 헬퍼 함수
def b64_to_pil(b64_str):
    # Base64 문자열 -> 바이너리 -> PIL 이미지 객체
    img_data = base64.b64decode(b64_str.split("base64,")[1])
    return Image.open(io.BytesIO(img_data))
```

* **분석**: 네트워크 전송에 유리한 Base64 형식을 AI 처리에 적합한 PIL 이미지로 실시간 변환하여 메모리 효율성을 높였습니다.

## 6. 클라이언트측 시뮬레이션 및 예외 처리

서버의 안정성을 검증하기 위한 타임아웃 및 데이터 검증 로직입니다.

```python
# client_test.py - 통신 설정
REQUEST_TIMEOUT = (10, 180) # (연결 대기, 생성 대기)
```

* **분석**: 생성형 AI 특성상 응답 시간이 길어질 수 있음을 고려하여 Read Timeout을 180초로 넉넉하게 설정, 사용자 경험(UX) 측면에서의 안정성을 고려했습니다.
