# Sistema Educativo de Frações

Sistema de atividades sobre frações com peças físicas, câmera e áudio. A criança encaixa **peças numéricas** (de um oitavo, um quarto e um meio) sobre uma **peça base**; a câmera lê as peças por marcadores ArUco, o sistema avalia a montagem e responde por voz, bipes e tela. Um **instrutor** acompanha a sessão, calibra a câmera e faz a troca da peça base quando a atividade pede.

O sistema foi pensado para uso com forte apoio de áudio: tudo o que aparece na tela também é falado, e todo comando tem resposta sonora.

## Sumário

1. [Requisitos](#requisitos)
2. [Material físico](#material-físico)
3. [Como executar](#como-executar)
4. [Uso: instrutor e aluno](#uso-instrutor-e-aluno)
5. [Comandos](#comandos)
6. [As fases](#as-fases)
7. [Como a avaliação funciona](#como-a-avaliação-funciona)
8. [Configuração](#configuração)
9. [Estrutura do código](#estrutura-do-código)
10. [Testes](#testes)
11. [Solução de problemas](#solução-de-problemas)
12. [Limitações conhecidas](#limitações-conhecidas)

## Requisitos

- Python 3.10 ou superior.
- Uma câmera USB ou integrada (o sistema pede 1280×720 e aceita o que a câmera entregar).
- Bibliotecas Python:
  - `opencv-python` (4.7 ou superior, para a API `ArucoDetector`). Se a sua instalação não tiver o módulo `aruco`, use `opencv-contrib-python`.
  - `numpy`
  - `Pillow` (desenha os textos com acentos na tela)
  - `pyttsx3` (opcional): voz sintetizada. Sem ele o sistema funciona sem fala e mostra "Sem áudio" na tela.

```bash
pip install opencv-python numpy Pillow pyttsx3
```

Sistema operacional: desenvolvido para **Windows** (bipes com `winsound`, voz do Windows). Em Linux e macOS funciona, mas todos os bipes viram o mesmo sinal do terminal, perdendo a diferença entre acerto, erro e aviso. Para a voz, o `pyttsx3` precisa de um motor instalado (por exemplo `espeak` no Linux), de preferência com voz em português do Brasil.

## Material físico

**Marcadores.** Cada peça numérica leva um marcador ArUco do dicionário `DICT_4X4_50`:

| Peça | Valor | ID do marcador |
|---|---|---|
| Um oitavo | 1/8 | 10 |
| Um quarto | 2/8 | 20 |
| Um meio | 4/8 | 30 |

Marcadores com outros IDs são **ignorados**, sem aviso. Assim, outras marcas na cena não atrapalham.

**Peça base.** Um disco escuro, grande, onde as peças numéricas são encaixadas. Ela deve ter raio entre 20% e 30% do menor lado da imagem (nos 720 pixels de altura, de 144 a 216 pixels de raio) e ser colocada sobre uma superfície **clara**, no centro da área da câmera. A fase 6 usa duas peças base, uma de cada vez.

**Posicionamento.** Câmera fixa, olhando para a mesa de cima, boa luz e sem sombra forte sobre as marcas. As mãos não devem cobrir os marcadores na hora de verificar.

## Como executar

Os módulos usam importações relativas, então o programa roda como módulo do pacote. Substitua `fracoes` pelo nome da pasta onde estão os arquivos:

```bash
python -m fracoes.app
```

A janela "Sistema Educativo de Frações" abre. Ela precisa estar em **foco** para receber as teclas. Todo comando recebido gera um bipe: se você apertar uma tecla e não ouvir nada, clique na janela.

## Uso: instrutor e aluno

**1. Calibração (começa por ela).** O sistema abre pedindo a calibração da peça base. O instrutor coloca a peça base **sozinha**, sem nenhuma peça numérica, no centro da câmera, sobre fundo claro, e aperta **ESPAÇO**. O contorno **amarelo** na tela mostra o objeto que será calibrado.

- A detecção da peça base **só liga depois de calibrada**. Se o instrutor pular com **N**, a detecção fica desligada: o sistema funciona, mas não verifica se há peças fora da base nem se a base está à vista.
- A calibração pode ser feita de novo **a qualquer momento** com **C**, mesmo no meio de uma atividade. A atividade, a etapa e as tentativas são preservadas.
- Falhas possíveis: peças numéricas à vista, base não encontrada, imagem instável, fundo escuro demais. Cada uma tem uma mensagem própria.

**2. Menu.** Depois da calibração, o sistema fala as boas-vindas. ESPAÇO começa pela fase 1; as teclas **1 a 6** escolhem a fase.

**3. Atividade.** O sistema fala a atividade. O aluno encaixa as peças e aperta **ESPAÇO** para verificar. Se acertar, ESPAÇO avança para a próxima atividade. Se errar, recebe uma dica que muda a cada tentativa.

**4. Troca de peça base (fase 6).** Quando a primeira etapa está certa, o sistema pede ao instrutor que retire a peça base e as peças, posicione a segunda base e aperte ESPAÇO para continuar.

**5. Modo Exploração (E).** O aluno encaixa peças e o sistema só descreve o que a câmera vê (por exemplo "um quarto e um oitavo: três oitavos"), sem avaliar.

## Comandos

A tela mostra só as teclas do momento. A lista completa do modo atual abre com **H** e também é falada.

| Tecla | Função |
|---|---|
| **ESPAÇO** | Verifica a montagem, avança, continua a troca de base, começa a fase 1 (no menu), lê as peças (exploração) ou calibra (durante a calibração) |
| **P** | Repete a pergunta, a instrução ou o menu |
| **R** | Refaz a atividade |
| **S** | Pula a atividade (pede confirmação) |
| **M** | Volta ao menu (pede confirmação se houver progresso) |
| **E** | Liga ou desliga o modo Exploração |
| **C** | Calibra a peça base |
| **N** | Pula ou cancela a calibração |
| **1 a 6** | Escolhe a fase (pede confirmação se houver progresso) |
| **H** | Abre ou fecha a lista de comandos |
| **ESC** | Silencia a fala |
| **Q** | Sai (pede confirmação) |

**Confirmações.** Ações que perdem progresso (trocar de fase, voltar ao menu, pular, sair) pedem para apertar **a mesma tecla de novo**. Qualquer outra tecla cancela. Há um intervalo de 0,6 s para a mesma tecla, que evita toques duplos acidentais.

## As fases

| Fase | Tema |
|---|---|
| 1 | Frações unitárias: um oitavo, um quarto, um meio |
| 2 | Formar o inteiro com peças iguais |
| 3 | Números como frações (metade, o inteiro) |
| 4 | Frações equivalentes |
| 5 | Parte e todo (situações do dia a dia) |
| 6 | Equivalência em duas peças base (com troca de base) |

Cada fase tem de 3 a 4 atividades. As atividades são definidas em `atividades.py`. Há dois critérios de resposta:

- **Peças exatas** (`ids_obrigatorios`): a montagem deve usar exatamente aquelas peças.
- **Soma alvo** (`soma_alvo`): vale qualquer combinação que some o valor em oitavos.

## Como a avaliação funciona

**Leitura estável.** A câmera lê os marcadores a cada quadro. O sistema decide quais peças estão na mesa olhando os últimos 7 quadros, o que filtra falhas de um quadro só. Se a leitura varia muito, o sistema avisa "leitura oscilando".

**Peça base.** Com a detecção ativa (depois de calibrar), só contam as peças cujo marcador está dentro do disco da base. Peças fora da base geram um aviso ao instrutor.

**Feedback por tentativa**, quando a resposta está errada:

1. O que a câmera viu e o que a atividade pede.
2. Quanto falta ou passou (a atividade é repetida em seguida).
3. A ação a fazer ("Acrescente dois oitavos", "Troque… por…").

Quando o valor está certo mas as peças são outras, o sistema explica a equivalência ("Um quarto vale o mesmo, mas a atividade pede dois oitavos").

**Leitura oscilando.** O sistema recusa avaliar até 2 vezes seguidas e pede para deixar as peças paradas. Depois disso avalia mesmo assim. Em nenhum caso a oscilação conta como tentativa errada.

**Sinais sonoros.** Cada tipo de resposta tem um bipe próprio: tecla, acerto, erro, aviso, informação, leitura, fase concluída e instrutor.

**Câmera desconectada.** O sistema avisa por voz e tela, tenta reconectar a cada 2 segundos e avisa quando voltar.

## Configuração

Tudo em `config.py`:

| Parâmetro | Padrão | Função |
|---|---|---|
| `TAG_ID_MAP` | `{1: 10, 2: 20, 4: 30}` | Valor da peça em oitavos → ID do marcador |
| `CAMERA_INDEX` | 0 | Qual câmera usar |
| `CAMERA_LARGURA` / `CAMERA_ALTURA` | 1280 / 720 | Resolução pedida |
| `FRAMES_ESTABILIDADE` | 7 | Janela de quadros para estabilizar a leitura |
| `DEBOUNCE_TECLA` | 0,6 s | Intervalo mínimo para repetir a mesma tecla |
| `BASE_RAIO_MIN` / `MAX` | 0,20 / 0,30 | Faixa de tamanho da base na calibração (fração do menor lado) |
| `BASE_CIRCULARIDADE_MIN` | 0,50 | Quão redondo o objeto precisa ser |
| `BASE_TOLERANCIA_RAIO` | 0,20 | Tolerância do raio depois de calibrar |
| `CALIBRACAO_QUADROS` | 10 | Quadros medidos para calibrar |
| `TTS_TAXA` | 160 | Velocidade da fala |
| `TTS_VOZ_DICAS` | pt-br… | Trechos para escolher a voz em português |
| `FALHAS_CAMERA_MAX` / `INTERVALO_RECONEXAO` | 15 / 2 s | Detecção de queda e reconexão |

## Estrutura do código

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Programa principal: câmera, teclado, janela e laço de quadros |
| `config.py` | Parâmetros centrais |
| `deteccao.py` | Marcadores ArUco, detecção e calibração da peça base, estabilização das leituras |
| `atividades.py` | Fases e atividades |
| `avaliacao.py` | Avaliação das respostas e geração das mensagens de erro |
| `estado.py` | Estado da sessão, transições, confirmações e calibração |
| `mensagens.py` | Textos falados e mostrados, ajuda por modo, números por extenso |
| `interface.py` | Desenho da interface sobre o quadro da câmera |
| `fala.py` | Voz (`pyttsx3`) e bipes |

**Texto.** As mensagens seguem um orçamento de tamanho (enunciados até 80 caracteres, feedback até 120, ajuda falada até 250, barra de atalhos até 60). Os limites são verificados por testes, então ao mudar um texto rode os testes.

## Testes

Os testes cobrem a lógica sem câmera nem áudio: avaliação, fluxo das fases (incluindo a troca de base), confirmações, calibração, ajuda e orçamento de texto. Rode a partir da **pasta que contém o pacote** (não de dentro dele):

```bash
python -m unittest discover -s fracoes/tests -t .
```

## Solução de problemas

| Sintoma | O que verificar |
|---|---|
| "Não foi possível abrir a câmera" | `CAMERA_INDEX`; outro programa usando a câmera; permissão de acesso |
| Tecla sem bipe | A janela perdeu o foco: clique nela |
| "Sem áudio" na tela | `pyttsx3` não instalado ou sem voz no sistema |
| Calibração diz "não vejo a peça base" | Base sozinha, centralizada, bem iluminada, com tamanho dentro da faixa (`BASE_RAIO_MIN`/`MAX`); confira o contorno amarelo |
| Calibração diz "fundo escuro demais" | Use uma superfície clara |
| "Leitura oscilando" | Luz fraca, marcador coberto pela mão ou impresso com baixa qualidade |
| "Não vejo peças numéricas" com peça na mesa | Marcador com ID errado, virado para baixo ou fora da base (com a detecção ativa) |
| Detecção da base falha depois de mover a câmera | Calibre de novo com **C** |

## Limitações conhecidas

- Marcadores com IDs diferentes de 10, 20 e 30 são ignorados sem aviso; uma peça com a tag errada aparece como "não vejo peças".
- Sem calibração, a detecção da base fica desligada e não há verificação de peças fora dela.
- O sistema não detecta a perda de foco do teclado. A pista é a falta de bipe.
- Cada frase falada abre um processo do `pyttsx3`, o que pode causar um atraso curto antes da voz.
- Fora do Windows, todos os bipes soam iguais.
- O desenvolvimento foi validado com testes automáticos e simulação de câmera; o comportamento com câmera, voz e peças reais precisa ser conferido em campo.