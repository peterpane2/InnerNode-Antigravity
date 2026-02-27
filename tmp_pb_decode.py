import os
import re

def read_varint(data, pos):
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result, pos

def parse_pb(data, pos, end, depth=0):
    strings = []
    if depth > 10:
        return strings
        
    while pos < end:
        try:
            tag, pos = read_varint(data, pos)
            wire_type = tag & 7
            field_num = tag >> 3
            
            if wire_type == 0:  # Varint
                _, pos = read_varint(data, pos)
            elif wire_type == 1:  # 64-bit
                pos += 8
            elif wire_type == 5:  # 32-bit
                pos += 4
            elif wire_type == 2:  # Length-delimited
                length, pos = read_varint(data, pos)
                if pos + length > end:
                    break
                
                payload = data[pos:pos+length]
                pos += length
                
                # 1. Try UTF-8 String
                try:
                    s = payload.decode('utf-8')
                    # Keep if > 2 chars and no crazy control characters
                    if len(s) > 2 and not re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', s):
                        strings.append(s.strip())
                except UnicodeDecodeError:
                    pass
                
                # 2. Recursively try embedded message parsing
                sub_strings = parse_pb(payload, 0, len(payload), depth + 1)
                strings.extend(sub_strings)
            else:
                # Unknown wire type or bad sync
                break
        except Exception:
            break
            
    return strings

def extract_strings(file_path):
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, 'rb') as f:
        data = f.read()
        
    raw_strings = parse_pb(data, 0, len(data))
    
    # Filter strings to only keep descriptive/human-readable content
    clean_strings = []
    for s in raw_strings:
        # Ignore UUIDs
        if re.match(r'^[0-9a-fA-F-]{36}$', s):
            continue
        # Ignore hashes/IDs (hex strings > 16 chars)
        if re.match(r'^[0-9a-fA-F]{16,64}$', s):
            continue
        # Ignore specific technical strings
        if s.startswith('{') or s.endswith('}'):
            continue
        if len(s) < 5:
            continue
        
        clean_strings.append(s)
        
    return clean_strings

if __name__ == "__main__":
    pb_file = r"C:\Users\Administrator\.gemini\antigravity\conversations\eb7dc218-341e-4149-9e03-7910f0fda413.pb"
    results = extract_strings(pb_file)
    print(f"Total valid strings: {len(results)}")
    
    # Show last 20 chunks
    for s in results[-20:]:
        print(f"----------------------\n{s}\n")
