"""Lê a tabela de textos (RT_STRING) de uma LangDll do AppMain e grava {id: texto}.

Só leitura. Cada bloco RT_STRING tem 16 entradas (uint16 tamanho + UTF-16);
o id do texto é (id_do_bloco - 1) * 16 + posição.

Uso: python -I langdll_strings.py <LangDllPTBR.dll> <saida.json>
Requer: pefile.
"""
import json
import struct
import sys

import pefile


def read_strings(path):
    pe = pefile.PE(path)
    out = {}
    for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if t.id != 6:           # RT_STRING
            continue
        for blk in t.directory.entries:
            for lang in blk.directory.entries:
                d = lang.data.struct
                raw = pe.get_data(d.OffsetToData, d.Size)
                o = 0
                for k in range(16):
                    n = struct.unpack_from("<H", raw, o)[0]
                    o += 2
                    if n:
                        out[(blk.id - 1) * 16 + k] = raw[o:o + 2 * n].decode("utf-16le")
                        o += 2 * n
    return out


if __name__ == "__main__":
    s = read_strings(sys.argv[1])
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=0)
    print(len(s), "textos", file=sys.stderr)
