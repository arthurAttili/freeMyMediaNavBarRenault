"""Leitura estática do upgrade.lgu: cabeçalho, entropia por bloco e assinaturas conhecidas."""
import math
import re
import sys
from collections import Counter

path = sys.argv[1]
data = open(path, "rb").read()
n = len(data)
print("tamanho", n)

print("\n== primeiros 512 bytes ==")
for off in range(0, 512, 16):
    chunk = data[off:off + 16]
    hx = " ".join(f"{b:02x}" for b in chunk)
    asc = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    print(f"{off:08x}  {hx:<48}  {asc}")


def entropy(b):
    if not b:
        return 0.0
    c = Counter(b)
    return -sum(v / len(b) * math.log2(v / len(b)) for v in c.values())


print("\n== entropia por bloco de 4 MiB ==")
step = 4 << 20
row = []
for off in range(0, n, step):
    row.append(f"{entropy(data[off:off + step]):.2f}")
print(" ".join(row))

sigs = {
    b"PK\x03\x04": "zip local header",
    b"\x1f\x8b\x08": "gzip",
    b"B000FF\n": "WinCE B000FF (.bin)",
    b"ECEC": "WinCE ROMHDR marker",
    b"MZ": None,  # contado à parte, muito ruidoso
    b"7z\xbc\xaf\x27\x1c": "7z",
    b"Rar!": "rar",
    b"hsqs": "squashfs",
    b"\x7fELF": "ELF",
    b"<?xml": "xml",
    b"-----BEGIN": "PEM",
    b"MSCE": "MSCE cab",
    b"MSCF": "MS cab",
}
print("\n== assinaturas ==")
for sig, name in sigs.items():
    if name is None:
        continue
    offs = [m.start() for m in re.finditer(re.escape(sig), data)]
    if offs:
        print(f"{name:24} {len(offs):6}  primeiros: {[hex(o) for o in offs[:8]]}")

pe = [m.start() for m in re.finditer(rb"MZ.{58}", data, re.S)
      if data[m.start() + int.from_bytes(data[m.start() + 60:m.start() + 64], "little"):][:4] == b"PE\x00\x00"
      ] if False else []
mz_pe = 0
first_pe = []
for m in re.finditer(rb"MZ", data):
    o = m.start()
    if o + 64 > n:
        continue
    e = int.from_bytes(data[o + 60:o + 64], "little")
    if 0 < e < 0x1000 and data[o + e:o + e + 4] == b"PE\x00\x00":
        mz_pe += 1
        if len(first_pe) < 8:
            first_pe.append(hex(o))
print(f"{'PE executáveis':24} {mz_pe:6}  primeiros: {first_pe}")
