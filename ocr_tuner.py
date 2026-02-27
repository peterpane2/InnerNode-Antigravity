import os
import sys
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import easyocr
import cv2

# 프로젝트 경로 추가 (agent_brain 임포트용)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent_brain import get_vscode_window_rect, clean_ocr_text, OCR_BLACKLIST

def run_ocr_tuning():
    print("🧪 [OCR Tuner] 시스템 시작...")
    
    # 1. 윈도우 찾기 및 캡처
    hwnd, rect, _ = get_vscode_window_rect()
    if not rect:
        print("❌ VS Code 창을 찾을 수 없습니다.")
        return

    l, t, r, b = rect
    w, h = r - l, b - t
    
    # agent_brain과 동일한 크롭 로직 적용
    # h_crop: 헤더(65), 하단(200), l_crop: 왼쪽(100)
    chat_x, chat_y = l + 100, t + 65
    chat_w, chat_h = w - 100, h - 65 - 200
    
    print(f"📸 캡처 영역: X={chat_x}, Y={chat_y}, W={chat_w}, H={chat_h}")
    import pyautogui
    img_pil = pyautogui.screenshot(region=(chat_x, chat_y, chat_w, chat_h))
    
    # 디버그용 원본 저장
    if not os.path.exists(".debug"): os.makedirs(".debug")
    img_pil.save(".debug/tuner_target.png")
    
    # 2. OCR 엔진 초기화
    print("[*] EasyOCR 로드 중...")
    reader = easyocr.Reader(['ko', 'en'])
    
    # 3. 테스트 파라미터 조합 설정
    # (scale, binarize, contrast)
    tests = [
        {"scale": 1.0, "binarize": False, "desc": "Original"},
        {"scale": 1.5, "binarize": False, "desc": "1.5x Scaling"},
        {"scale": 1.5, "binarize": True, "desc": "1.5x + Adaptive Binarization"},
        {"scale": 2.0, "binarize": False, "desc": "2.0x Scaling"}
    ]
    
    results_summary = []

    for test in tests:
        scale = test["scale"]
        do_bin = test["binarize"]
        desc = test["desc"]
        
        print(f"\n--- 🧪 Test: {desc} ---")
        
        # 전처리
        w_new, h_new = int(chat_w * scale), int(chat_h * scale)
        img_work = img_pil.resize((w_new, h_new), Image.Resampling.LANCZOS)
        
        if do_bin:
            gray = np.array(img_work.convert('L'))
            img_np = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        else:
            img_np = np.array(img_work.convert('L'))
            
        # OCR 실행
        t1 = time.time()
        results = reader.readtext(img_np, detail=1)
        t2 = time.time()
        
        # 결과 분석
        valid_text = []
        conf_sum = 0
        for (bbox, text, conf) in results:
            if conf > 0.15:
                valid_text.append(text)
                conf_sum += conf
        
        avg_conf = conf_sum / len(valid_text) if valid_text else 0
        print(f"⏱️ 시간: {t2-t1:.2f}s | 🧩 블록 수: {len(valid_text)} | 🎯 평균 신뢰도: {avg_conf:.2f}")
        
        full_result = " ".join(valid_text)
        corrected = clean_ocr_text(full_result)
        
        print(f"📝 결과 요약: {corrected[:100]}...")
        
        # 시각화 이미지 생성 (첫 번째 테스트 결과만 상세 저장)
        if scale == 1.5 and not do_bin:
            vis_img = Image.fromarray(img_np).convert("RGB")
            draw = ImageDraw.Draw(vis_img)
            for (bbox, text, conf) in results:
                pts = [tuple(p) for p in bbox]
                draw.polygon(pts, outline="red")
            vis_img.save(".debug/tuner_visualization.png")

    print("\n✅ 튜닝 테스트 완료. '.debug/tuner_target.png'와 'tuner_visualization.png'를 확인하세요.")

if __name__ == "__main__":
    run_ocr_tuning()
