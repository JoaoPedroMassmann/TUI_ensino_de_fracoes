"""Estado da atividade e transições entre questões e fases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import config
from .atividades import FASES, Fase, Questao
from .avaliacao import avaliar

INSTRUCAO = "Posicione as peças diante da câmera e aperte a tecla espaço para verificar."

# tipo -> rótulo na tela, cor da mensagem, frase falada antes da mensagem
TIPOS_FEEDBACK = {
    "ok": ("CORRETO", config.VERDE, "Correto!"),
    "erro": ("TENTE DE NOVO", config.VERMELHO, "Tente de novo."),
    "aviso": ("ATENÇÃO", config.AMARELO, "Atenção."),
    "parabens": ("FASE CONCLUÍDA", config.VERDE, None),
    "info": (None, config.BRANCO, None),
}


def com_ponto(texto: str) -> str:
    return texto if texto.endswith((".", "!", "?")) else texto + "."


def titulo_falado(fase: Fase) -> str:
    """Tratamento do título da fase para ser falado."""
    return re.sub(r":", ".", fase.titulo) + "."


@dataclass
class EstadoSistema:
    fase: int = 1
    questao_atual: int = 0
    resolvida: bool = False
    rotulo: str | None = None
    cor: tuple[int, int, int] = config.BRANCO
    mensagem: str = INSTRUCAO

    @property
    def fase_atual(self) -> Fase:
        return FASES[self.fase]

    @property
    def questao(self) -> Questao:
        return self.fase_atual.questoes[self.questao_atual]


class Sessao:
    """Regras da atividade."""
    def __init__(self, falador, estado: EstadoSistema | None = None) -> None:
        self.falador = falador
        self.estado = estado or EstadoSistema()

    # Falas e feedback
    def fala_questao(self, abertura: str = "") -> str:
        e = self.estado
        partes = [
            abertura,
            f"Questão {e.questao_atual + 1} de {len(e.fase_atual.questoes)}.",
            com_ponto(e.questao.enunciado),
        ]
        return " ".join(p for p in partes if p)

    def definir_feedback(self, tipo: str, texto: str, repetir_enunciado: bool = False) -> None:
        """Atualiza a tela e fornece o feedback. Se for erro, também repete o enunciado."""
        e = self.estado
        rotulo, cor, falado = TIPOS_FEEDBACK[tipo]
        e.rotulo, e.cor, e.mensagem = rotulo, cor, texto

        mensagem_falada = texto
        if repetir_enunciado:
            mensagem_falada = f"{texto} Repetindo o enunciado: {com_ponto(e.questao.enunciado)}"
        self.falador.falar(" ".join(p for p in (falado, mensagem_falada) if p))

    def anunciar_questao(self, abertura: str = "") -> None:
        e = self.estado
        e.rotulo, e.cor, e.mensagem = None, config.BRANCO, INSTRUCAO
        self.falador.falar(f"{self.fala_questao(abertura)} {INSTRUCAO}")

    # Comandos do usuário 
    def iniciar(self) -> None:
        self.anunciar_questao(abertura=titulo_falado(self.estado.fase_atual))

    def trocar_fase(self, fase: int, abertura_extra: str = "") -> None:
        self.estado.fase = fase
        self.estado.questao_atual = 0
        self.estado.resolvida = False
        abertura = f"{abertura_extra} {titulo_falado(self.estado.fase_atual)}".strip()
        self.anunciar_questao(abertura=abertura)

    def reiniciar_questao(self) -> None:
        self.estado.resolvida = False
        self.definir_feedback("info", "Questão reiniciada. " + INSTRUCAO)

    def repetir_pergunta(self) -> None:
        self.falador.falar(self.fala_questao())

    def verificar_ou_avancar(self, ids_validos: list[int], total: int) -> None:
        e = self.estado
        if not e.resolvida:
            resultado = avaliar(e.questao, ids_validos, total)
            e.resolvida = resultado.tipo == "ok"
            self.definir_feedback(
                resultado.tipo, resultado.texto, repetir_enunciado=resultado.repetir_enunciado
            )
            return

        if e.questao_atual + 1 < len(e.fase_atual.questoes):
            e.questao_atual += 1
            e.resolvida = False
            self.anunciar_questao()
        elif e.fase + 1 in FASES:
            self.trocar_fase(e.fase + 1, abertura_extra="Fase concluída! Avançando para")
        else:
            self.definir_feedback(
                "parabens",
                "Parabéns! Você concluiu todas as fases do sistema! "
                "Aperte 1 para recomeçar ou q para sair.",
            )
