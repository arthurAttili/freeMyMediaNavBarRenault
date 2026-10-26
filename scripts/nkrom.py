"""Monta a imagem do NK.bin (B000FF) em memória e lê o ROMHDR: módulos e arquivos da ROM.

uso: python -I nkrom.py <NK.bin> [--dump <pasta> <nome>...]
--dump grava arquivos não comprimidos da ROM numa pasta (só leitura de dados, nada é executado).
"""
import datetime
import os
import struct
import sys

data = open(sys.argv[1], "rb").read()
assert data[:7] == b"B000FF\n"
start, length = struct.unpack_from("<II", data, 7)
img = bytearray(length)
off = 15
while True:
    addr, ln, chk = struct.unpack_from("<III", data, off)
    off += 12
    if addr == 0:
        break
    img[addr - start:addr - start + ln] = data[off:off + ln]
    off += ln


def u32(va):
    return struct.unpack_from("<I", img, va - start)[0]


def cstr(va):
    o = va - start
    return img[o:img.index(b"\0", o)].decode("latin-1")


def ft(lo, hi):
    t = (hi << 32 | lo)
    return (datetime.datetime(1601, 1, 1) + datetime.timedelta(microseconds=t // 10)).strftime("%Y-%m-%d") if t else "-"


assert img[0x40:0x44] == b"ECEC"
romhdr = struct.unpack_from("<I", img, 0x44)[0]
f = struct.unpack_from("<16I2H5I", img, romhdr - start)
names = ("dllfirst dlllast physfirst physlast nummods ramstart ramfree ramend copyentries copyoffset "
         "profilelen profileoffset numfiles kernelflags fsrampercent drivglobstart drivgloblen cputype miscflags "
         "pextensions trackstart tracklen").split()
h = dict(zip(names, f))
print("ROMHDR", {k: hex(v) for k, v in h.items()})
print(f"RAM {h['ramstart']:#x}-{h['ramend']:#x} = {(h['ramend'] - h['ramstart']) >> 20} MB; CPU {h['cputype']:#x}")

toc = romhdr + 84
mods = []
for i in range(h["nummods"]):
    attr, tlo, thi, size, pname, e32, o32, load = struct.unpack_from("<8I", img, toc + i * 32 - start)
    mods.append((cstr(pname), size, attr, ft(tlo, thi)))
filesva = toc + h["nummods"] * 32
files = []
for i in range(h["numfiles"]):
    attr, tlo, thi, real, comp, pname, load = struct.unpack_from("<7I", img, filesva + i * 28 - start)
    files.append((cstr(pname), real, comp, attr, ft(tlo, thi), load))

print(f"\n== módulos: {len(mods)}, {sum(m[1] for m in mods) / 1e6:.1f} MB ==")
for n, s, a, t in sorted(mods, key=lambda m: -m[1]):
    print(f"{s:9} {t} {n}")
print(f"\n== arquivos: {len(files)}, real {sum(x[1] for x in files) / 1e6:.1f} MB ==")
for n, r, c, a, t, l in sorted(files, key=lambda x: x[0].lower()):
    print(f"{r:9} {c:9} {'C' if c != r else ' '} attr={a:#06x} {t} {n}")

if "--dump" in sys.argv:
    i = sys.argv.index("--dump")
    out, want = sys.argv[i + 1], {w.lower() for w in sys.argv[i + 2:]}
    os.makedirs(out, exist_ok=True)
    for n, r, c, a, t, l in files:
        if n.lower() in want:
            blob = bytes(img[l - start:l - start + c])
            open(os.path.join(out, n + (".cmp" if c != r else "")), "wb").write(blob)
            print("gravado", n, c, "bytes", "(comprimido)" if c != r else "")
