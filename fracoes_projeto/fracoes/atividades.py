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

    ids_obrigatorios: peças exatas que devem estar posicionadas na peça base (IDs das tags);
    soma_alvo: total em oitavos, com quaisquer peças;
    duas_etapas: se True, o usuário deve construir duas frações equivalentes em duas peças bases diferentes;
    segundo_enunciado: enunciado da segunda etapa, se houver;
    ids_obrigatorios_etapa_dois: peças exatas que devem estar posicionadas na peça base na segunda etapa (IDs das tags).

    """
    enunciado: str
    ids_obrigatorios: tuple[int, ...] | None = None
    soma_alvo: int | None = None
    duas_etapas: bool = False
    segundo_enunciado: str | None = None
    ids_obrigatorios_etapa_dois: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if (self.ids_obrigatorios is None) == (self.soma_alvo is None):
            raise ValueError("Informe ids_obrigatorios OU soma_alvo (apenas um).")
        if self.duas_etapas:
            if self.ids_obrigatorios is None or self.ids_obrigatorios_etapa_dois is None:
                raise ValueError("Questões com duas_etapas exigem ids_obrigatorios e ids_obrigatorios_etapa_dois.")
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
                "Encaixe a peça de 1 oitavo na peça base, para assim formar a fração de 1 oitavo.", 
                ids_obrigatorios=(OITAVO,),
            ),
            Questao(
                "Encaixe a peça de 1 quarto na peça base, para assim formar a fração de 1 quarto.", 
                ids_obrigatorios=(QUARTO,),
            ),
            Questao(
                "Encaixe a peça de 1 meio na peça base, para assim formar a fração de 1 meio.", 
                ids_obrigatorios=(MEIO,),
            ),
        ),
    ),
    2: Fase(
            "Fase 2: Representação de Números como Frações",
            (
                Questao(
                    "Encaixe peças de 1 oitavo na base até formar a fração de 1 inteiro.", 
                    ids_obrigatorios=(OITAVO,) * 8,
                ),
                Questao(
                    "Encaixe peças de 1 quarto na base até formar a fração de 1 inteiro.", 
                    ids_obrigatorios=(QUARTO,) * 4,
                ),
                Questao(
                    "Encaixe peças de 1 meio na base até formar a fração de 1 inteiro.", 
                    ids_obrigatorios=(MEIO,) * 2,
                ),
            ),
        ),
    3: Fase(
        "Fase 3: Representação de Números como Frações",
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
    4: Fase(
        "Fase 4: Frações Equivalentes",
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
    5: Fase(
        "Fase 5: Relação Parte / Todo",
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
    6: Fase(
        "Fase 6: Atividades com duas fases",
        (
            Questao(
                "Monte uma fração de 4 oitavos utilizando peças de um oitavo",
                ids_obrigatorios=(OITAVO,) * 4,
                duas_etapas=True,
                segundo_enunciado="Agora, monte uma com a mesma quantidade de oitavos utilizando peças de 1 quarto",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
            Questao(
                "Monte uma fração de 8 oitavos utilizando peças de 1 quarto",
                ids_obrigatorios=(QUARTO,) * 4,
                duas_etapas=True,
                segundo_enunciado="Agora, monte uma com a mesma quantidade de oitavos utilizando peças de 1 um meio",
                ids_obrigatorios_etapa_dois=(MEIO,) * 2,
            ),
            Questao(
                "Monte uma fração de 4 oitavos utilizando peças de 1 um meio",
                ids_obrigatorios=(MEIO,),
                duas_etapas=True,
                segundo_enunciado="Agora, monte uma com a mesma quantidade de oitavos utilizando peças de 1 quarto",
                ids_obrigatorios_etapa_dois=(QUARTO,) * 2,
            ),
        ),
    ),
}
