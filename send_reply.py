"""
send_reply.py — AI(Antigravity)가 폰으로 메시지를 보내는 도구
사용법: python send_reply.py '보낼 메시지'
"""
import json
import sys
import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAILBOX_PATH = os.path.join(BASE_DIR, "mailbox.json")


def send_reply(message: str) -> None:
    temp_path = MAILBOX_PATH + ".tmp"
    try:
        with open(MAILBOX_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"inbound": [], "outbound": [], "approval_request": None}

    data["outbound"].append(message)

    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    shutil.move(temp_path, MAILBOX_PATH)
    print(f"Reply queued: {message}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        send_reply(" ".join(sys.argv[1:]))
    else:
        print("Usage: python send_reply.py '메시지'")
