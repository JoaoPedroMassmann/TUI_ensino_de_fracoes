"""Textos falados e mostrados ao aluno e funções que escrevem números e peças por extenso."""

from __future__ import annotations

from collections import Counter

from .config import ID_VALUES_MAP

# frases fixas
SEM_PECAS = (
    "Não encontrei nenhuma peça. Coloque as peças à vista da câmera e aperte espaço de novo."
)
NOTA_OSCILANDO = (
    "A leitura está oscilando. Segure as peças paradas, sem cobrir as marcas com a mão."
)
OK_PECAS = "Você montou {total} com as peças exatas. Aperte espaço para continuar."
OK_SOMA = "Você montou {total} corretamente. Aperte espaço para continuar."

LEITURA = "Vejo {pecas}: {total} no total."
LEITURA_VALOR_CERTO = (
    "Vejo {pecas}. O valor total está certo, {total}, mas as peças não são as pedidas."
)
PEDE_SOMA = "A questão pede {esperado}."
PEDE_PECAS = "A questão pede peças específicas que somam {esperado}."

LEMBRAR_ENUNCIADO = "Aperte P para ouvir a pergunta de novo."

RETIRAR_PECA_BASE = "Agora, com a ajuda do instrutor, retire a peça base atual da área da câmera e aperte espaço para continuar."
RETIRAR_BASE_ERRO = "Ainda há peças na visão da câmera. Retire todas as peças e aperte espaço de novo."
POSICIONAR_PECA_BASE = "Agora, com a ajuda do instrutor, posicione a outra peça base pedida na área da câmera e aperte espaço para continuar."

# números e peças por extenso
_NUMEROS = [
    "zero",
    "um",
    "dois",
    "três",
    "quatro",
    "cinco",
    "seis",
    "sete",
    "oito",
    "nove",
    "dez",
    "onze",
    "doze",
    "treze",
    "quatorze",
    "quinze",
    "dezesseis",
]

# valor em oitavos -> (singular, plural)
_NOMES_PECAS = {1: ("oitavo", "oitavos"), 2: ("quarto", "quartos"), 4: ("meio", "meios")}


def por_extenso(n: int) -> str:
    return _NUMEROS[n] if 0 <= n < len(_NUMEROS) else str(n)


def oitavos(n: int) -> str:
    return f"{por_extenso(n)} oitavo" if n == 1 else f"{por_extenso(n)} oitavos"


def juntar(itens: list[str]) -> str:
    """['a', 'b', 'c'] -> 'a, b e c'."""
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def listar_pecas(ids: tuple[int, ...] | list[int]) -> str:
    """Descreve as peças pelo nome: [30, 20, 20] -> 'um meio e dois quartos'."""
    contagem = Counter(ids)
    itens = []
    for tag_id in sorted(contagem, key=lambda i: ID_VALUES_MAP[i], reverse=True):
        n = contagem[tag_id]
        singular, plural = _NOMES_PECAS[ID_VALUES_MAP[tag_id]]
        itens.append(f"{por_extenso(n)} {singular if n == 1 else plural}")
    return juntar(itens)


def concordar(ids: tuple[int, ...], singular: str, plural: str) -> str:
    """Escolhe o verbo no singular ou no plural conforme o número de peças."""
    return singular if len(ids) == 1 else plural


def maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:]
