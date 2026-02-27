# 🏁 Stage 3: 지능형 자동 승인 시스템 - 오토 어프로버(Sentinel)

### 🎯 이번 단계의 목표
AI가 작업할 때 뜨는 "Run", "Accept", "Allow" 버튼을 자동으로 찾아 클릭하는 `auto_approver.py`를 구축합니다.

---

### ⚠️ AI에게 전달할 핵심 지시

> **아래 코드를 그대로 사용하세요. scipy import는 반드시 try/except로 감싸야 합니다. 직접 import하면 scipy가 없을 때 즉시 크래시합니다.**

---

### 🛠️ 기술 사양 (AI 구현 가이드)

#### ⚠️ 필수 환경 설정 (코딩 전에 먼저 확인!)
*   **DPI 배율**: 윈도우 설정 → 디스플레이 → **"텍스트 및 앱 크기" 반드시 100%**. 이것이 아니면 좌표 계산이 어긋남.
*   **VS Code 테마**: **Dark Modern 또는 Dark+** 테마 사용 (버튼 색상 인식용).
*   **관리자 권한**: 스크립트를 관리자 권한으로 실행해야 VS Code 위에 클릭 가능.

#### `auto_approver.py` 전체 코드
아래 코드를 **변경 없이 그대로** 저장하세요:

```python
import time
import pyautogui
import win32gui
import win32con
import numpy as np
import sys, os, traceback
from PIL import Image

# ⚠️ 핵심: scipy는 선택적 의존성! try/except 필수!
# "import scipy.ndimage as ndimage"를 직접 쓰면 scipy 없을 때 크래시
try:
    from scipy import ndimage
except ImportError:
    ndimage = None

# --- 설정 ---
CHECK_INTERVAL = 0.5  # 탐색 주기 (초)
COOLDOWN = 1.0        # 클릭 후 대기 (초)
pyautogui.FAILSAFE = False  # 마우스가 구석에 가도 중지 안 됨

print("🚀 [Antigravity 오토 어프로버] 시작됨")
if ndimage is None:
    print("   ⚠️  scipy 미설치 (pip install scipy 권장)")
    print("       정밀 탐색 불가, 버튼 감지가 안 될 수 있습니다.\n")
else:
    print("   ✅  scipy 연결됨 (정밀 탐색 모드 활성화)\n")
print("   - VS Code 창을 감시합니다. 버튼이 뜨면 자동 클릭합니다.")
print("   - 종료: Ctrl+C\n")


def get_vscode_window():
    """VS Code 핸들과 위치 반환"""
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            # ⚠️ Chrome_WidgetWin_1 클래스 필터 + 소문자 비교
            if class_name == "Chrome_WidgetWin_1" and any(
                x in title.lower() for x in ["visual studio code", "antigravity", "openclaw"]
            ):
                windows.append((hwnd, title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    if not windows: return None, None, None

    hwnd, title = windows[0]
    try:
        rect = win32gui.GetWindowRect(hwnd)
        return hwnd, rect, title
    except Exception:
        return None, None, None


def is_point_in_vscode(x, y, target_hwnd):
    """클릭할 좌표가 진짜 VS Code 위인지 확인 (다른 앱 오클릭 방지)"""
    try:
        found_hwnd = win32gui.WindowFromPoint((int(x), int(y)))
        curr = found_hwnd
        while curr:
            if curr == target_hwnd: return True
            curr = win32gui.GetParent(curr)
        return False
    except: return False


def find_buttons(img_pil):
    """이미지에서 버튼 색상의 오브젝트를 탐지"""
    if ndimage is None: return []  # scipy 없으면 빈 리스트 (크래시 방지)
    try:
        img = np.array(img_pil)
        R, G, B = img[:,:,0], img[:,:,1], img[:,:,2]

        # VS Code 다크 테마 버튼 색상 필터 (보라색 제외를 위해 R값 억제)
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

            if w < 40 or h < 20: continue     # 너무 작음
            if w > 350 or h > 80: continue     # 너무 큼
            if area < 350: continue             # 면적 부족

            ratio = w / h
            if ratio < 1.1 or ratio > 7.0: continue   # 버튼 비율 아님
            if area / (w * h) < 0.50: continue         # 채움률 부족

            buttons.append({
                'x': sx.start + w // 2,
                'y': sy.start + h // 2,
                'w': w, 'h': h
            })
        return buttons
    except Exception:
        return []


def run_loop():
    """한 번의 탐색-클릭 사이클"""
    try:
        hwnd, rect, title = get_vscode_window()
        if not hwnd: return

        wl, wt, wr, wb = rect
        ww, wh = wr - wl, wb - wt
        if ww <= 0 or wh <= 0: return

        # 탐색 영역: 타이틀바(32px)와 상태바(60px) 제외, 사이드바(15%) 제외
        exclude_top = 32
        exclude_bottom = 60

        zone_l = wl + int(ww * 0.15)
        zone_t = wt + exclude_top
        zone_w = int(ww * 0.80)
        zone_h = wb - zone_t - exclude_bottom

        zone_l, zone_t = max(0, zone_l), max(0, zone_t)
        zone_w = min(zone_w, pyautogui.size()[0] - zone_l)
        zone_h = min(zone_h, pyautogui.size()[1] - zone_t)
        if zone_w <= 0 or zone_h <= 0: return

        img = pyautogui.screenshot(region=(zone_l, zone_t, zone_w, zone_h))
        buttons = find_buttons(img)

        if buttons:
            # 우선순위: 상단 35% → 글로벌 프롬프트(Run/Allow) 먼저
            top_buttons = [b for b in buttons if b['y'] < zone_h * 0.35]
            if top_buttons:
                top_buttons.sort(key=lambda b: b['y'])
                btn = top_buttons[0]
            else:
                buttons.sort(key=lambda b: b['y'], reverse=True)
                btn = buttons[0]

            rx, ry = zone_l + btn['x'], zone_t + btn['y']

            # ⚠️ 클릭 전 VS Code 위인지 확인!
            if is_point_in_vscode(rx, ry, hwnd):
                print(f"[{time.strftime('%H:%M:%S')}] 📋 버튼 탐지 및 클릭: ({rx}, {ry})")

                if win32gui.GetForegroundWindow() != hwnd:
                    try:
                        win32gui.SetForegroundWindow(hwnd)
                        time.sleep(0.05)
                    except: pass

                pyautogui.click(rx, ry)
                time.sleep(0.1)
                return True
    except Exception as e:
        print(f"\n❌ ERR: {e}")
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
    except Exception as major_e:
        print(f"\n🛑 치명적 오류: {major_e}")
        traceback.print_exc()
        input("\n계속하려면 엔터를 누르세요...")
```

### 🔑 핵심 포인트 요약

| 항목 | 올바른 코드 | 잘못된 코드 (에러 발생) |
|------|------------|----------------------|
| scipy import | `try: from scipy import ndimage` | `import scipy.ndimage as ndimage` |
| 창 필터 | `class_name == "Chrome_WidgetWin_1"` | 타이틀만 체크 (다른 앱 오감지) |
| 클릭 안전 | `is_point_in_vscode()` 확인 후 클릭 | 바로 클릭 (다른 앱 위 오클릭) |
| FAILSAFE | `pyautogui.FAILSAFE = False` | 기본값 True (마우스 구석이면 크래시) |

---

### ✅ 성공 체크리스트
- [ ] `pip install numpy scipy Pillow` 설치 완료.
- [ ] scipy가 **없어도** 에러 없이 실행되는가?
- [ ] VS Code 버튼이 뜨면 자동으로 클릭되는가?
- [ ] 터미널에 "버튼 탐지 및 클릭" 로그가 출력되는가?
- [ ] 크롬 브라우저 등 다른 앱은 잘못 클릭하지 않는가?
