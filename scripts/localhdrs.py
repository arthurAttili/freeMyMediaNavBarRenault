"""Percorre os cabeçalhos locais PK\\x03\\x04 do corpo e mostra o que cada um declara."""
import re
import struct
import sys

data = open(sys.argv[1], "rb").read()
for m in re.finditer(rb"PK\x03\x04", data):
    o = m.start()
    (ver, flag, meth, mt, md, crc, csz, usz, nlen, xlen) = struct.unpack_from("<HHHHHIIIHH", data, o + 4)
    name = data[o + 30:o + 30 + nlen]
    extra = data[o + 30 + nlen:o + 30 + nlen + xlen]
    start = o + 30 + nlen + xlen
    print(f"@{o:#010x} ver={ver} flag={flag:#06x} meth={meth} crc={crc:#010x} csz={csz} usz={usz} "
          f"nome={name[:80]!r} extra={extra[:24].hex()} dados@{start:#x}")
for sig, lab in ((rb"PK\x01\x02", "central dir"), (rb"PK\x05\x06", "EOCD"), (rb"PK\x07\x08", "data descriptor"), (rb"PK\x06\x06", "zip64 EOCD")):
    print(lab, len(re.findall(sig, data)))
print("últimos 64 bytes:", data[-64:].hex())
