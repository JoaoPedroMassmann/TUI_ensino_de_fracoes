"""Detecção das tags ArUco e estabilização das leituras entre quadros."""

from __future__ import annotations

from collections import Counter, deque

import cv2

from . import config


def criar_detector() -> cv2.aruco.ArucoDetector:
    aruco_dict = cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_TYPE)
    parametros = cv2.aruco.DetectorParameters()
    parametros.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parametros.minMarkerPerimeterRate = config.MIN_MARKER_PERIMETER_RATE
    parametros.adaptiveThreshWinSizeMin = config.ADAPTIVE_THRESH_WIN_MIN
    parametros.adaptiveThreshWinSizeMax = config.ADAPTIVE_THRESH_WIN_MAX
    parametros.adaptiveThreshWinSizeStep = config.ADAPTIVE_THRESH_WIN_STEP
    return cv2.aruco.ArucoDetector(aruco_dict, parametros)


class Estabilizador:
    """Decide quais peças estão na mesa olhando os últimos quadros.

    Para cada ID, vale a quantidade de peças vista na maioria dos quadros recentes. Assim,
    um quadro em que a câmera perdeu uma tag não derruba a leitura.
    """

    def __init__(self, janela: int = config.FRAMES_ESTABILIDADE) -> None:
        self._historico: deque[Counter] = deque(maxlen=janela)

    def atualizar(self, ids_do_quadro: list[int]) -> list[int]:
        self._historico.append(Counter(ids_do_quadro))
        todos = sorted(set().union(*self._historico))
        estaveis: list[int] = []
        for tag_id in todos:
            frequencia = Counter(h.get(tag_id, 0) for h in self._historico)
            melhor = max(frequencia.values())
            # em caso de empate, vale a maior contagem
            contagem = max(v for v, n in frequencia.items() if n == melhor)
            estaveis.extend([tag_id] * contagem)
        return estaveis

    def limpar(self) -> None:
        self._historico.clear()
