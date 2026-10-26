# Media Nav Evolution do Sandero Expression 2016: análise do firmware

Data: 26/10/2026. Os binários analisados não estão neste repositório (veja o README).

## Respostas curtas

| Pergunta | Resposta |
|---|---|
| Qual central vem no Sandero 2016 brasileiro? | Media Nav Evolution de primeira geração (v1), fabricada pela LG. Placa ULC2 (LAN5200). |
| Sistema operacional | Windows CE 6.0 num SoC MIPS Alchemy Au13xx com GPU Mali. Todos os executáveis são MIPS (`machine 0x0166`). |
| Versão mais nova do software | 9.1.3. Ela é a última da linha v1, e a Renault não lançou nada depois dela para este hardware. |
| Motor de navegação | NNG iGO (`nngnavi.exe` 9.12.126.727470) com mapas HERE. Os mapas são atualizados pelo Naviextras Toolbox. |
| Dá para atualizar mapas? | Sim, pela via oficial (Toolbox + pendrive). É o caminho de menor risco. |
| Dá para atualizar o software? | Sim, até a 9.1.3. O pacote tem 212 MB. |
| Dá para habilitar Android Auto ou CarPlay? | Não. O 9.1.3 não tem uma linha de código para isso (detalhe na seção 6). Android Auto e CarPlay só existem na central v2, que roda Linux. Ela chegou ao Brasil em 2019 e é outro hardware. |

## 1. Hardware e gerações

| Geração | Período | Base | Software |
|---|---|---|---|
| Media Nav (1ª) | até 2015 | WinCE, placa WR1 | 4.x |
| **Media Nav Evolution v1** (a do seu carro) | 2015 a meados de 2018 | WinCE 6.0, LG ULC2 | 5.x a 9.1.3 |
| Media Nav Evolution v2 | meados de 2018 em diante | Linux, LAN5800 | 1.0.x (última: 1.0.15.5), com Android Auto e CarPlay |
| Media Nav Evolution 8" | 2021 em diante | Linux | 6.0.10.2 |

Versões conhecidas da v1: 5.2.8, 6.0.3, 6.0.4, 7.0.5, 8.0.5, 9.1.1 e 9.1.3. Para ver a do seu carro, vá em Configurações > Sistema, segunda página, opção "Versão do sistema".

## 2. O pacote baixado

A Renault não publica o arquivo para download direto. O site oficial manda salvar os dados da central num pendrive FAT32 de 8 GB ou mais. Depois o Toolbox no computador lê esses dados e baixa a atualização. Como eu não tinha os dados do seu carro, usei a cópia da 9.1.3 mais citada em fórum, que é a do site gps-rlink.

| Campo | Valor |
|---|---|
| Arquivo | `firmware\9.1.3\upgrade.lgu` |
| Origem | https://gps-carminat.com/v3/Files/Update/ULC2/upgrade.lgu (link da página https://www.gps-rlink.com/medianav/update-software-medianav/) |
| Tamanho | 222.387.531 bytes |
| SHA-256 | `090FFAEF5C4047A1BCD6C9A0114C4E8569E63513A11088C532C5B0F609AEB568` |
| CRC-32 interno | `0x41AC486B`. Confere com o declarado no cabeçalho, então o arquivo chegou íntegro. |

Nada do pacote foi executado. Também não gravei nada em pendrive nem no carro.

## 3. Formato do `upgrade.lgu`

```
0x000  'ULC2'                         magic (a 1ª geração usa 'LGU0')
0x004  u32 = 7                        versão do cabeçalho
0x008  u32 = 0x400                    tamanho do cabeçalho
0x00C  u32                            tamanho total do arquivo
0x018  u32                            CRC-32 do corpo (de 0x400 até o fim)
0x024  UTF-16, 180 caracteres '0'     campo reservado, zerado neste pacote
0x400  corpo                          ZIP com ZipCrypto, embaralhado por XOR com tabela fixa de 1024 bytes
```

- O XOR usa a mesma tabela em todo arquivo ULC2. O índice volta a zero a cada 1 KB.
- A senha do ZIP também é fixa: `u8u8l^-^8@E4g_H2kq8X_pack` no ULC2 e `I_LOVE_LG^^` no LGU0.
- Tabelas e senhas vêm do código aberto do projeto MediaNavMods (`pc/lgutool/lgu2dir`). Meu decodificador em Python é `scripts\lgu_unpack.py`.

O pacote não tem assinatura digital. Toda a proteção se resume a ofuscação fixa e um CRC. Por isso existem firmwares de terceiros (Menaco, EvoTech): qualquer um consegue reempacotar um `.lgu` que a central aceita. Isso facilita personalizar, e facilita do mesmo jeito instalar um pacote quebrado ou adulterado.

## 4. Conteúdo e versões

O pacote tem 6.885 arquivos, 330 MB descompactados. As datas vão de 13/12/2017 a 09/03/2018.

| Componente | Arquivo | Versão / data | Função |
|---|---|---|---|
| Kernel e SO | `Storage Card\NK.bin` (16 MB) | formato B000FF, 106 registros, carga em `0x80100000` | Windows CE 6.0 com 148 módulos (drivers, shell, Explorer, DirectShow, Mali). `ULC_launcher` de 26/05/2017. |
| Interface | `Storage Card\System\AppMain.exe` + `QtCore4.dll` | link 21/09/2017, Qt 4.8.5 | Telas de rádio, mídia, telefone, Aha e configurações. 5.106 PNG e 1.613 BMP. |
| Atualizador | `UpgradeManager.exe` | link 12/02/2018 | Valida e instala o pacote (seção 5). |
| MCU (MICOM) | `upgrade\firmware.hex` | Intel HEX, 256 KB contínuos em `0x0`, de 09/03/2018 | Microcontrolador que liga a central, conversa com o carro (CAN, VIN) e controla o rádio. |
| Gerente do MCU | `MicomManager.exe` | link 12/02/2018 | Grava o `firmware.hex` e lê a região (SKU) e o VIN. |
| Bootloader | `upgrade\booter_standalone.bin` | "LGE ULC Bootloader 2.1.7_2017.01.02" | Dá boot pelo eMMC e também por pendrive USB. |
| Bluetooth | `Blue.exe` | link 22/06/2017 | Pilha CSR, viva-voz, áudio, Siri. |
| DAB | `ulc_dab_uc_LGe.bin`, `ulc_dab_bc_LGe.bin` | | Rádio digital europeu. O Brasil não tem DAB. |
| Navegação | `Storage Card4\NNG\nngnavi.exe` | NNG 9.12.126.727470, link 13/02/2018 | iGO. As skins ficam em `ux\`, os idiomas em `content\lang` (inclui `Lang_Portuguese-bra.zip`). |
| Sincronização de mapas | `NNG\synctool\synctool.exe` | NNG 9.12.42.410776 | Copia mapas, POI e radares do pendrive e confere licença e MD5. |

**Mapas não vêm no pacote.** A pasta `content\map` não existe aqui. Os mapas chegam só pelo Toolbox, num pacote separado com licença.

### O pacote serve para o Brasil

No começo eu suspeitava que este 9.1.3 fosse só europeu. Os binários dizem o contrário:

- `UpgradeManager.exe` lê a região do SKU no MCU e escolhe entre quatro variantes de restauração e licença de navegação: `_weu`, `_eeu`, `_amr` (Américas) e `_oth`.
- `MicomManager.exe` tem configurações `M0_AMR`, `MI_AMR` e `X87_AMR` (várias revisões) e a string "Brazil".
- O `firmware.hex` do MCU tem uma tabela de países com o grupo `AR BR CL CO MX PE`. Tem também uma lista de part numbers Renault no formato `28115xxxxR`, que parece ser a lista de centrais aceitas [suposição].
- A interface traz `list_flag_Brazil.bmp` e Aha, que é o app de rádio por streaming que o modelo brasileiro tinha.

O mesmo pacote atende todas as regiões, e a central decide pelo SKU gravado no MCU. Mesmo assim, eu não achei confirmação de que a Renault Brasil distribuiu a 9.1.3 aqui. A prova definitiva é o Toolbox oferecer essa versão depois de ler os dados do seu carro.

## 5. Como a central valida a atualização

Reconstruí a sequência pelas mensagens de log do `UpgradeManager.exe`. Não desmontei o código MIPS, então a ordem exata e o critério da comparação de versão ainda são inferência.

1. A central procura `\MD\upgrade.lgu` no pendrive. Ela aceita também `booter_standalone.bin`, `upgrade_root.lgu` e `navigation_restore*.lgu`.
2. Ela confere o CRC-32 do corpo e rejeita o arquivo com "header crc mismatch".
3. Ela compara a versão com `\Storage Card\system\Version_Info.txt` (que contém `9.1.3`) e rejeita com "incompatible version". Fóruns dizem que a v1 não aceita downgrade, o que combina com esse passo.
4. Ela lê a região do SKU no MCU e escolhe a licença de navegação certa.
5. Os arquivos vão primeiro para uma área de preparação (`Storage Card3\upgrade`). Quando a cópia termina, ela grava `filecopy_success.bin`. Só então passa os arquivos para `Storage Card` e guarda o atualizador antigo como `OLD_UpgradeManager.exe`.
6. Em seguida o `MicomManager.exe` grava o `firmware.hex` no MCU por porta serial. Esse é o passo mais delicado: se faltar energia aqui, o microcontrolador que liga a central pode ficar corrompido.
7. Para mapas, POI e radares, o synctool exige licença (`check_licenses=1` em `sync_files.ini`) e um `update_checksum.md5`.

Ninguém confere assinatura em nenhum desses passos. O pacote passa se tiver CRC correto e versão aceita. A licença só pesa no conteúdo de mapa.

## 6. Android Auto e CarPlay

Varri todos os `.exe`, `.dll`, `.bin` e `.hex` do pacote, em ASCII e UTF-16, atrás de `carplay`, `android auto`, `androidauto`, `iAP2` e `mirrorlink`. Deu zero ocorrência. As duas únicas ocorrências de `projection` estão no kernel e no motor de mapa e falam de projeção cartográfica e gráfica.

Para o celular, a 9.1.3 tem: Bluetooth (ligação, áudio, agenda), Siri pelo botão do volante, o app Aha por USB ou Bluetooth e iPod por USB.

Não há recurso escondido para ligar. Os vídeos e posts que prometem Android Auto numa v1 falam de três outras coisas: trocar pela central v2, instalar um módulo externo de espelhamento ou um firmware de terceiros que roda outro app. Nenhum dos três é atualização de software.

## 7. O que dá para personalizar, do menor para o maior risco

| Nível | O quê | Por onde | Risco |
|---|---|---|---|
| Baixo | Atualizar mapas, radares e POI | Naviextras Toolbox oficial | Quase nenhum. Às vezes é pago. |
| Baixo | Atualizar o software até a 9.1.3, se o carro estiver numa versão anterior | Toolbox, ou `.lgu` de fórum que confira com o SHA-256 da seção 2 | Médio-baixo. A instalação demora (um relato fala em 2h30) e não pode ser interrompida. |
| Médio | Skins, ícones e POI próprios do iGO | Arquivos em `Storage Card4\NNG\ux` e `content\userdata` (o `branding_allow.txt` já lista o que pode mudar) | Ruim no máximo para a navegação. O resto da central segue funcionando. Exige reempacotar ou ter acesso ao Explorer. |
| Médio | Menu de teste do MICOM (códigos 0362, 1111, 3746, 6971) | Tela da central | O código 6971 abre o Explorer do WinCE, e daí dá para apagar arquivo de sistema. Os códigos foram documentados na 1ª geração e não estão confirmados na sua. |
| Alto | Firmware de terceiros (Menaco, EvoTech 9.1.3.1.4) | `.lgu` reempacotado | Perde a garantia e a volta não é garantida. Exige 5.2.7 a 9.1.3. |
| Muito alto | Mexer em `NK.bin`, `firmware.hex` ou bootloader | | Pode deixar a central sem ligar. O bootloader aceita boot por USB, o que abre uma via de recuperação. Não testei e não sei se a Renault Brasil faz esse procedimento. |

## 8. Riscos

- **Fonte não oficial.** O arquivo veio de um site de entusiastas. O CRC interno confere e o conteúdo é coerente (binários LG, NNG e Qt com datas de 2017 e 2018). Mesmo assim, sem assinatura não dá para provar que é idêntico ao da Renault. Prefira o Toolbox.
- **Sem volta.** A v1 não aceita downgrade. Se a 9.1.3 trouxer problema, não dá para desfazer. Um usuário de fórum relatou piora no som na 9.1.3 em relação à 8.0.5.
- **Energia.** O motor precisa ficar ligado durante a atualização inteira. A gravação do MCU é o ponto em que uma queda faz mais estrago.
- **Região.** A central escolhe a variante pelo SKU do MCU. Se o SKU estiver errado ou alterado, a navegação pode subir com licença de outra região.
- **Pendrive.** FAT32. A Renault BR pede 8 GB ou mais. A central reconhece pendrive barato mal, então use um de marca.

## 9. Próximos passos

1. No carro, anote a versão atual (Configurações > Sistema > Versão do sistema) e, se der para ver, o part number `28115xxxxR` na etiqueta da central.
2. Se a versão for anterior à 9.1.3, use o caminho oficial: salve os dados da central no pendrive, abra o Toolbox em https://renault.welcome.naviextras.com e aceite a atualização que ele oferecer.
3. Se o Toolbox não oferecer a 9.1.3 e você quiser instalar a cópia de fórum, confira o SHA-256 antes e faça a atualização com o motor ligado.
4. Para ter Android Auto, cote a troca pela central v2 numa concessionária ou com um instalador. Peça o chicote e a peça compatível com o Sandero 2016. A alternativa é um adaptador externo de espelhamento.
5. Se quiser ir mais fundo no estudo, o próximo passo é desmontar o `UpgradeManager.exe` (MIPS, Ghidra) para confirmar a regra de versão e o uso do campo de 180 zeros do cabeçalho.

## Fontes

- Renault Brasil, Media Nav Evolution: https://www.renault.com.br/sistemas-multimidias/renault-media-nav-evolution.html
- Renault Irlanda, FAQ do Media Nav Evolution (procedimento do Toolbox): https://www.renault.ie/connect/faq-media-nav-evolution.html
- Naviextras Toolbox Renault: https://renault.welcome.naviextras.com
- GPS R-Link, versões e download da 9.1.3: https://www.gps-rlink.com/medianav/update-software-medianav/
- GPS R-Link, Android Auto e CarPlay no MediaNav (v2): https://www.gps-rlink.com/medianav/install-an-android-auto-and-apple-carplay-compatible-medianav/
- MediaNavMods, formato LGU e `lgu2dir`: https://github.com/yosicovich/MediaNavMods
- LGU-file-tools: https://github.com/m-a-x-s-e-e-l-i-g/LGU-file-tools
- MediaNav-to-Evolution-Upgrade (menu MICOM e códigos de serviço): https://github.com/m-a-x-s-e-e-l-i-g/MediaNav-to-Evolution-Upgrade
- Dacia Forum, relatos sobre 5.2.8, 8.0.5, 9.1.3 e Menaco: https://www.daciaforum.co.uk/threads/duster-medianav-evolution-questions-about-updated-versions-video-file-support.40279/
- GoDuster, downgrade na v2 Linux: https://goduster.pl/instrukcje-montazowe/wzrost-to-nie-wszystko-obnizamy-wersje-media-nav-evolution-na-linuxie-czyli-downgrade/

## Scripts

| Caminho | Conteúdo |
|---|---|
| `scripts\lgu_unpack.py` | Decodificador LGU/ULC2 (precisa do `xorArray.h` do MediaNavMods) |
| `scripts\probe.py`, `scripts\zipmap.py`, `scripts\localhdrs.py` | Primeiras leituras do cabeçalho e do ZIP embutido |
| `scripts\components.py` | Leitura do NK.bin, do firmware.hex e dos PEs |
| `scripts\strgrep.py`, `scripts\nngcfg.py`, `scripts\survey.py` | Busca de strings, config do NNG, mapa do conteúdo |
