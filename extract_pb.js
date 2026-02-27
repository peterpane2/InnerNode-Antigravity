const fs = require('fs');
const protobuf = require('protobufjs');

const filePath = process.argv[2];
if (!filePath || !fs.existsSync(filePath)) {
    console.error("Provide a valid file path");
    process.exit(1);
}

function parseBuffer(buffer, depth = 0) {
    const strings = [];
    if (depth > 10) return strings;

    const reader = protobuf.Reader.create(buffer);
    try {
        while (reader.pos < reader.len) {
            const tag = reader.uint32();
            const wireType = tag & 7;

            if (wireType === 2) {
                const len = reader.uint32();
                if (reader.pos + len > reader.len) break;
                
                const payload = buffer.slice(reader.pos, reader.pos + len);
                reader.skip(len);

                try {
                    const str = payload.toString('utf8');
                    // Check for general sanity (must be printable text)
                    if (str.length > 2 && !/[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(str)) {
                        strings.push(str);
                    }
                } catch (e) {}

                const subStrings = parseBuffer(payload, depth + 1);
                if (subStrings.length > 0) {
                    strings.push(...subStrings);
                }
            } else if (wireType === 0) {
                reader.skipType(wireType);
            } else if (wireType === 1) {
                reader.skipType(wireType);
            } else if (wireType === 5) {
                reader.skipType(wireType);
            } else {
                break;
            }
        }
    } catch (e) {
        // ignore parse errors and return what we got
    }
    return strings;
}

try {
    const data = fs.readFileSync(filePath);
    const results = parseBuffer(data);
    
    // Filter out some garbage heuristics
    const clean = results.filter(s => {
        const t = s.trim();
        if (t.length < 5) return false;
        if (/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(t)) return false;
        if (/^[0-9a-f]{16,64}$/i.test(t)) return false;
        
        // Exclude mostly symbols/garbage
        const noise = t.replace(/[a-zA-Z0-9\s가-힣]/g, '');
        if (noise.length > t.length * 0.3) return false;
        return true;
    });

    console.log(JSON.stringify(clean));
} catch (e) {
    console.error(e);
    process.exit(1);
}
