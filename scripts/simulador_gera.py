"""Gera o simulador local das telas do AppMain (rádio, mídia, telefone, configurações...).

Lê a extração do pacote (só leitura), tira o layout do AppMain.exe e os textos da
LangDllPTBR.dll, converte os BMPs usados para PNG (amarelo puro vira transparente) e
monta uma pasta com index.html + data.js + img/ que abre direto no navegador.
Nada do firmware é executado.

A pasta de saída tem imagens da LG/Renault: deixe-a FORA do repositório.

Uso: python -I simulador_gera.py <extract/.../root/upgrade> <pasta de saída> [<pasta Img com fundos modificados>]

A terceira pasta, se vier, tem a mesma estrutura de Img (<tema>/common/<fundo>.bmp). A página
ganha a opção "fundos modificados" para comparar com o original.
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
BOTOES = {"botao", "botao2", "softkey"}
BARRA = "0x14c20"                        # barra de status (relógio, temperatura, celular), desenhada por cima das telas
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
    "0x14c20": "Barra de status", "0x206c8": "Info 4x4",
}

# Funções que carregam o índice de common\home_bg.bmp / common\etc_bg.bmp no AppMain 9.1.3.
# O fundo não passa pelas criadoras de widget, então a pasta das imagens chutaria errado.
FUNDO_FN = {fn: "home_bg" for fn in ("0x206c8", "0x226a4", "0x27adc", "0x28ee4", "0x3a744", "0x5b584",
                                     "0x605b4", "0x66444", "0xc4fb8")}
FUNDO_FN["0x25b60"] = "etc_bg"     # aviso "Atenção!" da partida

# Tela de descanso (rádio desligado). Quem desenha é o MicomManager.exe, não o AppMain:
# limpa 800x480, põe common\etc_bg.bmp e o relógio grande (VA 0x1e000-0x1e6b4 no 9.1.3).
# Modo 24 h (byte 0xb02 da config != 0): dígitos de 60x85 em y 188, dois-pontos de 25 px em x 388.
# No modo 12 h os dígitos vão para x 224/292/393/461, o dois-pontos para 360 e am/pm para 533.
DESCANSO = {
    "fn": "micom:descanso", "nome": "Descanso (rádio desligado)", "pasta": "etc", "grupo": "Início",
    "fundo": "etc_bg", "origem": "MicomManager", "sem_barra": True, "conferida": True,
    "widgets": [{"id": "micom:descanso/" + at, "at": at, "tipo": "imagem", "img": -1, "nome": nome,
                 "rect": rect, "str": None, "var_de": None, "rect_src": [at, None, None, None], "relogio": k}
                for at, nome, rect, k in (
                    ("0x1e38c", r"etc\etc_clock_font.bmp", [252, 188, 60, 85], 0),
                    ("0x1e3d8", r"etc\etc_clock_font.bmp", [320, 188, 60, 85], 1),
                    ("0x1e5f8", r"etc\etc_clock_font_colon.bmp", [388, 188, 25, 85], None),
                    ("0x1e428", r"etc\etc_clock_font.bmp", [421, 188, 60, 85], 2),
                    ("0x1e474", r"etc\etc_clock_font.bmp", [489, 188, 60, 85], 3))],
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


def main(up, out, mod=None):
    sysdir = find_ci(up, "Storage Card/System/AppMain.exe")
    if not sysdir:
        sys.exit("AppMain.exe não encontrado em " + up)
    sysdir = os.path.dirname(sysdir)
    imgroot = os.path.join(sysdir, "Img")

    widgets, _ = appmain_layout.extract(os.path.join(sysdir, "AppMain.exe"))
    textos = langdll_strings.read_strings(find_ci(sysdir, "data/LangDllPTBR.dll"))

    os.makedirs(out, exist_ok=True)
    imgs = {}          # caminho original -> {arq: {tema: png}, tam: {tema: [w, h]}}
    for name in sorted({w["name"] for w in widgets if w["name"]} | {w["nome"] for w in DESCANSO["widgets"]}):
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
    fundos_mod = {}
    for t in THEMES if mod else ():
        for v in sorted(set(BG.values()) | {"etc_bg"}):
            src = find_ci(os.path.join(mod, t), "common/" + v + ".bmp")
            if src:
                rel = "mod/" + t + "/common/" + v + ".png"
                to_png(src, os.path.join(out, "img", rel))      # sempre refaz: a pasta muda entre testes
                fundos_mod.setdefault(t, {})[v] = "img/" + rel

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
        lista = []
        for i, w in enumerate(items):
            x, y, ww, hh = w["rect"]
            # Ramo alternativo: mesma imagem e mesmo tipo já criados perto daqui. O AppMain monta
            # layouts diferentes por tema (Dacia x Renault); a página escolhe o ramo que encaixa no sprite.
            # Botão de imagem diferente no mesmo retângulo também é ramo: o tile de baixo à
            # esquerda do início é Mapa, Driving Eco, Info 4x4 ou Veículo conforme o carro.
            raiz = next((lista[j]["var_de"] or lista[j]["id"] for j, o in enumerate(items[:i])
                         if o["tipo"] == w["tipo"] and
                         ((o["img"] == w["img"] and
                           (abs(o["rect"][0] - x) < 60 and abs(o["rect"][1] - y) < 60 if w["img"] >= 0
                            else o["rect"] == w["rect"])) or
                          (w["tipo"] in BOTOES and o["rect"] == w["rect"]))), None)
            lista.append({
                "id": fn + "/" + w["at"], "at": w["at"], "tipo": w["tipo"], "img": w["img"], "nome": w["name"],
                "rect": w["rect"], "str": w["str"],
                "var_de": raiz, "rect_src": w["rect_src"],
            })
        telas.append({"fn": fn, "nome": nome, "pasta": pasta, "grupo": GRUPO.get(pasta, "Outras"),
                      "fundo": FUNDO_FN.get(fn) or BG.get(pasta, "home_bg" if pasta == "popup" else "etc_bg"),
                      "widgets": lista, "conferida": fn in NOMES})
    telas.insert(0, DESCANSO)

    usados = {w["str"] for w in widgets if w["str"] is not None}
    dados = {"temas": THEMES, "telas": telas, "barra": BARRA, "imgs": imgs, "fundos": fundos, "fundos_mod": fundos_mod or None,
             "textos": {str(k): v for k, v in textos.items()}, "textos_usados": sorted(usados)}
    with open(os.path.join(out, "data.js"), "w", encoding="utf-8") as f:
        f.write("window.SIM = ")
        json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "simulador", "index.html")
    shutil.copy(tpl, os.path.join(out, "index.html"))
    print(len(telas), "telas,", len(widgets), "widgets,", len(imgs), "imagens ->", out, file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
