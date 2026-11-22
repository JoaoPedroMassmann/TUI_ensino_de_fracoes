"""Textos falados e mostrados ao aluno e funções que escrevem números e peças por extenso.

Orçamento de texto (verificado em tests/test_orcamento_texto.py): frases curtas, uma ideia por
mensagem, verbo primeiro. Mensagens de feedback até ~120 caracteres; ajudas, que só falam sob
demanda (tecla H), até 300.
"""

from __future__ import annotations

from collections import Counter

from .config import ID_VALUES_MAP

# Frases fixas

BOAS_VINDAS = (
    "Bem-vindo ao sistema de frações. "
    "Instrutor: centralize a peça base e entregue as peças ao estudante. "
    "H ouve os comandos."
)

MENU_OPCOES = (
    "Espaço começa pela fase 1. Números de {minimo} a {maximo} escolhem a fase. "
    "C calibra a base."
)

# Comandos por modo. A mesma lista alimenta a ajuda falada e o painel de comandos na tela (H).
# Cada comando: (rótulo na tela, como é falado, o que faz). Cada modo: (introdução, comandos, final).
_COMUNS = (
    ("ESC", "Escape", "silencia a fala"),
    ("Q", "Q", "sai"),
    ("H", "H", "fecha esta lista"),
)
_FASES = ("Números {min}-{max}", "Números de {min} a {max}", "escolhem a fase")
_COMANDOS = {
    "menu": ("", (
        ("ESPAÇO", "Espaço", "começa pela fase 1"),
        _FASES,
        ("C", "C", "calibra a base"),
        ("E", "E", "liga o modo Exploração"),
        ("P", "P", "repete o menu"),
    ), "Tecla sem bipe? Clique na janela."),
    "atividade": ("", (
        ("ESPAÇO", "Espaço", "verifica ou avança"),
        ("P", "P", "repete a pergunta"),
        ("R", "R", "refaz a atividade"),
        ("S", "S", "pula a atividade"),
        ("M", "M", "volta ao menu"),
        ("E", "E", "liga o modo Exploração"),
        ("C", "C", "calibra a base"),
        _FASES,
    ), ""),
    "troca": ("Instrutor: siga a instrução.", (
        ("ESPAÇO", "Espaço", "continua"),
        ("P", "P", "repete a instrução"),
        ("R", "R", "refaz a atividade"),
        ("C", "C", "calibra a base"),
    ), ""),
    "exploracao": ("", (
        ("ESPAÇO", "Espaço", "lê as peças"),
        ("E", "E", "volta à atividade"),
        ("M", "M", "volta ao menu"),
        ("C", "C", "calibra a base"),
        _FASES,
    ), ""),
    "calibracao": ("Base sozinha, sem peças numéricas, sobre fundo claro.", (
        ("ESPAÇO", "Espaço", "calibra"),
        ("N", "N", "pula ou cancela"),
        ("P", "P", "repete as instruções"),
    ), ""),
}


def _comandos(modo: str, minimo: int, maximo: int):
    intro, entradas, final = _COMANDOS[modo]
    lista = [
        tuple(t.format(min=minimo, max=maximo) for t in entrada)
        for entrada in (*entradas, *_COMUNS)
    ]
    return intro, lista, final


def ajuda_falada(modo: str, minimo: int, maximo: int) -> str:
    intro, lista, final = _comandos(modo, minimo, maximo)
    return " ".join(p for p in (intro, *(f"{falado} {desc}." for _, falado, desc in lista), final) if p)


def comandos_tela(modo: str, minimo: int, maximo: int) -> list[str]:
    _, lista, _ = _comandos(modo, minimo, maximo)
    return [f"[{rotulo}]  {desc}" for rotulo, _, desc in lista]


# Confirmações de ações que perdem progresso
CONFIRMAR_FASE = "Mudar para a fase {fase}? Perde o progresso. Aperte {fase} de novo. Outra tecla cancela."
CONFIRMAR_MENU = "Voltar ao menu? Perde o progresso. Aperte M de novo. Outra tecla cancela."
CONFIRMAR_PULAR = "Pular a atividade? Aperte S de novo. Outra tecla cancela."
CONFIRMAR_SAIDA = "Sair do programa? Aperte Q de novo. Outra tecla cancela."
ULTIMA_ATIVIDADE = "Esta é a última atividade. M volta ao menu; Q sai."

# Câmera
CAMERA_DESCONECTADA = "Instrutor: câmera desconectada. Verifique o cabo; o sistema tenta reconectar."
CAMERA_RECONECTADA = "Câmera reconectada."
CAMERA_AVISO_TELA = "Câmera desconectada. Verifique o cabo; reconectando."

# Peça base
SEM_BASE = "Não vejo a peça base. Coloque-a no centro da câmera e aperte espaço."
RETIRAR_BASE_VISIVEL = "Instrutor: a peça base ainda está à vista. Retire-a e aperte espaço."
BASE_NAO_VISTA = "Instrutor: não vejo a peça base. Centralize-a e aperte espaço."

# Calibração
CALIBRACAO_INICIO = (
    "Calibração da peça base. Instrutor: coloque a peça base sozinha, sem peças numéricas, "
    "no centro da câmera, sobre fundo claro, e aperte espaço. N pula."
)
CALIBRACAO_TELA = "O contorno amarelo mostra a peça base candidata."
CALIBRACAO_OK = "Calibrado. Detecção da base ativa."
CALIBRACAO_CANCELADA_ATIVA = "Calibração cancelada. Detecção da base ativa."
CALIBRACAO_CANCELADA_DESLIGADA = "Calibração cancelada. Detecção da base desligada."
CALIBRACAO_FALHAS = {
    "pecas": "Há peças numéricas à vista. Retire-as e aperte espaço.",
    "sem_base": "Não vejo a peça base. Centralize-a, com boa luz, e aperte espaço.",
    "instavel": "A base está instável. Deixe-a parada e aperte espaço.",
    "fundo_escuro": "Fundo escuro demais. Use uma superfície clara e aperte espaço.",
}

RETIRAR_PECA_BASE = "Instrutor: tire a peça base da frente da câmera e aperte espaço."
RETIRAR_BASE_ERRO = "Instrutor: ainda há peças à vista. Tire todas da mesa e aperte espaço."
POSICIONAR_PECA_BASE = "Instrutor: coloque a segunda peça base no centro da câmera e aperte espaço."

# Peças numéricas
SEM_PECAS = "Não vejo peças numéricas na peça base. Encaixe-as e aperte espaço."
OSCILANDO_AGUARDE = "Leitura oscilando. Deixe as peças paradas, sem cobrir as marcas, e aperte espaço."
NOTA_OSCILANDO = "Leitura oscilando: deixe as peças paradas, sem cobrir as marcas."
OK_PECAS = "Correto! Você montou {total}. Espaço para continuar."
OK_SOMA = OK_PECAS
PECAS_FORA_BASE = "Instrutor: há peças fora da peça base. Retire-as."

# Resultados de avaliação
LEITURA = "A câmera viu {pecas}: {total}."
LEITURA_EQUIVALENTE = "{pecas_cap} {valem} o mesmo, mas a atividade pede {pedidas}."
PEDE_SOMA = "A atividade pede {esperado}."
PEDE_PECAS = "A atividade pede peças específicas: {esperado}."


# Mensagens de ajuda e aviso
LEMBRAR_ENUNCIADO = "P repete a pergunta."
LEITURA_MUDOU = "Leitura mudou. Espaço para verificar."

# Modo Exploração
EXPLORACAO_INICIO = (
    "Modo Exploração. Encaixe peças na base e aperte espaço para ouvir a leitura. "
    "E volta à atividade."
)
EXPLORACAO_SAIDA = "Saindo do modo Exploração."
EXPLORACAO_VAZIA = "Não vejo peças numéricas na peça base."
EXPLORACAO_UMA_PECA = "A câmera viu {pecas}."
EXPLORACAO_UMA_PECA_VALE = "A câmera viu {pecas}, que equivale a {total}."
EXPLORACAO_INTEIRO = "Isso forma um inteiro."
EXPLORACAO_MAIS_QUE_INTEIRO = "Isso passa de um inteiro."
EXPLORACAO_IGUAL = "Isso equivale a {fracao}."

# Números e peças por extenso
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

# Valor em oitavos -> (singular, plural)
_NOMES_PECAS = {1: ("oitavo", "oitavos"), 2: ("quarto", "quartos"), 4: ("meio", "meios")}

# Denominador -> (singular, plural), para frações simplificadas como 1/2 e 3/4
_DENOMINADORES = {
    1: ("inteiro", "inteiros"),
    2: ("meio", "meios"),
    4: ("quarto", "quartos"),
    8: ("oitavo", "oitavos"),
}


def por_extenso(n: int) -> str:
    return _NUMEROS[n] if 0 <= n < len(_NUMEROS) else str(n)


def oitavos(n: int) -> str:
    return f"{por_extenso(n)} oitavo" if n == 1 else f"{por_extenso(n)} oitavos"


def fracao_falada(numerador: int, denominador: int) -> str:
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
