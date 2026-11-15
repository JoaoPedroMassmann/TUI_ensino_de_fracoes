"""Lógica de avaliação das respostas."""

from __future__ import annotations

import math
from typing import NamedTuple

from .atividades import Questao
from .config import ID_VALUES_MAP

TOTAL_OITAVOS = 8  # um inteiro

class Resultado(NamedTuple):
    tipo: str  # chave de TIPOS_FEEDBACK
    texto: str
    repetir_enunciado: bool


def oitavos(n: int) -> str:
    return f"{n} oitavo" if n == 1 else f"{n} oitavos"


def total_oitavos(ids: list[int]) -> int:
    """Soma, em oitavos, o valor das peças identificadas pelos IDs das tags."""
    return sum(ID_VALUES_MAP[i] for i in ids)


def simplificar_fracao(numerador: int, denominador: int = TOTAL_OITAVOS) -> tuple[int, int]:
    if numerador == 0:
        return 0, 1
    divisor = math.gcd(numerador, denominador)
    return numerador // divisor, denominador // divisor


def _dica(diferenca: int) -> str:
    return (
        f"Acrescente {oitavos(diferenca)}." if diferenca > 0 else f"Retire {oitavos(-diferenca)}."
    )


def avaliar(questao: Questao, ids_validos: list[int], total: int) -> Resultado:
    """Avalia a montagem atual contra a questão."""
    if not ids_validos:
        return Resultado(
            "aviso",
            "Não encontrei nenhuma peça. Coloque as peças à vista da câmera e aperte espaço de novo.",
            True,
        )

    if questao.ids_obrigatorios is not None:
        esperado_total = total_oitavos(list(questao.ids_obrigatorios))
        combinacao_exata = sorted(ids_validos) == sorted(questao.ids_obrigatorios)

        if combinacao_exata:
            return Resultado(
                "ok",
                f"Você montou {oitavos(total)} com as peças exatas. Aperte espaço para continuar.",
                False,
            )
        if total == esperado_total:
            return Resultado(
                "erro",
                f"O valor total está certo ({oitavos(total)}), "
                "mas as peças utilizadas não são as mesmas pedidas.",
                True,
            )
        return Resultado(
            "erro",
            f"Você montou {oitavos(total)}, mas a questão pede peças específicas que somem "
            f"{oitavos(esperado_total)}. {_dica(esperado_total - total)}",
            True,
        )

    esperado = questao.soma_alvo
    if total == esperado:
        return Resultado(
            "ok",
            f"Você montou {oitavos(total)} corretamente. Aperte espaço para continuar.",
            False,
        )
    return Resultado(
        "erro",
        f"Você montou {oitavos(total)}, mas o valor pedido é {oitavos(esperado)}. "
        f"{_dica(esperado - total)}",
        True,
    )


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
