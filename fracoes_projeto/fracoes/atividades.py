"""Fases e atividades do sistema."""

from __future__ import annotations

from dataclasses import dataclass

from .config import ID_VALUES_MAP, TAG_ID_MAP

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
            if not self.segundo_enunciado:
                raise ValueError("Atividades com duas_etapas exigem segundo_enunciado.")
            total1 = sum(ID_VALUES_MAP[i] for i in self.ids_obrigatorios)
            total2 = sum(ID_VALUES_MAP[i] for i in self.ids_obrigatorios_etapa_dois)
            if total1 != total2:
                raise ValueError("As duas etapas devem somar o mesmo valor.")
        elif self.ids_obrigatorios_etapa_dois is not None:
            raise ValueError("ids_obrigatorios_etapa_dois só deve ser usado com duas_etapas=True.")


@dataclass(frozen=True)
class Fase:
    titulo: str
    questoes: tuple[Questao, ...]


FASES: dict[int, Fase] = {
    1: Fase(
        "Fase 1: Frações unitárias",
        (
            Questao(
                "Encaixe a peça de um oitavo na peça base e forme um oitavo.",
                ids_obrigatorios=(OITAVO,),
                unidade_enunciado="um oitavo",
            ),
            Questao(
                "Encaixe a peça de um quarto na peça base e forme um quarto.",
                ids_obrigatorios=(QUARTO,),
                unidade_enunciado="um quarto",
            ),
            Questao(
                "Encaixe a peça de um meio na peça base e forme um meio.",
                ids_obrigatorios=(MEIO,),
                unidade_enunciado="um meio",
            ),
        ),
    ),
    2: Fase(
        "Fase 2: Formar o inteiro",
        (
            Questao(
                "Encaixe peças de um oitavo na peça base até encher e formar um inteiro.",
                ids_obrigatorios=(OITAVO,) * 8,
                unidade_enunciado="um inteiro",
            ),
            Questao(
                "Encaixe peças de um quarto na peça base até encher e formar um inteiro.",
                ids_obrigatorios=(QUARTO,) * 4,
                unidade_enunciado="um inteiro",
            ),
            Questao(
                "Encaixe peças de um meio na peça base até encher e formar um inteiro.",
                ids_obrigatorios=(MEIO,) * 2,
                unidade_enunciado="um inteiro",
            ),
        ),
    ),
    3: Fase(
        "Fase 3: Números fracionários",
        (
            Questao(
                "Monte quatro oitavos. Isso é metade de um inteiro.",
                soma_alvo=4,
                unidade_enunciado="metade de um inteiro",
            ),
            Questao(
                "Monte metade de um inteiro com quaisquer peças.",
                soma_alvo=4,
                unidade_enunciado="metade de um inteiro",
            ),
            Questao(
                "Uma pizza foi dividida em quatro pedaçoes. Monte a fração que equivale a um pedaço dessa pedaço.",
                soma_alvo=2,
                unidade_enunciado="um quarto",
            ),
        ),
    ),
    4: Fase(
        "Fase 4: Frações equivalentes",
        (
            Questao(
                "Monte um quarto usando peças de um oitavo.",
                ids_obrigatorios=(OITAVO, OITAVO),
                unidade_enunciado="um quarto",
            ),
            Questao(
                "Monte um meio usando peças de um quarto.",
                ids_obrigatorios=(QUARTO, QUARTO),
                unidade_enunciado="um meio",
            ),
            Questao(
                "Monte metade de um inteiro usando peças de um oitavo.",
                ids_obrigatorios=(OITAVO,) * 4,
                unidade_enunciado="metade de um inteiro",
            ),
        ),
    ),
    5: Fase(
        "Fase 5: Parte e todo",
        (
            Questao(
                "De uma caixa com oito ovos, você usou três. Monte a fração dos ovos que foi usada.",
                soma_alvo=3,
                unidade_enunciado="três oitavos",
            ),
            Questao(
                "De uma cartela com oito adesivos, você colou cinco. Monte a fração dos adesivos que foi colada.",
                soma_alvo=5,
                unidade_enunciado="cinco oitavos",
            ),
            Questao(
                "De uma barra com oito quadrados, você comeu dois. Monte a fração dos quadrados que sobraram.",
                soma_alvo=6,
                unidade_enunciado="seis oitavos",
            ),
        ),
    ),
    6: Fase(
        "Fase 6: Frações equivalentes com duas peças base",
        (
            Questao(
                "Na primeira peça base, monte quatro oitavos com peças de um oitavo.",
                ids_obrigatorios=(OITAVO,) * 4,
                unidade_enunciado="quatro oitavos",
                duas_etapas=True,
                segundo_enunciado="Na segunda peça base, monte quatro oitavos com peças de um quarto.",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
            Questao(
                "Na primeira peça base, monte um inteiro com peças de um quarto.",
                ids_obrigatorios=(QUARTO,) * 4,
                unidade_enunciado="um inteiro",
                duas_etapas=True,
                segundo_enunciado="Na segunda peça base, monte um inteiro com peças de um meio.",
                ids_obrigatorios_etapa_dois=(MEIO,) * 2,
            ),
            Questao(
                "Na primeira peça base, monte metade de um inteiro com uma peça de um meio.",
                ids_obrigatorios=(MEIO,),
                unidade_enunciado="metade de um inteiro",
                duas_etapas=True,
                segundo_enunciado="Na segunda peça base, monte metade de um inteiro com peças de um quarto.",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
        ),
    ),
}