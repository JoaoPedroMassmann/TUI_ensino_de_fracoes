"""Lógica de avaliação das respostas."""

from __future__ import annotations

import itertools
import math
from collections import Counter
from dataclasses import dataclass
from typing import NamedTuple

from . import mensagens as msg
from .atividades import Questao
from .config import ID_VALUES_MAP, TAG_ID_MAP

TOTAL_OITAVOS = 8  # um inteiro
_LIMITE_BUSCA_AJUSTE = 12  # com mais peças que isso, não procuramos a sugestão de ajuste


class Leitura(NamedTuple):
    """O que a câmera vê no momento de verificar."""
    ids: list[int]  # tags conhecidas, já estabilizadas
    oscilando: bool = False  # a leitura vem mudando de quadro para quadro
    base: bool = True

    @property
    def total(self) -> int:
        return total_oitavos(self.ids)


class Resultado(NamedTuple):
    tipo: str  # chave de TIPOS_FEEDBACK: "ok", "erro", "aviso", ...
    texto: str
    repetir_enunciado: bool


@dataclass(frozen=True)
class Diagnostico:
    """Resumo objetivo da diferença entre a mesa e a atividade."""

    situacao: str  # "ok" | "valor_certo_pecas_erradas" | "valor_errado"
    total: int
    esperado: int
    diferenca: int  # esperado - total (positivo: falta; negativo: passou)
    faltam: tuple[int, ...]  # IDs das peças a acrescentar
    sobram: tuple[int, ...]  # IDs das peças a retirar
    por_pecas: bool  # a atividade pede peças específicas
    pedidas: tuple[int, ...] = ()  # IDs exatos pedidos quando por_pecas=True
    unidade_enunciado: str | None = None  # termo utilizado pelo enunciado (ex.: "metade de um inteiro")


def total_oitavos(ids: list[int]) -> int:
    """Soma, em oitavos, o valor das peças identificadas pelos IDs das tags."""
    return sum(ID_VALUES_MAP[i] for i in ids)


def simplificar_fracao(numerador: int, denominador: int = TOTAL_OITAVOS) -> tuple[int, int]:
    if numerador == 0:
        return 0, 1
    divisor = math.gcd(numerador, denominador)
    return numerador // divisor, denominador // divisor


def formatar_valor_contextual(oitavos_val: int, unidade_enunciado: str | None = None) -> str:
    """Descreve o valor na linguagem da atividade primeiro e em oitavos em seguida."""
    em_oitavos = msg.oitavos(oitavos_val)
    if unidade_enunciado and unidade_enunciado.lower() != em_oitavos.lower():
        return f"{unidade_enunciado} (que equivale a {em_oitavos})"
    return em_oitavos


def ids_para_valor(valor: int) -> tuple[int, ...]:
    """Peças (IDs) que somam `valor` oitavos, usando as maiores primeiro."""
    ids: list[int] = []
    for v in sorted(TAG_ID_MAP, reverse=True):
        while valor >= v:
            ids.append(TAG_ID_MAP[v])
            valor -= v
    return tuple(ids)


def sugerir_ajuste(ids: list[int], diferenca: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Sugere (faltam, sobram) para chegar ao valor pedido, mexendo no mínimo de peças."""
    if diferenca > 0:
        return ids_para_valor(diferenca), ()
    if diferenca == 0 or len(ids) > _LIMITE_BUSCA_AJUSTE:
        return (), ()
    excesso = -diferenca
    melhor: tuple[int, int, tuple[int, ...]] | None = None
    for r in range(1, len(ids) + 1):
        for combinacao in itertools.combinations(sorted(ids), r):
            soma = total_oitavos(list(combinacao))
            if soma < excesso:
                continue
            chave = (soma - excesso, r, combinacao)
            if melhor is None or chave < melhor:
                melhor = chave
    if melhor is None:
        return (), ()
    sobra_extra, _, retirar = melhor
    devolver = Counter(ids_para_valor(sobra_extra))
    retirar_c = Counter(retirar)
    return (
        tuple(sorted((devolver - retirar_c).elements())),
        tuple(sorted((retirar_c - devolver).elements())),
    )


def diagnosticar(questao: Questao, ids: list[int], etapa_atual: int = 1) -> Diagnostico:
    total = total_oitavos(ids)
    ids_obrigatorios = (
        questao.ids_obrigatorios_etapa_dois
        if etapa_atual == 2 and questao.ids_obrigatorios_etapa_dois is not None
        else questao.ids_obrigatorios
    )

    if ids_obrigatorios is not None:
        esperado = total_oitavos(list(ids_obrigatorios))
        na_mesa, pedidas = Counter(ids), Counter(ids_obrigatorios)
        faltam = tuple(sorted((pedidas - na_mesa).elements()))
        sobram = tuple(sorted((na_mesa - pedidas).elements()))
        if not faltam and not sobram:
            situacao = "ok"
        elif total == esperado:
            situacao = "valor_certo_pecas_erradas"
        else:
            situacao = "valor_errado"
        return Diagnostico(
            situacao=situacao,
            total=total,
            esperado=esperado,
            diferenca=esperado - total,
            faltam=faltam,
            sobram=sobram,
            por_pecas=True,
            pedidas=ids_obrigatorios,
            unidade_enunciado=questao.unidade_enunciado,
        )

    esperado = questao.soma_alvo
    diferenca = esperado - total
    if diferenca == 0:
        return Diagnostico(
            situacao="ok",
            total=total,
            esperado=esperado,
            diferenca=0,
            faltam=(),
            sobram=(),
            por_pecas=False,
            unidade_enunciado=questao.unidade_enunciado,
        )
    faltam, sobram = sugerir_ajuste(ids, diferenca)
    return Diagnostico(
        situacao="valor_errado",
        total=total,
        esperado=esperado,
        diferenca=diferenca,
        faltam=faltam,
        sobram=sobram,
        por_pecas=False,
        unidade_enunciado=questao.unidade_enunciado,
    )


def _direcao(diferenca: int) -> str:
    if diferenca > 0:
        return (
            f"Falta {msg.oitavos(diferenca)}."
            if diferenca == 1
            else f"Faltam {msg.oitavos(diferenca)}."
        )
    n = -diferenca
    return f"Passou {msg.oitavos(n)}." if n == 1 else f"Passaram {msg.oitavos(n)}."


def _acao(diag: Diagnostico) -> str:
    if diag.faltam and diag.sobram:
        return f"Troque {msg.listar_pecas(diag.sobram)} por {msg.listar_pecas(diag.faltam)}."
    if diag.faltam:
        return f"Acrescente {msg.listar_pecas(diag.faltam)}."
    if diag.sobram:
        return f"Retire {msg.listar_pecas(diag.sobram)}."
    return ""


def _texto_erro(diag: Diagnostico, ids: list[int], tentativa: int) -> str:
    """Mensagem de erro que fica mais detalhada a cada tentativa."""
    pecas, total = msg.listar_pecas(ids), msg.oitavos(diag.total)
    partes: list[str] = []

    if diag.situacao == "valor_certo_pecas_erradas":
        pedidas_txt = msg.listar_pecas(diag.pedidas)
        partes.append(
            msg.LEITURA_EQUIVALENTE.format(
                pecas_cap=msg.maiuscula(pecas),
                valem=msg.concordar(ids, "vale", "valem"),
                pedidas=pedidas_txt,
            )
        )
        if tentativa >= 2:
            sobra = msg.concordar(diag.sobram, "Sobra", "Sobram")
            falta = msg.concordar(diag.faltam, "Falta", "Faltam")
            partes.append(f"{sobra} {msg.listar_pecas(diag.sobram)}.")
            partes.append(f"{falta} {msg.listar_pecas(diag.faltam)}.")
        if tentativa >= 3:
            partes.append(_acao(diag))
    else:
        if abs(diag.diferenca) == 1:
            partes.append("Quase!")
        partes.append(msg.LEITURA.format(pecas=pecas, total=total))
        alvo_txt = formatar_valor_contextual(diag.esperado, diag.unidade_enunciado)
        pedido = msg.PEDE_PECAS if diag.por_pecas else msg.PEDE_SOMA
        partes.append(pedido.format(esperado=alvo_txt))
        if tentativa >= 2:
            partes.append(_direcao(diag.diferenca))
        if tentativa >= 3:
            partes.append(_acao(diag))

    if tentativa >= 3:
        partes.append(msg.LEMBRAR_ENUNCIADO)
    return " ".join(p for p in partes if p)


def _com_nota(texto: str, leitura: Leitura) -> str:
    return f"{msg.NOTA_OSCILANDO} {texto}" if leitura.oscilando else texto


def avaliar(
    questao: Questao, leitura: Leitura, tentativa: int = 1, etapa_atual: int = 1
) -> Resultado:
    """Avalia a montagem atual. `tentativa` é o número desta tentativa (1, 2, 3...)."""
    if not leitura.base:
        return Resultado("aviso", _com_nota(msg.SEM_BASE, leitura), True)
    if not leitura.ids:
        return Resultado("aviso", _com_nota(msg.SEM_PECAS, leitura), True)

    diag = diagnosticar(questao, leitura.ids, etapa_atual=etapa_atual)
    alvo_txt = formatar_valor_contextual(diag.esperado, diag.unidade_enunciado)
    if diag.situacao == "ok":
        modelo = msg.OK_PECAS if diag.por_pecas else msg.OK_SOMA
        return Resultado("ok", modelo.format(total=alvo_txt), False)

    texto = _texto_erro(diag, leitura.ids, tentativa)
    # O enunciado é repetido na segunda tentativa errada; depois disso o aluno usa a tecla P
    return Resultado("erro", _com_nota(texto, leitura), tentativa == 2)


def descrever_leitura(leitura: Leitura) -> str:
    """Texto falado do Modo Exploração."""
    if not leitura.ids:
        return _com_nota(msg.EXPLORACAO_VAZIA, leitura)
    total = leitura.total
    pecas = msg.listar_pecas(leitura.ids)
    if len(leitura.ids) == 1:
        modelo = msg.EXPLORACAO_UMA_PECA if total == 1 else msg.EXPLORACAO_UMA_PECA_VALE
        return _com_nota(modelo.format(pecas=pecas, total=msg.oitavos(total)), leitura)
    partes = [msg.LEITURA.format(pecas=pecas, total=msg.oitavos(total))]
    if total == TOTAL_OITAVOS:
        partes.append(msg.EXPLORACAO_INTEIRO)
    elif total > TOTAL_OITAVOS:
        partes.append(msg.EXPLORACAO_MAIS_QUE_INTEIRO)
    else:
        n, d = simplificar_fracao(total)
        if d != TOTAL_OITAVOS:
            partes.append(msg.EXPLORACAO_IGUAL.format(fracao=msg.fracao_falada(n, d)))
    return _com_nota(" ".join(partes), leitura)


def texto_leitura(ids_validos: list[int], total: int) -> str:
    """Texto que descreve, na tela, as peças que a câmera está vendo."""
    if not ids_validos:
        return "Peças vistas pela câmera: nenhuma"
    partes = " + ".join(f"{ID_VALUES_MAP[i]}/8" for i in sorted(ids_validos))
    texto = f"Peças vistas: {partes} = {total}/8"
    if total > TOTAL_OITAVOS:
        texto += " (mais que 1 inteiro)"
    elif total == TOTAL_OITAVOS:
        texto += " (1 inteiro)"
    else:
        n, d = simplificar_fracao(total)
        if d != TOTAL_OITAVOS:
            texto += f" (igual a {n}/{d})"
    return texto
