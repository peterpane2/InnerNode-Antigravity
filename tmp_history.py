
import os
import re

def extract_latest_history():
    conv_dir = os.path.expanduser(r"~\.gemini\antigravity\conversations")
    if not os.path.exists(conv_dir):
        return ["대화 기록 폴더를 찾을 수 없습니다."]
    
    files = [os.path.join(conv_dir, f) for f in os.listdir(conv_dir) if f.endswith('.pb')]
    if not files:
        return ["대화 기록 파일(.pb)이 없습니다."]
        
    pb_file = max(files, key=os.path.getmtime)
    
    try:
        with open(pb_file, 'rb') as f:
            data = f.read()
            
        strings = []
        current_string = bytearray()
        
        for byte in data:
            # Printable ASCII or multi-byte UTF-8 start/continuation bytes
            # We enforce that newlines are fine, but other control chars break the run
            if byte == 10 or byte == 13 or byte == 9 or (32 <= byte <= 126) or byte >= 128:
                current_string.append(byte)
            else:
                if len(current_string) > 10:
                    try:
                        s = current_string.decode('utf-8').strip()
                        if validate_string(s):
                            strings.append(s)
                    except:
                        pass
                current_string = bytearray()
                
        if len(current_string) > 10:
            try:
                s = current_string.decode('utf-8').strip()
                if validate_string(s):
                    strings.append(s)
            except:
                pass
                
        if not strings:
            return ["추출된 대화가 없습니다."]
            
        return [s for s in strings if "{" not in s and "}" not in s]
    except Exception as e:
        return [f"오류 발생: {e}"]

def validate_string(s):
    if len(s) < 10: return False
    # No UUIDs
    if re.match(r'^[0-9a-fA-F-]{36}$', s): return False
    # No purely hex strings
    if re.match(r'^[0-9a-fA-F]{10,}$', s): return False
    # No standard UUID-like variations
    if re.search(r'[0-9a-fA-F-]{20,}', s): return False
    # Filter out excessive garbage characters (e.g., gibberish ASCII)
    garbage_ratio = len(re.findall(r'[^a-zA-Z0-9\s가-힣\.,\?!;:()\[\]\n\r\'\"]', s)) / len(s)
    if garbage_ratio > 0.3: return False
    
    # Needs to contain at least some alphabetic or Korean characters
    if not re.search(r'[a-zA-Z가-힣]', s): return False
    
    return True

if __name__ == "__main__":
    results = extract_latest_history()
    print(f"Extracted {len(results)} strings")
    for r in results[-10:]:
        print(f"--- \n{r}")
