"""Lê o cabeçalho ULC2 e lista o ZIP embutido (sem extrair)."""
import struct
import sys
import zipfile
import zlib

path = sys.argv[1]
f = open(path, "rb")
hdr = f.read(0x400)
magic, ver, hsize, total, z1, one, chk = struct.unpack_from("<4sIIIIII", hdr, 0)
print("magic", magic, "ver", ver, "hsize", hex(hsize), "total", total, "campo10", z1, "campo14", one, "campo18", hex(chk))
s = hdr[0x24:0x18c].decode("utf-16le").rstrip("\x00")
print("string utf16 @0x24:", repr(s[:40]), "len", len(s))
f.seek(0, 2)
size = f.tell()
print("tamanho real", size, "bate com header:", size == total)

# candidatos de checksum: crc32 do corpo, crc32 do arquivo com campo zerado
f.seek(hsize)
body = f.read()
print("crc32(corpo)", hex(zlib.crc32(body)))
h0 = bytearray(hdr)
h0[0x18:0x1c] = b"\0\0\0\0"
print("crc32(header zerado+corpo)", hex(zlib.crc32(body, zlib.crc32(bytes(h0)))))
print("crc32(header[0x1c:]+corpo)", hex(zlib.crc32(body, zlib.crc32(hdr[0x1c:]))))

z = zipfile.ZipFile(path)
infos = z.infolist()
print("\nentradas:", len(infos))
enc = sum(1 for i in infos if i.flag_bits & 1)
print("criptografadas:", enc)
print("comentário:", z.comment[:200])
for i in infos:
    print(f"{i.compress_type:2} {'E' if i.flag_bits & 1 else ' '} {i.file_size:12} {i.compress_size:12} {i.date_time} {i.filename}")
