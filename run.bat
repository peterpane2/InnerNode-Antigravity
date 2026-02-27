@echo off
title Antigravity Telegram Remote Control
chcp 65001 > nul

echo ===================================================
echo   🚀 Antigravity Telegram 봇 + 자동승인 시스템
echo ===================================================

:: 0. 기존 프로세스 정리 (중복 실행 방지)
echo [*] 기존 프로세스 정리 중...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Antigravity*" > nul 2>&1
:: 세밀하게 우리 스크립트만 골라 끄기 (PowerShell 이용)
powershell -Command "Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*antigravity_bot.py*' -or $_.CommandLine -like '*agent_brain.py*' -or $_.CommandLine -like '*auto_approver.py*' } | Stop-Process -Force" > nul 2>&1

:: 1. 가상환경 생성 (최초 1회)
if not exist .venv (
    echo [1/4] 가상환경 생성 중...
    python -m venv .venv
)
call .venv\Scripts\activate

:: 2. 패키지 설치 (출력 표시 — 첫 실행 시 opencv 등 시간 소요)
echo [2/4] 필수 패키지 확인 중... (첫 실행 시 1~2분 걸림)
pip install -q -r requirements.txt

:: 3. .env 파일 확인
if not exist .env (
    echo [오류] .env 파일이 없습니다!
    echo.
    echo .env 파일을 생성하고 아래 내용을 입력하세요:
    echo   TELEGRAM_BOT_TOKEN=your_bot_token_here
    echo   TELEGRAM_CHAT_ID=your_chat_id_here
    echo.
    echo @BotFather 에서 봇 토큰을 받고,
    echo @userinfobot 에서 chat_id를 확인하세요.
    pause
    exit /b 1
)

:: 4. 자동 승인 시스템 (Brain 통합)
echo [3/4] 자동 승인 준비 완료...
:: start "" /b python auto_approver.py  <-- Brain으로 통합됨

:: 5. Telegram 봇 (백그라운드)
echo [4/4] Telegram 봇 시작...
start "" /b python antigravity_bot.py

:: 잠시 대기 후 Brain 시작
timeout /t 3 > nul

:: 6. Brain 브릿지 (포그라운드 — 종료 시 전체 종료)
echo.
echo ✅ 모든 시스템 가동 완료!
echo    텔레그램 앱에서 봇을 찾아 /start 를 보내세요.
echo    이 창을 닫으면 모든 프로세스가 종료됩니다.
echo.
python agent_brain.py

pause
