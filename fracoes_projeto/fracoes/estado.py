"""Estado da atividade e transições entre questões e fases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import config
from . import mensagens as msg
from .atividades import FASES, Fase, Questao
from .avaliacao import Leitura, avaliar, descrever_leitura

INSTRUCAO = "Posicione as peças diante da câmera e aperte a tecla espaço para verificar."

# tipo -> rótulo na tela, cor da mensagem, frase falada antes da mensagem
TIPOS_FEEDBACK = {
    "ok": ("CORRETO", config.VERDE, "Correto!"),
    "erro": ("TENTE DE NOVO", config.VERMELHO, "Tente de novo."),
    "aviso": ("ATENÇÃO", config.AMARELO, "Atenção."),
    "parabens": ("FASE CONCLUÍDA", config.VERDE, None),
    "info": (None, config.BRANCO, None),
    "leitura": ("LEITURA", config.BRANCO, None),
}

TROCA_NENHUMA = 0
TROCA_RETIRAR = 1
TROCA_POSICIONAR = 2

def com_ponto(texto: str) -> str:
    return texto if texto.endswith((".", "!", "?")) else texto + "."


def titulo_falado(fase: Fase) -> str:
    """Tratamento do título da fase para ser falado."""
    return re.sub(r":", ".", fase.titulo) + "."


@dataclass
class EstadoSistema:
    fase: int = 1
    questao_atual: int = 0
    etapa_atual: int = 1
    troca: int = TROCA_NENHUMA
    exploracao: bool = False
    resolvida: bool = False
    tentativas: int = 0
    rotulo: str | None = None
    cor: tuple[int, int, int] = config.BRANCO
    mensagem: str = INSTRUCAO

    @property
    def fase_atual(self) -> Fase:
        return FASES[self.fase]

    @property
    def questao(self) -> Questao:
        return self.fase_atual.questoes[self.questao_atual]

    @property
    def enunciado_atual(self) -> str:
        if self.questao.duas_etapas and self.etapa_atual == 2 and self.questao.segundo_enunciado:
            return self.questao.segundo_enunciado
        return self.questao.enunciado

class Sessao:
    """Regras da atividade."""
    def __init__(self, falador, estado: EstadoSistema | None = None) -> None:
        self.falador = falador
        self.estado = estado or EstadoSistema()

    # Falas e feedback
    def fala_questao(self, abertura: str = "") -> str:
        estado = self.estado
        partes = [
            abertura,
            f"Questão {estado.questao_atual + 1} de {len(estado.fase_atual.questoes)}.",
            com_ponto(estado.enunciado_atual),
        ]
        return " ".join(p for p in partes if p)

    def definir_feedback(self, tipo: str, texto: str, repetir_enunciado: bool = False) -> None:
        """Atualiza a tela e fornece o feedback. Se for erro, também repete o enunciado."""
        estado = self.estado
        rotulo, cor, falado = TIPOS_FEEDBACK[tipo]
        estado.rotulo, estado.cor, estado.mensagem = rotulo, cor, texto

        mensagem_falada = texto
        if repetir_enunciado:
            mensagem_falada = f"{texto} Repetindo o enunciado: {com_ponto(estado.enunciado_atual)}"
        self.falador.bipe(tipo)
        self.falador.falar(" ".join(p for p in (falado, mensagem_falada) if p))

    def anunciar_questao(self, abertura: str = "") -> None:
        estado = self.estado
        estado.rotulo, estado.cor, estado.mensagem = None, config.BRANCO, INSTRUCAO
        self.falador.falar(f"{self.fala_questao(abertura)} {INSTRUCAO}")

    # Comandos do usuário 
    def iniciar(self) -> None:
        self.anunciar_questao(abertura=titulo_falado(self.estado.fase_atual))

    def trocar_fase(self, fase: int, abertura_extra: str = "") -> None:
        self.estado.fase = fase
        self.estado.exploracao = False
        self.estado.questao_atual = 0
        self._zerar_questao()
        abertura = f"{abertura_extra} {titulo_falado(self.estado.fase_atual)}".strip()
        self.anunciar_questao(abertura=abertura)

    def _zerar_questao(self) -> None:
        self.estado.etapa_atual = 1
        self.estado.resolvida = False
        self.estado.troca = TROCA_NENHUMA
        self.estado.tentativas = 0

    def reiniciar_questao(self) -> None:
        if self.estado.exploracao:
            return
        self._zerar_questao()
        self.definir_feedback("info", "Questão reiniciada. " + INSTRUCAO)

    def _instrucao_troca(self) -> str | None:
        """Instrução da troca de base em andamento, ou None se não há troca."""
        instrucoes = {
            TROCA_RETIRAR: msg.RETIRAR_PECA_BASE,
            TROCA_POSICIONAR: msg.POSICIONAR_PECA_BASE,
        }
        return instrucoes.get(self.estado.troca)

    def repetir_pergunta(self) -> None:
        if self.estado.exploracao:
            self.falador.falar(msg.EXPLORACAO_INICIO)
            return
        self.falador.falar(self._instrucao_troca() or self.fala_questao())

    def alternar_exploracao(self) -> None:
        """Liga ou desliga o modo exploração, que só lê o que a câmera vê."""
        estado = self.estado
        if estado.exploracao:
            estado.exploracao = False
            estado.rotulo, estado.cor = None, config.BRANCO
            estado.mensagem = self._instrucao_troca() or INSTRUCAO
            retomada = self._instrucao_troca() or self.fala_questao()
            self.falador.falar(f"{msg.EXPLORACAO_SAIDA} {retomada}")
        else:
            estado.exploracao = True
            self.definir_feedback("info", msg.EXPLORACAO_INICIO)


    def verificar_ou_avancar(self, leitura: Leitura) -> None:
        estado = self.estado
        if estado.exploracao:
            self.definir_feedback("leitura", descrever_leitura(leitura))
            return
        if estado.troca != TROCA_NENHUMA:
            self._tratar_troca(leitura)
            return
        if estado.resolvida:
            self._avancar()
            return
        resultado = avaliar(estado.questao, leitura, tentativa=estado.tentativas + 1, etapa_atual=estado.etapa_atual)
        if resultado.tipo == "erro":  # "nenhuma peça" (aviso) não conta como tentativa
            estado.tentativas += 1

        if resultado.tipo == "ok" and estado.questao.duas_etapas and estado.etapa_atual == 1:
            self._iniciar_troca()
            return

        estado.resolvida = resultado.tipo == "ok"
        self.definir_feedback(
            resultado.tipo, resultado.texto, repetir_enunciado=resultado.repetir_enunciado
        )

    def _iniciar_troca(self) -> None:
        """Primeira etapa certa: pede a retirada da base."""
        estado = self.estado
        estado.troca = TROCA_RETIRAR
        estado.tentativas = 0
        estado.resolvida = False
        self.definir_feedback("ok", msg.RETIRAR_PECA_BASE)

    def _tratar_troca(self, leitura: Leitura) -> None:
        """Comportamento quando o usuário está trocando a peça base (duas etapas)."""
        estado = self.estado
        if estado.troca == TROCA_RETIRAR:
            if leitura.ids:
                self.definir_feedback("aviso", msg.RETIRAR_BASE_ERRO)
                return
            estado.troca = TROCA_POSICIONAR
            self.definir_feedback("info", msg.POSICIONAR_PECA_BASE)
            return
        estado.troca = TROCA_NENHUMA
        estado.etapa_atual = 2
        self.anunciar_questao(abertura="Segunda etapa.")

    def _avancar(self) -> None:
        estado = self.estado
        if estado.questao_atual + 1 < len(estado.fase_atual.questoes):
            estado.questao_atual += 1
            self._zerar_questao()
            self.anunciar_questao()
        elif estado.fase + 1 in FASES:
            self.trocar_fase(estado.fase + 1, abertura_extra="Fase concluída! Avançando para")
        else:
            self.definir_feedback(
                "parabens",
                "Parabéns! Você concluiu todas as fases do sistema! "
                "Aperte 1 para recomeçar ou q para sair.",
            )
