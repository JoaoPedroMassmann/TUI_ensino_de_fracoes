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

    @property
    def total(self) -> int:
        return total_oitavos(self.ids)


class Resultado(NamedTuple):
    tipo: str  # chave de TIPOS_FEEDBACK: "ok", "erro", "aviso", ...
    texto: str
    repetir_enunciado: bool


@dataclass(frozen=True)
class Diagnostico:
    """Resumo objetivo da diferença entre a mesa e a questão."""

    situacao: str  # "ok" | "valor_certo_pecas_erradas" | "valor_errado"
    total: int
    esperado: int
    diferenca: int  # esperado - total (positivo: falta; negativo: passou)
    faltam: tuple[int, ...]  # IDs das peças a acrescentar
    sobram: tuple[int, ...]  # IDs das peças a retirar
    por_pecas: bool  # a questão pede peças específicas


def total_oitavos(ids: list[int]) -> int:
    """Soma, em oitavos, o valor das peças identificadas pelos IDs das tags."""
    return sum(ID_VALUES_MAP[i] for i in ids)


def simplificar_fracao(numerador: int, denominador: int = TOTAL_OITAVOS) -> tuple[int, int]:
    if numerador == 0:
        return 0, 1
    divisor = math.gcd(numerador, denominador)
    return numerador // divisor, denominador // divisor


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
        return Diagnostico(situacao, total, esperado, esperado - total, faltam, sobram, True)

    esperado = questao.soma_alvo
    diferenca = esperado - total
    if diferenca == 0:
        return Diagnostico("ok", total, esperado, 0, (), (), False)
    faltam, sobram = sugerir_ajuste(ids, diferenca)
    return Diagnostico("valor_errado", total, esperado, diferenca, faltam, sobram, False)


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
    """Mensagem de erro que fica mais detalhada a cada tentativa (1 = só o resultado)."""
    pecas, total = msg.listar_pecas(ids), msg.oitavos(diag.total)
    partes: list[str] = []

    if diag.situacao == "valor_certo_pecas_erradas":
        partes.append(msg.LEITURA_VALOR_CERTO.format(pecas=pecas, total=total))
        if tentativa >= 2:
            sobra = msg.concordar(diag.sobram, "Sobra", "Sobram")
            falta = msg.concordar(diag.faltam, "Falta", "Faltam")
            partes.append(f"{sobra} {msg.listar_pecas(diag.sobram)}.")
            partes.append(f"{falta} {msg.listar_pecas(diag.faltam)}.")
        if tentativa >= 3:
            partes.append(_acao(diag))
            vale = msg.concordar(diag.sobram, "vale", "valem")
            partes.append(
                f"{msg.maiuscula(msg.listar_pecas(diag.sobram))} {vale} o mesmo que "
                f"{msg.listar_pecas(diag.faltam)}."
            )
    else:
        if abs(diag.diferenca) == 1:
            partes.append("Quase!")
        partes.append(msg.LEITURA.format(pecas=pecas, total=total))
        pedido = msg.PEDE_PECAS if diag.por_pecas else msg.PEDE_SOMA
        partes.append(pedido.format(esperado=msg.oitavos(diag.esperado)))
        if tentativa >= 2:
            partes.append(_direcao(diag.diferenca))
        if tentativa >= 3:
            partes.append(_acao(diag))

    if tentativa >= 3:
        partes.append(msg.LEMBRAR_ENUNCIADO)
    return " ".join(p for p in partes if p)


def _com_nota(texto: str, leitura: Leitura) -> str:
    return f"{texto} {msg.NOTA_OSCILANDO}" if leitura.oscilando else texto


def avaliar(questao: Questao, leitura: Leitura, tentativa: int = 1, etapa_atual: int = 1) -> Resultado:
    """Avalia a montagem atual. `tentativa` é o número desta tentativa (1, 2, 3...)."""
    if not leitura.ids:
        return Resultado("aviso", _com_nota(msg.SEM_PECAS, leitura), True)

    diag = diagnosticar(questao, leitura.ids, etapa_atual=etapa_atual)
    total = msg.oitavos(diag.total)
    if diag.situacao == "ok":
        modelo = msg.OK_PECAS if diag.por_pecas else msg.OK_SOMA
        return Resultado("ok", modelo.format(total=total), False)

    texto = _texto_erro(diag, leitura.ids, tentativa)
    # O enunciado é repetido na segunda tentativa errada; depois disso o aluno usa a tecla P
    return Resultado("erro", _com_nota(texto, leitura), tentativa == 2)

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
