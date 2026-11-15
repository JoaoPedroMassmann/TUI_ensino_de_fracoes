"""Programa principal: câmera, teclado e janela."""

from __future__ import annotations

import logging

import cv2

from . import config
from .avaliacao import total_oitavos
from .deteccao import Estabilizador, criar_detector
from .estado import Sessao
from .fala import Falador, tts_disponivel
from .interface import desenhar_interface

logger = logging.getLogger(__name__)

TECLAS_AJUDA = "Teclas: [1-4] fases | [ESPAÇO] verificar/avançar | [R] refazer | [P] repetir pergunta | [Q] sair"


def ler_tecla(codigo: int) -> str:
    """Tratamento de código de tecla para string. Devolve string vazia se não for uma tecla válida."""
    codigo &= 0xFF
    if codigo == 255:
        return ""
    try:
        return chr(codigo).lower()
    except ValueError:
        return ""


def tratar_tecla(tecla: str, sessao: Sessao, ids_validos: list[int], total: int) -> bool:
    """Executa o comando da tecla. Devolve False quando o usuário pediu para sair."""
    if tecla == "q":
        return False
    if tecla in ("1", "2", "3", "4"):
        sessao.trocar_fase(int(tecla))
    elif tecla == "r":
        sessao.reiniciar_questao()
    elif tecla == "p":
        sessao.repetir_pergunta()
    elif tecla in ("s", " "):
        sessao.verificar_ou_avancar(ids_validos, total)
    return True

"""Função principal do programa."""
def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info("Iniciando o Sistema Educativo de Frações...")

    tem_audio = tts_disponivel()
    if not tem_audio:
        logger.warning(
            "pyttsx3 não encontrado: o sistema vai funcionar sem áudio. "
            "Instale com: pip install pyttsx3"
        )

    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        logger.error("Erro: Não foi possível abrir a câmera.")
        return 1
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_ALTURA)

    detector = criar_detector()
    estabilizador = Estabilizador()
    falador = Falador(habilitado=tem_audio)
    falador.iniciar()
    sessao = Sessao(falador)
    sessao.iniciar()
    logger.info(TECLAS_AJUDA)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)
            ids_detectados = ids.flatten().tolist() if ids is not None else []
            ids_do_quadro = [i for i in ids_detectados if i in config.ID_VALUES_MAP]
            ids_validos = estabilizador.atualizar(ids_do_quadro)
            total = total_oitavos(ids_validos)

            tecla = ler_tecla(cv2.waitKey(1))
            if not tratar_tecla(tecla, sessao, ids_validos, total):
                break

            display = frame.copy()
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(display, corners, ids)
            display = desenhar_interface(display, sessao.estado, ids_validos, total)
            cv2.imshow(config.JANELA_TITULO, display)
    finally:
        falador.parar()
        cap.release()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
