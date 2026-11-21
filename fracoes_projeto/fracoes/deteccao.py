"""Detecção das tags ArUco e estabilização das leituras entre quadros."""

from __future__ import annotations

from collections import Counter, deque

import cv2
import numpy as np

from . import config


def criar_detector() -> cv2.aruco.ArucoDetector:
    aruco_dict = cv2.aruco.getPredefinedDictionary(config.ARUCO_DICT_TYPE)
    parametros = cv2.aruco.DetectorParameters()
    parametros.minMarkerPerimeterRate = config.MIN_MARKER_PERIMETER_RATE
    parametros.adaptiveThreshWinSizeMin = config.ADAPTIVE_THRESH_WIN_MIN
    parametros.adaptiveThreshWinSizeMax = config.ADAPTIVE_THRESH_WIN_MAX
    parametros.adaptiveThreshWinSizeStep = config.ADAPTIVE_THRESH_WIN_STEP
    return cv2.aruco.ArucoDetector(aruco_dict, parametros)


def candidatos_base(frame: np.ndarray) -> list[tuple[float, float, tuple[int, int]]]:
    gray = cv2.GaussianBlur(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (7, 7), 0)
    _, mascara = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    menor_lado = min(frame.shape[:2])
    candidatos = []
    for c in contornos:
        (cx, cy), raio = cv2.minEnclosingCircle(c)
        if raio < 5:
            continue
        circularidade = cv2.contourArea(c) / (np.pi * raio**2)
        candidatos.append((raio / menor_lado, circularidade, (int(cx), int(cy))))
    return sorted(candidatos, reverse=True)


class DetectorBase:
    """Detecta a peça base (disco escuro grande); pode ser calibrada com a base sozinha."""

    def __init__(self) -> None:
        self.raio_ref: float | None = None
        self.ativo = config.DETECTAR_BASE
        self._recentes: deque[list] = deque(maxlen=config.CALIBRACAO_QUADROS)

    def _limites(self) -> tuple[float, float]:
        if self.raio_ref is None:
            return config.BASE_RAIO_MIN, config.BASE_RAIO_MAX
        tol = config.BASE_TOLERANCIA_RAIO
        return self.raio_ref * (1 - tol), self.raio_ref * (1 + tol)

    def medir(self, frame: np.ndarray) -> bool:
        """Chamar a cada quadro: guarda as medidas e diz se há base à vista."""
        candidatos = candidatos_base(frame)
        self._recentes.append(candidatos)
        minimo, maximo = self._limites()
        return any(
            minimo <= r <= maximo and c >= config.BASE_CIRCULARIDADE_MIN
            for r, c, _ in candidatos
        )

    def calibrar(self, frame: np.ndarray, ha_pecas: bool) -> str:
        """Mede a base sozinha. Devolve "ok", "pecas", "sem_base", "instavel" ou "fundo_escuro"."""
        if ha_pecas:
            return "pecas"
        raios = []
        for candidatos in self._recentes:
            redondos = [
                r for r, c, _ in candidatos
                if config.BASE_RAIO_MIN <= r <= config.BASE_RAIO_MAX
                and c >= config.BASE_CIRCULARIDADE_MIN
            ]
            if redondos:
                raios.append(max(redondos))
        if len(raios) < 0.8 * config.CALIBRACAO_QUADROS:
            return "sem_base"
        mediana = float(np.median(raios))
        if (max(raios) - min(raios)) / mediana > config.CALIBRACAO_DISPERSAO_MAX:
            return "instavel"
        if not self._fundo_claro(frame):
            return "fundo_escuro"
        self.raio_ref = mediana
        return "ok"

    @staticmethod
    def _fundo_claro(frame: np.ndarray) -> bool:
        candidatos = candidatos_base(frame)
        if not candidatos:
            return False
        raio, _, centro = candidatos[0]  # o maior blob é a base
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fora = np.full(gray.shape, 255, np.uint8)
        cv2.circle(fora, centro, int(raio * min(gray.shape) * 1.1), 0, -1)
        return float(np.median(gray[fora > 0])) >= 120

    
class EstabilizadorBase:
    def __init__(self, janela: int = config.FRAMES_ESTABILIDADE) -> None:
        self._historico: deque[bool] = deque(maxlen=janela)

    def atualizar(self, visivel: bool) -> bool:
        self._historico.append(visivel)
        return sum(self._historico) > len(self._historico) / 2

    def limpar(self) -> None:
        self._historico.clear()


class Estabilizador:
    """Decide quais peças estão na mesa olhando os últimos quadros."""

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

    @property
    def oscilando(self) -> bool:
        """True se pelo menos 2 quadros da janela divergem da leitura mais comum."""
        if len(self._historico) < 2:
            return False
        padroes = Counter(tuple(sorted(h.items())) for h in self._historico)
        return len(self._historico) - max(padroes.values()) >= 2

    def limpar(self) -> None:
        self._historico.clear()
