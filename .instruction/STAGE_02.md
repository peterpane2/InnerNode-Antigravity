# 🏁 Stage 2: 신경망 연결 — Brain 브릿지 구현

### 🎯 이번 단계의 목표

`mailbox.json`을 직접 읽어 VS Code 채팅창에 자동 타이핑하는 **`agent_brain.py`**를 구현합니다.
이전 Flask 방식과 달리 HTTP 호출 없이 파일을 직접 읽습니다.

---

### ⚠️ AI에게 전달할 핵심 지시

> **`mailbox.json`의 `inbound` 배열을 1초마다 직접 읽습니다. Flask HTTP 호출은 사용하지 않습니다.**
> **`push_msg()`는 Telegram sendMessage API를 직접 호출합니다. `/api/agent/push` 엔드포인트는 없습니다.**

---

### 🛠️ 기술 사양

#### `agent_brain.py` 핵심 변경 사항

**1. Inbound 수신 방식 변경**

```python
# ❌ 기존 (Flask HTTP)
r = requests.get(f"{HOST_URL}/api/agent/poll").json()
tasks = r.get("requests", [])

# ✅ 변경 (mailbox.json 직접 읽기)
box = read_mailbox()
tasks = box.get("inbound", [])
if tasks:
    box["inbound"] = []
    write_mailbox(box)
```

**2. push_msg() 변경 — Telegram 직접 호출**

```python
# ❌ 기존 (Flask HTTP)
def push_msg(msg):
    requests.post(f"{HOST_URL}/api/agent/push", json={"message": msg})

# ✅ 변경 (Telegram API 직접)
def push_msg(msg: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": int(chat_id), "text": msg},
        timeout=5,
    )
```

**3. VS Code 창 탐지 필터 (변경 없음)**

| 항목        | 값                        | 이유                  |
| ----------- | ------------------------- | --------------------- |
| 창 클래스   | `Chrome_WidgetWin_1`      | VS Code만 정확히 타겟 |
| 입력 방식   | `Ctrl+A → Ctrl+V → Enter` | 한글 지원             |
| 포커스 대기 | `0.4초`                   | 창 전환 안정화        |

---

### 🔑 핵심 포인트 요약

| 항목          | Stage 1 방식 (Flask) | Stage 2 방식 (Telegram)  |
| ------------- | -------------------- | ------------------------ |
| Inbound 수신  | GET /api/agent/poll  | mailbox.json 직접 읽기   |
| Outbound 전송 | POST /api/agent/push | Telegram sendMessage API |
| 포트 의존성   | PORT=9150 필요       | 없음                     |

---

### ✅ 성공 체크리스트

- [ ] `agent_brain.py`가 mailbox.json을 **직접** 읽는가? (HTTP 호출 아님)
- [ ] 폰에서 보낸 텔레그램 메시지가 VS Code 채팅창에 자동 입력되는가?
- [ ] VS Code 창이 숨어 있어도 자동으로 앞으로 나오는가?
- [ ] 한글 메시지가 깨지지 않고 정상 입력되는가?
- [ ] `push_msg()`가 Telegram에 직접 전송하는가?
