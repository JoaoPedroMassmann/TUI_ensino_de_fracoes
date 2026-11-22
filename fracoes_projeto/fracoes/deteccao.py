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


_LADO_ANALISE = 360  # a base é grande: basta analisar o quadro reduzido a este menor lado


def candidatos_base(frame: np.ndarray) -> list[tuple[float, float, tuple[int, int]]]:
    """Blobs escuros candidatos a peça base: (raio / menor lado, circularidade, centro em pixels do quadro)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    escala = min(1.0, _LADO_ANALISE / min(gray.shape[:2]))
    if escala < 1.0:
        gray = cv2.resize(gray, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mascara = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    menor_lado = min(gray.shape[:2])
    candidatos = []
    for c in contornos:
        (cx, cy), raio = cv2.minEnclosingCircle(c)
        if raio < 3:
            continue
        circularidade = cv2.contourArea(c) / (np.pi * raio**2)
        candidatos.append((raio / menor_lado, circularidade, (int(cx / escala), int(cy / escala))))
    return sorted(candidatos, reverse=True)


def ids_na_base(
    ids: np.ndarray | None,
    corners,
    base: tuple[tuple[int, int], int] | None,
) -> tuple[list[int], bool]:
    """Separa os marcadores numéricos dentro da base dos que estão fora dela.

    `base` é (centro, raio em pixels) ou None quando a base não foi vista.
    Devolve (IDs dentro da base, há marcador numérico fora ou sem base à vista).
    """
    dentro: list[int] = []
    fora = False
    if ids is None:
        return dentro, fora
    for idx, marker_id in enumerate(ids.flatten()):
        if int(marker_id) not in config.ID_VALUES_MAP:
            continue
        if base is None:
            fora = True
            continue
        (cx, cy), raio = base
        mx, my = corners[idx][0].mean(axis=0)
        if np.hypot(mx - cx, my - cy) <= raio:
            dentro.append(int(marker_id))
        else:
            fora = True
    return dentro, fora


class DetectorBase:
    """Detecta a peça base (disco escuro grande).

    A detecção só fica ativa depois de calibrada com a base sozinha; antes disso `ativo` é False.
    """

    def __init__(self) -> None:
        self.raio_ref: float | None = None
        self._recentes: deque[list] = deque(maxlen=config.CALIBRACAO_QUADROS)

    @property
    def ativo(self) -> bool:
        return self.raio_ref is not None

    def limpar_medidas(self) -> None:
        """Descarta as medidas recentes (usar ao começar uma calibração). Mantém a calibração atual."""
        self._recentes.clear()

    def candidata_calibracao(self, menor_lado: int) -> tuple[tuple[int, int], int] | None:
        """(centro, raio em pixels) do blob que a calibração usaria como base, ou None.

        Usa os limites iniciais, os mesmos de `calibrar`, para o instrutor ver o que será calibrado.
        """
        if not self._recentes:
            return None
        for r, c, centro in self._recentes[-1]:
            if config.BASE_RAIO_MIN <= r <= config.BASE_RAIO_MAX and c >= config.BASE_CIRCULARIDADE_MIN:
                return centro, int(r * menor_lado)
        return None

    def limites(self) -> tuple[float, float]:
        if self.raio_ref is None:
            return config.BASE_RAIO_MIN, config.BASE_RAIO_MAX
        tol = config.BASE_TOLERANCIA_RAIO
        return self.raio_ref * (1 - tol), self.raio_ref * (1 + tol)

    def medir(self, frame: np.ndarray) -> bool:
        """Chamar a cada quadro: guarda as medidas e diz se há base à vista."""
        self._recentes.append(candidatos_base(frame))
        return self._escolher(self._recentes[-1]) is not None

    def _escolher(self, candidatos):
        minimo, maximo = self.limites()
        for candidato in candidatos:
            r, c, _ = candidato
            if minimo <= r <= maximo and c >= config.BASE_CIRCULARIDADE_MIN:
                return candidato
        return None

    def base_atual(self, menor_lado: int) -> tuple[tuple[int, int], int] | None:
        """(centro, raio em pixels) da base no último quadro medido, ou None."""
        if not self._recentes:
            return None
        escolhido = self._escolher(self._recentes[-1])
        if escolhido is None:
            return None
        r, _, centro = escolhido
        return centro, int(r * menor_lado)

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
        self._minimo = janela // 2 + 1  # aquecimento: evita aceitar um falso positivo isolado

    def atualizar(self, ids_do_quadro: list[int]) -> list[int]:
        self._historico.append(Counter(ids_do_quadro))
        if len(self._historico) < self._minimo:
            return []
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
