"""
auto_approver.py — VS Code 자동 승인 시스템
VS Code 창을 감시하여 승인 버튼(파란색/초록색)이 나타나면 자동으로 클릭합니다.
"""
import time
import pyautogui
import win32gui
import sys
import traceback

try:
    from scipy import ndimage
except ImportError:
    ndimage = None

from PIL import Image
import numpy as np

CHECK_INTERVAL = 0.5   # 탐색 주기 (초)
COOLDOWN = 1.0          # 클릭 후 대기 (초)
pyautogui.FAILSAFE = False

print("🚀 [Antigravity 오토 어프로버] 시작됨")
if ndimage is None:
    print("   ⚠️  scipy 미설치 — 버튼 감지가 제한될 수 있습니다.")
    print("       pip install scipy 권장\n")
else:
    print("   ✅  scipy 연결됨 (정밀 탐색 모드)\n")
print("   VS Code 창을 감시합니다. 버튼이 뜨면 자동 클릭합니다.")
print("   종료: Ctrl+C\n")


def get_vscode_window():
    windows = []

    def callback(hwnd, res):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        if class_name == "Chrome_WidgetWin_1" and any(
            x in title.lower() for x in ["visual studio code", "antigravity", "openclaw"]
        ):
            res.append((hwnd, title))
        return True

    win32gui.EnumWindows(callback, windows)
    if not windows:
        return None, None, None

    hwnd, title = windows[0]
    try:
        rect = win32gui.GetWindowRect(hwnd)
        return hwnd, rect, title
    except Exception:
        return None, None, None


def is_point_in_vscode(x, y, target_hwnd):
    try:
        found = win32gui.WindowFromPoint((int(x), int(y)))
        curr = found
        while curr:
            if curr == target_hwnd:
                return True
            curr = win32gui.GetParent(curr)
        return False
    except Exception:
        return False


def find_buttons(img_pil):
    if ndimage is None:
        return []
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
            if slices is None:
                continue
            sy, sx = slices
            h, w = sy.stop - sy.start, sx.stop - sx.start
            area = np.sum(labeled[slices] == (i + 1))
            if w < 40 or h < 20:
                continue
            if w > 350 or h > 80:
                continue
            if area < 350:
                continue
            ratio = w / h
            if ratio < 1.1 or ratio > 7.0:
                continue
            if area / (w * h) < 0.50:
                continue
            buttons.append({"x": sx.start + w // 2, "y": sy.start + h // 2, "w": w, "h": h})
        return buttons
    except Exception:
        return []


def run_loop():
    hwnd, rect, title = get_vscode_window()
    if not hwnd:
        return False

    wl, wt, wr, wb = rect
    ww, wh = wr - wl, wb - wt
    if ww <= 0 or wh <= 0:
        return False

    exclude_top = 32
    exclude_bottom = 60

    zone_l = wl + int(ww * 0.15)
    zone_t = wt + exclude_top
    zone_w = int(ww * 0.80)
    zone_h = wb - zone_t - exclude_bottom

    zone_l = max(0, zone_l)
    zone_t = max(0, zone_t)
    zone_w = min(zone_w, pyautogui.size()[0] - zone_l)
    zone_h = min(zone_h, pyautogui.size()[1] - zone_t)

    if zone_w <= 0 or zone_h <= 0:
        return False

    img = pyautogui.screenshot(region=(zone_l, zone_t, zone_w, zone_h))
    buttons = find_buttons(img)

    if not buttons:
        return False

    # 상단 35% 버튼 우선 (Run/Allow 글로벌 프롬프트)
    top_buttons = [b for b in buttons if b["y"] < zone_h * 0.35]
    if top_buttons:
        top_buttons.sort(key=lambda b: b["y"])
        btn = top_buttons[0]
    else:
        buttons.sort(key=lambda b: b["y"], reverse=True)
        btn = buttons[0]

    rx, ry = zone_l + btn["x"], zone_t + btn["y"]

    if is_point_in_vscode(rx, ry, hwnd):
        print(f"[{time.strftime('%H:%M:%S')}] 📋 버튼 탐지 및 클릭: ({rx}, {ry})")
        if win32gui.GetForegroundWindow() != hwnd:
            try:
                win32gui.SetForegroundWindow(hwnd)
                time.sleep(0.05)
            except Exception:
                pass
        pyautogui.click(rx, ry)
        time.sleep(0.1)
        return True
    return False


if __name__ == "__main__":
    last_click = 0
    try:
        while True:
            now = time.time()
            if now - last_click >= COOLDOWN:
                if run_loop():
                    last_click = time.time()
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        print("\n👋 종료됨")
    except Exception as e:
        print(f"\n🛑 치명적 오류: {e}")
        traceback.print_exc()
        input("\n계속하려면 엔터를 누르세요...")
