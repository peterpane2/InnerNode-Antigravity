
import os
import re

def DecodeVarint(buffer, pos):
    """Decodes a protobuf varint from buffer starting at pos."""
    result = 0
    shift = 0
    while True:
        if pos >= len(buffer):
            raise EOFError()
        b = buffer[pos]
        pos += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7

def parse_protobuf_messages(buffer):
    """Recursively parse a protobuf buffer to extract all valid UTF-8 strings."""
    def _parse(buf, depth=0):
        strings = []
        if depth > 10:
            return strings
            
        pos = 0
        end = len(buf)
        
        while pos < end:
            try:
                tag, pos = DecodeVarint(buf, pos)
                wire_type = tag & 7
                field_number = tag >> 3
                
                if wire_type == 0:  # VARINT
                    _, pos = DecodeVarint(buf, pos)
                elif wire_type == 1:  # 64-BIT
                    pos += 8
                elif wire_type == 5:  # 32-BIT
                    pos += 4
                elif wire_type == 2:  # LENGTH-DELIMITED
                    length, pos = DecodeVarint(buf, pos)
                    if pos + length > end:
                        break  # Invalid length
                        
                    payload = buf[pos:pos+length]
                    pos += length
                    
                    # Strategy 1: Attempt UTF-8 String
                    try:
                        s = payload.decode('utf-8')
                        # Filter out strings with excessive control characters
                        if len(s) >= 2 and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', s):
                            strings.append(s)
                    except UnicodeDecodeError:
                        pass
                        
                    # Strategy 2: Attempt Recursive Message Parsing
                    sub_strings = _parse(payload, depth + 1)
                    if sub_strings:
                        strings.extend(sub_strings)
                        
                else:
                    # Unknown wire type, likely not a protobuf message or lost sync
                    break
            except Exception:
                break
                
        return strings

    return _parse(buffer)

def get_latest_conversation_file():
    conv_dir = os.path.expanduser(r"~\.gemini\antigravity\conversations")
    if not os.path.exists(conv_dir):
        return None
    files = [os.path.join(conv_dir, f) for f in os.listdir(conv_dir) if f.endswith('.pb')]
    return max(files, key=os.path.getmtime) if files else None

def extract_latest_history():
    pb_file = get_latest_conversation_file()
    if not pb_file:
        return ["대화 기록 펄더를 찾을 수 없습니다."]
    
    with open(pb_file, 'rb') as f:
        data = f.read()
        
    all_strings = parse_protobuf_messages(data)
    
    # Filter candidates to return meaningful text
    candidates = []
    for s in all_strings:
        s = s.strip()
        if len(s) < 2:
            continue
            
        # Exclude pure UUIDs or hex IDs
        if re.match(r'^[0-9a-fA-F-]{36}$', s): continue
        if re.match(r'^[0-9a-fA-F]{16,64}$', s): continue
            
        # Ignore strings that look like random base64 or garbage
        garbage_ratio = len(re.findall(r'[^a-zA-Z0-9\s가-힣\.,\?!;:()\[\]\n\r\'\"<>/_=-]', s)) / len(s)
        if garbage_ratio > 0.2:
            continue
            
        # Ignore JSON/Python syntax fragments that are just empty objects
        if s in ["{}", "[]", "()"]: continue
        if s.startswith("{") and s.endswith("}") and '"' not in s: continue
        
        candidates.append(s)
        
    return candidates

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    res = extract_latest_history()
    print(f"Total pure strings: {len(res)}")
    for x in res[-30:]:
        print(f"[{len(x)}] {x}")
