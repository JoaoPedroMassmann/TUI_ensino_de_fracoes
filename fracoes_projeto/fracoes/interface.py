"""Desenho da interface sobre o quadro da câmera (PIL para texto com acentos)."""

from __future__ import annotations

from functools import cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config
from .atividades import FASES
from .avaliacao import texto_leitura
from .estado import EstadoSistema


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


def desenhar_painel(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    largura: int,
    blocos: list[tuple[str, ImageFont.ImageFont, tuple[int, int, int]]],
    borda: tuple[int, int, int] | None = None,
    base: int | None = None,
    escala: float = 1.0,
) -> tuple[int, int]:
    """Desenha um painel de texto. Se `base` for dado, o painel termina nessa altura."""
    margem_interna = int(14 * escala)
    linhas = []
    for texto, fonte, cor in blocos:
        for linha in quebrar_linhas(draw, texto, fonte, largura - 2 * margem_interna):
            linhas.append((linha, fonte, cor))
    altura = 2 * margem_interna + sum(altura_linha(f) for _, f, _ in linhas)
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
    base_ok: bool = False,
) -> np.ndarray:
    h, w = frame.shape[:2]
    escala = max(0.6, w / 1280)
    fontes = {k: get_font(max(12, int(v * escala))) for k, v in config.TAMANHOS_FONTE.items()}

    base = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).convert("RGBA")
    camada = Image.new("RGBA", base.size, (0, 0, 0, 0))
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
        saida = Image.alpha_composite(base, camada).convert("RGB")
        return cv2.cvtColor(np.array(saida), cv2.COLOR_RGB2BGR)

    fase = estado.fase_atual
    etapa_texto = f" (Etapa {estado.etapa_atual}/2)" if estado.questao.duas_etapas else ""
    if estado.troca:
        etapa_texto = " (troca de peça base)"
    tentativa_texto = (
        f"  |  Tentativas anteriores: {estado.tentativas}" if estado.tentativas > 0 else ""
    )
    status_cam = "Câmera: OK" if camera_ok else "Câmera: ERRO"
    status_som = "Áudio: OK" if audio_ok else "Sem áudio"
    cabecalho = (
        f"Atividade {estado.questao_atual + 1} de {len(fase.questoes)}"
        f"{etapa_texto}{tentativa_texto}  |  {status_cam}  |  {status_som}"
    )

    blocos = [
        (fase.titulo, fontes["titulo"], config.AMARELO),
        (cabecalho, fontes["pequeno"], config.CINZA if audio_ok else config.AMARELO),
        (estado.enunciado_atual, fontes["enunciado"], config.BRANCO),
    ]
    if estado.calibrando:
        blocos = [
            ("Calibração da peça base", fontes["titulo"], config.AMARELO),
            (f"{status_cam}  |  {status_som}", fontes["pequeno"],
             config.CINZA if audio_ok else config.AMARELO),
            ("Peça base sozinha, sem peças numéricas, sobre fundo claro. "
             "Aperte espaço para calibrar.", fontes["enunciado"], config.BRANCO),
        ]
    if estado.menu:
        blocos = [
            ("Sistema Educativo de Frações", fontes["titulo"], config.AMARELO),
            (
                f"{status_cam}  |  {status_som}",
                fontes["pequeno"],
                config.CINZA if audio_ok else config.AMARELO,
            ),
            (
                "Escolha a fase ou aperte espaço para começar pela fase 1:",
                fontes["enunciado"],
                config.BRANCO,
            ),
            *[(f.titulo, fontes["pequeno"], config.BRANCO) for f in FASES.values()],
        ]
    if estado.exploracao:
        blocos = [
            (f"Modo Exploração  |  {status_cam}  |  {status_som}", fontes["titulo"], config.AMARELO),
            (
                "Encaixe peças numéricas na peça base e aperte espaço para ouvir o que foi identificado.",
                fontes["enunciado"],
                config.BRANCO,
            ),
        ]
    _, y = desenhar_painel(draw, margem, margem, largura, blocos, escala=escala)

    blocos = []
    if estado.rotulo:
        blocos.append((estado.rotulo, fontes["tag"], estado.cor))
    blocos.append((estado.mensagem, fontes["mensagem"], config.BRANCO))
    desenhar_painel(
        draw,
        margem,
        y + gap,
        largura,
        blocos,
        borda=estado.cor if estado.rotulo else config.CINZA,
        escala=escala,
    )

    fase_min, fase_max = min(FASES), max(FASES)
    acao = "Próxima atividade" if estado.resolvida else "Continuar" if estado.troca else "Verificar"
    if estado.exploracao:
        atalhos = (
            f"[ESPAÇO] Ler peças    [P] Repetir instrução    [E] Sair do modo explorar    "
            f"[{fase_min}-{fase_max}] Fases    [H] Ajuda    [Q] Sair"
        )
    elif estado.calibrando:
        atalhos = (
            "[ESPAÇO] Calibrar    [N] Continuar sem detectar a base    "
            "[P] Repetir instruções    [H] Ajuda    [Q] Sair"
        )
    elif estado.menu:
        atalhos = (
            f"[ESPAÇO] Começar na fase 1    [{fase_min}-{fase_max}] Escolher fase    "
            "[P] Repetir instruções    [E] Explorar    [H] Ajuda    [Q] Sair"
        )
    else:
        atalhos = (
            f"[ESPAÇO] {acao}    [R] Refazer    [P] Repetir pergunta    [E] Explorar    "
            f"[{fase_min}-{fase_max}] Fases    [H] Ajuda    [Q] Sair"
        )
    topo, _ = desenhar_painel(
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
            ("Leitura oscilando — mantenha as peças paradas.", fontes["pequeno"], config.AMARELO)
        )
    if base_ok is not None:
        blocos_leitura.append(
            (f"Peça base: {'vista' if base_ok else 'não vista'}", fontes["pequeno"],
             config.CINZA if base_ok else config.AMARELO)
        )
    desenhar_painel(
        draw,
        margem,
        0,
        largura,
        blocos_leitura,
        base=topo - gap,
        escala=escala,
    )

    saida = Image.alpha_composite(base, camada).convert("RGB")
    return cv2.cvtColor(np.array(saida), cv2.COLOR_RGB2BGR)
