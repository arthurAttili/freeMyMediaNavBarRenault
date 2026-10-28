"""Escreve uma linha de texto num BMP de fundo da central (8 bits paletado), sem mudar o formato.

O arquivo de saída tem o mesmo tamanho em bytes, o mesmo cabeçalho e a mesma quantidade de
cores na paleta que o original. As cores novas do texto (a cor dele e os tons da borda
suavizada) vão para entradas da paleta que nenhum pixel usa. A cor-chave amarela (255,255,0)
fica intacta. Só mudam os pixels dentro da caixa do texto.

A central pede a fonte Tahoma pelo nome (AppMain.exe e MicomManager.exe), então o padrão é a
Tahoma Bold do Windows.

A saída é imagem da LG/Renault modificada: grave FORA do repositório.

Uso: python -I fundo_texto.py <entrada.bmp> <saida.bmp> "<texto>" <y_centro> <tamanho_px>
                              [--x <x_centro>] [--cor RRGGBB] [--fonte arquivo.ttf]
Requer: pillow.
"""
import argparse
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

CHAVE = (255, 255, 0)


def le_bmp(caminho):
    d = bytearray(open(caminho, "rb").read())
    if d[:2] != b"BM":
        sys.exit("não é BMP: " + caminho)
    off, hs = struct.unpack_from("<II", d, 10)
    w, h, _, bpp, comp = struct.unpack_from("<iiHHI", d, 18)
    if bpp != 8 or comp != 0:
        sys.exit(f"esperava 8 bits sem compressão, veio {bpp} bits / compressão {comp}")
    n = (off - 14 - hs) // 4
    pal = [tuple(d[14 + hs + 4 * i + k] for k in (2, 1, 0)) for i in range(n)]
    return d, off, hs, w, h, pal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("saida")
    ap.add_argument("texto")
    ap.add_argument("y", type=int, help="centro vertical do texto, em px da tela")
    ap.add_argument("tam", type=int, help="altura da fonte em px")
    ap.add_argument("--x", type=int, default=None, help="centro horizontal (padrão: meio da imagem)")
    ap.add_argument("--cor", default="ffffff")
    ap.add_argument("--fonte", default=r"C:\Windows\Fonts\tahomabd.ttf")
    a = ap.parse_args()

    d, off, hs, w, h, pal = le_bmp(a.entrada)
    passo = (w + 3) & ~3
    topo_baixo = struct.unpack_from("<i", d, 22)[0] < 0
    h = abs(h)

    def idx(x, y):
        return off + (y if topo_baixo else h - 1 - y) * passo + x

    usados = {d[idx(x, y)] for y in range(h) for x in range(w)}
    livres = [i for i in range(len(pal)) if i not in usados and pal[i] != CHAVE]

    # máscara do texto com borda suavizada
    fonte = ImageFont.truetype(a.fonte, a.tam)
    cx = w // 2 if a.x is None else a.x
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((cx, a.y), a.texto, font=fonte, fill=255, anchor="mm")
    caixa = mask.getbbox()
    if not caixa:
        sys.exit("texto vazio")
    if caixa[0] < 0 or caixa[2] > w or caixa[1] < 0 or caixa[3] > h:
        sys.exit("texto sai da imagem: " + str(caixa))

    cor = tuple(int(a.cor[i:i + 2], 16) for i in (0, 2, 4))
    fundo = [pal[d[idx(x, y)]] for y in range(caixa[1], caixa[3]) for x in range(caixa[0], caixa[2])]
    media = tuple(sum(c[k] for c in fundo) // len(fundo) for k in range(3))

    # cor do texto: usa a entrada existente se houver, senão a primeira livre
    novas = {}
    if cor in pal and (pal.index(cor) in usados or pal.index(cor) in livres):
        i = pal.index(cor)
        if i in livres:
            livres.remove(i)
            novas[i] = cor
    elif livres:
        i = livres.pop(0)
        pal[i] = cor
        novas[i] = cor
    else:
        sys.exit("paleta sem entrada livre para a cor do texto")
    # tons intermediários entre o fundo médio e o texto nas entradas que sobraram
    for k, i in enumerate(livres):
        t = (k + 1) / (len(livres) + 1)
        pal[i] = tuple(round(media[c] * (1 - t) + cor[c] * t) for c in range(3))
        novas[i] = pal[i]
    validos = sorted(usados | set(novas))
    validos = [i for i in validos if pal[i] != CHAVE]

    def perto(rgb):
        return min(validos, key=lambda i: sum((pal[i][c] - rgb[c]) ** 2 for c in range(3)))

    mudou = 0
    for y in range(caixa[1], caixa[3]):
        for x in range(caixa[0], caixa[2]):
            al = mask.getpixel((x, y)) / 255
            if al < 0.08:
                continue
            o = idx(x, y)
            bg = pal[d[o]]
            alvo = tuple(bg[c] * (1 - al) + cor[c] * al for c in range(3))
            n = perto(alvo)
            if n != d[o]:
                d[o] = n
                mudou += 1
    for i, rgb in novas.items():
        p = 14 + hs + 4 * i
        d[p:p + 3] = bytes((rgb[2], rgb[1], rgb[0]))

    open(a.saida, "wb").write(d)
    print(f"{mudou} pixels em {caixa}; paleta: {len(pal)} entradas, novas {sorted(novas)}", file=sys.stderr)


if __name__ == "__main__":
    main()
