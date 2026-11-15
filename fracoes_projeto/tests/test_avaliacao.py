import pytest

from fracoes.atividades import FASES, Questao
from fracoes.avaliacao import avaliar, simplificar_fracao, total_oitavos
from fracoes.config import TAG_ID_MAP

OITAVO, QUARTO, MEIO = TAG_ID_MAP[1], TAG_ID_MAP[2], TAG_ID_MAP[4]


def test_total_oitavos():
    assert total_oitavos([OITAVO, QUARTO, MEIO]) == 7


@pytest.mark.parametrize(
    "n,esperado", [(0, (0, 1)), (4, (1, 2)), (2, (1, 4)), (8, (1, 1)), (3, (3, 8))]
)
def test_simplificar(n, esperado):
    assert simplificar_fracao(n) == esperado


def test_questao_exige_exatamente_um_criterio():
    with pytest.raises(ValueError):
        Questao("x")
    with pytest.raises(ValueError):
        Questao("x", ids_obrigatorios=(OITAVO,), soma_alvo=1)


def test_sem_pecas_e_aviso():
    questao = Questao("x", soma_alvo=4)
    assert avaliar(questao, [], 0).tipo == "aviso"


def test_soma_correta_e_errada():
    questao = Questao("x", soma_alvo=4)
    assert avaliar(questao, [MEIO], 4).tipo == "ok"
    resultado = avaliar(questao, [QUARTO], 2)
    assert resultado.tipo == "erro" and resultado.repetir_enunciado and "Acrescente 2 oitavos" in resultado.texto


def test_pecas_obrigatorias():
    questao = Questao("x", ids_obrigatorios=(QUARTO, QUARTO))
    assert avaliar(questao, [QUARTO, QUARTO], 4).tipo == "ok"
    assert avaliar(questao, [MEIO], 4).tipo == "erro"  # valor certo, peças erradas
    assert "Retire" in avaliar(questao, [MEIO, QUARTO], 6).texto


def test_todas_as_fases_tem_questoes():
    assert set(FASES) == {1, 2, 3, 4}
    assert all(f.questoes for f in FASES.values())
