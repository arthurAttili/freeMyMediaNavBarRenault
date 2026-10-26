"""Strings ASCII e UTF-16 de binários escolhidos, filtradas por palavra-chave. Nada é executado.

uso: python -I strgrep.py <pasta upgrade/> <regex> <arquivo relativo> [...]
"""
import os
import re
import sys

root, pat, rels = sys.argv[1], re.compile(sys.argv[2], re.I), sys.argv[3:]
for rel in rels:
    d = open(os.path.join(root, rel), "rb").read()
    out = [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{5,}", d)]
    out += [m.group().decode("utf-16le") for m in re.finditer(rb"(?:[\x20-\x7e]\x00){5,}", d)]
    hits = []
    for s in out:
        if pat.search(s) and s not in hits:
            hits.append(s[:160])
    print(f"===== {rel}: {len(hits)}")
    for s in hits[:70]:
        print("  ", s)
