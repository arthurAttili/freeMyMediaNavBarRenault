"""Lista os zips do NNG (sem extrair para disco) e mostra os arquivos de configuração em texto.

uso: python -I nngcfg.py <pasta NNG>
"""
import os
import sys
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
root = sys.argv[1]
for dp, _, fn in os.walk(root):
    for f in fn:
        if not f.lower().endswith(".zip"):
            continue
        p = os.path.join(dp, f)
        try:
            z = zipfile.ZipFile(p)
        except zipfile.BadZipFile:
            print("== não é zip padrão:", os.path.relpath(p, root))
            continue
        infos = z.infolist()
        exts = {}
        for i in infos:
            e = os.path.splitext(i.filename)[1].lower()
            exts[e] = exts.get(e, 0) + 1
        print(f"== {os.path.relpath(p, root)}: {len(infos)} entradas {dict(sorted(exts.items(), key=lambda x: -x[1])[:8])}")
        for i in infos:
            n = i.filename.lower()
            if n.endswith((".txt", ".ini")) and i.file_size < 20000 and any(k in n for k in ("sys", "brand", "feature", "skin", "device")):
                try:
                    txt = z.read(i).decode("utf-8", "replace")
                except RuntimeError as ex:
                    print("   ", i.filename, "->", ex)
                    continue
                print(f"   --- {i.filename} ({i.file_size})")
                for line in txt.splitlines()[:60]:
                    if line.strip():
                        print("     ", line[:150])
