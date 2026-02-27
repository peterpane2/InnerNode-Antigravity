"""
agent_brain.py — 브릿지 에이전트 (v3.4)
- 125% DPI 배율 및 마우스 좌표 최종 보정 완료
- DEBUG_IMAGE 토글 추가 (기본 False)
- 이미지 기반 버튼 클릭 지원 (icon_*.png)
- /auto: 실시간 자동 아이콘 감시 & 클릭
"""
import os, json, time, threading, tempfile, ctypes, requests
import pyautogui, pyperclip, win32gui, win32con
import numpy as np
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

try:
    from scipy import ndimage
except ImportError:
    ndimage = None

# 🛠️ 디버그 설정: 클릭 지점을 사진으로 확인하고 싶을 때만 True로 변경하세요.
DEBUG_IMAGE = False

# DPI Awareness 설정 (125% 배율 등 대응)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "0")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAILBOX_PATH = os.path.join(BASE_DIR, "mailbox.json")

def read_mailbox():
    try:
        with open(MAILBOX_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"inbound": [], "outbound": [], "approval_request": None}

def write_mailbox(box):
    fd, tmp = tempfile.mkstemp(dir=BASE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(box, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MAILBOX_PATH)

def push_msg(msg: str):
    if not BOT_TOKEN: return
    try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                      json={"chat_id": int(CHAT_ID), "text": msg}, timeout=5)
    except: pass

def push_img(img_obj, caption=""):
    if not BOT_TOKEN or not DEBUG_IMAGE: return
    try:
        buf = BytesIO()
        img_obj.save(buf, format="PNG")
        buf.seek(0)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                      files={'photo': buf}, data={'chat_id': int(CHAT_ID), 'caption': caption}, timeout=10)
    except: pass

def get_vscode_window_rect():
    found = []
    win32gui.EnumWindows(lambda hwnd, res: res.append((hwnd, win32gui.GetWindowText(hwnd))) if win32gui.IsWindowVisible(hwnd) else None, found)
    target = None
    for hwnd, title in found:
        class_name = win32gui.GetClassName(hwnd)
        if class_name == "Chrome_WidgetWin_1" and any(x in title for x in ["Visual Studio Code", "Antigravity", "OpenClaw"]):
            if not any(title.endswith(x) for x in [" - Chrome", " - Microsoft Edge"]):
                target = (hwnd, title)
                break
    if not target: return None, None, None
    hwnd, title = target
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMINIMIZED: win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else: win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    try: win32gui.SetForegroundWindow(hwnd)
    except: pass
    time.sleep(0.5)
    rect = win32gui.GetWindowRect(hwnd)
    return hwnd, rect, title

# ── 이미지 기반 버튼 클릭 ──────────────────────────────────────────────────────

ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".instruction")

def click_icon(icon_name: str, confidence: float = 0.8, timeout: float = 0.0) -> bool:
    """화면에서 아이콘 이미지를 찾아 클릭합니다.
    timeout > 0 이면 해당 초만큼 반복 탐색합니다.
    """
    icon_path = os.path.join(ICON_DIR, f"icon_{icon_name}.png")
    if not os.path.exists(icon_path):
        push_msg(f"⚠️ 아이콘 파일 없음: icon_{icon_name}.png")
        return False

    deadline = time.time() + max(timeout, 0)
    while True:
        try:
            pos = pyautogui.locateCenterOnScreen(icon_path, confidence=confidence)
            if pos:
                pyautogui.moveTo(pos, duration=0.2)
                pyautogui.click()
                return True
        except Exception:
            pass  # opencv 미설치 등 — 아래서 별도 안내
        if time.time() >= deadline:
            break
        time.sleep(0.5)
    return False


def type_into_chatwindow(text: str) -> bool:
    """채팅 입력창에 텍스트를 입력하고 → 버튼(proceed)을 클릭합니다.
    일반 텍스트 입력과 동일한 좌표(0.88, 0.927)를 사용합니다."""

    # 1. VS Code 창 정보 가져오기
    hwnd, rect, title = get_vscode_window_rect()
    if not rect:
        push_msg("❌ VS Code 창을 찾을 수 없습니다.")
        return False

    l, t, r, b = rect
    w, h = r - l, b - t

    # 2. 채팅 입력창 클릭 (일반 텍스트와 동일한 좌표 — 이미 검증됨)
    click_x = int(l + w * 0.88)
    click_y = int(t + h * 0.927)
    pyautogui.moveTo(click_x, click_y, duration=0.2)
    pyautogui.click()
    time.sleep(0.1)
    pyautogui.click()
    time.sleep(0.3)

    # 3. 텍스트 입력
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)

    # 4. → (proceed) 버튼 클릭으로 전송
    if not click_icon("proceed", confidence=0.8):
        # proceed 못 찾으면 Enter로 전송 시도
        pyautogui.press("enter")
        push_msg("⚠️ → 버튼 못 찾아서 Enter로 전송했습니다.")

    return True


def execute_brain_task(command: str) -> bool:
    global _auto_watch_active

    # 0. VS Code 없이도 처리 가능한 명령어 (Auto Watch 등)
    if command.startswith("__COMMAND:"):
        clean_command = command[:-2] if command.endswith("__") else command
        parts = clean_command.split(":")
        cmd_type = parts[1]

        if cmd_type == "AUTO_WATCH_ON":
            _auto_watch_active = True
            push_msg("🤖 Auto Watch ON: accept_all / proceed / run / scrolldown 감시 시작!")
            return True

        elif cmd_type == "AUTO_WATCH_OFF":
            _auto_watch_active = False
            push_msg("⏹️ Auto Watch OFF: 자동 감시 중단")
            return True

    # 1. VS Code 창 필요한 명령어
    hwnd, rect, title = get_vscode_window_rect()
    if not rect:
        push_msg("❌ VS Code 창을 찾을 수 없습니다.")
        return False

    l, t, r, b = rect
    w, h = r - l, b - t

    # 2. 시스템 명령어 처리 (매크로)
    if command.startswith("__COMMAND:"):
        clean_command = command[:-2] if command.endswith("__") else command
        parts = clean_command.split(":")
        cmd_type = parts[1]
        
        if cmd_type == "SCROLL":
            direction = parts[2]
            scroll_x = int(l + w * 0.85)
            scroll_y = int(t + h * 0.5)
            pyautogui.moveTo(scroll_x, scroll_y)
            amount = 800 if direction == "UP" else -800
            pyautogui.scroll(amount)
            return True
        
        elif cmd_type == "CLICK":
            target_x, target_y = int(parts[2]), int(parts[3])
            pyautogui.moveTo(target_x, target_y, duration=0.5)
            pyautogui.click()
            return True

        elif cmd_type == "CLICK_RUN_ONCE":
            btn_x = int(l + w * 0.78) 
            btn_y = int(t + h * 0.88)
            pyautogui.moveTo(btn_x, btn_y, duration=0.5)
            pyautogui.click()
            return True

        elif cmd_type == "CLICK_RUN_ALL":
            btn_x = int(l + w * 0.85) 
            btn_y = int(t + h * 0.88)
            pyautogui.moveTo(btn_x, btn_y, duration=0.5)
            pyautogui.click()
            return True

        elif cmd_type == "ICON":
            icon_name = parts[2] if len(parts) > 2 else ""
            if not icon_name:
                push_msg("❌ ICON 명령에 아이콘 이름이 없습니다.")
                return False
            # 5초 동안 버튼이 나타날 때까지 반복 탐색 (신뢰성 상승)
            found = click_icon(icon_name, confidence=0.8, timeout=5.0)
            if not found:
                push_msg(f"⚠️ 5초 동안 기다렸지만 '{icon_name}' 버튼을 찾지 못했습니다.")
            return found

        elif cmd_type == "ICON_TYPE":
            raw = ":".join(parts[2:]) if len(parts) > 2 else ""
            text = raw[:-2] if raw.endswith("__") else raw
            if not text:
                push_msg("❌ ICON_TYPE 명령에 텍스트가 없습니다.")
                return False
            push_msg(f"🔍 입력 타겟: '{text[:40]}'")
            return type_into_chatwindow(text)

    # 2. 일반 텍스트 입력 처리
    text = command
    if text.startswith("[📱MOBILE]"):
        text = text.replace("[📱MOBILE]", "").strip()

    # 📌 125% 배율 환경의 채팅 입력창 좌표
    click_x = int(l + w * 0.88) 
    click_y = int(t + h * 0.927)

    if DEBUG_IMAGE:
        try:
            shot = pyautogui.screenshot(region=(click_x-100, click_y-100, 200, 200))
            push_img(shot, f"📊 클릭 위치 디버그 ({click_x}, {click_y})")
        except: pass

    # 이동 및 포커스 확보를 위한 클릭
    pyautogui.moveTo(click_x, click_y, duration=0.3)
    pyautogui.click()
    time.sleep(0.1)
    pyautogui.click() 
    time.sleep(0.3)

    # 텍스트 입력 및 엔터
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("backspace")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    # 4. 전송 버튼(proceed) 클릭 시도 (또는 엔터)
    if not click_icon("proceed", confidence=0.8, timeout=3.0):
        pyautogui.press("enter")
        # push_msg("⚠️ 전송 버튼(→) 못 찾아서 Enter로 전송함") # 너무 잦은 알림 방지 원하시면 주석
    
    return True

def inbound_loop():
    print("🚀 [Inbound Thread] v3.4 시작")
    while True:
        try:
            box = read_mailbox()
            tasks = box.get("inbound", [])
            if tasks:
                box["inbound"] = []
                write_mailbox(box)
                for task in tasks: execute_brain_task(task)
        except Exception as e: print(f"Error: {e}")
        time.sleep(1)


# ── Auto Watcher ─────────────────────────────────────────────────────────────────

_auto_watch_active = False
_auto_watch_lock = threading.Lock()

# 감시할 아이콘 목록: (아이콘이름, 표시라벨, confidence)
# ⚠️ proceed는 비활성(grey) 상태를 무시하기 위해 confidence 매우 높게 설정
AUTO_ICONS = [
    ("accept_all",  "✅ Accept all",   0.8),
    ("proceed",     "➡️ Proceed",      0.95),
    ("run",         "▶️ Run",          0.8),
    ("scrolldown",  "🔽 Scroll Down",   0.8),
]

def find_color_buttons(img_pil):
    """auto_approver.py에서 가져온 색상 기반 버튼 감지 로직"""
    if ndimage is None: return []
    try:
        img = np.array(img_pil)
        R, G, B = img[:, :, 0], img[:, :, 1], img[:, :, 2]
        mask_blue = (B > 130) & (B > R * 1.5) & (B > G * 1.1)
        mask_green = (G > 130) & (G > R * 1.2)
        mask_combined = mask_blue | mask_green
        labeled, _ = ndimage.label(mask_combined)
        objects = ndimage.find_objects(labeled)
        buttons = []
        for i, slices in enumerate(objects):
            if slices is None: continue
            sy, sx = slices
            h, w = sy.stop - sy.start, sx.stop - sx.start
            area = np.sum(labeled[slices] == (i + 1))
            if w < 40 or h < 20 or w > 350 or h > 80: continue
            if area < 350 or (w/h) < 1.1 or (w/h) > 7.0: continue
            # Solidity 체크: 사각형 면적 대비 실제 색상이 60% 이상 채워져야 버튼으로 인정
            if area / (w * h) < 0.60: continue
            buttons.append({"x": sx.start + w // 2, "y": sy.start + h // 2})
        return buttons
    except Exception: return []

_ocr_reader = None
_ocr_lock = threading.Lock()

# 무시할 UI 텍스트 목록 (블랙리스트)
OCR_BLACKLIST = [
    "0 Files With Changes", "Review Changes", "Ask anything", "mention", 
    "workflows", "Fast", "Gemini 3 Flash", "Screen Reader Optimized", 
    "Antigravity - Settings", "Usage", "Thought for", "Open Agent Manager",
    "Running background command", "Relocate", "Cancel", "Good", "Bad", "Always run"
]

def clean_ocr_text(text):
    """OCR 엔진이 자주 틀리는 한국어/영어 패턴 지능형 교정 (데이터 기반)"""
    corrections = {
        "I니다": "합니다", "습I니다": "습니다", "I니": "하니", "I다": "하다",
        "인스템스": "인스턴스", "붓이": "봇이", "리모건": "리모컨", "캠처": "캡처",
        "전승": "전송", "kil": "kill", "인스템": "인스턴", "충들": "충돌",
        "성올": "성을", "중은": "좋은", "활성화면": "할 수 있게", "루프과부": "루프 과부",
        "하서도": "하셔도", "I니다!": "합니다!", "I니다.": "합니다.", "I니다?": "합니다?",
        "시I": "사용자", "시의": "사용자의", "입에서": "앱에서", "젊습니다": "졌습니다",
        "나p": "up", "로그록": "로그를", "리포트록": "리포트가", "Antigrav": "Antigravity",
        "Objec": "Object", "Intjg": "Antig", "lntegration": "Integration"
    }
    for wrong, right in corrections.items():
        text = text.replace(wrong, right)
    return text

def get_local_ocr(img_pil):
    """2.0x 정밀 스케일링 + 지능형 교정 기반의 최적화된 OCR"""
    global _ocr_reader
    try:
        import easyocr
        with _ocr_lock:
            if _ocr_reader is None:
                _ocr_reader = easyocr.Reader(['ko', 'en'])
        
        # 튜닝 결과(ocr_tuner.py)에 따라 2.0배 확대가 가장 신뢰도가 높음
        w, h = img_pil.size
        img_resized = img_pil.resize((int(w * 2.0), int(h * 2.0)), Image.Resampling.LANCZOS)
        img_np = np.array(img_resized.convert('L'))
        
        # OCR 판독
        results = _ocr_reader.readtext(img_np, detail=1, paragraph=False)
        
        if not results: return ""
        
        # 유효한 텍스트 필터링
        valid_blocks = []
        for (bbox, text, conf) in results:
            text = text.strip()
            if len(text) < 1 or conf < 0.20: continue
            
            if any(bl.lower() in text.lower() for bl in OCR_BLACKLIST): continue
            
            y_top = bbox[0][1]
            x_left = bbox[0][0]
            valid_blocks.append({'y': y_top, 'x': x_left, 'text': text})
            
        if not valid_blocks: return ""
        
        # 스마트 문장 병합 (2.0배 확대에 맞춰 임계값 30px로 상향)
        valid_blocks.sort(key=lambda b: b['y'])
        
        lines = []
        if valid_blocks:
            current_line = valid_blocks[0]['text']
            last_y = valid_blocks[0]['y']
            threshold = 30
            
            for i in range(1, len(valid_blocks)):
                block = valid_blocks[i]
                if block['y'] - last_y > threshold: 
                    lines.append(current_line)
                    current_line = block['text']
                else:
                    current_line += " " + block['text']
                last_y = block['y']
            lines.append(current_line)
        
        full_text = "\n".join(lines)
        corrected_text = clean_ocr_text(full_text)
        
        return f"📖 **Full Text OCR 전문 (AI 교정):**\n\n{corrected_text.strip()[:2000]}" 
    except Exception as e:
        return f"⚠️ OCR 오류 발생: {str(e)}"

get_gemini_ocr = get_local_ocr 

def send_chat_snapshot(caption="📊 [Auto] 변화 감지", include_ocr=True):
    """채팅 본문만 정밀 캡처 + 리모컨 인라인 버튼 전송 + 진단 정보 제공"""
    hwnd, rect, _ = get_vscode_window_rect()
    if not rect: return None
    l, t, r, b = rect
    w, h = r - l, b - t
    
    # 🎯 이미지 캡처 영역 정밀 조절
    # 1. 좌측 여백 건너뛰기: 오른쪽 35% 영역 중에서도 100px 더 오른쪽에서 시작 (사이드바/라인넘버 제거)
    chat_x = int(l + w * 0.65) + 100
    chat_w = int(w * 0.35) - 100
    
    # 2. 상하단 헤더/푸터 건너뛰기
    chat_y = t + 65 # 헤더 약 65px 무시
    chat_h = h - 65 - 200 # 하단 입력창/푸터 약 200px 무시 (더 강화)
    
    if chat_w <= 0 or chat_h <= 0: return

    try:
        shot = pyautogui.screenshot(region=(chat_x, chat_y, chat_w, chat_h))
        
        # [DEBUG 전 전용] 로컬에 캡처본 저장하여 확인 가능케 함
        debug_dir = os.path.join(os.getcwd(), ".debug")
        os.makedirs(debug_dir, exist_ok=True)
        debug_path = os.path.join(debug_dir, "last_capture.png")
        shot.save(debug_path)

        # OCR 처리 여부 선택
        ocr_text = None
        if include_ocr:
            ocr_text = get_gemini_ocr(shot)
        
        # 디버그 정보 추가 (캡처 영역 좌표)
        debug_info = ""
        if "DEBUG" in caption or "Manual" in caption:
            debug_info = f"\n📐 `X:{chat_x}, Y:{chat_y}, W:{chat_w}, H:{chat_h}`"
        
        photo_caption = f"{caption}{debug_info}"

        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "✅ Accept All", "callback_data": "btn_accept"},
                    {"text": "➡️ Proceed", "callback_data": "btn_proceed"}
                ],
                [
                    {"text": "▶️ Run", "callback_data": "btn_run"},
                    {"text": "🛑 Stop", "callback_data": "btn_stop_agent"}
                ],
                [
                    {"text": "📸 Refresh", "callback_data": "btn_chat_refresh"}
                ]
            ]
        }

        buf = BytesIO()
        shot.save(buf, format="PNG")
        buf.seek(0)
        
        # 1. 사진 전송 (기본 정보 + 버튼)
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", 
                      files={'photo': ( 'chat.png', buf, 'image/png')}, 
                      data={
                          'chat_id': int(CHAT_ID), 
                          'caption': photo_caption,
                          'reply_markup': json.dumps(reply_markup),
                          'parse_mode': 'Markdown'
                      }, 
                      timeout=15)
        
        # 2. OCR 리포트 별도 전송 (요청 시에만)
        if include_ocr and ocr_text and len(ocr_text.strip()) > 0:
            print(f"[*] Sending OCR report ({len(ocr_text)} chars)...")
            # MarkdownV2 대신 일반 Markdown을 쓰되, 특수문자 충돌 방지를 위해 실패 시 일반 텍스트로 재시도
            msg_res = requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        data={
                            'chat_id': int(CHAT_ID),
                            'text': ocr_text,
                            'parse_mode': 'Markdown'
                        }, timeout=15)
            
            if msg_res.status_code != 200:
                print(f"[!] Markdown OCR delivery failed ({msg_res.status_code}), retrying as plain text...")
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                            data={
                                'chat_id': int(CHAT_ID),
                                'text': ocr_text
                            }, timeout=15)
        else:
            print("[!] OCR text is empty, skipping message.")

        return shot
    except Exception as e: 
        print(f"Error in send_chat_snapshot: {e}")
        import traceback
        traceback.print_exc()
        return None

def auto_watcher_loop():
    """7초마다 감시, 변화 감지 시 즉시 스냅샷(버튼 포함) 전송"""
    global _auto_watch_active
    COOLDOWN = 5.0 
    last_click: dict = {}
    
    # 변화 감지용 변수
    prev_chat_thumb = None
    last_change_time = 0
    change_notified = True
    last_interval_snapshot = 0 # 1분 간격 스냅샷용

    while True:
        with _auto_watch_lock:
            active = _auto_watch_active
        if not active:
            time.sleep(1)
            continue

        hwnd, rect, _ = get_vscode_window_rect()
        if not rect:
            time.sleep(7)
            continue
        
        l, t, r, b = rect
        w, h = r - l, b - t

        # A. 아이콘 감시 (모양 인식)
        for icon_name, label, conf in AUTO_ICONS:
            icon_path = os.path.join(ICON_DIR, f"icon_{icon_name}.png")
            if not os.path.exists(icon_path): continue
            now = time.time()
            if now - last_click.get(icon_name, 0) < COOLDOWN: continue
            try:
                pos = pyautogui.locateCenterOnScreen(icon_path, confidence=conf)
                if pos:
                    pyautogui.moveTo(pos, duration=0.15)
                    pyautogui.click()
                    last_click[icon_name] = time.time()
                    push_msg(f"🤖 [Auto] {label} 자동 클릭")
                    time.sleep(0.3)
            except: pass

        # B. 스마트 변화 감지 (새 메시지 알림) - 상태 업데이트 및 감지만 수행
        curr_thumb = None
        try:
            # 윈도우의 우측 50% 영역 감시 (더 넓게 확보)
            chat_x, chat_w = int(l + w * 0.50), int(w * 0.50)
            current_chat = pyautogui.screenshot(region=(chat_x, t, chat_w, h))
            curr_thumb = np.array(current_chat.resize((50, 100)).convert('L'))
            
            if prev_chat_thumb is not None:
                diff = np.mean(np.abs(curr_thumb.astype(float) - prev_chat_thumb.astype(float)))
                # 민감도 향상 (1.5 -> 0.7)
                if diff > 0.7: 
                    last_change_time = time.time()
                    change_notified = False
                
                # 변화가 멈춘 지 3초가 지났고 아직 알림 전이라면 전송
                if not change_notified and (time.time() - last_change_time > 3.0):
                    send_chat_snapshot("🔔 [Auto] AI가 새로운 내용을 작성했습니다.")
                    change_notified = True
        except: pass

        # C. 색상 기반 승인 버튼 감지
        try:
            zone_l, zone_t = max(0, l + int(w*0.40)), max(0, t + 40)
            zone_w, zone_h = min(int(w*0.55), pyautogui.size()[0]-zone_l), min(h-100, pyautogui.size()[1]-zone_t)
            if zone_w > 0 and zone_h > 0:
                shot = pyautogui.screenshot(region=(zone_l, zone_t, zone_w, zone_h))
                c_btns = find_color_buttons(shot)
                if c_btns:
                    top_b = [btn for btn in c_btns if btn["y"] < zone_h * 0.35]
                    target = top_b[0] if top_b else sorted(c_btns, key=lambda b: b["y"], reverse=True)[0]
                    rx, ry = zone_l + target["x"], zone_t + target["y"]
                    pyautogui.moveTo(rx, ry, duration=0.15)
                    pyautogui.click()
                    push_msg("🤖 [Auto] 색상 감지 승인 버튼 클릭")
                    time.sleep(0.3)
        except: pass

        # D. 마우스 휠 스크롤 다운 (채팅 따라가기)
        try:
            sx, sy = int(l + w * 0.85), int(t + h * 0.5)
            pyautogui.moveTo(sx, sy)
            pyautogui.scroll(-50)
            # 스크롤 후 잠깐 대기하여 화면 안정화
            if not change_notified: time.sleep(0.2)
        except: pass

        # E. 다음 루프를 위한 베이스라인 갱신 (모든 액션 완료 후!!)
        try:
            # 액션(클릭, 스크롤) 후의 상태를 캡처해야 다음 루프에서 '순수한 변화'만 감지 가능
            chat_x, chat_w = int(l + w * 0.50), int(w * 0.50)
            after_action_chat = pyautogui.screenshot(region=(chat_x, t, chat_w, h))
            prev_chat_thumb = np.array(after_action_chat.resize((50, 100)).convert('L'))
        except: pass

        time.sleep(1) # 루프 과부하 방지

if __name__ == "__main__":
    threading.Thread(target=inbound_loop, daemon=True).start()
    threading.Thread(target=auto_watcher_loop, daemon=True).start()
    print("🤖 Auto Watcher (아이콘+색상) 스레드 대기 중 (/auto 명령으로 활성화)")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
