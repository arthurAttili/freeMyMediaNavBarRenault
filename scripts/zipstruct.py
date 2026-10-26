"""Descreve como o ZIP interno do upgrade.lgu foi montado (o empacotador precisa repetir isso).

uso: python -I zipstruct.py <_decoded.zip>
"""
import collections
import struct
import sys
import zipfile

path = sys.argv[1]
z = zipfile.ZipFile(path)
infos = z.infolist()
c = collections.Counter
print("entradas", len(infos))
print("método", c(i.compress_type for i in infos))
print("flags", c(hex(i.flag_bits) for i in infos))
print("version made/needed", c((i.create_version, i.create_system, i.extract_version) for i in infos))
print("extra (central) tamanhos", c(len(i.extra) for i in infos))
print("ext attr", c(hex(i.external_attr) for i in infos).most_common(5))
print("internal attr", c(i.internal_attr for i in infos))
print("diretórios", sum(1 for i in infos if i.filename.endswith(("/", "\\"))))
print("separador '\\\\' no nome", sum(1 for i in infos if "\\" in i.filename), "| '/'", sum(1 for i in infos if "/" in i.filename))
print("primeiros nomes", [i.filename for i in infos[:5]])
print("ordem == ordem dos offsets", [i.header_offset for i in infos] == sorted(i.header_offset for i in infos))
print("comentários de arquivo", sum(1 for i in infos if i.comment))

raw = open(path, "rb").read()
# compara cabeçalho local x central e procura bytes entre registros
gaps, lextra, dd = 0, c(), 0
ends = []
for i in infos:
    o = i.header_offset
    sig, ver, flag, meth, mt, md, crc, csz, usz, nl, xl = struct.unpack_from("<IHHHHHIIIHH", raw, o)
    lextra[xl] += 1
    dd += bool(flag & 8)
    ends.append((o, o + 30 + nl + xl + i.compress_size + (12 if flag & 8 else 0)))
for (a, e), (b, _) in zip(ends, ends[1:]):
    if b != e:
        gaps += 1
print("extra (local) tamanhos", lextra, "| data descriptor", dd, "| lacunas entre registros", gaps)
eocd = raw.rfind(b"PK\x05\x06")
print("EOCD em", eocd, "de", len(raw), "| fim do último registro", ends[-1][1], "| início do central dir", struct.unpack_from("<I", raw, eocd + 16)[0])
print("zip comment len", struct.unpack_from("<H", raw, eocd + 20)[0])
