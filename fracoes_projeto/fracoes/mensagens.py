"""Textos falados e mostrados ao aluno e funções que escrevem números e peças por extenso."""

from __future__ import annotations

from collections import Counter

from .config import ID_VALUES_MAP

# frases fixas
SEM_PECAS = (
    "A câmera não identificou nenhuma peça numérica na peça base. "
    "Coloque as peças na frente da câmera e aperte espaço de novo."
)
NOTA_OSCILANDO = (
    "A leitura está oscilando. Deixe as peças paradas sobre a mesa, sem cobrir as marcas com a mão."
)
OK_PECAS = "Correto! Você montou {total} com as peças numéricas pedidas. Aperte espaço para continuar."
OK_SOMA = "Correto! Você montou {total}. Aperte espaço para continuar."

LEITURA = "A câmera identificou {pecas}, que somam {total}."
LEITURA_EQUIVALENTE = (
    "{pecas_cap} {valem} o mesmo que {pedidas}, mas esta atividade pede {pedidas}."
)
PEDE_SOMA = "A atividade pede {esperado}."
PEDE_PECAS = "A atividade pede peças numéricas específicas que somam {esperado}."

LEMBRAR_ENUNCIADO = "Aperte P para ouvir a pergunta de novo."
LEITURA_MUDOU = "A leitura mudou. Aperte espaço para verificar."
CONFIRMAR_SAIDA = (
    "Quer mesmo sair do programa? Aperte Q de novo para sair, ou qualquer outra tecla para continuar."
)

# modo exploração
EXPLORACAO_INICIO = (
    "Modo exploração ativado. Coloque peças numéricas sobre a mesa, na frente da câmera, "
    "e aperte espaço para ouvir o que foi identificado, ou E para voltar à atividade."
)
EXPLORACAO_SAIDA = "Saindo do modo exploração."
EXPLORACAO_VAZIA = "A câmera não identificou nenhuma peça numérica na peça base."
EXPLORACAO_UMA_PECA = "A câmera identificou {pecas}."
EXPLORACAO_UMA_PECA_VALE = "A câmera identificou {pecas}, que equivale a {total}."
EXPLORACAO_INTEIRO = "Isso forma um inteiro."
EXPLORACAO_MAIS_QUE_INTEIRO = "Isso passa de um inteiro."
EXPLORACAO_IGUAL = "Isso equivale a {fracao}."

RETIRAR_PECA_BASE = (
    "Aviso ao instrutor: tire a peça base atual de cima da mesa, "
    "longe da câmera, e aperte espaço para continuar."
)
RETIRAR_BASE_ERRO = (
    "Aviso ao instrutor: ainda há peças na visão da câmera. "
    "Retire todas as peças de cima da mesa e aperte espaço de novo."
)
POSICIONAR_PECA_BASE = (
    "Aviso ao instrutor: posicione a segunda peça base no centro da mesa, "
    "na frente da câmera, e aperte espaço para continuar."
)

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

# denominador -> (singular, plural), para frações simplificadas como 1/2 e 3/4
_DENOMINADORES = {1: ("inteiro", "inteiros"), 2: ("meio", "meios"), 4: ("quarto", "quartos"), 8: ("oitavo", "oitavos")}


def por_extenso(n: int) -> str:
    return _NUMEROS[n] if 0 <= n < len(_NUMEROS) else str(n)


def oitavos(n: int) -> str:
    return f"{por_extenso(n)} oitavo" if n == 1 else f"{por_extenso(n)} oitavos"


def fracao_falada(numerador: int, denominador: int) -> str:
    if denominador == 1:
        singular, plural = _DENOMINADORES[1]
        return f"{por_extenso(numerador)} {singular if numerador == 1 else plural}"
    singular, plural = _DENOMINADORES.get(denominador, (f"/{denominador}", f"/{denominador}"))
    return f"{por_extenso(numerador)} {singular if numerador == 1 else plural}"


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


def concordar(ids: tuple[int, ...] | list[int], singular: str, plural: str) -> str:
    """Escolhe o verbo no singular ou no plural conforme o número de peças."""
    return singular if len(ids) == 1 else plural


def maiuscula(texto: str) -> str:
    return texto[:1].upper() + texto[1:] if texto else texto
