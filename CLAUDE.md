# freeMyMediaNavBarRenault

Estudo do Media Nav Evolution v1 (LG ULC2, WinCE 6.0, MIPS Au13xx) do Sandero 2016 brasileiro. O objetivo é entender o que dá para atualizar e personalizar sem travar a central. Os achados ficam em `RELATORIO.md`.

## Regras

- **Nunca executar nada do firmware.** Só leitura estática: parse, strings, listagem.
- **Nunca gravar em pendrive nem no carro.** Nenhum script deste repo prepara mídia de instalação, a não ser que o Arthur peça com todas as letras e confirme.
- **Repo público:** nenhum binário da LG/Renault entra no git (`.gitignore` cobre `*.lgu`, `*.bin`, `*.hex`, `*.zip`, `firmware/`, `extract/`). O `scripts/xorArray.h` é do MediaNavMods e também fica fora.
- Pacote baixado e extração ficam fora de `scripts/`. Rodar Python com `-I` e passar caminhos por argumento.
- Antes de baixar arquivo acima de 2 GB, perguntar.

## Onde estão os dados

- Pacote 9.1.3 e extração: `C:\Dev\medianav-sandero2016\` (`firmware\9.1.3\upgrade.lgu`, `extract\9.1.3\root\upgrade\`).
- SHA-256 do `upgrade.lgu` analisado: `090FFAEF5C4047A1BCD6C9A0114C4E8569E63513A11088C532C5B0F609AEB568`.

## Armadilhas

- `upgrade.lgu` não abre como ZIP direto. O corpo (a partir de 0x400) é XOR com tabela de 1024 bytes cujo índice reinicia a cada 1 KB, e por baixo vem um ZIP ZipCrypto com senha fixa por magic (ULC2/LGU0). Ver `scripts/lgu_unpack.py`.
- O CRC-32 em 0x18 é do corpo, sem o cabeçalho.
- O 9.1.3 é o mesmo para todas as regiões. A central escolhe a variante (`_weu`, `_eeu`, `_amr`, `_oth`) pelo SKU gravado no MCU.
- Android Auto e CarPlay não existem na v1. Isso já foi verificado no código; não reabrir sem dado novo.
- No Windows, `print` de texto UTF-16 quebra no console cp1252. Use `sys.stdout.reconfigure(encoding="utf-8")`. Com `-I` o Python ignora `PYTHONIOENCODING`.
