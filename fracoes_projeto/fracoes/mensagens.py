"""Textos falados e mostrados ao aluno e funções que escrevem números e peças por extenso."""

from __future__ import annotations

from collections import Counter

from .config import ID_VALUES_MAP

# Frases fixas

BOAS_VINDAS = (
    "Bem-vindo ao sistema de frações. "
    "Instrutor: posicione a peça base no centro da área da câmera e entregue as peças à criança. "
    "Aluno: encaixe as peças numéricas na peça base, mantenha as mãos longe das marcas e "
    "aperte espaço para verificar. "
    "Aperte H a qualquer momento para ouvir todos os comandos."
)

MENU_OPCOES = (
    "Aperte espaço para começar pela fase 1, ou aperte um número de {minimo} a {maximo} "
    "para escolher a fase."
)

AJUDA_TECLAS = (
    "Comandos: espaço verifica a montagem ou avança. P repete a pergunta. R refaz a atividade. "
    "E liga ou desliga o modo Exploração. "
    "Números de {minimo} a {maximo} escolhem a fase. Q sai. H repete estes comandos."
)

# Câmera
CAMERA_DESCONECTADA = (
    "Aviso ao instrutor: a câmera foi desconectada. Verifique o cabo. "
    "O sistema tenta reconectar sozinho."
)
CAMERA_RECONECTADA = "Câmera reconectada. Pode continuar."
CAMERA_AVISO_TELA = (
    "A câmera foi desconectada. Verifique o cabo enquanto o programa tenta reconectar sozinho."
)

# Peça base
SEM_BASE = (
    "A câmera não identificou a peça base. "
    "Coloque a peça base no centro da área da câmera e aperte espaço de novo."
)
RETIRAR_BASE_VISIVEL = (
    "Aviso ao instrutor: a peça base ainda está na visão da câmera. "
    "Retire-a e aperte espaço de novo."
)
BASE_NAO_VISTA = (
    "Aviso ao instrutor: a câmera não identificou a peça base. "
    "Posicione-a no centro da área da câmera e aperte espaço de novo."
)

# Calibração
CALIBRACAO_INICIO = (
    "Calibração da peça base. Instrutor: coloque a peça base sozinha, sem nenhuma peça numérica, "
    "no centro da área da câmera, sobre um fundo claro, e aperte espaço. "
    "Para continuar sem detectar a base, aperte N."
)
CALIBRACAO_OK = "Calibração concluída."
CALIBRACAO_PULADA = "Calibração ignorada. A peça base não será detectada nesta sessão."
CALIBRACAO_FALHAS = {
    "pecas": "Há peças numéricas na visão da câmera. Retire todas e aperte espaço de novo.",
    "sem_base": "A câmera não identificou a peça base. Coloque-a no centro, bem iluminada, "
    "e aperte espaço de novo.",
    "instavel": "A imagem da peça base está instável. Deixe-a parada e aperte espaço de novo.",
    "fundo_escuro": "O fundo parece escuro demais. Use uma superfície clara e aperte espaço de novo.",
}

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

# Peças numéricas
SEM_PECAS = (
    "A câmera não identificou nenhuma peça numérica na peça base. "
    "Coloque as peças na frente da câmera e aperte espaço de novo."
)
NOTA_OSCILANDO = (
    "A leitura está oscilando. Deixe as peças paradas sobre a mesa, sem cobrir as marcas com a mão."
)
OK_PECAS = "Correto! Você montou {total} com as peças numéricas pedidas. Aperte espaço para continuar."
OK_SOMA = "Correto! Você montou {total}. Aperte espaço para continuar."
PECAS_FORA_BASE = "Aviso ao instrutor: existem peças fora da peça base. Remova-as antes de prosseguir."

# Resultados de avaliação
LEITURA = "A câmera identificou {pecas}, que somam {total}."
LEITURA_EQUIVALENTE = (
    "{pecas_cap} {valem} o mesmo que {pedidas}, mas esta atividade pede {pedidas}."
)
PEDE_SOMA = "A atividade pede {esperado}."
PEDE_PECAS = "A atividade pede peças numéricas específicas que somam {esperado}."


# Mensagens de ajuda e aviso
LEMBRAR_ENUNCIADO = "Aperte P para ouvir a pergunta de novo."
LEITURA_MUDOU = "A leitura mudou. Aperte espaço para verificar."
CONFIRMAR_SAIDA = (
    "Quer mesmo sair do programa? Aperte Q de novo para sair, ou qualquer outra tecla para continuar."
)

# Modo Exploração
EXPLORACAO_INICIO = (
    "Modo Exploração ativado. Encaixe peças na base, na frente da câmera, "
    "e aperte espaço para ouvir o que foi identificado, ou E para voltar à atividade."
)
EXPLORACAO_SAIDA = "Saindo do modo Exploração."
EXPLORACAO_VAZIA = "A câmera não identificou nenhuma peça numérica na peça base."
EXPLORACAO_UMA_PECA = "A câmera identificou {pecas}."
EXPLORACAO_UMA_PECA_VALE = "A câmera identificou {pecas}, que equivale a {total}."
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
