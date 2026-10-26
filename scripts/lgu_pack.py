"""Gera um upgrade.lgu (ULC2) a partir de um .lgu original e de uma lista de mudanças.

Entradas que não mudam são copiadas cruas do ZIP original (já cifradas). Só as
trocadas ou novas são comprimidas (deflate) e cifradas com ZipCrypto. Depois o
diretório central é refeito, o corpo leva o XOR e o cabeçalho recebe tamanho e CRC.
Sem lista de mudanças, a saída tem que ser idêntica byte a byte à entrada.

uso: python -I lgu_pack.py <base.lgu> <saida.lgu> [mudancas.txt]

mudancas.txt (UTF-8, uma ação por linha, '#' comenta; nomes como no ZIP, com '/'):
  remove  upgrade/Storage Card4/NNG/content/lang/Lang_Arabic.zip
  remove  upgrade/Storage Card4/NNG/content/voice/Voice_Per-*      (aceita curinga)
  replace upgrade/Storage Card4/NNG/SYS.TXT | arquivos/SYS.TXT
  add     upgrade/Storage Card4/NNG/novo.txt | arquivos/novo.txt
Caminho local relativo é resolvido a partir da pasta do mudancas.txt.

Bloqueios fixos: NK.bin, firmware.hex, booter_standalone.bin e firmware do DAB não
podem ser trocados nem removidos, e a saída não pode ir para unidade removível.
Precisa de xorArray.h ao lado do script (ver lgu_unpack.py).
"""
import ctypes
import fnmatch
import hashlib
import os
import re
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PASSWORDS = {b"ULC2": b"u8u8l^-^8@E4g_H2kq8X_pack", b"LGU0": b"I_LOVE_LG^^"}
PROTECTED = re.compile(r"(?i)(^|/)(nk\.bin|firmware\.hex|booter_standalone\.bin|ulc_dab_\w+\.bin)$")

def _crctab():
    tab = []
    for i in range(256):
        c = i
        for _ in range(8):
            c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
        tab.append(c)
    return tab


CRCTAB = _crctab()


def load_tables():
    path = os.path.join(HERE, "xorArray.h")
    if not os.path.exists(path):
        sys.exit("falta scripts/xorArray.h: baixe de "
                 "https://raw.githubusercontent.com/yosicovich/MediaNavMods/master/pc/lgutool/lgu2dir/xorArray.h")
    src = open(path, encoding="utf8").read()
    tables = {}
    for name, body in re.findall(r"unsigned char (\w+)\[\]\s*=\s*\{(.*?)\};", src, re.S):
        tables[name] = bytes(int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{2})", body))
    return {b"LGU0": tables["xorArrLGU0"], b"ULC2": tables["xorArrULC2"]}


def xor_body(data, key):
    rep = key * (1 << 12)  # 4 MiB, múltiplo de 1024: o índice continua reiniciando a cada 1 KB
    out = bytearray()
    for off in range(0, len(data), len(rep)):
        chunk = data[off:off + len(rep)]
        out += (int.from_bytes(chunk, "little") ^ int.from_bytes(rep[:len(chunk)], "little")).to_bytes(len(chunk), "little")
    return bytes(out)


def crc_step(c, b):
    return CRCTAB[(c ^ b) & 0xFF] ^ (c >> 8)


def zipcrypto_encrypt(plain, password, check_byte, seed):
    k0, k1, k2 = 0x12345678, 0x23456789, 0x34567890

    def update(b):
        nonlocal k0, k1, k2
        k0 = crc_step(k0, b)
        k1 = ((k1 + (k0 & 0xFF)) * 134775813 + 1) & 0xFFFFFFFF
        k2 = crc_step(k2, k1 >> 24)

    for b in password:
        update(b)
    out = bytearray()
    # 11 bytes de cabeçalho derivados do nome+CRC (build reprodutível) + byte de checagem
    for p in seed[:11] + bytes([check_byte]):
        t = (k2 | 2) & 0xFFFF
        out.append(p ^ (((t * (t ^ 1)) >> 8) & 0xFF))
        update(p)
    for p in plain:
        t = (k2 | 2) & 0xFFFF
        out.append(p ^ (((t * (t ^ 1)) >> 8) & 0xFF))
        update(p)
    return bytes(out)


def dos_datetime(ts):
    t = time.localtime(ts)
    return ((t.tm_hour << 11) | (t.tm_min << 5) | (t.tm_sec // 2),
            ((t.tm_year - 1980) << 9) | (t.tm_mon << 5) | t.tm_mday)


def ntfs_extra(ts):
    ft = int(ts * 10_000_000) + 116444736000000000
    return struct.pack("<HHIHHQQQ", 0x000A, 32, 0, 1, 24, ft, ft, ft)


def is_removable(path):
    if os.name != "nt":
        return False
    drive = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
    return ctypes.windll.kernel32.GetDriveTypeW(drive) == 2  # DRIVE_REMOVABLE


def read_changes(path):
    removes, puts = [], {}
    base = os.path.dirname(os.path.abspath(path))
    for n, line in enumerate(open(path, encoding="utf-8-sig"), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        op, _, rest = line.partition(" ")
        rest = rest.strip()
        if op == "remove":
            removes.append(rest)
        elif op in ("replace", "add"):
            name, _, local = (x.strip() for x in rest.partition("|"))
            if not local:
                sys.exit(f"linha {n}: falta '| arquivo_local'")
            puts[name] = (op, os.path.join(base, local))
        else:
            sys.exit(f"linha {n}: ação desconhecida {op!r}")
    return removes, puts


def central_records(z):
    eocd = z.rfind(b"PK\x05\x06")
    count, cdsize, cdoff = struct.unpack_from("<HII", z, eocd + 10)
    recs, o = [], cdoff
    for _ in range(count):
        assert z[o:o + 4] == b"PK\x01\x02"
        nl, xl, cl = struct.unpack_from("<HHH", z, o + 28)
        size = 46 + nl + xl + cl
        name = z[o + 46:o + 46 + nl].decode("cp437")
        recs.append((name, z[o:o + size]))
        o += size
    return recs, z[eocd:]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    removes, puts = read_changes(sys.argv[3]) if len(sys.argv) > 3 else ([], {})
    if is_removable(dst):
        sys.exit("saída em unidade removível: este script não grava em pendrive")

    raw = open(src, "rb").read()
    magic, _, hsize = struct.unpack_from("<4sII", raw, 0)
    key = load_tables()[magic]
    pwd = PASSWORDS[magic]
    z = xor_body(raw[hsize:], key)
    recs, eocd = central_records(z)
    names = {n for n, _ in recs}

    for name in list(puts) + removes:
        hit = [n for n in names if fnmatch.fnmatchcase(n, name)] if name in removes else [name]
        if any(PROTECTED.search(h) for h in hit):
            sys.exit(f"bloqueado: {name} é firmware de base (NK/MICOM/bootloader/DAB)")
    for name, (op, _) in puts.items():
        if op == "replace" and name not in names:
            sys.exit(f"replace de entrada inexistente: {name}")
        if op == "add" and name in names:
            sys.exit(f"add de entrada que já existe (use replace): {name}")
    removed = set()
    for pat in removes:
        hit = {n for n in names if fnmatch.fnmatchcase(n, pat)}
        if not hit:
            sys.exit(f"remove sem correspondência: {pat}")
        removed |= hit

    body, central = bytearray(), bytearray()

    def put_entry(name, path, orig_cd):
        data = open(path, "rb").read()
        ts = os.path.getmtime(path)
        crc = zlib.crc32(data)
        method = struct.unpack_from("<H", orig_cd, 10)[0] if orig_cd else 8
        if method == 8:
            co = zlib.compressobj(9, zlib.DEFLATED, -15)
            comp = co.compress(data) + co.flush()
        else:
            comp = data
        seed = hashlib.sha256(name.encode() + crc.to_bytes(4, "little")).digest()
        enc = zipcrypto_encrypt(comp, pwd, crc >> 24, seed)
        bname = name.encode("cp437")
        if orig_cd:
            # herda data e extra da entrada original: o hash da saída não depende do mtime local
            tm, dt = struct.unpack_from("<HH", orig_cd, 12)
            nl, xl = struct.unpack_from("<HH", orig_cd, 28)
            extra = bytes(orig_cd[46 + nl:46 + nl + xl])
        else:
            tm, dt = dos_datetime(ts)
            extra = ntfs_extra(ts)
        local = struct.pack("<IHHHHHIIIHH", 0x04034B50, 20, 1, method, tm, dt, crc, len(enc), len(data), len(bname), 0)
        cd = struct.pack("<IHHHHHHIIIHHHHHII", 0x02014B50, 63, 20, 1, method, tm, dt, crc, len(enc), len(data),
                         len(bname), len(extra), 0, 0, 0, 0x20, len(body))
        body.extend(local + bname + enc)
        central.extend(cd + bname + extra)

    changed = 0
    for name, cd in recs:
        if name in removed:
            changed += 1
            continue
        if name in puts:
            put_entry(name, puts[name][1], cd)
            changed += 1
            continue
        off, csize = struct.unpack_from("<I", cd, 42)[0], struct.unpack_from("<I", cd, 20)[0]
        nl, xl = struct.unpack_from("<HH", z, off + 26)
        rec = z[off:off + 30 + nl + xl + csize]
        cd = bytearray(cd)
        struct.pack_into("<I", cd, 42, len(body))
        body.extend(rec)
        central.extend(cd)
    for name, (op, path) in puts.items():
        if op == "add":
            put_entry(name, path, None)
            changed += 1

    count = sum(1 for n, _ in recs if n not in removed) + sum(1 for o, _ in puts.values() if o == "add")
    eocd = bytearray(eocd)
    struct.pack_into("<HHII", eocd, 8, count, count, len(central), len(body))
    zipbytes = bytes(body + central + eocd)

    enc_body = xor_body(zipbytes, key)
    header = bytearray(raw[:hsize])
    struct.pack_into("<I", header, 0x0C, hsize + len(enc_body))
    struct.pack_into("<I", header, 0x18, zlib.crc32(enc_body))
    out = bytes(header) + enc_body
    with open(dst, "wb") as f:
        f.write(out)

    h_in, h_out = hashlib.sha256(raw).hexdigest().upper(), hashlib.sha256(out).hexdigest().upper()
    print(f"entradas: {count} ({changed} mudadas/removidas/adicionadas), {len(out)} bytes")
    print("sha256 saída :", h_out)
    if not removes and not puts:
        print("sha256 base  :", h_in)
        print("IDÊNTICO" if h_in == h_out else "DIFERENTE: o empacotador não reproduz o original")


main()
