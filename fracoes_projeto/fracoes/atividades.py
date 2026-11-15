"""Fases e questões do sistema"""

from __future__ import annotations

from dataclasses import dataclass

from .config import TAG_ID_MAP

OITAVO = TAG_ID_MAP[1]  # 1/8
QUARTO = TAG_ID_MAP[2]  # 1/4 equivale a (2/8)
MEIO = TAG_ID_MAP[4]  # 1/2 equivale a (4/8)


@dataclass(frozen=True)
class Questao:
    """Uma questão. Use exatamente um dos dois critérios de resposta:

    ids_obrigatorios: peças exatas que devem estar na mesa (IDs das tags);
    soma_alvo: total em oitavos, com quaisquer peças.
    """
    enunciado: str
    ids_obrigatorios: tuple[int, ...] | None = None
    soma_alvo: int | None = None

    def __post_init__(self) -> None:
        if (self.ids_obrigatorios is None) == (self.soma_alvo is None):
            raise ValueError("Informe ids_obrigatorios OU soma_alvo (apenas um).")


@dataclass(frozen=True)
class Fase:
    titulo: str
    questoes: tuple[Questao, ...]


FASES: dict[int, Fase] = {
    1: Fase(
        "Fase 1: Frações Unitárias Usuais",
        (
            Questao(
                "Monte a fração unitária 1 oitavo", 
                ids_obrigatorios=(OITAVO,),
            ),
            Questao(
                "Uma pizza foi dividida em 8 partes. Monte a fração que corresponde a um pedaço dessa pizza",
                ids_obrigatorios=(OITAVO,),
            ),
            Questao(
                "Posicione a peça unitária 1 quarto", 
                ids_obrigatorios=(QUARTO,),
            ),
            Questao(
                "Posicione a peça unitária 1 meio", 
                ids_obrigatorios=(MEIO,),
            ),
        ),
    ),
    2: Fase(
        "Fase 2: Representação de Números como Frações",
        (
            Questao(
                "Monte 4 oitavos, que representa metade de um inteiro", 
                soma_alvo=4,
            ),
            Questao(
                "Uma receita pede metade de uma xícara. Monte 4 oitavos com quaisquer peças",
                soma_alvo=4,
            ),
            Questao(
                "Você comprou uma pizza inteira dividida em 8 partes. Monte o inteiro completo",
                soma_alvo=8,
            ),
        ),
    ),
    3: Fase(
        "Fase 3: Frações Equivalentes",
        (
            Questao(
                "Monte uma fração equivalente a 1 quarto usando oitavos",
                ids_obrigatorios=(OITAVO, OITAVO),
            ),
            Questao(
                "Dividindo um lanche: 2 pedaços de 1 oitavo equivalem a 1 quarto",
                ids_obrigatorios=(OITAVO, OITAVO),
            ),
            Questao(
                "Para repartir igualmente, 4 pedaços de 1 oitavo formam a metade de uma torta",
                ids_obrigatorios=(OITAVO,) * 4,
            ),
        ),
    ),
    4: Fase(
        "Fase 4: Relação Parte / Todo",
        (
            Questao(
                "Monte 3 oitavos, 3 partes de um total de 8",
                soma_alvo=3,
            ),
            Questao(
                "De uma caixa com 8 ovos para um bolo, você usou 3. Monte 3 oitavos",
                soma_alvo=3,
            ),
            Questao(
                "De uma cartela com 8 adesivos, você colou 5. Monte 5 oitavos",
                soma_alvo=5,
            ),
            Questao(
                "De uma barra de cereal com 8 quadradinhos, você comeu 2. Monte a fração que sobrou",
                soma_alvo=6,
            ),
        ),
    ),
}
