"""
agent_brain.py — 브릿지 에이전트 (v3.3)
- 125% DPI 배율 및 마우스 좌표 최종 보정 완료
- DEBUG_IMAGE 토글 추가 (기본 False)
- 이미지 기반 버튼 클릭 지원 (icon_*.png)
"""
import os, json, time, threading, tempfile, ctypes, requests
import pyautogui, pyperclip, win32gui, win32con
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

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
    """Review Changes 창의 입력창을 찾아 텍스트를 입력하고 → 버튼(proceed)을 클릭합니다."""
    # 1. chatwindow 패널 감지 (패널 중앙 어딘가 클릭 – 포커스 확보)
    icon_path = os.path.join(ICON_DIR, "icon_chatwindow.png")
    try:
        panel_pos = pyautogui.locateCenterOnScreen(icon_path, confidence=0.75)
    except Exception:
        panel_pos = None

    if panel_pos:
        # 패널보다 조금 아래(입력창 영역) 클릭
        pyautogui.moveTo(panel_pos.x, panel_pos.y + 80, duration=0.2)
        pyautogui.click()
    else:
        push_msg("⚠️ Review Changes 창을 찾지 못했습니다. 창이 열려 있는지 확인하세요.")
        return False

    time.sleep(0.3)

    # 2. 텍스트 입력
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)

    # 3. → (proceed) 버튼 클릭
    if not click_icon("proceed", confidence=0.8):
        push_msg("⚠️ → 버튼을 찾지 못했습니다. 수동으로 전송해 주세요.")
        return False

    return True


def execute_brain_task(command: str) -> bool:
    hwnd, rect, title = get_vscode_window_rect()
    if not rect:
        push_msg("❌ VS Code 창을 찾을 수 없습니다.")
        return False

    l, t, r, b = rect
    w, h = r - l, b - t

    # 1. 시스템 명령어 처리 (매크로)
    if command.startswith("__COMMAND:"):
        parts = command.split(":")
        cmd_type = parts[1]
        
        if cmd_type == "SCROLL":
            direction = parts[2]
            # 채팅창 위치로 이동 후 스크롤
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
            # 125% 배율 기준 'Run Once' 버튼 추정 위치 (보통 입력창 위쪽)
            btn_x = int(l + w * 0.78) 
            btn_y = int(t + h * 0.88)
            pyautogui.moveTo(btn_x, btn_y, duration=0.5)
            pyautogui.click()
            return True

        elif cmd_type == "CLICK_RUN_ALL":
            # 125% 배율 기준 'Run All' 버튼 추정 위치
            btn_x = int(l + w * 0.85) 
            btn_y = int(t + h * 0.88)
            pyautogui.moveTo(btn_x, btn_y, duration=0.5)
            pyautogui.click()
            return True

        elif cmd_type == "ICON":
            # 이미지 기반 버튼 클릭
            icon_name = parts[2] if len(parts) > 2 else ""
            if not icon_name:
                push_msg("❌ ICON 명령에 아이콘 이름이 없습니다.")
                return False
            found = click_icon(icon_name, confidence=0.8)
            if not found:
                push_msg(f"⚠️ 화면에서 '{icon_name}' 버튼을 찾지 못했습니다.")
            return found

        elif cmd_type == "ICON_TYPE":
            # Review Changes 창 입력 (나머지 parts를 text로 재조합)
            text = ":".join(parts[2:]) if len(parts) > 2 else ""
            if not text:
                push_msg("❌ ICON_TYPE 명령에 텍스트가 없습니다.")
                return False
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
    pyautogui.press("enter")
    return True

def inbound_loop():
    print("🚀 [Inbound Thread] v2.6 정식판 시작")
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

if __name__ == "__main__":
    t = threading.Thread(target=inbound_loop, daemon=True)
    t.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: pass
