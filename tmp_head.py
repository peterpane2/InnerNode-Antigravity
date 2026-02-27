
import os

conv_dir = os.path.expanduser(r"~\.gemini\antigravity\conversations")
files = [os.path.join(conv_dir, f) for f in os.listdir(conv_dir) if f.endswith('.pb')]
latest = max(files, key=os.path.getmtime)
print("Latest file:", latest)
with open(latest, 'rb') as f:
    data = f.read(16)
    print("Header:", data.hex(' '))
