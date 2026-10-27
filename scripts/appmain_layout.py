"""Extrai do AppMain.exe (9.1.3) as chamadas que criam os widgets das telas.

Só leitura estática: desmonta o código MIPS e acompanha constantes em registradores
e na pilha até as funções que criam botão, imagem e texto. Nada do firmware é executado.

Para cada widget sai: função (= tela), função criadora, id e caminho da imagem,
retângulo [x, y, w, h], id do último texto pedido antes da chamada e o endereço das
instruções que carregam x, y, w e h (é ali que um patch de posição mexeria).

Uso: python -I appmain_layout.py <AppMain.exe> <saida.json>
Requer: pefile, capstone.
"""
import collections
import json
import re
import struct
import sys

import capstone
import pefile
from capstone import mips

# Valem para o AppMain do 9.1.3. Outra versão precisa reconferir os três.
IMG_TABLE_OFF = 0x178B84   # offset no arquivo da tabela de ponteiros de imagem (id 0 = caution_bg_dark.bmp)
STR_FN = 0x1F074           # get_string(obj, id): o id do texto vai em a1
CREATORS = {
    0x131D1C: "botao",
    0x131C58: "imagem",
    0x12BB64: "softkey",
    0x12BC00: "texto",
    0x1320BC: "botao2",
    0x12BCA8: "texto2",
    0x12BD44: "lista",
    0x12BDE4: "lista2",
}

SKIP_WRITE = {"sw", "sh", "sb", "swc1", "sdc1", "beq", "bne", "beqz", "bnez", "jr", "jalr", "b",
              "bgez", "bltz", "blez", "bgtz", "j", "jal", "nop", ".byte", "mtc1", "mthi", "mtlo"}
CLOBBER = ("v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9")


def extract(path):
    pe = pefile.PE(path, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    data = pe.__data__

    def va2off(va):
        for s in pe.sections:
            a = base + s.VirtualAddress
            if a <= va < a + s.SizeOfRawData:
                return s.PointerToRawData + va - a
        return None

    def wstr(va):
        o = va2off(va)
        if o is None:
            return None
        m = re.match(rb"((?:[\x20-\x7e]\x00){3,})\x00\x00", data[o:o + 300])
        return m.group(1).decode("utf-16le") if m else None

    def img(i):
        if not 0 <= i < 4000:
            return None
        return wstr(struct.unpack_from("<I", data, IMG_TABLE_OFF + i * 4)[0])

    text = pe.sections[0]
    code = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]
    tva = base + text.VirtualAddress
    md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
    md.detail = True
    md.skipdata = True

    # valores: ("c", constante, endereço da instrução) | ("sp", deslocamento, _) | ("hi", lui<<16, _)
    reg, stack = {}, {}
    st = {"fn": tva, "last_str": None}
    out = []
    calls = collections.Counter()

    def step(ins):
        ops, mn = ins.operands, ins.mnemonic
        if mn in ("addiu", "ori", "addi") and len(ops) == 3 and ops[1].type == mips.MIPS_OP_REG:
            dst, src, imm = ins.reg_name(ops[0].reg), ins.reg_name(ops[1].reg), ops[2].imm
            if src == "zero":
                reg[dst] = ("c", imm & 0xFFFF if mn == "ori" else imm, ins.address)
            elif src == "sp":
                reg[dst] = ("sp", imm, None)
            elif src in reg and reg[src][0] in ("hi", "c"):
                v = reg[src][1] | (imm & 0xFFFF) if mn == "ori" else reg[src][1] + imm
                reg[dst] = ("c", v, None)
            else:
                reg.pop(dst, None)
        elif mn == "lui":
            reg[ins.reg_name(ops[0].reg)] = ("hi", (ops[1].imm << 16) & 0xFFFFFFFF, None)
        elif mn == "move":
            d, s = ins.reg_name(ops[0].reg), ins.reg_name(ops[1].reg)
            if s == "zero":
                reg[d] = ("c", 0, None)
            elif s in reg:
                reg[d] = reg[s]
            else:
                reg.pop(d, None)
        elif mn == "sw" and ops[1].type == mips.MIPS_OP_MEM and ins.reg_name(ops[1].mem.base) == "sp":
            r = ins.reg_name(ops[0].reg)
            stack[ops[1].mem.disp] = ("c", 0, None) if r == "zero" else reg.get(r)
        elif ops and ops[0].type == mips.MIPS_OP_REG and mn not in SKIP_WRITE:
            reg.pop(ins.reg_name(ops[0].reg), None)

    def do_call(t, at):
        a1, a2, a3 = reg.get("a1"), reg.get("a2"), reg.get("a3")
        if t == STR_FN and a1 and a1[0] == "c":
            st["last_str"] = a1[1]
        if t in CREATORS and a2 and a2[0] == "c" and a3 and a3[0] == "sp":
            r = [stack.get(a3[1] + k) for k in (0, 4, 8, 12)]
            if all(x and x[0] == "c" for x in r):
                rect = [x[1] for x in r]
                if 0 <= rect[0] <= 800 and 0 <= rect[1] <= 480 and 0 < rect[2] <= 800 and 0 < rect[3] <= 480:
                    calls[CREATORS[t]] += 1
                    out.append({
                        "at": hex(at), "fn": hex(st["fn"]), "tipo": CREATORS[t],
                        "img": a2[1], "name": img(a2[1]), "rect": rect, "str": st["last_str"],
                        "rect_src": [hex(x[2]) if x[2] else None for x in r],
                    })
        for k in CLOBBER:
            reg.pop(k, None)

    pending = None      # alvo do jal esperando o delay slot
    end_after = False   # 'jr $ra' visto: a função acaba depois do delay slot
    for ins in md.disasm(code, tva):
        try:
            if pending is not None:           # delay slot roda antes da chamada
                step(ins)
                do_call(pending, ins.address - 4)
                pending = None
            elif end_after:
                step(ins)
            elif ins.mnemonic == "jal":
                pending = ins.operands[0].imm
            elif ins.mnemonic == "jr" and ins.op_str == "$ra":
                end_after = True
                continue
            else:
                step(ins)
            if end_after:
                reg.clear()
                stack.clear()
                st["last_str"] = None
                st["fn"] = ins.address + 4
                end_after = False
        except Exception:
            reg.clear()
    return out, calls


if __name__ == "__main__":
    res, calls = extract(sys.argv[1])
    with open(sys.argv[2], "w") as f:
        json.dump(res, f, indent=0)
    print(len(res), "widgets em", len({o["fn"] for o in res}), "funções;", dict(calls), file=sys.stderr)
