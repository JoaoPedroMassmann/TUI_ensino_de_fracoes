"""Desenho da interface sobre o quadro da câmera (PIL para texto com acentos)."""

from __future__ import annotations

from dataclasses import astuple
from functools import cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config
from . import mensagens as msg
from .atividades import FASES
from .avaliacao import texto_leitura
from .estado import EstadoSistema, modo_ajuda

Bloco = tuple[str, ImageFont.ImageFont, tuple[int, int, int]]

# Fatores de redução da fonte da mensagem quando ela não cabe entre os painéis.
_FATORES_MENSAGEM = (1.0, 0.85, 0.7, 0.6, 0.5)

# Última camada de interface desenhada: (chave, 1 - alfa, cor pré-multiplicada em BGR).
# O texto só é redesenhado quando algo na tela muda, não a cada quadro.
_cache: tuple[tuple, np.ndarray, np.ndarray] | None = None


@cache
def get_font(size: int) -> ImageFont.ImageFont:
    for caminho in config.FONT_CANDIDATES:
        try:
            return ImageFont.truetype(caminho, size)
        except OSError:
            continue
    return ImageFont.load_default()


def quebrar_linhas(draw: ImageDraw.ImageDraw, texto: str, fonte, largura_max: float) -> list[str]:
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def altura_linha(fonte) -> int:
    return fonte.getbbox("Ágy")[3] + 8


def _preparar_painel(
    draw: ImageDraw.ImageDraw, largura: int, blocos: list[Bloco], escala: float
) -> tuple[list[tuple[str, ImageFont.ImageFont, tuple[int, int, int]]], int, int]:
    """Quebra o texto em linhas e devolve (linhas, margem interna, altura do painel)."""
    margem_interna = int(14 * escala)
    linhas = []
    for texto, fonte, cor in blocos:
        for linha in quebrar_linhas(draw, texto, fonte, largura - 2 * margem_interna):
            linhas.append((linha, fonte, cor))
    altura = 2 * margem_interna + sum(altura_linha(f) for _, f, _ in linhas)
    return linhas, margem_interna, altura


def desenhar_painel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    largura: int,
    blocos: list[Bloco],
    borda: tuple[int, int, int] | None = None,
    base: int | None = None,
    escala: float = 1.0,
) -> tuple[int, int]:
    """Desenha um painel de texto. Se `base` for dado, o painel termina nessa altura."""
    linhas, margem_interna, altura = _preparar_painel(draw, largura, blocos, escala)
    if base is not None:
        y = base - altura

    opcoes = {"outline": borda, "width": 4} if borda else {}
    draw.rounded_rectangle(
        (x, y, x + largura, y + altura), radius=12, fill=(15, 15, 20, 215), **opcoes
    )

    texto_y = y + margem_interna
    for linha, fonte, cor in linhas:
        draw.text((x + margem_interna, texto_y), linha, font=fonte, fill=cor)
        texto_y += altura_linha(fonte)
    return y, y + altura


def texto_atalhos(estado: EstadoSistema) -> str:
    """Só as teclas do momento (2 ou 3); a lista completa abre com H."""
    if estado.ajuda_visivel:
        return "[H] Fechar    [ESC] Fechar e silenciar"
    if estado.confirmando_saida:
        return "[Q] Confirmar saída    [outra tecla] Cancelar"
    if estado.acao_pendente is not None:
        return f"[{estado.acao_pendente.upper()}] Confirmar    [outra tecla] Cancelar"
    if estado.calibrando:
        return "[ESPAÇO] Calibrar    [N] Pular    [H] Ajuda"
    if estado.exploracao:
        return "[ESPAÇO] Ler peças    [E] Voltar    [H] Ajuda"
    if estado.menu:
        return f"[1-{max(FASES)}] Fase    [ESPAÇO] Começar    [H] Ajuda"
    acao = "Próxima atividade" if estado.resolvida else "Continuar" if estado.troca else "Verificar"
    return f"[ESPAÇO] {acao}    [P] Repetir    [H] Ajuda"


def _montar_camada(
    w: int,
    h: int,
    estado: EstadoSistema,
    ids_validos: list[int],
    total: int,
    oscilando: bool,
    camera_ok: bool,
    audio_ok: bool,
    erro_fatal: str | None,
    base_ok: bool | None,
    candidata_base: bool | None,
) -> Image.Image:
    escala = max(0.6, w / 1280)
    fontes = {k: get_font(max(12, int(v * escala))) for k, v in config.TAMANHOS_FONTE.items()}

    camada = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(camada)

    margem = int(24 * escala)
    gap = int(10 * escala)
    largura = w - 2 * margem

    if erro_fatal:
        desenhar_painel(
            draw,
            margem,
            h // 3,
            largura,
            [
                ("ERRO DE HARDWARE", fontes["tag"], config.VERMELHO),
                (erro_fatal, fontes["enunciado"], config.BRANCO),
            ],
            borda=config.VERMELHO,
            escala=escala,
        )
        return camada

    fase = estado.fase_atual
    # Status normal fica oculto: só aparece quando há problema.
    problemas = [t for ok, t in ((camera_ok, "Câmera com erro"), (audio_ok, "Sem áudio")) if not ok]
    status = "  ·  ".join(problemas)
    cor_status = config.AMARELO if problemas else config.CINZA
    sufixo_status = f"  ·  {status}" if status else ""

    etapa_texto = f"  ·  Etapa {estado.etapa_atual}/2" if estado.questao.duas_etapas else ""
    if estado.troca:
        etapa_texto = "  ·  Troca da peça base"
    tentativa_texto = f"  ·  Tentativa {estado.tentativas + 1}" if estado.tentativas > 0 else ""
    cabecalho = (
        f"Atividade {estado.questao_atual + 1}/{len(fase.questoes)}"
        f"{etapa_texto}{tentativa_texto}{sufixo_status}"
    )

    blocos = [
        (fase.titulo, fontes["titulo"], config.AMARELO),
        (cabecalho, fontes["pequeno"], cor_status),
        (estado.enunciado_atual, fontes["enunciado"], config.BRANCO),
    ]
    if estado.menu:
        blocos = [
            ("Sistema Educativo de Frações", fontes["titulo"], config.AMARELO),
            *([(status, fontes["pequeno"], config.AMARELO)] if status else []),
            (f"Escolha a fase (1-{max(FASES)}) ou aperte espaço:", fontes["enunciado"], config.BRANCO),
            *[(f.titulo, fontes["pequeno"], config.BRANCO) for f in FASES.values()],
        ]
    if estado.exploracao:
        blocos = [
            (f"Modo Exploração{sufixo_status}", fontes["titulo"], config.AMARELO),
            ("Encaixe peças na base e aperte espaço para ouvir a leitura.",
             fontes["enunciado"], config.BRANCO),
        ]
    if estado.calibrando:
        blocos = [
            (f"Calibração da peça base{sufixo_status}", fontes["titulo"], config.AMARELO),
            ("Base sozinha, sobre fundo claro. Espaço calibra, N pula.",
             fontes["enunciado"], config.BRANCO),
        ]
    _, y_cabecalho = desenhar_painel(draw, margem, margem, largura, blocos, escala=escala)

    # Painéis de baixo primeiro: o que sobra entre eles e o cabeçalho é o espaço da mensagem.
    atalhos = texto_atalhos(estado)
    topo_atalhos, _ = desenhar_painel(
        draw,
        margem,
        0,
        largura,
        [(atalhos, fontes["pequeno"], config.CINZA)],
        base=h - margem,
        escala=escala,
    )

    blocos_leitura = [(texto_leitura(ids_validos, total), fontes["leitura"], config.BRANCO)]
    if oscilando:
        blocos_leitura.append(
            ("Leitura oscilando: peças paradas.", fontes["pequeno"], config.AMARELO)
        )
    if estado.calibrando and candidata_base is not None:
        blocos_leitura.append(
            (f"Candidata à peça base: {'vista (contorno amarelo)' if candidata_base else 'não vista'}",
             fontes["pequeno"], config.VERDE if candidata_base else config.AMARELO)
        )
    elif base_ok is None:
        blocos_leitura.append(
            ("Base não calibrada (C calibra)",
             fontes["pequeno"], config.CINZA)
        )
    elif not base_ok:
        blocos_leitura.append(("Peça base não vista", fontes["pequeno"], config.AMARELO))
    topo_leitura, _ = desenhar_painel(
        draw,
        margem,
        0,
        largura,
        blocos_leitura,
        base=topo_atalhos - gap,
        escala=escala,
    )

    # Mensagem: reduz a fonte até caber no espaço livre entre cabeçalho e leitura.
    topo_msg = y_cabecalho + gap
    espaco = topo_leitura - gap - topo_msg
    largura_msg = largura
    blocos_dir: list[Bloco] = []
    if estado.ajuda_visivel:
        # Lista em duas colunas (painéis lado a lado) para caber com fonte maior.
        linhas_ajuda = msg.comandos_tela(modo_ajuda(estado), min(FASES), max(FASES))
        corte = (len(linhas_ajuda) + 1) // 2
        esquerda, direita = linhas_ajuda[:corte], linhas_ajuda[corte:]
        largura_msg = largura // 2 - gap // 2
        borda_msg = config.AMARELO

        def montar(fonte):
            return [("COMANDOS", fontes["tag"], config.AMARELO),
                    *[(linha, fonte, config.BRANCO) for linha in esquerda]]

        def montar_direita(fonte):
            return [("COMANDOS (cont.)", fontes["tag"], config.AMARELO),
                    *[(linha, fonte, config.BRANCO) for linha in direita]]
    else:
        rotulo = [(estado.rotulo, fontes["tag"], estado.cor)] if estado.rotulo else []
        borda_msg = estado.cor if estado.rotulo else config.CINZA

        def montar(fonte):
            return [*rotulo, (estado.mensagem, fonte, config.BRANCO)]

        montar_direita = None

    for fator in _FATORES_MENSAGEM:
        fonte_msg = get_font(max(12, int(config.TAMANHOS_FONTE["mensagem"] * escala * fator)))
        blocos_msg = montar(fonte_msg)
        if _preparar_painel(draw, largura_msg, blocos_msg, escala)[2] <= espaco:
            break
    desenhar_painel(
        draw, margem, topo_msg, largura_msg, blocos_msg, borda=borda_msg, escala=escala
    )
    if montar_direita is not None:
        desenhar_painel(
            draw, margem + largura - largura_msg, topo_msg, largura_msg,
            montar_direita(fonte_msg), borda=borda_msg, escala=escala,
        )
    return camada


def _camada_em_cache(chave: tuple, camada_fn) -> tuple[np.ndarray, np.ndarray]:
    global _cache
    if _cache is None or _cache[0] != chave:
        rgba = np.asarray(camada_fn(), dtype=np.float32)
        alfa = rgba[..., 3:4] / 255.0
        _cache = (chave, 1.0 - alfa, rgba[..., 2::-1] * alfa)  # cor já em BGR
    return _cache[1], _cache[2]


def desenhar_interface(
    frame: np.ndarray,
    estado: EstadoSistema,
    ids_validos: list[int],
    total: int,
    *,
    oscilando: bool = False,
    camera_ok: bool = True,
    audio_ok: bool = True,
    erro_fatal: str | None = None,
    base_ok: bool | None = False,
    candidata_base: bool | None = None,
) -> np.ndarray:
    """`base_ok` é None quando a detecção da peça base está desativada."""
    h, w = frame.shape[:2]
    chave = (
        w, h, astuple(estado), tuple(ids_validos), total,
        oscilando, camera_ok, audio_ok, erro_fatal, base_ok,
        candidata_base,
    )
    inverso_alfa, cor_pre = _camada_em_cache(
        chave,
        lambda: _montar_camada(
            w, h, estado, ids_validos, total, oscilando, camera_ok, audio_ok, erro_fatal, base_ok,
            candidata_base,
        ),
    )
    saida = frame.astype(np.float32) * inverso_alfa + cor_pre
    return saida.astype(np.uint8)
