"""Fala assíncrona (text-to-speech) com pyttsx3 e sinais sonoros imediatos."""

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

# tipo de feedback -> sequência de (frequência em Hz, duração em ms)
# Frequências >= 330 Hz para boa audibilidade em alto-falantes de notebook.
_PADROES_BIPE = {
    "tecla": ((580, 35),),
    "ok": ((660, 120), (880, 160)),
    "parabens": ((660, 120), (880, 120), (1100, 240)),
    "erro": ((330, 320),),
    "aviso": ((480, 110), (480, 110)),
    "info": ((540, 90),),
    "leitura": ((620, 70), (740, 70)),
    "instrutor": ((880, 90), (660, 90), (880, 120)),
}


def _tocar_bipe(padrao: tuple[tuple[int, int], ...]) -> None:
    try:
        import winsound
    except ImportError:
        sys.stdout.write("\a")
        sys.stdout.flush()
        return
    try:
        for frequencia, duracao in padrao:
            winsound.Beep(frequencia, duracao)
    except RuntimeError:
        logger.exception("Não foi possível tocar o bipe")


def tts_disponivel() -> bool:
    return importlib.util.find_spec("pyttsx3") is not None


class Falador:
    """Fila de falas e sinais sonoros."""

    def __init__(
        self,
        habilitado: bool = True,
        taxa: int = config.TTS_TAXA,
        dicas_voz: tuple[str, ...] = config.TTS_VOZ_DICAS,
        bipes: bool = True,
    ) -> None:
        self._habilitado = habilitado
        self._erro_audio = False
        self._bipes = bipes
        self._taxa = taxa
        self._dicas_voz = tuple(dicas_voz)
        self._fila: queue.Queue[tuple[int, str]] = queue.Queue()
        self._lock = threading.Lock()
        self._processo: subprocess.Popen | None = None
        self._geracao = 0
        self._thread: threading.Thread | None = None
        self.tocou_bipe = False
        self._cortado = False

    @property
    def saude_ok(self) -> bool:
        """True se o TTS está instalado e funcionando sem erros."""
        return self._habilitado and not self._erro_audio

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

    def bipe(self, tipo: str) -> None:
        """Toca um sinal curto imediato."""
        padrao = _PADROES_BIPE.get(tipo)
        if self._bipes and padrao:
            self.tocou_bipe = True
            threading.Thread(target=_tocar_bipe, args=(padrao,), daemon=True).start()

    def parar(self) -> None:
        """Corta qualquer fala em andamento (usado ao sair do programa)."""
        with self._lock:
            self._geracao += 1
            self._terminar_processo()

    def _terminar_processo(self) -> None:
        if self._processo is not None and self._processo.poll() is None:
            self._cortado = True
            self._processo.terminate()

    def _registrar_saida(self, codigo: int | None) -> None:
        """Só conta como falha do áudio se o processo falhou sem termos cortado a fala."""
        with self._lock:
            cortado, self._cortado = self._cortado, False
        if cortado or codigo is None:
            return
        if codigo == 0:
            self._erro_audio = False
        else:
            if not self._erro_audio:
                self.bipe("erro")
            self._erro_audio = True

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
                self._registrar_saida(processo.wait())
            except Exception:
                self._erro_audio = True
                logger.exception("Erro no sistema de áudio")
            finally:
                with self._lock:
                    self._processo = None
