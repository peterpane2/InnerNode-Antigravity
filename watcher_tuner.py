import os
import sys
import time
import numpy as np
import pyautogui
from PIL import Image

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent_brain import get_vscode_window_rect

def run_watcher_tuner():
    print("🔬 [Watcher Tuner] 변화 감지 알고리즘 진단 시작...")
    print("이 도구는 현재 채팅 영역의 변화값(diff)을 실시간으로 추적합니다.")
    print("AI가 답변 중일 때와 멈췄을 때의 값 차이를 확인해보세요.\n")
    
    prev_thumb = None
    
    # 디버그용 디렉토리
    if not os.path.exists(".debug"): os.makedirs(".debug")

    try:
        while True:
            try:
                hwnd, rect, _ = get_vscode_window_rect()
                if not rect:
                    print(f"[{time.strftime('%H:%M:%S')}] ⚠️ VS Code 창 미감지... 대기 중", end="\r")
                    time.sleep(2)
                    continue
                
                l, t, r, b = rect
                w, h = r - l, b - t
                
                # 1. 채팅 영역 정의 (agent_brain과 동일: 우측 50%)
                chat_x, chat_w = int(l + w * 0.50), int(w * 0.50)
                
                # 2. 캡처 및 썸네일 생성
                current_chat = pyautogui.screenshot(region=(chat_x, t, chat_w, h))
                curr_thumb = np.array(current_chat.resize((50, 100)).convert('L'))
                
                status = "STABLE"
                diff = 0.0
                
                if prev_thumb is not None:
                    diff = np.mean(np.abs(curr_thumb.astype(float) - prev_thumb.astype(float)))
                    
                    # 민감도 (0.7)
                    if diff > 0.7:
                        status = "✨ CHANGING"
                        current_chat.resize((200, 400)).save(".debug/watcher_diff_detect.png")
                    
                    print(f"[{time.strftime('%H:%M:%S')}] Diff: {diff:6.2f} | Status: {status}    ", end="\r")
                
                # 3. 베이스라인 갱신 (agent_brain의 새로운 로직 반영)
                # 여기서는 액션이 없지만, 구조를 맞춤
                prev_thumb = curr_thumb
                time.sleep(1)
            except Exception as loop_e:
                print(f"\n❌ 루프 에러: {loop_e}")
                time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n✅ 진단 종료.")

if __name__ == "__main__":
    run_watcher_tuner()
