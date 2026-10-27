# Simulador das telas e mudanças visuais

O simulador é uma página local que mostra as telas do Media Nav 9.1.3 com as imagens, as posições e os textos tirados do próprio pacote. Ele serve para testar mudanças estéticas no PC e saber o custo de cada uma antes de pensar em levar para o carro.

Nada do firmware roda. O AppMain é lido como arquivo: o script desmonta o MIPS, segue as constantes até as funções que criam botão, imagem e texto, e anota o retângulo de cada chamada. A página é HTML que recria o desenho a partir desses números.

## Como gerar

Precisa de um Python com `pefile`, `capstone` e `pillow` (um venv basta).

```
python -I scripts/simulador_gera.py "C:\Dev\medianav-sandero2016\extract\9.1.3\root\upgrade" "C:\Dev\medianav-sandero2016\simulador"
```

Depois é abrir `C:\Dev\medianav-sandero2016\simulador\index.html` no navegador. A pasta tem 13 MB de imagens da LG/Renault e fica **fora do repo**. No git vão só os scripts e o template `simulador/index.html`.

| Script | O que faz |
|---|---|
| `scripts/appmain_layout.py` | Layout do AppMain: 1.950 widgets em 110 funções, com imagem, retângulo, texto e o endereço de cada imediato |
| `scripts/langdll_strings.py` | Os 392 textos do `LangDllPTBR.dll` (ids 1001 a 3313) |
| `scripts/simulador_gera.py` | Junta os dois, converte os BMPs usados em PNG e monta a pasta |

## Onde a interface mora

São duas camadas, com donos diferentes.

**AppMain** (início, rádio, mídia, telefone, configurações, Driving Eco). Não usa QtGui; desenha tudo com rotinas próprias.

- Imagens: `Storage Card\System\Img\<tema>\<tela>\*.bmp`. São BMP de 8 bits com paleta. Amarelo puro (255,255,0) é transparente. Os botões são sprites com os estados lado a lado: 178 das 280 imagens usadas têm 4 estados. O primeiro é o normal. A ordem dos outros três é suposição (pressionado, desabilitado, foco).
- Temas: `M1` é o Renault preto do Sandero, `M1_INV` é o claro, `M0` é o Dacia azul. O `M1_INV` tem os 518 BMPs com o mesmo tamanho do `M1`. O `M0` difere em 4, e para esses o AppMain cria widgets com outro retângulo (o "Escuro" do Dacia tem 144 px, o do Renault 104 px).
- Posições: compiladas no `AppMain.exe`. Cada x, y, largura e altura é uma instrução `addiu reg, zero, N` antes da chamada. O simulador mostra o endereço das quatro.
- Textos: tabela de recursos do `data\LangDllPTBR.dll`. Um id serve várias telas: mudar o 1411 ("Áudio") muda todos os softkeys de áudio.

**Navegação iGO**: zips em `Storage Card4\NNG\ux`, sem senha. Layout em `.ui`, estilo em `.css`, cores em `ui_core/scheme/*/color.ini`. A lógica está em `.lua` compilado. A skin já lê velocidade, altitude, rumo, temperatura externa, música tocando, sinal do celular, hora de chegada, tempo e distância restantes e rua atual.

## O que o simulador faz

- Lista as 110 telas por grupo. 29 têm nome conferido à mão; as outras levam o primeiro texto e o endereço.
- Troca entre os três temas. Escolhe sozinho o ramo do layout que encaixa no sprite do tema.
- Modo uso: os tiles da tela inicial, os softkeys e o botão de casa navegam. O estado pressionado aparece no toque.
- Modo inspeção: clique mostra imagem, tamanho, estados, texto e endereços. Dá para arrastar, digitar x/y/w/h, trocar a imagem por um arquivo do PC, esconder e editar o texto.
- Cada mudança entra numa lista com o risco e o caminho até a central. "Exportar mudanças" baixa um JSON.
- Uma tela de navegação feita à mão mostra os campos de informação que dá para ligar no iGO.

**Limites conhecidos.** Frequência, faixa e nome da rádio são preenchidos pelo AppMain em tempo real. No simulador são exemplos. A fonte, o tamanho e a cor do texto são aproximados. A barra de status (relógio, temperatura) vem de outra rotina que o extrator ainda não pega. Telas com lista mostram itens de páginas diferentes como ramos alternativos, escondidos por padrão.

## Mudanças, viabilidade e risco

Toda mudança chega à central dentro de um `upgrade.lgu` montado pelo `scripts/lgu_pack.py`, com número de versão acima do instalado. Isso depende da versão atual do carro e da pendência do `update_checksum.md5` (ver `CUSTOMIZACAO.md`, etapa 2). Antes de qualquer pacote, a gente confere juntos.

| Mudança | Onde mexe | Dá? | Risco | Observação |
|---|---|---|---|---|
| Usar o visual claro | Configurações > Tela > Plano de fundo: Ilumin. | sim | nenhum | Já existe na central. Teste no carro antes de qualquer patch |
| Trocar ícones e fundos | BMP em `Img\M1` | sim | baixo | Mesmo tamanho, 8 bits com paleta, amarelo como transparência |
| Esconder um elemento | BMP todo amarelo | sim | baixo | Some da tela, mas a área continua respondendo ao toque |
| Recolorir um tema inteiro | Os BMPs do `M1` | sim | baixo | Trabalho de imagem, sem código. A cor do texto vem do código e fica igual |
| Encurtar ou corrigir textos | `LangDllPTBR.dll` | sim | médio | Igual ou menor reescreve no lugar. Maior exige remontar a seção de recursos e pode ser cortado na tela |
| Mais informação na navegação | `.ui` da skin iGO no zip | sim | médio | As variáveis já existem. Erro de sintaxe deve derrubar só a navegação, mas falta confirmar |
| Cores da navegação | `color.ini` do iGO | sim | baixo | Texto puro, por esquema dia e noite |
| Mover ou redimensionar botões | Imediatos no `AppMain.exe` | possível | alto | Cada número é uma instrução. Falta confirmar se a central ainda entra em modo de atualização com o AppMain quebrado |
| Mudar a cor ou o tamanho da fonte do AppMain | Código do AppMain | não por enquanto | alto | Ainda não localizado |
| Telas, menus ou informações novas no AppMain | Código novo | não | — | Só dá para mexer no que já é desenhado |

Fica de fora, como combinado: `NK.bin`, bootloader, drivers, `firmware.hex` e firmware do DAB.

## Propostas de UX

Você não listou incômodos, então tirei estas das telas. Estão em ordem de valor por risco.

1. **Temperatura externa e música tocando na tela do mapa.** O iGO já recebe os dois do carro (`%other.lg_renault.temperature_value` e `media_string`). Hoje é preciso sair da navegação para ver a faixa. Mudança no `.ui`.
2. **Escolher os campos da barra de baixo da navegação**: hora de chegada, tempo e distância restantes, rumo. A tela de navegação do simulador tem a lista para marcar. Mesma edição.
3. **"Mapa" e "GPS" lado a lado na tela inicial.** Pelos nomes das imagens (`map` e `navi`), um abre o mapa e o outro o menu de navegação, mas o rótulo não conta isso. Trocar "GPS" por "Destino" resolve com um patch de texto do mesmo tamanho. Falta confirmar no carro o que cada um abre.
4. **Abreviações**: "Relat. Viagem", "Ajust. Hora", "Inf. programa", "Ilumin.", "Autom." e "Predefs". Onde couber, a palavra inteira ("Viagem", "Hora", "Favoritas"). Cada uma precisa ser medida no simulador antes.
5. **Visual claro de dia.** Testar o Ilumin. no carro com sol. Se o brilho resolver, o resto do item 6 fica opcional.
6. **Ícones com mais contraste** no `M1`, se o teste do item 5 mostrar que o preto com ciano some ao sol. É só imagem.

## Para calibrar

Fotos das telas reais (início, rádio FM, mídia USB, telefone, configurações e navegação) servem para acertar fonte, cor e posição dos textos, a ordem dos estados dos sprites e onde ficam o relógio e a temperatura. Com elas, o simulador passa de aproximado para fiel.
