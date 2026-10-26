"""Decodifica upgrade.lgu (LGU0/ULC2) sem executar nada do pacote.

Formato (lido de yosicovich/MediaNavMods, pc/lgutool/lgu2dir):
  0x000  magic 'LGU0' ou 'ULC2'
  0x004  u32 versão do cabeçalho (7)
  0x008  u32 tamanho do cabeçalho (0x400)
  0x00C  u32 tamanho total do arquivo
  0x018  u32 CRC-32 do corpo (offset 0x400 até o fim)
  0x024  UTF-16 com 180 '0' (campo reservado)
  0x400  corpo = ZIP com ZipCrypto, XOR com tabela de 1024 bytes (índice reinicia a cada 1 KB)

uso: python -I lgu_unpack.py <upgrade.lgu> <pasta_saida> [--list]

Precisa de xorArray.h ao lado deste script. Ele é de terceiro e não vem no repositório:
  https://raw.githubusercontent.com/yosicovich/MediaNavMods/master/pc/lgutool/lgu2dir/xorArray.h
"""
import os
import re
import struct
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PASSWORDS = {b"ULC2": b"u8u8l^-^8@E4g_H2kq8X_pack", b"LGU0": b"I_LOVE_LG^^"}


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


def main():
    src, out = sys.argv[1], sys.argv[2]
    only_list = "--list" in sys.argv
    raw = open(src, "rb").read()
    magic, ver, hsize, total, _, _, crc = struct.unpack_from("<4sIIIIII", raw, 0)
    body = raw[hsize:]
    print(f"magic={magic.decode()} ver={ver} header={hsize:#x} total={total} (real {len(raw)})")
    print(f"crc32 declarado={crc:#010x} calculado={zlib.crc32(body):#010x}")

    key = load_tables()[magic]
    assert len(key) == 1024
    # XOR com a tabela repetida; bytes.translate não serve, então usa int grande por blocos
    rep = (key * (1 << 12))  # 4 MiB
    os.makedirs(out, exist_ok=True)
    zpath = os.path.join(out, "_decoded.zip")
    with open(zpath, "wb") as fz:
        for off in range(0, len(body), len(rep)):
            chunk = body[off:off + len(rep)]
            k = rep[:len(chunk)]
            fz.write((int.from_bytes(chunk, "little") ^ int.from_bytes(k, "little")).to_bytes(len(chunk), "little"))
    del raw, body

    z = zipfile.ZipFile(zpath)
    z.setpassword(PASSWORDS[magic])
    infos = z.infolist()
    tot_u = sum(i.file_size for i in infos)
    print(f"zip ok: {len(infos)} entradas, {tot_u} bytes descomprimidos, comentário={z.comment[:120]!r}")
    for i in infos:
        print(f"  {'E' if i.flag_bits & 1 else ' '} m{i.compress_type} {i.file_size:11} {i.date_time[0]}-{i.date_time[1]:02}-{i.date_time[2]:02} {i.filename}")
    if only_list:
        return
    dest = os.path.join(out, "root")
    for i in infos:
        # bloqueia caminho absoluto / '..' antes de gravar
        norm = os.path.normpath(i.filename.replace("\\", "/"))
        if norm.startswith("..") or os.path.isabs(norm):
            print("ignorado (caminho inseguro):", i.filename)
            continue
        z.extract(i, dest)
    print("extraído em", dest)


main()
