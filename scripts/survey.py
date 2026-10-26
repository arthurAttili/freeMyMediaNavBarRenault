"""Mapa do conteúdo extraído: árvore resumida, extensões, arquivos de controle e binários principais."""
import collections
import os
import sys

root = sys.argv[1]
files = []
for dp, dn, fn in os.walk(root):
    for f in fn:
        p = os.path.join(dp, f)
        files.append((os.path.relpath(p, root).replace("\\", "/"), os.path.getsize(p)))

print("total", len(files), sum(s for _, s in files))


def depth_summary(level):
    agg = collections.defaultdict(lambda: [0, 0])
    for p, s in files:
        parts = p.split("/")
        k = "/".join(parts[:level]) if len(parts) > level else p
        agg[k][0] += 1
        agg[k][1] += s
    return agg


print("\n== nível 3 ==")
for k, (c, s) in sorted(depth_summary(3).items(), key=lambda x: -x[1][1]):
    print(f"{c:6} {s / 1e6:9.1f} MB  {k}")

print("\n== extensões ==")
ext = collections.Counter()
exts = collections.defaultdict(int)
for p, s in files:
    e = os.path.splitext(p)[1].lower() or "(sem)"
    ext[e] += 1
    exts[e] += s
for e, c in ext.most_common(40):
    print(f"{e:10} {c:6} {exts[e] / 1e6:8.1f} MB")

print("\n== arquivos na raiz de upgrade/ e maiores que 2 MB ==")
for p, s in sorted(files, key=lambda x: -x[1]):
    if p.count("/") <= 1 or s > 2_000_000:
        print(f"{s:11}  {p}")
