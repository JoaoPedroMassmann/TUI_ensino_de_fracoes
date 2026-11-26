"""Programa principal: câmera, teclado e janela."""

from __future__ import annotations

import logging
import time

import cv2
import numpy as np

from . import config
from . import mensagens as msg
from .atividades import FASES
from .avaliacao import Leitura
from .deteccao import (
    DetectorBase,
    Estabilizador,
    EstabilizadorBase,
    ids_na_base,
    criar_detector,
)
from .estado import Sessao
from .fala import Falador, tts_disponivel
from .interface import desenhar_interface

logger = logging.getLogger(__name__)

FASE_MIN = min(FASES)
FASE_MAX = max(FASES)
TECLAS_FASE = {str(k): k for k in FASES}

TECLAS_AJUDA = (
    f"Teclas: [{FASE_MIN}-{FASE_MAX}] fases | [ESPAÇO] verificar/avançar | "
    "[R] refazer | [S] pular | [M] menu | [P] repetir pergunta | [E] alternar exploração | "
    "[C] calibrar a base | [ESC] silenciar | [H] ajuda | [Q] sair"
)
ESC = "\x1b"
TECLAS_NA_CALIBRACAO = ("q", "h", "p", ESC)


def abrir_camera() -> cv2.VideoCapture | None:
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_LARGURA)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_ALTURA)
    return cap


def contar_cameras() -> int:
    """Quantos índices de câmera abrem agora. Só chamar com a câmera principal fechada."""
    total = 0
    for indice in range(config.CAMERA_BUSCA_MAX):
        cap = cv2.VideoCapture(indice)
        if cap.isOpened():
            total += 1
        cap.release()
    return total


def resolucao(cap: cv2.VideoCapture) -> tuple[int, int]:
    return int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))


class Camera:
    """Leitura de quadros com detecção de falhas e reconexão automática.

    Com `n_cameras`, a reconexão recusa a câmera que assumir o índice quando a externa cai
    (por exemplo, a do notebook): só aceita quando voltam a existir `n_cameras` câmeras
    e a resolução é a mesma da câmera original.
    """

    def __init__(self, cap: cv2.VideoCapture, n_cameras: int | None = None) -> None:
        self._cap: cv2.VideoCapture | None = cap
        self._falhas = 0
        self._proxima = 0.0
        self.caiu = False
        self._n_cameras = n_cameras
        self._resolucao = resolucao(cap) if n_cameras is not None else None

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
        if self._n_cameras is not None and contar_cameras() < self._n_cameras:
            logger.info("Reconexão adiada: a câmera original ainda não voltou.")
            self._proxima = agora + config.INTERVALO_RECONEXAO
            return None
        self._cap = abrir_camera()
        if self._cap is not None and self._resolucao is not None and resolucao(self._cap) != self._resolucao:
            logger.info("Reconexão recusada: a câmera aberta não é a original (resolução diferente).")
            self._cap.release()
            self._cap = None
        if self._cap is None:
            self._proxima = agora + config.INTERVALO_RECONEXAO
            return None
        self.caiu, self._falhas = False, 0
        return "voltou"

    def liberar(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class VigiaJanela:
    """Detecta o fechamento da janela pelo X, que o imshow desfaria recriando a janela."""

    def __init__(self) -> None:
        self._ja_visivel = False

    def fechada(self) -> bool:
        visivel = cv2.getWindowProperty(config.JANELA_TITULO, cv2.WND_PROP_VISIBLE)
        if visivel >= 1:
            self._ja_visivel = True
            return False
        # Alguns backends devolvem -1 sempre: só vale como "fechada" depois de ter sido vista aberta.
        return self._ja_visivel


def destacar_candidata(display: np.ndarray, centro: tuple[int, int], raio: int) -> None:
    """Contorno amarelo grosso no blob que a calibração usaria como peça base."""
    amarelo = (0, 255, 255)
    cv2.circle(display, centro, raio, amarelo, 4)
    cv2.drawMarker(display, centro, amarelo, cv2.MARKER_CROSS, 30, 3)
    cv2.putText(
        display, "CANDIDATA A BASE", (centro[0] - raio, max(30, centro[1] - raio - 12)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.9, amarelo, 2, cv2.LINE_AA,
    )


def ler_tecla(codigo: int) -> str:
    """Tratamento de código de tecla para string. Devolve string vazia se não for uma tecla válida."""
    # Só ASCII: teclas especiais (setas etc.) têm códigos fora de 0-127 e
    # não podem ser mascaradas para virar caracteres.
    if not 0 <= codigo < 128:
        return ""
    return chr(codigo).lower()


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
    estado = sessao.estado
    if estado.ajuda_visivel and tecla != "h":
        estado.ajuda_visivel = False  # qualquer outra tecla fecha a lista e age normalmente

    if estado.confirmando_saida:
        if tecla == "q":
            sessao.falador.bipe("tecla")
            return False
        sessao.cancelar_confirmacao_saida()
        return True

    if estado.acao_pendente is not None:
        if tecla == estado.acao_pendente:
            sessao.confirmar_acao()
        else:
            sessao.cancelar_acao_pendente()
        if not sessao.falador.tocou_bipe:
            sessao.falador.bipe("tecla")
        return True

    if estado.calibrando and tecla not in TECLAS_NA_CALIBRACAO:
        return True

    if tecla == "q":
        sessao.pedir_confirmacao_saida()
    elif tecla in TECLAS_FASE:
        sessao.solicitar_fase(TECLAS_FASE[tecla])
    elif tecla == "m":
        sessao.solicitar_menu()
    elif tecla == "s":
        sessao.solicitar_pular()
    elif tecla == ESC:
        sessao.calar_fala()
    elif tecla == "e":
        sessao.alternar_exploracao()
    elif tecla == "r":
        sessao.reiniciar_questao()
    elif tecla == "p":
        sessao.repetir_pergunta()
    elif tecla == " ":
        sessao.verificar_ou_avancar(leitura)
    elif tecla == "h":
        sessao.alternar_ajuda()
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

    # Conta as câmeras antes de abrir a principal: abrir o mesmo índice duas vezes falha em alguns sistemas.
    n_cameras = contar_cameras() if config.CAMERA_EXIGIR_MESMA else None
    cap = abrir_camera()
    if cap is None:
        logger.error("Erro: Não foi possível abrir a câmera.")
        falador.bipe("erro")
        falador.falar("Não foi possível abrir a câmera.")
        time.sleep(3)
        falador.parar()
        return 1
    camera = Camera(cap, n_cameras)

    detector = criar_detector()
    estabilizador = Estabilizador()
    sessao = Sessao(falador)
    detector_base = DetectorBase()
    estabilizador_base = EstabilizadorBase()
    estabilizador_fora = EstabilizadorBase()
    sessao.iniciar(calibrar=True)  # a calibração pode ser pulada com N
    logger.info(TECLAS_AJUDA)

    ids_anteriores: tuple[int, ...] = ()
    vigia = VigiaJanela()
    ultimo_frame = np.zeros((config.CAMERA_ALTURA, config.CAMERA_LARGURA, 3), dtype=np.uint8)
    ultima_tecla, instante_tecla = "", 0.0

    try:
        cv2.namedWindow(config.JANELA_TITULO)
        cv2.setWindowProperty(config.JANELA_TITULO, cv2.WND_PROP_TOPMOST, 1)
    except (cv2.error, AttributeError):
        pass  # sem suporte a "sempre no topo" neste sistema

    try:
        while True:
            frame, evento = camera.ler()
            if evento == "caiu":
                logger.error("Câmera desconectada")
                falador.bipe("erro")
                falador.falar(msg.CAMERA_DESCONECTADA)
            elif evento == "voltou":
                estabilizador.limpar()
                estabilizador_base.limpar()
                estabilizador_fora.limpar()
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
                        base_ok=False,
                    )
                    cv2.imshow(config.JANELA_TITULO, tela)
                tecla, ultima_tecla, instante_tecla = filtrar_tecla(
                    ler_tecla(cv2.waitKey(30 if camera.caiu else 1)),
                    ultima_tecla,
                    instante_tecla,
                    time.monotonic(),
                )
                if vigia.fechada():
                    break
                # Sem câmera, ignora comandos que dependem dela.
                if tecla in (" ", "r", "n", "c"):
                    tecla = ""
                if not tratar_tecla(tecla, sessao, Leitura([], base=False)):
                    break
                continue

            ultimo_frame = frame.copy()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            corners, ids, _ = detector.detectMarkers(gray)
            ids_detectados = ids.flatten().tolist() if ids is not None else []

            display = frame.copy()
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(display, corners, ids)

            if detector_base.ativo or sessao.estado.calibrando:
                base_visivel = detector_base.medir(frame)
            else:
                base_visivel = True  # sem calibração a base não é detectada
            if detector_base.ativo:
                base = detector_base.base_atual(min(frame.shape[:2]))
                ids_do_quadro, tem_pecas_fora_base = ids_na_base(ids, corners, base)
                if base is not None and not sessao.estado.calibrando:
                    cv2.circle(display, base[0], base[1], (0, 255, 0), 2)
                    cv2.circle(display, base[0], 4, (0, 0, 255), -1)
            else:
                ids_do_quadro = [i for i in ids_detectados if i in config.ID_VALUES_MAP]
                tem_pecas_fora_base = False

            candidata_vista = None
            if sessao.estado.calibrando:
                candidata = detector_base.candidata_calibracao(min(frame.shape[:2]))
                candidata_vista = candidata is not None
                if candidata is not None:
                    destacar_candidata(display, *candidata)

            ids_validos = estabilizador.atualizar(ids_do_quadro)
            base_ok = estabilizador_base.atualizar(base_visivel)
            fora_base_ok = estabilizador_fora.atualizar(tem_pecas_fora_base)
            leitura = Leitura(
                ids_validos,
                estabilizador.oscilando,
                base_ok,
                fora_base_ok,
                detector_base.ativo,
            )

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
            if vigia.fechada():
                break
            if sessao.estado.calibrando:
                if tecla == " ":
                    ha_pecas = any(i in config.ID_VALUES_MAP for i in ids_detectados)
                    codigo = detector_base.calibrar(frame, ha_pecas)
                    sessao.resultado_calibracao(codigo)
                    if codigo == "ok":  # leituras antigas foram feitas sem (ou com outra) base
                        for e in (estabilizador, estabilizador_base, estabilizador_fora):
                            e.limpar()
                    tecla = ""
                elif tecla == "n":
                    sessao.cancelar_calibracao(detector_base.ativo)
                    tecla = ""
            elif tecla == "c" and not sessao.estado.confirmando_saida:
                detector_base.limpar_medidas()
                falador.bipe("info")
                sessao.iniciar_calibracao()
                tecla = ""
            if not tratar_tecla(tecla, sessao, leitura):
                break

            display = desenhar_interface(
                display,
                sessao.estado,
                leitura.ids,
                leitura.total,
                oscilando=leitura.oscilando,
                camera_ok=True,
                audio_ok=falador.saude_ok,
                base_ok=base_ok if detector_base.ativo else None,
                candidata_base=candidata_vista,
            )
            cv2.imshow(config.JANELA_TITULO, display)
            if vigia.fechada():
                break
    finally:
        falador.parar()
        camera.liberar()
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
