
import zlib
import gzip
import traceback

pb_file = r"C:\Users\Administrator\.gemini\antigravity\conversations\eb7dc218-341e-4149-9e03-7910f0fda413.pb"
with open(pb_file, 'rb') as f:
    data = f.read()

print("Testing zlib...")
try:
    dec = zlib.decompress(data)
    print("Zlib SUCCESS!", dec[:100])
except Exception as e:
    print("Zlib failed:", e)

print("Testing gzip...")
try:
    dec = gzip.decompress(data)
    print("Gzip SUCCESS!", dec[:100])
except Exception as e:
    print("Gzip failed:", e)

# Test zstd, lz4, brotli...
try:
    import zstandard as zstd
    dctx = zstd.ZstdDecompressor()
    dec = dctx.decompress(data)
    print("Zstd SUCCESS!", dec[:100])
except Exception as e:
    print("Zstd failed:", e)
