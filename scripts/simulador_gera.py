"""Gera o simulador local das telas do AppMain (rádio, mídia, telefone, configurações...).

Lê a extração do pacote (só leitura), tira o layout do AppMain.exe e os textos da
LangDllPTBR.dll, converte os BMPs usados para PNG (amarelo puro vira transparente) e
monta uma pasta com index.html + data.js + img/ que abre direto no navegador.
Nada do firmware é executado.

A pasta de saída tem imagens da LG/Renault: deixe-a FORA do repositório.

Uso: python -I simulador_gera.py <extract/.../root/upgrade> <pasta de saída>
Requer: pefile, capstone, pillow.
"""
import collections
import json
import os
import shutil
import sys

from PIL import Image, ImageChops

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # -I tira a pasta do script do path
import appmain_layout    # noqa: E402
import langdll_strings   # noqa: E402

THEMES = ["M1", "M0", "M1_INV"]          # M1 = Renault (preto), M0 = Dacia (azul), M1_INV = claro
BG = {"home": "home_bg", "fm radio": "fmradio_bg", "media": "media_bg", "phone": "phone_bg",
      "setting": "setting_bg", "eco": "eco_bg"}
GRUPO = {"home": "Início", "fm radio": "Rádio", "media": "Mídia", "phone": "Telefone",
         "setting": "Configurações", "eco": "Driving Eco", "popup": "Pop-ups"}

# Nomes conferidos à mão no layout (função do AppMain -> tela).
NOMES = {
    "0x226a4": "Início", "0x9b1c0": "FM principal", "0x993a0": "FM predefinidas",
    "0x86b28": "AM principal", "0x84ee8": "AM lista", "0x47a70": "USB player", "0x4a400": "USB lista",
    "0x37ca0": "Bluetooth áudio", "0x3db78": "iPod player", "0x411a4": "iPod lista", "0x2bb18": "aha",
    "0x4e96c": "Telefone: chamadas", "0x5b584": "Telefone: discar", "0x605b4": "Telefone: discar 2",
    "0x53314": "Telefone: agenda", "0xbd320": "Configurações do sistema", "0xb1378": "Configuração da tela",
    "0xb6430": "Volume", "0xad504": "Configurações de áudio", "0xbb804": "Balanço / fader",
    "0xbf9a0": "Relógio / unidades", "0xc5ba8": "Ajuste de hora", "0xaf074": "Bluetooth",
    "0xc145c": "Detecção de obstáculo", "0x101bcc": "Driving Eco 1", "0x105814": "Driving Eco 2",
    "0xfe6c8": "Driving Eco 3", "0xaa7c8": "Ligar motor à distância", "0x66444": "Smartphone",
}


def find_ci(root, rel):
    """Resolve caminho relativo sem diferenciar maiúsculas (a central é Windows CE)."""
    cur = root
    for part in rel.replace("\\", "/").split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            cur = os.path.dirname(cur)
            continue
        hit = next((e for e in os.listdir(cur) if e.lower() == part.lower()), None) if os.path.isdir(cur) else None
        if hit is None:
            return None
        cur = os.path.join(cur, hit)
    return cur if os.path.isfile(cur) else None


def to_png(src, dst):
    im = Image.open(src).convert("RGB")
    r, g, b = im.split()
    chave = ImageChops.multiply(ImageChops.multiply(r.point(lambda v: 255 if v >= 248 else 0),
                                                    g.point(lambda v: 255 if v >= 248 else 0)),
                                b.point(lambda v: 255 if v <= 8 else 0))    # amarelo puro = cor-chave da LG
    im.putalpha(ImageChops.invert(chave))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst, optimize=True)
    return im.size


def slug(rel):
    return rel.replace("..\\COMMON\\", "COMMON\\").replace("\\", "/").replace(" ", "_").lower()[:-4] + ".png"


def main(up, out):
    sysdir = find_ci(up, "Storage Card/System/AppMain.exe")
    if not sysdir:
        sys.exit("AppMain.exe não encontrado em " + up)
    sysdir = os.path.dirname(sysdir)
    imgroot = os.path.join(sysdir, "Img")

    widgets, _ = appmain_layout.extract(os.path.join(sysdir, "AppMain.exe"))
    textos = langdll_strings.read_strings(find_ci(sysdir, "data/LangDllPTBR.dll"))

    os.makedirs(out, exist_ok=True)
    imgs = {}          # caminho original -> {arq: {tema: png}, tam: {tema: [w, h]}}
    for name in sorted({w["name"] for w in widgets if w["name"]}):
        info = {"arq": {}, "tam": {}}
        for t in THEMES:
            src = find_ci(os.path.join(imgroot, t), name)
            if not src:
                continue
            rel = slug(name) if name.startswith("..") else t + "/" + slug(name)
            dst = os.path.join(out, "img", rel)
            tam = to_png(src, dst) if not os.path.exists(dst) else Image.open(dst).size
            info["arq"][t] = "img/" + rel
            info["tam"][t] = list(tam)
        imgs[name] = info
    fundos = {}
    for t in THEMES:
        for v in sorted(set(BG.values()) | {"etc_bg"}):
            src = find_ci(os.path.join(imgroot, t), "common/" + v + ".bmp")
            if src:
                rel = t + "/common/" + v + ".png"
                if not os.path.exists(os.path.join(out, "img", rel)):
                    to_png(src, os.path.join(out, "img", rel))
                fundos.setdefault(t, {})[v] = "img/" + rel

    by_fn = collections.OrderedDict()
    for w in sorted(widgets, key=lambda w: int(w["fn"], 16)):
        by_fn.setdefault(w["fn"], []).append(w)
    telas = []
    for fn, items in by_fn.items():
        pastas = collections.Counter(w["name"].split("\\")[0].lower() for w in items
                                     if w["name"] and not w["name"].startswith(".."))
        pasta = pastas.most_common(1)[0][0] if pastas else "etc"
        prim = [textos.get(w["str"]) for w in items if w["str"] in textos]
        nome = NOMES.get(fn) or (prim[0] if prim else fn)
        lista, prev_str = [], None
        for i, w in enumerate(items):
            x, y, ww, hh = w["rect"]
            # Ramo alternativo: mesma imagem e mesmo tipo já criados perto daqui. O AppMain monta
            # layouts diferentes por tema (Dacia x Renault); a página escolhe o ramo que encaixa no sprite.
            raiz = next((lista[j]["var_de"] or lista[j]["id"] for j, o in enumerate(items[:i])
                         if o["img"] == w["img"] and o["tipo"] == w["tipo"] and
                         (abs(o["rect"][0] - x) < 60 and abs(o["rect"][1] - y) < 60 if w["img"] >= 0
                          else o["rect"] == w["rect"])), None)
            lista.append({
                "id": fn + "/" + w["at"], "at": w["at"], "tipo": w["tipo"], "img": w["img"], "nome": w["name"],
                "rect": w["rect"], "str": w["str"] if w["str"] != prev_str else None,
                "var_de": raiz, "rect_src": w["rect_src"],
            })
            prev_str = w["str"]
        telas.append({"fn": fn, "nome": nome, "pasta": pasta, "grupo": GRUPO.get(pasta, "Outras"),
                      "fundo": BG.get(pasta, "home_bg" if pasta == "popup" else "etc_bg"), "widgets": lista, "conferida": fn in NOMES})

    usados = {w["str"] for w in widgets if w["str"] is not None}
    dados = {"temas": THEMES, "telas": telas, "imgs": imgs, "fundos": fundos,
             "textos": {str(k): v for k, v in textos.items()}, "textos_usados": sorted(usados)}
    with open(os.path.join(out, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.SIM = ")
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulador", "index.html")
    shutil.copy(tpl, os.path.join(out, "index.html"))
    print(len(telas), "telas,", len(widgets), "widgets,", len(imgs), "imagens ->", out, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
