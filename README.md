# freeMyMediaNavBarRenault

Estudo do Media Nav Evolution v1 (LG, Windows CE 6), a central multimídia do Sandero Expression 2016 vendido no Brasil. O repositório tem o relatório e os scripts Python que leem o pacote de atualização sem executar nada dele.

O resultado está em [RELATORIO.md](RELATORIO.md): versões, formato do `upgrade.lgu`, como a central valida a atualização, o que dá para personalizar e por que Android Auto não roda nessa geração.

## O que não está aqui

O firmware é da LG e da Renault, então o repositório não traz nenhum binário dele. Para refazer a análise:

1. Baixe o `upgrade.lgu` 9.1.3. O link está na página https://www.gps-rlink.com/medianav/update-software-medianav/.
2. Confira o hash. O arquivo analisado tem 222.387.531 bytes e este SHA-256:

   ```
   090FFAEF5C4047A1BCD6C9A0114C4E8569E63513A11088C532C5B0F609AEB568
   ```

   No PowerShell: `Get-FileHash .\upgrade.lgu -Algorithm SHA256`

3. Baixe o `xorArray.h` do MediaNavMods para dentro de `scripts\`:
   https://raw.githubusercontent.com/yosicovich/MediaNavMods/master/pc/lgutool/lgu2dir/xorArray.h

## Uso

Guarde o pacote e a extração em pastas fora de `scripts\`. Rode o Python sempre com `-I`.

```
python -I scripts\lgu_unpack.py <caminho>\upgrade.lgu <saida> --list
python -I scripts\lgu_unpack.py <caminho>\upgrade.lgu <saida>
python -I scripts\survey.py <saida>\root
python -I scripts\components.py <saida>\root\upgrade
python -I scripts\strgrep.py <saida>\root\upgrade "<regex>" "Storage Card\System\UpgradeManager.exe"
python -I scripts\nngcfg.py "<saida>\root\upgrade\Storage Card4\NNG"
```

## Aviso

Isto é estudo. Nenhum script grava em pendrive ou na central. Instalar firmware que não veio da Renault pode deixar a central sem ligar, e a v1 não aceita voltar para uma versão anterior.

## Créditos

O formato LGU/ULC2 foi documentado pelo projeto [MediaNavMods](https://github.com/yosicovich/MediaNavMods) (djeman/FavreMod) e empacotado pelo [LGU-file-tools](https://github.com/m-a-x-s-e-e-l-i-g/LGU-file-tools).
