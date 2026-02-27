
import os

pb_file = r"C:\Users\Administrator\.gemini\antigravity\conversations\eb7dc218-341e-4149-9e03-7910f0fda413.pb"
with open(pb_file, 'rb') as f:
    data = f.read(1024)
    print(data.hex(' '))
