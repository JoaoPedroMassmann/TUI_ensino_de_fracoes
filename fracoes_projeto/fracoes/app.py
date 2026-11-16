"""Programa principal: câmera, teclado e janela."""

from __future__ import annotations

import logging

import cv2
import numpy as np

from . import config
from .atividades import FASES
from .avaliacao import Leitura
from .deteccao import Estabilizador, criar_detector
from .estado import Sessao
from .fala import Falador, tts_disponivel
from .interface import desenhar_interface

logger = logging.getLogger(__name__)

FASE_MIN = min(FASES)
FASE_MAX = max(FASES)
TECLAS_FASE = {str(k): k for k in FASES}

TECLAS_AJUDA = (
    f"Teclas: [{FASE_MIN}-{FASE_MAX}] fases | [ESPAÇO] verificar/avançar | "
    "[R] refazer | [P] repetir pergunta | [E] alternar exploração | [Q] sair"
)


def ler_tecla(codigo: int) -> str:
    """Tratamento de código de tecla para string. Devolve string vazia se não for uma tecla válida."""
    codigo &= 0xFF
    if codigo == 255:
        return ""
    try:
        return chr(codigo).lower()
    except ValueError:
        return ""


def tratar_tecla(tecla: str, sessao: Sessao, leitura: Leitura) -> bool:
    """Executa o comando da tecla. Devolve False quando o usuário pediu para sair."""
    if not tecla:
        return True

    sessao.falador.tocou_bipe = False

    if sessao.estado.confirmando_saida:
        sessao.falador.bipe("tecla")
        if tecla == "q":
            return False
        sessao.cancelar_confirmacao_saida()
        return True

    if tecla == "q":
        sessao.pedir_confirmacao_saida()
    elif tecla in TECLAS_FASE:
        sessao.trocar_fase(TECLAS_FASE[tecla])
    elif tecla == "e":
        sessao.alternar_exploracao()
    elif tecla == "r":
        sessao.reiniciar_questao()
    elif tecla == "p":
        sessao.repetir_pergunta()
    elif tecla == " ":
        sessao.verificar_ou_avancar(leitura)
    else:
        return True

    if not sessao.falador.tocou_bipe:
        sessao.falador.bipe("tecla")
    return True


def main() -> int:
    """Função principal do programa."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Iniciando o Sistema Educativo de Frações...")

    tem_audio = tts_disponivel()
    if not tem_audio:
        logger.warning(
            "pyttsx3 não encontrado: o sistema vai funcionar sem áudio. "
            "Instale com: pip install pyttsx3"
        )

    falador = Falador(habilitado=tem_audio)
    falador.iniciar()

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("Erro: Não foi possível abrir a câmera.")
        falador.bipe("erro")
        falador.falar("Não foi possível abrir a câmera.")
        cv2.waitKey(2500)
        falador.parar()
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_ALTURA)

    detector = criar_detector()
    estabilizador = Estabilizador()
    sessao = Sessao(falador)
    sessao.iniciar()
    logger.info(TECLAS_AJUDA)

    ids_anteriores: tuple[int, ...] = ()
    ultimo_frame = np.zeros((config.CAMERA_ALTURA, config.CAMERA_LARGURA, 3), dtype=np.uint8)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Erro: A câmera foi desconectada durante a sessão.")
                falador.bipe("erro")
                falador.falar("A câmera foi desconectada.")
                aviso = desenhar_interface(
                    ultimo_frame,
                    sessao.estado,
                    [],
                    0,
                    camera_ok=False,
                    audio_ok=falador.saude_ok,
                    erro_fatal="A câmera foi desconectada. Verifique o cabo e reinicie o programa.",
                )
                cv2.imshow(config.JANELA_TITULO, aviso)
                cv2.waitKey(3000)
                break

            ultimo_frame = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)
            ids_detectados = ids.flatten().tolist() if ids is not None else []
            ids_do_quadro = [i for i in ids_detectados if i in config.ID_VALUES_MAP]
            ids_validos = estabilizador.atualizar(ids_do_quadro)
            ids_ordenados = tuple(sorted(ids_validos))

            if ids_ordenados != ids_anteriores:
                sessao.notificar_mudanca_mesa(ids_ordenados)

            leitura = Leitura(ids_validos, estabilizador.oscilando)

            tecla = ler_tecla(cv2.waitKey(1))
            if not tratar_tecla(tecla, sessao, leitura):
                break

            display = frame.copy()
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(display, corners, ids)
            display = desenhar_interface(
                display,
                sessao.estado,
                leitura.ids,
                leitura.total,
                oscilando=leitura.oscilando,
                camera_ok=True,
                audio_ok=falador.saude_ok,
            )
            cv2.imshow(config.JANELA_TITULO, display)
    finally:
        falador.parar()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())