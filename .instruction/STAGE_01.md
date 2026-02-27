# 🚀 Stage 1: 기반 구축 — Telegram 봇 서버 구현

### 🎯 이번 단계의 목표

Flask 웹 서버 대신 **Telegram 봇(`antigravity_bot.py`)**을 기반으로 스마트폰과 PC를 연결합니다.
폰에서 텔레그램으로 메시지를 보내면 `mailbox.json`에 저장되고, AI 답장은 텔레그램으로 즉시 전달됩니다.

---

### 🔑 핵심 구조 변경: Flask → Telegram

```
[기존]  폰 브라우저 → Flask(port 9150) → mailbox.json → agent_brain → VS Code
[변경]  텔레그램 앱 → Telegram Cloud → antigravity_bot.py → mailbox.json → agent_brain → VS Code
```

**왜 더 좋은가?**

- 포트 포워딩/방화벽 설정 불필요
- Tailscale 없이도 어디서나 접속
- Telegram의 E2E 보안 + `chat_id` 기반 인증
- `/screenshot` 명령으로 스크린샷을 채팅창에서 바로 수신

---

### 🛠️ 기술 사양 (AI 구현 가이드)

#### 파일 1: 환경 변수 (`.env`)

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

> 📌 봇 토큰: `@BotFather` → `/newbot`
> 📌 Chat ID: `@userinfobot` → `/start`

#### 파일 2: 필수 패키지 (`requirements.txt`)

```
python-telegram-bot[job-queue]>=21.0
python-dotenv
pyautogui
pyperclip
pywin32
requests
numpy
scipy
Pillow
```

#### 파일 3: 데이터 버스 (`mailbox.json`)

초기 구조:

```json
{ "inbound": [], "outbound": [], "approval_request": null }
```

- `inbound`: 텔레그램에서 받은 메시지 대기열
- `outbound`: AI가 텔레그램으로 보낼 답장 대기열
- `approval_request`: 승인 요청 상태

#### 파일 4: 응답 도구 (`send_reply.py`)

AI(Antigravity)가 직접 실행하여 텔레그램으로 답장을 보냅니다.

```python
import json, sys, os, shutil

def send_reply(message):
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    mailbox_path = os.path.join(BASE_DIR, "mailbox.json")
    temp_path = mailbox_path + ".tmp"

    try:
        with open(mailbox_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"inbound": [], "outbound": [], "approval_request": None}

    data["outbound"].append(message)

    with open(temp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(temp_path, mailbox_path)
    print(f"Reply queued: {message}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_reply(" ".join(sys.argv[1:]))
    else:
        print("Usage: python send_reply.py '메시지'")
```

#### 파일 5: Telegram 봇 서버 (`antigravity_bot.py`)

> ⚠️ **Flask 서버(`antigravity_host.py`)는 더 이상 사용하지 않습니다.**
> ⚠️ **PORT 환경 변수가 필요 없습니다. BOT_TOKEN과 CHAT_ID만 필요합니다.**

주요 기능:

- `/start` — 연결 확인
- `/screenshot` — 현재 화면 캡처 후 텔레그램 전송
- `/stop` — 긴급 중지
- `/status` — 시스템 상태 확인
- 일반 텍스트 메시지 → `mailbox.json` inbound에 `[📱MOBILE]` 태그와 함께 저장
- **`outbound_watcher` 백그라운드 스레드**: outbound 배열을 0.5초마다 감시 → Telegram push

```python
# 핵심 구조 (전체 코드는 antigravity_bot.py 참고)
def outbound_watcher(bot_token, chat_id):
    """mailbox.json outbound → Telegram sendMessage"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    while True:
        box = read_mailbox()
        messages = box.get("outbound", [])
        if messages:
            box["outbound"] = []
            write_mailbox(box)
            for msg in messages:
                requests.post(url, json={"chat_id": chat_id, "text": msg})
        time.sleep(0.5)
```

### 🤖 AI 시스템 프롬프트 설정 (핵심!)

AI에게 다음과 같이 지시하세요:

> **"앞으로 `[📱MOBILE]` 태그가 붙은 요청이 오면, 작업을 마친 후 반드시 `python send_reply.py '결과 메시지'`를 실행해서 텔레그램으로 결과를 알려줘."**

---

### ✅ 성공 체크리스트

- [ ] `.env` 파일에 `TELEGRAM_BOT_TOKEN`과 `TELEGRAM_CHAT_ID`가 있는가?
- [ ] `mailbox.json`이 자동 생성되는가?
- [ ] `python send_reply.py "테스트"` 실행 시 `mailbox.json`의 `outbound`에 추가되는가?
- [ ] `antigravity_bot.py` 실행 시 "봇 시작됨" 출력이 나오는가?
- [ ] 텔레그램에서 `/start` 전송 시 "연결됨" 응답이 오는가?
- [ ] `outbound`에 데이터가 있을 때 텔레그램으로 자동 전송되는가?
