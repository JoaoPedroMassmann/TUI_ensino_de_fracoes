"""Fala assíncrona (text-to-speech) com pyttsx3."""

from __future__ import annotations

import importlib.util
import logging
import queue
import subprocess
import sys
import threading

from . import config

logger = logging.getLogger(__name__)

# argv: [1] texto, [2] velocidade, [3:] trechos para escolher a voz (ex.: "pt-br").
_SCRIPT_TTS = (
    "import sys, pyttsx3\n"
    "e = pyttsx3.init()\n"
    "e.setProperty('rate', int(sys.argv[2]))\n"
    "dicas = [d.lower() for d in sys.argv[3:]]\n"
    "for v in e.getProperty('voices'):\n"
    "    ident = ' '.join([str(v.id), str(v.name), str(getattr(v, 'languages', ''))]).lower()\n"
    "    if any(d in ident for d in dicas):\n"
    "        e.setProperty('voice', v.id)\n"
    "        break\n"
    "e.say(sys.argv[1])\n"
    "e.runAndWait()\n"
)


def tts_disponivel() -> bool:
    return importlib.util.find_spec("pyttsx3") is not None


class Falador:
    """Fila de falas."""
    def __init__(
        self,
        habilitado: bool = True,
        taxa: int = config.TTS_TAXA,
        dicas_voz: tuple[str, ...] = config.TTS_VOZ_DICAS,
    ) -> None:
        self._habilitado = habilitado
        self._taxa = taxa
        self._dicas_voz = tuple(dicas_voz)
        self._fila: queue.Queue[tuple[int, str]] = queue.Queue()
        self._lock = threading.Lock()
        self._processo: subprocess.Popen | None = None
        self._geracao = 0
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._habilitado and self._thread is None:
            self._thread = threading.Thread(target=self._trabalhar, daemon=True)
            self._thread.start()

    def falar(self, texto: str) -> None:
        """Corta a fala atual, descarta as pendentes e fala o novo texto."""
        if not self._habilitado:
            return
        with self._lock:
            self._geracao += 1
            self._terminar_processo()
            geracao = self._geracao
        self._fila.put((geracao, texto))

    def parar(self) -> None:
        """Corta qualquer fala em andamento (usado ao sair do programa)."""
        with self._lock:
            self._geracao += 1
            self._terminar_processo()

    def _terminar_processo(self) -> None:
        if self._processo is not None and self._processo.poll() is None:
            self._processo.terminate()

    def _trabalhar(self) -> None:
        while True:
            geracao, texto = self._fila.get()
            try:
                with self._lock:
                    if geracao != self._geracao:
                        continue
                    processo = subprocess.Popen(
                        [
                            sys.executable,
                            "-c",
                            _SCRIPT_TTS,
                            texto,
                            str(self._taxa),
                            *self._dicas_voz,
                        ]
                    )
                    self._processo = processo
                processo.wait()
            except Exception:
                logger.exception("Erro no sistema de áudio")
            finally:
                with self._lock:
                    self._processo = None
