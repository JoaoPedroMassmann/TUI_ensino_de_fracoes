"""Estado da atividade e transições entre atividades e fases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import config
from . import mensagens as msg
from .atividades import FASES, Fase, Questao
from .avaliacao import Leitura, avaliar, descrever_leitura

INSTRUCAO = (
    "Encaixe as peças numéricas na peça base e aperte espaço para verificar."
)

# tipo -> rótulo na tela, cor da mensagem, frase falada antes da mensagem
TIPOS_FEEDBACK = {
    "ok": ("CORRETO", config.VERDE, None),
    "erro": ("TENTE DE NOVO", config.VERMELHO, "Tente de novo."),
    "aviso": ("ATENÇÃO", config.AMARELO, "Atenção."),
    "parabens": ("FASE CONCLUÍDA", config.VERDE, None),
    "info": (None, config.BRANCO, None),
    "leitura": ("LEITURA", config.BRANCO, None),
    "instrutor": ("INSTRUTOR", config.AMARELO, None),
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
    etapa_atual: int = 1  # 1 = utilizando a primeira base, 2 = utilizando a segunda base
    troca: int = TROCA_NENHUMA
    exploracao: bool = False
    menu: bool = False
    calibrando: bool = False
    resolvida: bool = False
    tentativas: int = 0
    confirmando_saida: bool = False
    rotulo: str | None = None
    cor: tuple[int, int, int] = config.BRANCO
    mensagem: str = INSTRUCAO
    ids_ultima_avaliacao: tuple[int, ...] | None = None

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

    def fala_questao(self, abertura: str = "") -> str:
        estado = self.estado
        prefixo_etapa = f"Etapa {estado.etapa_atual} de 2." if estado.questao.duas_etapas else ""
        partes = [
            abertura,
            f"Atividade {estado.questao_atual + 1} de {len(estado.fase_atual.questoes)}.",
            prefixo_etapa,
            com_ponto(estado.enunciado_atual),
        ]
        return " ".join(p for p in partes if p)

    def definir_feedback(
        self,
        tipo: str,
        texto: str,
        repetir_enunciado: bool = False,
        bipe_tipo: str | None = None,
    ) -> None:
        """Atualiza a tela e fornece o feedback."""
        estado = self.estado
        rotulo, cor, falado = TIPOS_FEEDBACK[tipo]
        estado.rotulo, estado.cor, estado.mensagem = rotulo, cor, texto

        mensagem_falada = texto
        if repetir_enunciado:
            mensagem_falada = f"{texto} Repetindo a atividade: {com_ponto(estado.enunciado_atual)}"
        self.falador.bipe(bipe_tipo or tipo)
        self.falador.falar(" ".join(p for p in (falado, mensagem_falada) if p))

    def _texto_menu(self) -> str:
        return msg.MENU_OPCOES.format(minimo=min(FASES), maximo=max(FASES))


    def _anunciar_menu(self, prefixo: str = "") -> None:
        estado = self.estado
        estado.menu = True
        estado.rotulo, estado.cor = None, config.BRANCO
        estado.mensagem = msg.BOAS_VINDAS
        estado.ids_ultima_avaliacao = None
        self.falador.falar(f"{prefixo} {msg.BOAS_VINDAS} {self._texto_menu()}".strip())

    def falar_ajuda(self) -> None:
        self.falador.falar(msg.AJUDA_TECLAS.format(minimo=min(FASES), maximo=max(FASES)))

    def anunciar_questao(self, abertura: str = "", bipe_tipo: str | None = None) -> None:
        self.falador.bipe("tecla")
        estado = self.estado
        estado.rotulo, estado.cor, estado.mensagem = None, config.BRANCO, INSTRUCAO
        estado.ids_ultima_avaliacao = None
        if bipe_tipo:
            self.falador.bipe(bipe_tipo)
        self.falador.falar(f"{self.fala_questao(abertura)} {INSTRUCAO}")

    def iniciar_calibracao(self) -> None:
        estado = self.estado
        estado.calibrando, estado.menu = True, False
        estado.rotulo, estado.cor = None, config.BRANCO
        estado.mensagem = msg.CALIBRACAO_INICIO
        self.falador.falar(msg.CALIBRACAO_INICIO)

    def resultado_calibracao(self, codigo: str) -> None:
        if codigo == "ok":
            self.estado.calibrando = False
            self.falador.bipe("ok")
            self._anunciar_menu(msg.CALIBRACAO_OK)
        else:
            self.definir_feedback("aviso", msg.CALIBRACAO_FALHAS[codigo])

    def pular_calibracao(self) -> None:
        self.estado.calibrando = False
        self.falador.bipe("info")
        self._anunciar_menu(msg.CALIBRACAO_PULADA)

    def iniciar(self, calibrar: bool = False) -> None:
        self.falador.bipe("info")
        if calibrar:
            self.iniciar_calibracao()
        else:
            self._anunciar_menu()

    # Comandos do usuário

    def trocar_fase(self, fase: int, abertura_extra: str = "") -> None:
        if fase not in FASES:
            return
        self.estado.fase = fase
        self.estado.exploracao = False
        self.estado.menu = False
        self.estado.questao_atual = 0
        self._zerar_questao()
        abertura = f"{abertura_extra} {titulo_falado(self.estado.fase_atual)}".strip()
        self.anunciar_questao(abertura=abertura)

    def _zerar_questao(self) -> None:
        self.estado.etapa_atual = 1
        self.estado.resolvida = False
        self.estado.troca = TROCA_NENHUMA
        self.estado.tentativas = 0
        self.estado.confirmando_saida = False
        self.estado.ids_ultima_avaliacao = None

    def reiniciar_questao(self) -> None:
        if self.estado.exploracao or self.estado.menu:
            return
        self._zerar_questao()
        self.definir_feedback("info", "Atividade reiniciada. " + INSTRUCAO)

    def _instrucao_troca(self) -> str | None:
        """Instrução da troca de base em andamento, ou None se não há troca."""
        instrucoes = {
            TROCA_RETIRAR: msg.RETIRAR_PECA_BASE,
            TROCA_POSICIONAR: msg.POSICIONAR_PECA_BASE,
        }
        return instrucoes.get(self.estado.troca)

    def repetir_pergunta(self) -> None:
        self.falador.bipe("tecla")
        if self.estado.exploracao:
            self.falador.falar(msg.EXPLORACAO_INICIO)
            return
        if self.estado.calibrando:
            self.falador.falar(msg.CALIBRACAO_INICIO)
            return
        if self.estado.menu:
            self._anunciar_menu()
            return
        self.falador.falar(self._instrucao_troca() or self.fala_questao())

    def alternar_exploracao(self) -> None:
        """Liga ou desliga o modo Exploração, que só lê o que a câmera vê."""
        estado = self.estado
        estado.ids_ultima_avaliacao = None
        if estado.exploracao:
            estado.exploracao = False
            estado.rotulo, estado.cor = None, config.BRANCO
            if estado.menu:
                estado.mensagem = msg.BOAS_VINDAS
                self.falador.bipe("info")
                self.falador.falar(f"{msg.EXPLORACAO_SAIDA} {self._texto_menu()}")
                return
            estado.mensagem = self._instrucao_troca() or INSTRUCAO
            retomada = self._instrucao_troca() or self.fala_questao()
            self.falador.bipe("info")
            self.falador.falar(f"{msg.EXPLORACAO_SAIDA} {retomada}")
        else:
            estado.exploracao = True
            self.definir_feedback("info", msg.EXPLORACAO_INICIO)

    def pedir_confirmacao_saida(self) -> None:
        self.estado.confirmando_saida = True
        self.definir_feedback("aviso", msg.CONFIRMAR_SAIDA)

    def cancelar_confirmacao_saida(self) -> None:
        self.estado.confirmando_saida = False
        contexto = (
            self._texto_menu()
            if self.estado.menu
            else (self._instrucao_troca() or INSTRUCAO)
        )
        self.definir_feedback("info", "Saída cancelada. " + contexto)

    def notificar_mudanca_mesa(self, ids_atuais: tuple[int, ...]) -> None:
        """Limpa feedback desatualizado na tela quando o aluno altera as peças após verificar."""
        estado = self.estado
        if (
            estado.ids_ultima_avaliacao is None
            or estado.exploracao
            or estado.resolvida
            or estado.troca != TROCA_NENHUMA
            or estado.rotulo == "FASE CONCLUÍDA"
        ):
            return
        if ids_atuais != estado.ids_ultima_avaliacao:
            estado.ids_ultima_avaliacao = None
            estado.rotulo = None
            estado.cor = config.BRANCO
            estado.mensagem = msg.LEITURA_MUDOU

    def verificar_ou_avancar(self, leitura: Leitura) -> None:
        estado = self.estado
        if estado.exploracao:
            self.definir_feedback("leitura", descrever_leitura(leitura))
            return
        if estado.menu:
            self.trocar_fase(1)
            return
        if estado.troca != TROCA_NENHUMA:
            self._tratar_troca(leitura)
            return
        if estado.resolvida:
            self._avancar()
            return

        resultado = avaliar(
            estado.questao,
            leitura,
            tentativa=estado.tentativas + 1,
            etapa_atual=estado.etapa_atual,
        )
        estado.ids_ultima_avaliacao = tuple(sorted(leitura.ids))

        if resultado.tipo == "erro":
            estado.tentativas += 1

        if resultado.tipo == "ok" and estado.questao.duas_etapas and estado.etapa_atual == 1:
            self._iniciar_troca()
            return

        estado.resolvida = resultado.tipo == "ok"
        self.definir_feedback(
            resultado.tipo, resultado.texto, repetir_enunciado=resultado.repetir_enunciado
        )

    def _iniciar_troca(self) -> None:
        """Primeira base certa: pede a retirada da peça base ao instrutor."""
        estado = self.estado
        estado.troca = TROCA_RETIRAR
        estado.tentativas = 0
        estado.resolvida = False
        estado.ids_ultima_avaliacao = None
        self.definir_feedback("ok", "Primeira etapa certa. " + msg.RETIRAR_PECA_BASE)

    def _tratar_troca(self, leitura: Leitura) -> None:
        """Comportamento quando o instrutor está trocando a peça base."""
        estado = self.estado
        if estado.troca == TROCA_RETIRAR:
            if leitura.ids:
                self.definir_feedback("aviso", msg.RETIRAR_BASE_ERRO, bipe_tipo="instrutor")
                return
            if leitura.base:
                self.definir_feedback("aviso", msg.RETIRAR_BASE_VISIVEL, bipe_tipo="instrutor")
                return
            estado.troca = TROCA_POSICIONAR
            self.definir_feedback("instrutor", msg.POSICIONAR_PECA_BASE)
            return
        if not leitura.base:  # TROCA_POSICIONAR
            self.definir_feedback("aviso", msg.BASE_NAO_VISTA, bipe_tipo="instrutor")
            return
        estado.troca = TROCA_NENHUMA
        estado.etapa_atual = 2
        self.anunciar_questao(abertura="Etapa 2 de 2.")

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
                "Aperte 1 para recomeçar ou Q para sair.",
            )
