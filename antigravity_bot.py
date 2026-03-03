"""
antigravity_bot.py — Telegram 봇 메인 서버
Flask antigravity_host.py를 대체하며, 화면 캡처, 채팅창 캡처, 대화 로그 추출 기능을 포함합니다.
"""
import os
import json
import shutil
import time
import threading
import tempfile
import ctypes
import pyautogui
import re
import win32gui
import win32con

from io import BytesIO
from dotenv import load_dotenv

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# 🛠️ DPI Awareness (125% 배율 등에서 화면 캡처 시 오차 방지)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAILBOX_PATH = os.path.join(BASE_DIR, "mailbox.json")


# ── 공유 mailbox 유틸 ────────────────────────────────────────────────────────

def read_mailbox() -> dict:
    try:
        with open(MAILBOX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"inbound": [], "outbound": [], "approval_request": None}


def write_mailbox(box: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=BASE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(box, f, ensure_ascii=False, indent=2)
    os.replace(tmp, MAILBOX_PATH)


def push_inbound(message: str) -> None:
    box = read_mailbox()
    box["inbound"].append(message)
    write_mailbox(box)


# ── VS Code 유틸 ────────────────────────────────────────────────────────────

def get_vscode_window_rect():
    found = []
    def callback(hwnd, res):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            if class_name == "Chrome_WidgetWin_1" and any(x in title for x in ["Visual Studio Code", "Antigravity", "OpenClaw"]):
                if not any(title.endswith(x) for x in [" - Chrome", " - Microsoft Edge"]):
                    res.append((hwnd, title))
        return True
    
    win32gui.EnumWindows(callback, found)
    if not found: return None, None, None
    hwnd, title = found[0]
    
    placement = win32gui.GetWindowPlacement(hwnd)
    if placement[1] == win32con.SW_SHOWMINIMIZED: 
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    else: 
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        
    try: win32gui.SetForegroundWindow(hwnd)
    except: pass
    time.sleep(0.5)
    
    rect = win32gui.GetWindowRect(hwnd)
    return hwnd, rect, title


# ── Antigravity 내용 추출 유틸 ──────────────────────────────────────────────

def get_latest_conversation_dir():
    brain_dir = os.path.expanduser(r"~\.gemini\antigravity\brain")
    if not os.path.exists(brain_dir): return None
    dirs = [os.path.join(brain_dir, d) for d in os.listdir(brain_dir) if os.path.isdir(os.path.join(brain_dir, d))]
    return max(dirs, key=os.path.getmtime) if dirs else None

def extract_latest_history():
    conv_dir = get_latest_conversation_dir()
    if not conv_dir: return ["대화 기록(brain) 폴더를 찾을 수 없습니다."]
    
    # task.md.resolved.* 파일들 찾기
    files = [f for f in os.listdir(conv_dir) if f.startswith("task.md.resolved")]
    if not files: return ["최근 대화 텍스트가 없습니다."]
    
    # 끝의 숫자 확장자 기준으로 정렬
    def sort_key(f):
        parts = f.split('.')
        try: return int(parts[-1])
        except: return -1
    files.sort(key=sort_key)
    
    history_entries = []
    
    for f in files:
        file_path = os.path.join(conv_dir, f)
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
                
            pieces = content.split("Step Id:")
            for p in pieces:
                p = p.strip()
                if not p: continue
                # 간단한 클리닝
                p = re.sub(r'<ADDITIONAL_METADATA>.*?</ADDITIONAL_METADATA>', '', p, flags=re.DOTALL)
                p = p.replace("<USER_REQUEST>", "👤 **USER**:").replace("</USER_REQUEST>", "")
                history_entries.append(p.strip()[:1000]) # 하나의 엔트리는 최대 1000자
                
        except Exception as e:
            pass
            
    if not history_entries: return ["대화를 추출하지 못했습니다."]
    return history_entries


# ── 인증 헬퍼 ────────────────────────────────────────────────────────────────

async def authorized(update: Update) -> bool:
    if update.effective_chat.id != CHAT_ID:
        await update.message.reply_text("❌ 권한 없음: 허가되지 않은 사용자입니다.")
        return False
    return True


# ── Telegram 핸들러 ─────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    await update.message.reply_text(
        "✅ **Antigravity V3.3 원격 제어 가동 중**\n\n"
        "🔎 **모니터링**\n"
        "  /chat — 채팅창 줌인 캡처\n"
        "  /history — 최근 대화 로그 추출\n"
        "  /screenshot — 전체 화면 캡처\n\n"
        "🔖 **아이콘 매크로 (이미지 기반)**\n"
        "  /accept — Accept all (코드 수용)\n"
        "  /proceed — → 버튼 (Agent 실행)\n"
        "  /run — Run Alt+↵ (터미널 실행)\n"
        "  /stop_agent — ■ 정지 (Agent 중단)\n"
        "  /type <텍스트> — Review Changes 에 입력 & 전송\n\n"
        "🎮 **좌표/스크롤 매크로**\n"
        "  /su /sd — 위/아래 스크롤\n"
        "  /runonce / /runall — 실행 버튼 (좌표 기반)\n"
        "  /click x y — 특정 좌표 클릭\n\n"
        "📊 **기타**\n"
        "  /status — 통신 상태 확인\n"
        "  /stop — 긴급 중지"
    )

async def cmd_accept(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:ICON:accept_all__")
    await update.message.reply_text("✅ Accept all 클릭 지시")

async def cmd_proceed(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:ICON:proceed__")
    await update.message.reply_text("➡️ → (Agent 실행) 클릭 지시")

async def cmd_run_terminal(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:ICON:run__")
    await update.message.reply_text("▶️ Run Alt+↵ (터미널 실행) 클릭 지시")

async def cmd_stop_agent(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:ICON:stop__")
    await update.message.reply_text("⏹️ Agent 정지 클릭 지시")

async def cmd_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    if not ctx.args:
        await update.message.reply_text("사용법: /type <입력할 텍스트>")
        return
    text = " ".join(ctx.args)
    push_inbound(f"__COMMAND:ICON_TYPE:{text}__")
    preview = text[:50] + "..." if len(text) > 50 else text
    await update.message.reply_text(f"✍️ Review Changes 에 입력 지시: {preview}")

async def cmd_scrolldown(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:ICON:scrolldown__")
    await update.message.reply_text("🔽 스크롤다운 아이콘 클릭 지시")

async def cmd_auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:AUTO_WATCH_ON__")
    await update.message.reply_text(
        "🤖 **Auto Watch 시작!**\n"
        "7초마다 다음 아이콘을 감시합니다:\n"
        "✅ Accept all | ➡️ Proceed | ▶️ Run | 🔽 Scroll Down\n"
        "/autooff 로 중단할 수 있습니다."
    )

async def cmd_autooff(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:AUTO_WATCH_OFF__")
    await update.message.reply_text("⏹️ Auto Watch 중단 지시")

async def cmd_su(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:SCROLL:UP__")
    await update.message.reply_text("🔼 위로 스크롤 지시")

async def cmd_sd(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:SCROLL:DOWN__")
    await update.message.reply_text("🔽 아래로 스크롤 지시")

async def cmd_runonce(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:CLICK_RUN_ONCE__")
    await update.message.reply_text("▶️ 'Run Once' 클릭 시도")

async def cmd_runall(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    push_inbound("__COMMAND:CLICK_RUN_ALL__")
    await update.message.reply_text("⏩ 'Run All' 클릭 시도")

async def cmd_click_manual(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text("사용법: /click x y (예: /click 2000 1000)")
        return
    x, y = ctx.args[0], ctx.args[1]
    push_inbound(f"__COMMAND:CLICK:{x}:{y}__")
    await update.message.reply_text(f"🎯 좌표 ({x}, {y}) 클릭 지시")

async def cmd_screenshot(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
# ... (rest of the file handles follow)
    if not await authorized(update): return
    await update.message.reply_text("📸 전체 화면 캡처 중...")
    try:
        img = pyautogui.screenshot()
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        await update.message.reply_photo(buf, caption="전체 화면")
    except Exception as e:
        await update.message.reply_text(f"❌ 스크린샷 실패: {e}")

async def cmd_ss(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """채팅창 본문 정밀 캡처 (OCR 제외)"""
    if not await authorized(update): return
    await update.message.reply_text("📸 채팅창 본문 정밀 캡처 중...")
    try:
        from agent_brain import send_chat_snapshot
        send_chat_snapshot("📸 [Manual] 채팅창 스냅샷", include_ocr=False)
    except Exception as e:
        await update.message.reply_text(f"❌ 캡처 실패: {e}")

async def cmd_ocr(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """채팅창 본문 정밀 캡처 + OCR 리포트"""
    if not await authorized(update): return
    await update.message.reply_text("📖 채팅창 OCR 분석 중...")
    try:
        from agent_brain import send_chat_snapshot
        send_chat_snapshot("📸 [Manual] 채팅창 OCR 리포트", include_ocr=True)
    except Exception as e:
        await update.message.reply_text(f"❌ 분석 실패: {e}")

async def cmd_debug(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """OCR 및 캡처 영역 정밀 진단"""
    if not await authorized(update): return
    await update.message.reply_text("🔎 시스템 정밀 진단 중 (캡처영역 + OCR)...")
    try:
        from agent_brain import send_chat_snapshot
        # 'DEBUG' 문자열을 포함하여 호출 (좌표 정보 출력됨)
        send_chat_snapshot("🧪 [DEBUG] 시스템 진단 리포트")
    except Exception as e:
        await update.message.reply_text(f"❌ 진단 실패: {e}")

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    await update.message.reply_text("📖 최근 대화 내용 추출 중...")
    
    # Run in a separate thread to prevent blocking
    history = extract_latest_history()
    recent_history = history[-25:] # Last 25 entries
    
    text = "\n\n---\n".join(recent_history)
    if len(text) > 4000:
        text = text[-4000:]
        
    await update.message.reply_text(f"📝 **최근 대화 로그**\n\n{text}", parse_mode=None)

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    box = read_mailbox()
    box["approval_request"] = "__EMERGENCY_STOP__"
    write_mailbox(box)
    await update.message.reply_text("🛑 긴급 중지 신호를 전송했습니다.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    box = read_mailbox()
    status = (
        f"📊 **시스템 상태**\n"
        f"  Inbound 대기: {len(box.get('inbound', []))}개\n"
        f"  Outbound 대기: {len(box.get('outbound', []))}개\n"
        f"  승인 요청: {'있음 ⚠️' if box.get('approval_request') else '없음 ✅'}"
    )
    await update.message.reply_text(status, parse_mode="Markdown")

# async def on_callback_query(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
#     """인라인 버튼 클릭 처리"""
#     query = update.callback_query
#     await query.answer() # 시계 아이콘 제거
#     
#     data = query.data
#     if data == "btn_accept":
#         push_inbound("__COMMAND:ICON:accept_all__")
#         await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ Accept All 지시 완료")
#     elif data == "btn_proceed":
#         push_inbound("__COMMAND:ICON:proceed__")
#         await query.edit_message_caption(caption=f"{query.message.caption}\n\n➡️ Proceed 지시 완료")
#     elif data == "btn_run":
#         push_inbound("__COMMAND:ICON:run__")
#         await query.edit_message_caption(caption=f"{query.message.caption}\n\n▶️ Run 지시 완료")
#     elif data == "btn_stop_agent":
#         push_inbound("__COMMAND:ICON:stop__")
#         await query.edit_message_caption(caption=f"{query.message.caption}\n\n🛑 Stop 지시 완료")
#     elif data == "btn_chat_refresh":
#         push_inbound("__COMMAND:ICON:chat_refresh_trigger__") # 임시 트리거
#         # cmd_chat 로직을 직접 실행하거나 inbound로 요청
#         from agent_brain import send_chat_snapshot
#         send_chat_snapshot("📸 [Manual] 채팅창 새로고침")

async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not await authorized(update): return
    text = update.message.text or ""
    tagged = f"[📱MOBILE] {text}"
    push_inbound(tagged)
    await update.message.reply_text("📨 Antigravity에 전달됨")


# ── outbound 감시 스레드 ─────────────────────────────────────────────────────

def outbound_watcher(bot_token: str, chat_id: int) -> None:
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    print("🚀 [Outbound Watcher] 시작 - AI 답장을 감시합니다.")
    while True:
        try:
            box = read_mailbox()
            messages = box.get("outbound", [])
            if messages:
                box["outbound"] = []
                write_mailbox(box)
                for msg in messages:
                    try: requests.post(url, json={"chat_id": chat_id, "text": msg}, timeout=10)
                    except: pass
        except: pass
        time.sleep(0.5)


# ── 메인 진입점 ─────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        print("❌ .env 파일에 TELEGRAM_BOT_TOKEN을 입력하세요.")
        return
    if CHAT_ID == 0:
        print("❌ .env 파일에 TELEGRAM_CHAT_ID를 입력하세요.")
        return

    if not os.path.exists(MAILBOX_PATH):
        write_mailbox({"inbound": [], "outbound": [], "approval_request": None})

    watcher = threading.Thread(target=outbound_watcher, args=(BOT_TOKEN, CHAT_ID), daemon=True)
    watcher.start()

    async def post_init(application):
        commands = [
            BotCommand("auto", "🤖 자동 승인 시작"),
            BotCommand("autooff", "⏹️ 자동 승인 중단"),
            BotCommand("ss", "📸 채팅창 본문 정밀 캡처"),
            BotCommand("ocr", "📖 채팅창 본문 정밀 캡처 + OCR"),
            BotCommand("debug", "🔎 OCR/캡처 영역 정밀 진단"),
            BotCommand("type", "✍️ 텍스트 입력 및 전송 (사용법: /type 메시지)"),
            BotCommand("accept", "✅ Accept All 클릭"),
            BotCommand("proceed", "➡️ Proceed 클릭"),
            BotCommand("run", "▶️ Terminal Run 클릭"),
            BotCommand("stop_agent", "🛑 에이전트 중지 클릭"),
            BotCommand("scrolldown", "🔽 하단 화살표 클릭"),
            BotCommand("screenshot", "🖥️ 전체 화면 캡처"),
            BotCommand("history", "📖 최근 대화 로그 추출"),
            BotCommand("status", "📊 시스템 상태 체크"),
            BotCommand("stop", "🚨 긴급 중지 (Durable Object)"),
        ]
        await application.bot.set_my_commands(commands)

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    app.add_handler(CommandHandler("ss", cmd_ss)) 
    app.add_handler(CommandHandler("ocr", cmd_ocr))
    app.add_handler(CommandHandler("debug", cmd_debug))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("su", cmd_su))
    app.add_handler(CommandHandler("sd", cmd_sd))
    app.add_handler(CommandHandler("runonce", cmd_runonce))
    app.add_handler(CommandHandler("runall", cmd_runall))
    app.add_handler(CommandHandler("click", cmd_click_manual))
    # 이미지 기반 아이콘 명령어
    app.add_handler(CommandHandler("accept", cmd_accept))
    app.add_handler(CommandHandler("proceed", cmd_proceed))
    app.add_handler(CommandHandler("run", cmd_run_terminal))
    app.add_handler(CommandHandler("stop_agent", cmd_stop_agent))
    app.add_handler(CommandHandler("type", cmd_type))
    app.add_handler(CommandHandler("scrolldown", cmd_scrolldown))
    app.add_handler(CommandHandler("auto", cmd_auto))
    app.add_handler(CommandHandler("autooff", cmd_autooff))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))
    # app.add_handler(CallbackQueryHandler(on_callback_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("✅ Antigravity Telegram 봇 V3 작동 시작...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
