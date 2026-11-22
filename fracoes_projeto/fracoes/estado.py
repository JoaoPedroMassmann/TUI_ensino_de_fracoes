"""Estado da atividade e transições entre atividades e fases."""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import config
from . import mensagens as msg
from .atividades import FASES, Fase, Questao
from .avaliacao import Leitura, avaliar, descrever_leitura
from .mensagens import ajuda_falada

INSTRUCAO = (
    "Encaixe as peças e aperte espaço."
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

# Quantas vezes seguidas a verificação é recusada por leitura oscilando antes de avaliar mesmo assim.
LIMITE_RECUSAS_OSCILACAO = 2

TROCA_NENHUMA = 0
TROCA_RETIRAR = 1
TROCA_POSICIONAR = 2


def com_ponto(texto: str) -> str:
    return texto if texto.endswith((".", "!", "?")) else texto + "."


def titulo_falado(fase: Fase) -> str:
    """Tratamento do título da fase para ser falado."""
    return re.sub(r":", ".", fase.titulo) + "."


def modo_ajuda(estado: "EstadoSistema") -> str:
    """Chave do conjunto de comandos válido no modo atual."""
    if estado.calibrando:
        return "calibracao"
    if estado.exploracao:
        return "exploracao"
    if estado.menu:
        return "menu"
    return "troca" if estado.troca != TROCA_NENHUMA else "atividade"


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
    ajuda_visivel: bool = False  # painel com a lista de comandos na tela
    acao_pendente: str | None = None  # tecla que confirma uma ação que perde progresso
    recusas_oscilacao: int = 0
    boas_vindas_pendente: bool = False
    feedback_antes_calibracao: tuple[str | None, tuple[int, int, int], str] | None = None

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
            mensagem_falada = f"{texto} Repito: {com_ponto(estado.enunciado_atual)}"
        self.falador.bipe(bipe_tipo or tipo)
        self.falador.falar(" ".join(p for p in (falado, mensagem_falada) if p))

    def _texto_menu(self) -> str:
        return msg.MENU_OPCOES.format(minimo=min(FASES), maximo=max(FASES))


    def _preparar_menu(self) -> None:
        estado = self.estado
        estado.menu = True
        estado.ajuda_visivel = False
        estado.rotulo, estado.cor = None, config.BRANCO
        estado.mensagem = msg.BOAS_VINDAS
        estado.ids_ultima_avaliacao = None

    def _anunciar_menu(self, prefixo: str = "") -> None:
        self._preparar_menu()
        self.estado.boas_vindas_pendente = False
        self.falador.falar(f"{prefixo} {msg.BOAS_VINDAS} {self._texto_menu()}".strip())

    def alternar_ajuda(self) -> None:
        """H: mostra a lista de comandos do modo atual na tela e a fala; de novo, fecha."""
        estado = self.estado
        if estado.ajuda_visivel:
            estado.ajuda_visivel = False
            self.falador.calar()
            return
        estado.ajuda_visivel = True
        self.falador.falar(ajuda_falada(modo_ajuda(estado), min(FASES), max(FASES)))

    def calar_fala(self) -> None:
        self.falador.calar()

    def anunciar_questao(self, abertura: str = "", bipe_tipo: str | None = None) -> None:
        self.falador.bipe("tecla")
        estado = self.estado
        estado.rotulo, estado.cor, estado.mensagem = None, config.BRANCO, INSTRUCAO
        estado.ids_ultima_avaliacao = None
        if bipe_tipo:
            self.falador.bipe(bipe_tipo)
        self.falador.falar(f"{self.fala_questao(abertura)} {INSTRUCAO}")

    def _contexto_atual(self) -> str:
        """O que falar para retomar o que o aluno estava fazendo."""
        estado = self.estado
        if estado.exploracao:
            return msg.EXPLORACAO_INICIO
        if estado.menu:
            if estado.boas_vindas_pendente:  # primeira vez, depois da calibração inicial
                estado.boas_vindas_pendente = False
                return f"{msg.BOAS_VINDAS} {self._texto_menu()}"
            return self._texto_menu()
        return self._instrucao_troca() or self.fala_questao()

    def iniciar_calibracao(self) -> None:
        """Calibração a qualquer momento: guarda a tela atual e não mexe na atividade."""
        estado = self.estado
        if estado.calibrando:
            return
        estado.ajuda_visivel = False
        estado.feedback_antes_calibracao = (estado.rotulo, estado.cor, estado.mensagem)
        estado.calibrando = True
        estado.rotulo, estado.cor = None, config.BRANCO
        estado.mensagem = msg.CALIBRACAO_TELA
        self.falador.falar(msg.CALIBRACAO_INICIO)

    def _encerrar_calibracao(self, aviso: str, bipe: str) -> None:
        estado = self.estado
        estado.calibrando = False
        estado.ajuda_visivel = False
        if estado.feedback_antes_calibracao is not None:
            estado.rotulo, estado.cor, estado.mensagem = estado.feedback_antes_calibracao
            estado.feedback_antes_calibracao = None
        self.falador.bipe(bipe)
        self.falador.falar(f"{aviso} {self._contexto_atual()}")

    def resultado_calibracao(self, codigo: str) -> None:
        if codigo == "ok":
            self._encerrar_calibracao(msg.CALIBRACAO_OK, "ok")
        else:
            self.definir_feedback("aviso", msg.CALIBRACAO_FALHAS[codigo])

    def cancelar_calibracao(self, detecta_base: bool) -> None:
        aviso = msg.CALIBRACAO_CANCELADA_ATIVA if detecta_base else msg.CALIBRACAO_CANCELADA_DESLIGADA
        self._encerrar_calibracao(aviso, "info")

    def iniciar(self, calibrar: bool = False) -> None:
        """Abre no menu; com `calibrar`, começa pela calibração (que o instrutor pode pular com N)."""
        self.falador.bipe("info")
        if calibrar:
            self._preparar_menu()
            self.estado.boas_vindas_pendente = True
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
        self.estado.acao_pendente = None
        self.estado.ajuda_visivel = False
        self.estado.recusas_oscilacao = 0
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
        if self.estado.calibrando:
            self.falador.falar(msg.CALIBRACAO_INICIO)
            return
        if self.estado.exploracao:
            self.falador.falar(msg.EXPLORACAO_INICIO)
            return
        if self.estado.menu:
            self._anunciar_menu()
            return
        self.falador.falar(self._instrucao_troca() or self.fala_questao())

    def alternar_exploracao(self) -> None:
        """Liga ou desliga o modo Exploração, que só lê o que a câmera vê."""
        estado = self.estado
        estado.ids_ultima_avaliacao = None
        estado.ajuda_visivel = False
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
        self._voltar_do_aviso("Saída cancelada.")

    def _voltar_do_aviso(self, prefixo: str) -> None:
        estado = self.estado
        if estado.calibrando:
            contexto = msg.CALIBRACAO_INICIO
        elif estado.exploracao:
            contexto = msg.EXPLORACAO_INICIO
        elif estado.menu:
            contexto = self._texto_menu()
        else:
            contexto = self._instrucao_troca() or INSTRUCAO
        self.definir_feedback("info", f"{prefixo} {contexto}")

    # Ações que perdem progresso pedem confirmação: apertar a mesma tecla de novo.

    def _tem_progresso(self) -> bool:
        e = self.estado
        if e.menu:
            return False
        ultima = len(e.fase_atual.questoes) - 1
        if e.fase == max(FASES) and e.questao_atual == ultima and e.resolvida:
            return False  # tudo concluído
        return not (
            e.questao_atual == 0 and not e.resolvida and e.tentativas == 0
            and e.etapa_atual == 1 and e.troca == TROCA_NENHUMA
        )

    def _solicitar(self, tecla: str, texto: str, exige_confirmacao: bool) -> None:
        if not exige_confirmacao and not self._tem_progresso():
            self._executar(tecla)
            return
        self.estado.acao_pendente = tecla
        self.definir_feedback("aviso", texto)

    def _executar(self, tecla: str) -> None:
        self.estado.acao_pendente = None
        if tecla.isdigit():
            self.trocar_fase(int(tecla))
        elif tecla == "m":
            self.estado.exploracao = False
            self.estado.questao_atual = 0
            self._zerar_questao()
            self._anunciar_menu()
        elif tecla == "s":
            self._avancar(pulou=True)

    def solicitar_fase(self, fase: int) -> None:
        if fase in FASES:
            self._solicitar(str(fase), msg.CONFIRMAR_FASE.format(fase=fase), False)

    def solicitar_menu(self) -> None:
        if not self.estado.menu:
            self._solicitar("m", msg.CONFIRMAR_MENU, False)

    def solicitar_pular(self) -> None:
        if not (self.estado.menu or self.estado.exploracao):
            self._solicitar("s", msg.CONFIRMAR_PULAR, True)

    def confirmar_acao(self) -> None:
        if self.estado.acao_pendente is not None:
            self._executar(self.estado.acao_pendente)

    def cancelar_acao_pendente(self) -> None:
        self.estado.acao_pendente = None
        self._voltar_do_aviso("Cancelado.")

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
        if leitura.base and leitura.tem_pecas_fora_base:
            self.definir_feedback("aviso", msg.PECAS_FORA_BASE)
            return
        if leitura.oscilando and leitura.ids:
            # Mão cobrindo marca etc.: não avalia (e não gasta tentativa). Se a leitura
            # nunca estabilizar, avalia depois de algumas recusas, ainda sem contar tentativa.
            estado.recusas_oscilacao += 1
            if estado.recusas_oscilacao <= LIMITE_RECUSAS_OSCILACAO:
                self.definir_feedback("aviso", msg.OSCILANDO_AGUARDE)
                return
        else:
            estado.recusas_oscilacao = 0

        resultado = avaliar(
            estado.questao,
            leitura,
            tentativa=estado.tentativas + 1,
            etapa_atual=estado.etapa_atual,
        )
        estado.ids_ultima_avaliacao = tuple(sorted(leitura.ids))

        if resultado.tipo == "erro" and not leitura.oscilando:
            estado.tentativas += 1

        if resultado.tipo == "ok" and estado.questao.duas_etapas and estado.etapa_atual == 1:
            self._iniciar_troca()
            return

        estado.resolvida = resultado.tipo == "ok"
        self.definir_feedback(
            resultado.tipo,
            resultado.texto,
            repetir_enunciado=resultado.repetir_enunciado and not leitura.oscilando,
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
            if leitura.ids or leitura.tem_pecas_fora_base:
                self.definir_feedback("aviso", msg.RETIRAR_BASE_ERRO, bipe_tipo="instrutor")
                return
            if leitura.detecta_base and leitura.base:
                self.definir_feedback("aviso", msg.RETIRAR_BASE_VISIVEL, bipe_tipo="instrutor")
                return
            estado.troca = TROCA_POSICIONAR
            self.definir_feedback("instrutor", msg.POSICIONAR_PECA_BASE)
            return
        if leitura.detecta_base and not leitura.base:  # TROCA_POSICIONAR
            self.definir_feedback("aviso", msg.BASE_NAO_VISTA, bipe_tipo="instrutor")
            return
        estado.troca = TROCA_NENHUMA
        estado.etapa_atual = 2
        self.anunciar_questao(abertura="Etapa 2 de 2.")

    def _avancar(self, pulou: bool = False) -> None:
        estado = self.estado
        if estado.questao_atual + 1 < len(estado.fase_atual.questoes):
            estado.questao_atual += 1
            self._zerar_questao()
            self.anunciar_questao(abertura="Atividade pulada." if pulou else "")
        elif estado.fase + 1 in FASES:
            extra = "Atividade pulada. Avançando para" if pulou else "Fase concluída! Avançando para"
            self.trocar_fase(estado.fase + 1, abertura_extra=extra)
        elif pulou:
            self.definir_feedback("info", msg.ULTIMA_ATIVIDADE)
        else:
            self.definir_feedback(
                "parabens",
                "Parabéns! Você concluiu todas as fases! M volta ao menu; 1 recomeça.",
            )
