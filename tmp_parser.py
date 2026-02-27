
import os
import re

def extract_strings_heuristic(file_path):
    if not os.path.exists(file_path):
        return []
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    strings = []
    # Find sequences of printable ASCII
    pattern = re.compile(rb'[\x20-\x7E\r\n\t]{4,}')
    for match in pattern.finditer(data):
        try:
            s = match.group().decode('ascii').strip()
            if s and len(s) > 5:
                # Filter out UUIDs and common noise if we just want content
                if not re.match(r'^[0-9a-f-]{36}$', s):
                    strings.append(s)
        except:
            pass
            
    return strings

if __name__ == "__main__":
    # Current conversation ID from artifact path
    pb_file = r"C:\Users\Administrator\.gemini\antigravity\conversations\eb7dc218-341e-4149-9e03-7910f0fda413.pb"
    results = extract_strings_heuristic(pb_file)
    print(f"Total candidate strings found: {len(results)}")
    
    # Print the last 50 strings, which should be the most recent part of the conversation
    for s in results[-50:]:
        print(f"[{len(s)}] {s}")
