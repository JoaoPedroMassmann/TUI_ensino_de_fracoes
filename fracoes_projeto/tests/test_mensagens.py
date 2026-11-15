import pytest

from fracoes import mensagens as m
from fracoes.config import TAG_ID_MAP

OITAVO, QUARTO, MEIO = TAG_ID_MAP[1], TAG_ID_MAP[2], TAG_ID_MAP[4]


@pytest.mark.parametrize(
    "n,esperado", [(1, "um oitavo"), (2, "dois oitavos"), (3, "três oitavos"), (20, "20 oitavos")]
)
def test_oitavos_por_extenso(n, esperado):
    assert m.oitavos(n) == esperado


def test_listar_pecas():
    assert m.listar_pecas([QUARTO, MEIO, QUARTO]) == "um meio e dois quartos"
    assert m.listar_pecas([OITAVO]) == "um oitavo"
    assert m.listar_pecas([MEIO, QUARTO, OITAVO]) == "um meio, um quarto e um oitavo"


def test_concordar_e_maiuscula():
    assert m.concordar((MEIO,), "Sobra", "Sobram") == "Sobra"
    assert m.concordar((QUARTO, QUARTO), "Sobra", "Sobram") == "Sobram"
    assert m.maiuscula("um meio") == "Um meio"
