"""Leitura estática dos componentes extraídos (NK.bin, firmware.hex, PEs). Nada é executado.

uso: python -I components.py <pasta upgrade/>
"""
import os
import re
import struct
import sys

root = sys.argv[1]
SC = os.path.join(root, "Storage Card")


def ascii_strings(data, n=6):
    return [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{%d,}" % n, data)]


def utf16_strings(data, n=6):
    return [m.group().decode("utf-16le") for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % n, data)]


# ---------- NK.bin ----------
nk = open(os.path.join(SC, "NK.bin"), "rb").read()
print("== NK.bin ==", len(nk))
print("início:", nk[:16].hex(), nk[:7])
if nk[:7] == b"B000FF\n":
    start, length = struct.unpack_from("<II", nk, 7)
    print(f"formato B000FF: image start={start:#x} len={length:#x}")
    recs, off = [], 15
    while off + 12 <= len(nk):
        addr, ln, chk = struct.unpack_from("<III", nk, off)
        off += 12
        if addr == 0:
            print(f"registro final: entry point={ln:#x}")
            break
        recs.append((addr, ln))
        off += ln
    print("registros:", len(recs), "primeiro", hex(recs[0][0]) if recs else None)
ecec = [m.start() for m in re.finditer(b"ECEC", nk)]
print("ECEC em:", [hex(o) for o in ecec[:4]])
s = ascii_strings(nk)
mods = sorted({x.lower() for x in s if re.fullmatch(r"[\w\-]+\.(exe|dll)", x, re.I)})
print(f"nomes de módulos (exe/dll) citados: {len(mods)}")
print("  " + " ".join(mods))
for kw in ("Windows CE", "CE 6", "WINCE", "Build", "LG", "ULC", "BSP", "Version", "Copyright"):
    hits = sorted({x for x in s + utf16_strings(nk) if kw in x})[:6]
    if hits:
        print(f"  [{kw}]", hits)

# ---------- firmware.hex ----------
print("\n== firmware.hex ==")
mem, base, types = {}, 0, {}
for line in open(os.path.join(root, "firmware.hex"), encoding="ascii", errors="replace"):
    line = line.strip()
    if not line.startswith(":"):
        continue
    b = bytes.fromhex(line[1:])
    ln, addr, typ = b[0], (b[1] << 8) | b[2], b[3]
    types[typ] = types.get(typ, 0) + 1
    payload = b[4:4 + ln]
    if typ == 0:
        for i, v in enumerate(payload):
            mem[base + addr + i] = v
    elif typ == 2:
        base = int.from_bytes(payload, "big") << 4
    elif typ == 4:
        base = int.from_bytes(payload, "big") << 16
print("tipos de registro:", types)
addrs = sorted(mem)
ranges, st = [], addrs[0]
for a, b2 in zip(addrs, addrs[1:] + [None]):
    if b2 != a + 1:
        ranges.append((st, a))
        if b2 is not None:
            st = b2
print(f"bytes: {len(mem)}  faixas: {len(ranges)}")
for a, b2 in ranges[:12]:
    print(f"  {a:#010x}-{b2:#010x} ({b2 - a + 1} bytes)")
blob = bytes(mem[a] for a in addrs)
hs = ascii_strings(blob, 5)
print("strings (amostra):", [x for x in hs if re.search(r"[A-Za-z]{3}", x)][:40])

# ---------- PEs ----------
print("\n== PEs: máquina, data de link, VersionInfo ==")
pes = []
for dp, _, fn in os.walk(root):
    for f in fn:
        if f.lower().endswith((".exe", ".dll")) and not f.startswith("LangDll"):
            pes.append(os.path.join(dp, f))
import datetime
for p in pes:
    d = open(p, "rb").read()
    e = struct.unpack_from("<I", d, 60)[0]
    mach, _, ts = struct.unpack_from("<HHI", d, e + 4)
    sub = struct.unpack_from("<H", d, e + 24 + 68)[0]
    vi = {}
    for k in ("FileVersion", "ProductVersion", "CompanyName", "FileDescription", "ProductName"):
        m = re.search(k.encode("utf-16le") + rb"\x00\x00(?:\x00\x00)?((?:[\x20-\x7e]\x00)+)", d)
        if m:
            vi[k] = m.group(1).decode("utf-16le")
    print(f"{os.path.relpath(p, root):45} mach={mach:#06x} subsys={sub} link={datetime.datetime.utcfromtimestamp(ts):%Y-%m-%d} {vi}")
