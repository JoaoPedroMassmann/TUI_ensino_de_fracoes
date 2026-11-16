"""Fases e atividades do sistema."""

from __future__ import annotations

from dataclasses import dataclass

from .config import TAG_ID_MAP

OITAVO = TAG_ID_MAP[1]  # 1/8
QUARTO = TAG_ID_MAP[2]  # 1/4 equivale a (2/8)
MEIO = TAG_ID_MAP[4]  # 1/2 equivale a (4/8)


@dataclass(frozen=True)
class Questao:
    """Uma atividade. Use exatamente um dos dois critérios de resposta:

    ids_obrigatorios: peças numéricas exatas na peça base (IDs das tags);
    soma_alvo: total em oitavos, com quaisquer peças numéricas;
    unidade_enunciado: como a atividade nomeia o alvo (ex.: "um meio", "um inteiro");
    duas_etapas: se True, o usuário constrói duas frações equivalentes em duas peças base diferentes;
    segundo_enunciado: enunciado da Base 2, se houver;
    ids_obrigatorios_etapa_dois: peças numéricas exatas na peça base 2 (IDs das tags).
    """

    enunciado: str
    ids_obrigatorios: tuple[int, ...] | None = None
    soma_alvo: int | None = None
    unidade_enunciado: str | None = None
    duas_etapas: bool = False
    segundo_enunciado: str | None = None
    ids_obrigatorios_etapa_dois: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if (self.ids_obrigatorios is None) == (self.soma_alvo is None):
            raise ValueError("Informe ids_obrigatorios OU soma_alvo (apenas um).")
        if self.duas_etapas:
            if self.ids_obrigatorios is None or self.ids_obrigatorios_etapa_dois is None:
                raise ValueError(
                    "Atividades com duas_etapas exigem ids_obrigatorios e ids_obrigatorios_etapa_dois."
                )
        elif self.ids_obrigatorios_etapa_dois is not None:
            raise ValueError("ids_obrigatorios_etapa_dois só deve ser usado com duas_etapas=True.")


@dataclass(frozen=True)
class Fase:
    titulo: str
    questoes: tuple[Questao, ...]


FASES: dict[int, Fase] = {
    1: Fase(
        "Fase 1: Frações Unitárias Usuais",
        (
            Questao(
                "Encaixe a peça numérica de um oitavo na peça base, para formar a fração de um oitavo.",
                ids_obrigatorios=(OITAVO,),
                unidade_enunciado="um oitavo",
            ),
            Questao(
                "Encaixe a peça numérica de um quarto na peça base, para formar a fração de um quarto.",
                ids_obrigatorios=(QUARTO,),
                unidade_enunciado="um quarto",
            ),
            Questao(
                "Encaixe a peça numérica de um meio na peça base, para formar a fração de um meio.",
                ids_obrigatorios=(MEIO,),
                unidade_enunciado="um meio",
            ),
        ),
    ),
    2: Fase(
        "Fase 2: Formação do Inteiro com Peças Iguais",
        (
            Questao(
                "Encaixe peças numéricas de um oitavo na peça base até formar um inteiro.",
                ids_obrigatorios=(OITAVO,) * 8,
                unidade_enunciado="um inteiro",
            ),
            Questao(
                "Encaixe peças numéricas de um quarto na peça base até formar um inteiro.",
                ids_obrigatorios=(QUARTO,) * 4,
                unidade_enunciado="um inteiro",
            ),
            Questao(
                "Encaixe peças numéricas de um meio na peça base até formar um inteiro.",
                ids_obrigatorios=(MEIO,) * 2,
                unidade_enunciado="um inteiro",
            ),
        ),
    ),
    3: Fase(
        "Fase 3: Representação de Números como Frações",
        (
            Questao(
                "Monte quatro oitavos, o que representa metade de um inteiro.",
                soma_alvo=4,
                unidade_enunciado="metade de um inteiro",
            ),
            Questao(
                "Monte metade de um inteiro com quaisquer peças numéricas.",
                soma_alvo=4,
                unidade_enunciado="metade de um inteiro",
            ),
            Questao(
                "Você comprou uma pizza inteira dividida em oito partes. Monte o inteiro completo.",
                soma_alvo=8,
                unidade_enunciado="um inteiro",
            ),
        ),
    ),
    4: Fase(
        "Fase 4: Frações Equivalentes",
        (
            Questao(
                "Monte uma fração equivalente a um quarto usando peças de um oitavo.",
                ids_obrigatorios=(OITAVO, OITAVO),
                unidade_enunciado="um quarto",
            ),
            Questao(
                "Dividindo um lanche: dois pedaços de um oitavo equivalem a um quarto. Monte essa fração.",
                ids_obrigatorios=(OITAVO, OITAVO),
                unidade_enunciado="um quarto",
            ),
            Questao(
                "Para repartir igualmente, quatro pedaços de um oitavo formam a metade de uma torta. Monte essa fração.",
                ids_obrigatorios=(OITAVO,) * 4,
                unidade_enunciado="metade de um inteiro",
            ),
        ),
    ),
    5: Fase(
        "Fase 5: Relação Parte e Todo",
        (
            Questao(
                "Três oitavos equivalem a três partes de um total de oito. Monte essa fração utilizando quaisquer peças numéricas.",
                soma_alvo=3,
                unidade_enunciado="três oitavos",
            ),
            Questao(
                "De uma caixa com oito ovos para um bolo, você usou três. Monte a fração que representa os ovos usados.",
                soma_alvo=3,
                unidade_enunciado="três oitavos",
            ),
            Questao(
                "De uma cartela com oito adesivos, você colou cinco. Monte a fração que representa os adesivos colados.",
                soma_alvo=5,
                unidade_enunciado="cinco oitavos",
            ),
            Questao(
                "De uma barra de cereal com oito quadrados, você comeu dois. Monte a fração que representa os quadrados que sobraram.",
                soma_alvo=6,
                unidade_enunciado="seis oitavos",
            ),
        ),
    ),
    6: Fase(
        "Fase 6: Equivalência em Duas Peças Base",
        (
            Questao(
                "Na primeira peça base, monte quatro oitavos utilizando peças numéricas de um oitavo.",
                ids_obrigatorios=(OITAVO,) * 4,
                unidade_enunciado="quatro oitavos",
                duas_etapas=True,
                segundo_enunciado="Agora, na segunda peça base, monte a mesma quantidade utilizando peças numéricas de um quarto.",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
            Questao(
                "Na primeira peça base, monte um inteiro utilizando peças numéricas de um quarto.",
                ids_obrigatorios=(QUARTO,) * 4,
                unidade_enunciado="um inteiro",
                duas_etapas=True,
                segundo_enunciado="Agora, na segunda peça base, monte a mesma quantidade utilizando peças numéricas de um meio.",
                ids_obrigatorios_etapa_dois=(MEIO,) * 2,
            ),
            Questao(
                "Na primeira peça base, monte metade de um inteiro utilizando uma peça numérica de um meio.",
                ids_obrigatorios=(MEIO,),
                unidade_enunciado="metade de um inteiro",
                duas_etapas=True,
                segundo_enunciado="Agora, na segunda peça base, monte a mesma quantidade utilizando peças numéricas de um quarto.",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
        ),
    ),
}
