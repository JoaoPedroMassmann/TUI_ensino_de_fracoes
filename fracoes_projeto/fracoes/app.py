"""Programa principal: câmera, teclado e janela."""

from __future__ import annotations

import logging
import time

import cv2
import numpy as np
import tkinter as tk

from . import config
from . import mensagens as msg
from .atividades import FASES
from .avaliacao import Leitura
from .deteccao import DetectorBase, Estabilizador, EstabilizadorBase, criar_detector
from .estado import Sessao
from .fala import Falador, tts_disponivel
from .interface import desenhar_interface

logger = logging.getLogger(__name__)

FASE_MIN = min(FASES)
FASE_MAX = max(FASES)
TECLAS_FASE = {str(k): k for k in FASES}

TECLAS_AJUDA = (
    f"Teclas: [{FASE_MIN}-{FASE_MAX}] fases | [ESPAÇO] verificar/avançar | "
    "[R] refazer | [P] repetir pergunta | [E] alternar exploração | "
    "[H] ajuda | [Q] sair"
)


def abrir_camera() -> cv2.VideoCapture | None:
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_ALTURA)
    return cap


class Camera:
    """Leitura de quadros com detecção de falhas e reconexão automática."""

    def __init__(self, cap: cv2.VideoCapture) -> None:
        self._cap: cv2.VideoCapture | None = cap
        self._falhas = 0
        self._proxima = 0.0
        self.caiu = False

    def ler(self) -> tuple[np.ndarray | None, str | None]:
        """Devolve (quadro, evento); evento é 'caiu', 'voltou' ou None."""
        if self.caiu:
            return None, self._reconectar()
        ret, frame = self._cap.read()
        if ret:
            self._falhas = 0
            return frame, None
        self._falhas += 1
        if self._falhas < config.FALHAS_CAMERA_MAX:
            return None, None
        self.caiu = True
        self._cap.release()
        self._cap = None
        self._proxima = time.monotonic() + config.INTERVALO_RECONEXAO
        return None, "caiu"

    def _reconectar(self) -> str | None:
        agora = time.monotonic()
        if agora < self._proxima:
            return None
        self._cap = abrir_camera()
        if self._cap is None:
            self._proxima = agora + config.INTERVALO_RECONEXAO
            return None
        self.caiu, self._falhas = False, 0
        return "voltou"

    def liberar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


def ler_tecla(codigo: int) -> str:
    """Tratamento de código de tecla para string. Devolve string vazia se não for uma tecla válida."""
    codigo &= 0xFF
    if codigo == 255:
        return ""

    try:
        return chr(codigo).lower()
    except ValueError:
        return ""


def filtrar_tecla(
    tecla: str,
    ultima_tecla: str,
    instante_tecla: float,
    agora: float,
) -> tuple[str, str, float]:
    """Ignora repetição rápida da mesma tecla sem empurrar a janela do debounce."""
    if not tecla:
        return "", ultima_tecla, instante_tecla
    if tecla == ultima_tecla and agora - instante_tecla < config.DEBOUNCE_TECLA:
        return "", ultima_tecla, instante_tecla
    return tecla, tecla, agora


def tratar_tecla(tecla: str, sessao: Sessao, leitura: Leitura) -> bool:
    """Executa o comando da tecla. Devolve False quando o usuário pediu para sair."""
    if not tecla:
        return True

    sessao.falador.tocou_bipe = False

    if sessao.estado.confirmando_saida:
        if tecla == "q":
            sessao.falador.bipe("tecla")
            return False
        sessao.cancelar_confirmacao_saida()
        return True

    if sessao.estado.calibrando and tecla not in ("q", "h", "p"):
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
    elif tecla == "h":
        sessao.falar_ajuda()
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

    cap = abrir_camera()
    if cap is None:
        logger.error("Erro: Não foi possível abrir a câmera.")
        falador.bipe("erro")
        falador.falar("Não foi possível abrir a câmera.")
        time.sleep(3)
        falador.parar()
        return 1
    camera = Camera(cap)

    detector = criar_detector()
    estabilizador = Estabilizador()
    estabilizador_base = EstabilizadorBase()
    sessao = Sessao(falador)
    detector_base = DetectorBase()
    estabilizador_base = EstabilizadorBase()
    sessao.iniciar(calibrar=detector_base.ativo)
    logger.info(TECLAS_AJUDA)

    ids_anteriores: tuple[int, ...] = ()
    ultimo_frame = np.zeros((config.CAMERA_ALTURA, config.CAMERA_LARGURA, 3), dtype=np.uint8)
    ultima_tecla, instante_tecla = "", 0.0

    try:
        while True:
            frame, evento = camera.ler()
            if evento == "caiu":
                logger.error("Câmera desconectada")
                falador.bipe("erro")
                falador.falar(msg.CAMERA_DESCONECTADA)
            elif evento == "voltou":
                estabilizador.limpar()
                falador.bipe("ok")
                falador.falar(msg.CAMERA_RECONECTADA)

            if frame is None:
                if camera.caiu:
                    tela = desenhar_interface(
                        ultimo_frame,
                        sessao.estado,
                        [],
                        0,
                        camera_ok=False,
                        audio_ok=falador.saude_ok,
                        erro_fatal=msg.CAMERA_AVISO_TELA,
                    )
                    cv2.imshow(config.JANELA_TITULO, tela)
                tecla, ultima_tecla, instante_tecla = filtrar_tecla(
                    ler_tecla(cv2.waitKey(30 if camera.caiu else 1)),
                    ultima_tecla,
                    instante_tecla,
                    time.monotonic(),
                )
                if not tratar_tecla(tecla, sessao, Leitura([])):
                    break
                continue

            ultimo_frame = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)
            ids_detectados = ids.flatten().tolist() if ids is not None else []
            ids_do_quadro = [i for i in ids_detectados if i in config.ID_VALUES_MAP]
            ids_validos = estabilizador.atualizar(ids_do_quadro)
            base_ok = estabilizador_base.atualizar(
                detector_base.medir(frame) if detector_base.ativo else True
            )
            leitura = Leitura(ids_validos, estabilizador.oscilando, base_ok)

            ids_ordenados = tuple(sorted(ids_validos))

            if ids_ordenados != ids_anteriores:
                sessao.notificar_mudanca_mesa(ids_ordenados)
                ids_anteriores = ids_ordenados


            tecla, ultima_tecla, instante_tecla = filtrar_tecla(
                ler_tecla(cv2.waitKey(1)),
                ultima_tecla,
                instante_tecla,
                time.monotonic(),
            )
            if sessao.estado.calibrando:
                if tecla == " ":
                    sessao.resultado_calibracao(detector_base.calibrar(frame, bool(ids_validos)))
                    tecla = ""
                elif tecla == "n":
                    detector_base.ativo = False
                    sessao.pular_calibracao()
                    tecla = ""
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
        camera.liberar()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())