# Customização do Media Nav Evolution v1 (Sandero 2016)

Estudo feito sobre o pacote 9.1.3, só com leitura estática. Nada aqui foi testado no carro.

**Estado em 26/10/2026:**
- O empacotador `scripts/lgu_pack.py` está testado: reempacotar a 9.1.3 sem mudanças devolve o mesmo SHA-256 do original.
- O pacote lite (9.1.3.1) e o pacote de volta (9.1.3.2) estão gerados e verificados no PC.
- O carro está na **5.2.7.A**. O plano é subir primeiro para a 9.1.3 oficial e só depois aplicar o lite (ver [Plano de instalação](#plano-de-instalação)).

## O que esperar

O ganho de velocidade vai ser pequeno. A LG já deixou o iGO no modo econômico: mapa em 3D achatado (`use_flat3d=1`), relevo desligado (`disable_dem=1`), inicialização em segundo plano (`background_startup=1`), teto de 120 MB de memória e EULA pulada. O que sobra para ajustar é o desenho de prédios 3D e os shaders. Ninguém publicou medição de antes e depois nesta central, nem a Menaco nem a EvoTech.

Também não dá para "tirar o que é inútil" pela atualização oficial. O `upgrade.lgu` **sobrescreve** arquivos na central e não apaga a partição. Arquivo que sai do pacote continua gravado no aparelho. Só `data.zip`, `nngnavi.exe`, `sys.txt` e a pasta `synctool` do iGO são apagados, e só quando o pacote traz substitutos. Isso vem da análise estática do UpgradeManager da 7.0.5 feita no repositório MediaNav-to-Evolution-Upgrade. Na 9.1.3 os mesmos caminhos aparecem nas strings do UpgradeManager, mas não segui o código.

Na prática:
- **Ajuste de configuração** (o `SYS.TXT` do iGO) chega à central pelo pacote.
- **Remoção de arquivo** só reduz o tamanho do pacote. Tirar arquivo da central exige outro caminho, que roda código no aparelho e fica fora deste estudo.

## Como a central sobe

```
kernel (NK.bin, ULC_launcher)
├─ \Storage Card\ATSA.exe
├─ \Storage Card\iTaskMgr.exe
├─ \Storage Card\System\UpgradeManager.exe
│   ├─ MicomManager.exe
│   │   ├─ CodeChecker.exe
│   │   ├─ AppMain.exe ── Blue.exe, MgrIpod.exe, MgrUSB.exe, MgrDAB.exe,
│   │   │                 \Storage Card4\NNG\nngnavi.exe, ULC2_Trigger.exe, explorer.exe
│   │   ├─ Blue.exe
│   │   └─ MgrDAB.exe
│   └─ nngnavi.exe, Synctool.exe (na hora de atualizar)
└─ \MD\ULC2_recovery.exe   (\MD é o pendrive)
```

O `MgrDAB.exe` é lançado duas vezes, pelo AppMain e pelo MicomManager. No Brasil não existe rádio DAB. É o processo mais claramente inútil, mas a atualização não consegue apagá-lo e não sei o que o AppMain faz quando ele não sobe.

O AppMain carrega as imagens da interface numa área de memória própria do driver. As mensagens `[IntMemory Alloc] successed, [SYS]` e `[SYS-4WD]` indicam uma área reservada só para as telas de 4x4.

O registro do Windows CE (`default.fdf` dentro do `NK.bin`) está comprimido no formato de ROM do CE. Ainda não tenho descompressor. Por isso não há ajuste de registro nesta lista.

## O que ocupa espaço

O pacote tem 330 MB descomprimidos.

| Onde | Tamanho | O que é |
|---|---|---|
| `Storage Card\System\Img\M1_INV` | 58,5 MB | Tema da interface (variante invertida) |
| `Storage Card\System\Img\M1` | 48,3 MB | Tema da interface |
| `Storage Card\System\Img\M0` | 45,6 MB | Tema da interface |
| ↳ pasta `4wd` dentro dos três temas | 83 MB no total | Telas de inclinação e tração do Duster 4x4 |
| `Storage Card\System\Img\RVC` | 26,8 MB | Guias da câmera de ré para 24 códigos de carro |
| `Storage Card\NK.bin` | 16 MB | Kernel e drivers |
| `NNG\nngnavi.exe` + `data.zip` | 29,3 MB | Programa e dados do iGO |
| `NNG\ux` (skins) | 29,9 MB | `basic`, `primo`, `lg_renault_ulc20`, `dacia`, `renault` |
| `NNG\content\voice` | 17,9 MB | Só vozes TTS de cazaque e persa |
| `NNG\synctool` | 16,1 MB | Atualizador de mapas, com 32 idiomas próprios |
| `NNG\content\global_cfg` | 12,2 MB | Configuração global e fusos horários |
| `NNG\content\userdata\POI` | 7,3 MB | Concessionárias de 8 marcas |
| `NNG\content\lang` | 3,8 MB | 32 idiomas da navegação |

As skins do iGO dependem umas das outras: `renault` → `lg_renault_ulc20` → `primo` → `basic`. As duas maiores (`basic` e `primo`, 12 MB cada) não podem sair.

## O que tirar e o que ajustar

Classes de risco:
- **Nav**: na pior hipótese, a navegação não abre ou fica feia; o rádio e o resto da central seguem funcionando.
- **Sistema**: pode quebrar uma tela ou uma função do AppMain.
- **Trava**: pode deixar a central sem ligar.

| # | Item | Tamanho | Ganho esperado | Risco | No lite? | Como voltar |
|---|---|---|---|---|---|---|
| 1 | `SYS.TXT`: distâncias de prédios 3D em 0 | 0 | Menos trabalho da GPU no mapa 3D em cidade com prédios no mapa | Nav | Sim | Reinstalar o `SYS.TXT` original |
| 2 | `SYS.TXT`: `simple_shaders=1` | 0 | Mapa mais leve para a Mali, com visual mais simples | Nav | Sim | Idem |
| 3 | 28 idiomas da navegação (ficam pt-BR, pt, es, en-uk) | 3,3 MB | Só pacote menor | Nav | Sim | Pacote original |
| 4 | Vozes de cazaque e persa | 17,9 MB | Só pacote menor | Nav | Sim | Pacote original |
| 5 | Concessionárias de 7 marcas (fica Renault) | 4,7 MB | Só pacote menor. Na central, o iGO carrega esses POIs ao abrir | Nav | Sim | Pacote original |
| 6 | Plugin `india` (fontes do híndi) | 0,15 MB | Só pacote menor | Nav | Sim | Pacote original |
| 7 | Skin `dacia` | 0,16 MB | Nenhum | Nav | Não | — |
| 8 | Telas `4wd` nos três temas | 83 MB | Talvez boot mais rápido, se o AppMain pré-carrega essas imagens | Sistema | Não | — |
| 9 | Um dos temas `M0`/`M1`/`M1_INV` | 45 a 58 MB | Espaço | Sistema ou trava | Não | — |
| 10 | Guias de ré de outros carros (`RVC`) | ~25 MB | Espaço | Sistema | Não | — |
| 11 | 28 `LangDll*.dll` da interface | ~1 MB | Espaço | Sistema | Não | — |
| 12 | `MgrDAB.exe` | 0,46 MB | Um processo a menos na RAM | Sistema | Não | — |
| 13 | Firmware DAB, `firmware.hex`, `booter_standalone.bin`, `NK.bin` | — | — | Trava | Bloqueado no empacotador | — |

Motivos de ter ficado de fora:
- **7:** a skin vem da marca gravada no MCU (`0:dacia, 1:renault`).
- **8 a 11:** o AppMain referencia os caminhos dessas imagens e DLLs pelo nome. Não sei qual tema e qual código de ré o Sandero usa: `X52_PH1` e `X52_PH2_*` são da plataforma do Logan e do Sandero II, mas falta confirmar. Errar aqui pode deixar uma tela em branco ou o AppMain caindo em loop.
- **12:** dois processos o lançam e não sei como reagem à falta dele.
- **8 a 12 em geral:** nem resolveriam nada pela atualização oficial, que não apaga arquivo.

### Outras chaves do iGO

Estas chaves existem no `nngnavi.exe` 9.12, mas não ponho no lite porque não confirmei em que seção do `SYS.TXT` cada uma entra:

| Chave | Para que serve |
|---|---|
| `show_fps` | Mostra quadros por segundo na tela. É o jeito de medir o ganho dos itens 1 e 2 antes e depois |
| `max_fps` | Teto de quadros por segundo |
| `3d_buildings`, `3d_landmarks`, `show_landmark` | Prédios e pontos de referência em 3D |
| `menu_animation`, `disable_smooth_anim`, `building_animation`, `auto_camera_animation` | Animações de menu e de câmera |

Para descobrir a seção, o próximo passo é procurar no `nngnavi.exe` a tabela que liga cada chave à sua seção.

## O que a Menaco e a EvoTech fazem

Nenhuma das duas deixa a central mais rápida. As duas acrescentam funções e exigem a 9.1.3 de fábrica.

- **Menaco** (Wide Road Ltd., paga):
  - Mantém o firmware original rodando e soma Navitel, vídeo com o carro andando, gerenciador de arquivos, equalizador e comandos de volante.
  - A licença é amarrada ao aparelho: o pendrive gera um `.did` que vira `.lic` no site deles.
- **EvoTech** (Yosic, medianav.ru, gratuita):
  - Aplica patches binários sobre a 9.1.3 original. O código está no MediaNavMods.
  - Para reinstalar a mesma versão, o autor manda descer antes para uma "5.0.0 falsa". Isso confirma que a central recusa o pacote de mesma versão.
  - Há relatos de câmera de ré parando a partir da 8.0.5.

As duas se excluem: com a EvoTech instalada, a Menaco não instala.

## Empacotador

`scripts/lgu_pack.py` lê o `.lgu` original, aplica uma lista de mudanças e grava um novo.

Como funciona:
1. Entradas que não mudam são copiadas cruas, já cifradas.
2. As trocadas ou novas passam por deflate e ZipCrypto.
3. O diretório central é refeito, o corpo leva o XOR e o cabeçalho recebe o tamanho e o CRC novos.
4. Uma entrada trocada herda a data da original, então o mesmo `mudancas.txt` sempre gera o mesmo arquivo.

O script recusa trocar ou remover `NK.bin`, `firmware.hex`, `booter_standalone.bin` e o firmware do DAB. Também recusa gravar em unidade removível.

```
python -I scripts\lgu_pack.py <9.1.3>\upgrade.lgu <saida>\upgrade.lgu lite\mudancas.txt
python -I scripts\lgu_unpack.py <saida>\upgrade.lgu <pasta_de_conferencia>
```

Testes de 26/10/2026:

| Teste | Resultado |
|---|---|
| 9.1.3 sem mudanças | SHA-256 `090FFAEF…B568` igual ao original, 9 s |
| Trocar o `nngnavi.exe` (14,7 MB) por ele mesmo e adicionar um arquivo novo | Decodifica, `testzip` sem erro, conteúdo igual byte a byte |
| Remover `NK.bin` | Recusado |
| Lite (`lite/mudancas.txt`) | 6845 entradas. As 40 removidas somam 26 MB. Só o `SYS.TXT` e o `Version_Info.txt` diferem do original, iguais aos de `lite/`. Decodifica e passa no `testzip` |
| Volta (`lite/volta/mudancas.txt`) | Original inteiro, só com o `Version_Info.txt` trocado |

Os pacotes ficam fora do repo, em `C:\Dev\medianav-sandero2016\custom\`, cada um com um `SHA256.txt` ao lado:

| Pacote | Versão declarada | SHA-256 | Bytes |
|---|---|---|---|
| `lite-9.1.3.1\upgrade.lgu` | 9.1.3.1 | `81E23131FABD34A9915C21A2E3FC045C3B565D3C73AE3D86D7C28108C82850CC` | 204.254.320 |
| `volta-9.1.3.2\upgrade.lgu` | 9.1.3.2 | `E2D17030EAD5997E968C6513E46BD38C0F352DDDDE3C3B3E2B5E92066BCB3E26` | 222.387.533 |

Na verificação de 26/10/2026, um arquivo da extração de referência apareceu com um bit trocado no disco do PC. O ZIP e os pacotes estavam íntegros. Por isso, depois de copiar qualquer pacote para o pendrive, confira o hash **no pendrive**: `Get-FileHash E:\upgrade.lgu`.

## Plano de instalação

O carro está na 5.2.7.A. Na v1 não existe volta para versão anterior: depois da 9.1.3, a 5.2.7 não reinstala. A Menaco e a EvoTech partem do mesmo caminho (5.2.7 até 9.1.3).

### Etapa 1: 9.1.3 oficial, sem modificação

Esta etapa grava kernel, MICOM e bootloader. Por isso ela usa só arquivo da Renault.

1. **Pelo Toolbox (preferido):**
   - Pendrive FAT32 de 8 GB ou mais, vazio.
   - No carro, com a navegação aberta, procure no menu a atualização de mapas e a opção de salvar os dados da central no pendrive.
   - No PC, abra o Toolbox (https://renault.welcome.naviextras.com) com esse pendrive.
   - Se ele oferecer a 9.1.3 para o seu carro, isso confirma que a Renault distribui essa versão para o Sandero brasileiro.
2. **Se o Toolbox não oferecer**, a alternativa é o `upgrade.lgu` 9.1.3 que estudei (`090FFAEF…B568`). Antes de usá-lo, me avise. Ele veio de site de terceiros, e sem a oferta do Toolbox falta a confirmação de que vale para o seu SKU.
3. **Na instalação:**
   - Coloque o `upgrade.lgu` na raiz do pendrive e confira o hash no pendrive.
   - Motor ligado do começo ao fim. Um relato fala em 2h30 de instalação.
   - Não engate a ré, não desligue o carro e não tire o pendrive até a central reiniciar e mostrar a versão nova.
   - Anote antes as estações de rádio e os telefones pareados, que podem se perder.
4. Depois de instalar, confira se a tela de versão mostra 9.1.3. Use o carro alguns dias: câmera de ré, Bluetooth, som, GPS.

### Etapa 2: lite 9.1.3.1

1. Só com a central já na 9.1.3 e funcionando bem.
2. Pendrive com o `lite-9.1.3.1\upgrade.lgu` na raiz, com o hash conferido no pendrive.
3. Mesmos cuidados da etapa 1. Os arquivos de kernel e MICOM do lite são os mesmos da 9.1.3 oficial, mas a central pode regravá-los.
4. Para medir o ganho, o ideal é ligar o `show_fps` do iGO antes e depois. Ainda falta descobrir em que seção do `SYS.TXT` essa chave entra.

### Para conferir sem mexer

Os códigos de serviço (tocar 5 pontos em Configurações > Sistema > Versão e digitar `1111` para versão ou `0362` para modo de teste) vêm de relato para a MediaNav 1. Não estão confirmados no Evolution, então deixe-os para depois.

## Como voltar atrás

- **Do lite para a 9.1.3 de fábrica:** instale o `volta-9.1.3.2\upgrade.lgu`. É a 9.1.3 original inteira, com o `SYS.TXT` de duas linhas:
  ```
  [device]
  type="lge_ulc"
  ```
  O número 9.1.3.2 existe só para a central aceitar o pacote por cima da 9.1.3.1. Os idiomas, vozes e POIs que o lite deixou de fora continuam gravados na central.
- **Da 9.1.3 para a 5.2.7:** não existe caminho conhecido.

## Achados paralelos

- O UpgradeManager procura no pendrive `MicomManager.exe`, `Special_tool.exe`, `update_checksum.md5`, `special_file.ini` e os arquivos `navigation_restore*.lgu`.
- O AppMain procura `mcmtest_activate_4medianav.ini` e `mcmtest_activate_4nng.ini`.
- São portas de modo de serviço e de recuperação. Elas permitiriam apagar arquivos da central, mas rodam código no aparelho.
- Perto de `update_checksum.md5` há uma segunda senha de ZIP, `kk9r2a@=4F2g-J2tw6X@navi`. Ela provavelmente abre os pacotes de navegação.

## Fontes

- Análise do updater 7.0.5 e códigos de serviço: https://github.com/m-a-x-s-e-e-l-i-g/MediaNav-to-Evolution-Upgrade
- EvoTech: https://github.com/yosicovich/MediaNavMods e https://4pda.to/forum/index.php?showtopic=514735&st=780
- Menaco: https://menaco.co/ e https://manuals.plus/menaco/medianav-evolution-car-gps-multimedia-device-manual
- Atualização oficial pela Toolbox: https://www.renault.fr/faq-multimedia/media-nav-evolution/mise-a-jour-systeme.html
