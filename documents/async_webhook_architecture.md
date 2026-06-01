# AI 서버 비동기(Async) 및 웹훅(Webhook) 아키텍처 가이드

안녕하세요! 이 문서는 백엔드(Spring Boot), AI 서버(FastAPI), 그리고 프론트엔드가 **"이미지 생성"**이라는 오래 걸리는 작업을 어떻게 주고받는지 주니어 개발자분들의 눈높이에 맞춰 설명하는 문서입니다.

---

## 1. 왜 이렇게 복잡하게 바뀌었나요? (동기 vs 비동기)

기존에는 프론트엔드가 "이미지 만들어줘!" 라고 요청하면, AI 서버가 이미지를 다 그릴 때까지(약 5~10초) 프론트엔드와 백엔드가 **하염없이 기다렸습니다.** (동기 방식)
이러면 서버 연결이 끊기거나(Timeout), 사용자가 멈춘 줄 알고 새로고침을 누르는 등 문제가 발생하기 쉽습니다.

그래서 우리는 **"진동벨 시스템 (비동기 + 웹훅)"**을 도입했습니다!

---

## 2. 진동벨 시스템 (웹훅) 작동 원리

카페에서 주문할 때를 상상해 보세요!
1. **주문 접수 (FE ➡️ BE ➡️ AI)**: 프론트가 케이크를 주문하면, 백엔드가 AI에게 주문서를 넘깁니다.
2. **진동벨 배부 (AI ➡️ BE ➡️ FE)**: AI 서버는 "오래 걸리니까 일단 이거(Task ID) 받고 자리에서 기다려!" 하고 바로 202 상태 코드와 함께 통신을 끊습니다.
3. **상태 확인 (FE ➡️ BE 폴링)**: 프론트엔드는 2~3초마다 "제 거(Task ID) 다 됐나요?" 하고 백엔드에 물어봅니다. (폴링)
4. **완료 알림 (AI ➡️ BE 웹훅)**: AI가 그림을 다 그리고 S3에 업로드를 마치면, 백엔드의 전용 수신처(웹훅 주소)로 "다 그렸어! 주소는 이거야!" 하고 전화를 줍니다.
5. **서빙 완료**: 백엔드가 결과를 DB에 저장해 두면, 다음 번 프론트가 "다 됐나요?" 물어볼 때 완성된 이미지를 줍니다.

---

## 3. 코드와 로직 상세 설명

### 🟢 AI 서버 (FastAPI) 로직
AI 서버는 들어온 요청을 `BackgroundTasks`라는 백그라운드 스레드로 던져버리고 바로 202 응답을 줍니다.

```python
# [main.py 내의 API 엔드포인트]
@app.post("/api/ai/inpaint", status_code=202)
async def generate_cake(request: InpaintRequest, background_tasks: BackgroundTasks):
    
    # 1. 실제 이미지 그리기와 웹훅 전송은 백그라운드 스레드에 맡깁니다. (비동기)
    background_tasks.add_task(process_and_send_webhook, request.task_id, request)
    
    # 2. 그리고 자신은 즉시 "접수됨(202)"을 반환하고 통신을 끊습니다.
    return {"message": "Processing started"}
```

실제로 백그라운드에서 실행되는 `process_and_send_webhook` 함수는 아래처럼 동작합니다.
```python
async def process_and_send_webhook(task_id: int, request: InpaintRequest):
    # ... (AI 이미지 생성 로직) ...

    # 1. 만들어진 이미지를 S3에 바로 업로드합니다.
    result_url = upload_to_s3(img_bytes)

    # 2. 백엔드의 웹훅 주소로 "작업 끝났어!" 라고 POST 요청을 보냅니다.
    # 이것이 바로 '웹훅(Webhook)' 입니다! 백엔드가 뚫어놓은 수신함에 결과물을 던져주는 것이죠.
    payload = {"task_id": task_id, "result_image": result_url, "status": "COMPLETED"}
    await http_client.post(webhook_url, json=payload)
```

### 🔵 백엔드 서버 (Spring Boot) 로직
백엔드는 AI 서버가 작업 완료를 알려줄 수 있도록 수신함(Webhook Endpoint)을 열어둡니다.

```java
// [AiInpaintingController.java]
// AI 서버가 "다 만들었어!" 하고 호출하는 주소 (이 주소가 WEBHOOK_URL이 됩니다)
@PostMapping("/webhook/inpaint")
public ResponseEntity<Void> inpaintingWebhookCallback(@RequestBody AiWebhookRequest request) {
    // AI 서버가 보낸 결과 이미지 URL을 DB의 해당 Task ID에 저장합니다.
    inpaintingService.processWebhookCallback(
            request.task_id(), 
            request.result_image(), 
            request.status()
    );
    return ResponseEntity.ok().build();
}
```

### 🟠 프론트엔드 (React / Vue) 로직
프론트엔드는 처음 요청 시 완성된 이미지가 오지 않으므로, 작업 ID만 받고 `setInterval` 등으로 계속 확인해야 합니다.

```javascript
// 1. 처음 인페인팅 요청 (응답으로 Task ID를 받음)
const response = await axios.post('/api/ai-agent/inpaint/123', requestData);
const taskId = response.data.taskId;
setIsLoading(true);

// 2. 3초마다 백엔드에 "다 됐나요?" 물어보기 (Polling)
const interval = setInterval(async () => {
    const statusRes = await axios.get(`/api/ai-agent/inpaint/123/${taskId}`);
    
    // 백엔드가 웹훅을 받아서 상태가 COMPLETED로 바뀌었다면!
    if (statusRes.data.status === 'COMPLETED') {
        setResultImage(statusRes.data.resultImage); // 화면에 그림 표시
        setIsLoading(false);
        clearInterval(interval); // 반복 질문 종료
    }
}, 3000);
```

---

## 4. 🚀 핵심 요약
- **웹훅(Webhook)** 은 연락처를 남겨두고 "다 되면 이리로 전화해 줘"라고 하는 방식입니다.
- AI 서버는 무거운 이미지 데이터를 낑낑대며 백엔드에 보내지 않고, S3에 가볍게 올린 뒤 URL만 웹훅으로 쏴줍니다.
- 이 아키텍처 덕분에 백엔드 서버가 멈추지 않고 쾌적하게 동작할 수 있습니다! 화이팅! 🚀
