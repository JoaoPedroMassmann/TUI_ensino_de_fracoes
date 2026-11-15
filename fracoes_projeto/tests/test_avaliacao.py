import pytest

from fracoes.atividades import FASES, Questao
from fracoes.avaliacao import (
    Leitura,
    avaliar,
    diagnosticar,
    ids_para_valor,
    simplificar_fracao,
    sugerir_ajuste,
    total_oitavos,
)
from fracoes.config import TAG_ID_MAP

OITAVO, QUARTO, MEIO = TAG_ID_MAP[1], TAG_ID_MAP[2], TAG_ID_MAP[4]


def ler(*ids, **kw):
    return Leitura(list(ids), **kw)


def test_total_oitavos():
    assert total_oitavos([OITAVO, QUARTO, MEIO]) == 7
    assert ler(OITAVO, QUARTO, MEIO).total == 7


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


def test_todas_as_fases_tem_questoes():
    assert set(FASES) == {1, 2, 3, 4}
    assert all(f.questoes for f in FASES.values())


# sem peças
def test_sem_pecas_e_aviso():
    r = avaliar(Questao("x", soma_alvo=4), ler())
    assert r.tipo == "aviso" and "nenhuma peça" in r.texto and r.repetir_enunciado



def test_oscilando_acrescenta_nota():
    r = avaliar(Questao("x", soma_alvo=4), ler(oscilando=True))
    assert "oscilando" in r.texto


# questões de soma
def test_soma_correta():
    r = avaliar(Questao("x", soma_alvo=4), ler(MEIO))
    assert r.tipo == "ok" and "quatro oitavos" in r.texto


def test_erro_diz_o_que_a_camera_viu():
    r = avaliar(Questao("x", soma_alvo=4), ler(QUARTO))
    assert r.tipo == "erro"
    assert "Vejo um quarto" in r.texto and "pede quatro oitavos" in r.texto


def test_dicas_graduais_na_soma():
    q = Questao("x", soma_alvo=4)
    t1 = avaliar(q, ler(OITAVO), tentativa=1).texto
    t2 = avaliar(q, ler(OITAVO), tentativa=2).texto
    t3 = avaliar(q, ler(OITAVO), tentativa=3).texto
    assert "Faltam" not in t1 and "Acrescente" not in t1
    assert "Faltam três oitavos." in t2 and "Acrescente" not in t2
    assert "Acrescente um quarto e um oitavo." in t3 and "Aperte P" in t3


def test_repete_enunciado_so_na_segunda_tentativa():
    q = Questao("x", soma_alvo=4)
    flags = [avaliar(q, ler(OITAVO), tentativa=n).repetir_enunciado for n in (1, 2, 3, 4)]
    assert flags == [False, True, False, False]


def test_quase_quando_falta_um_oitavo():
    r = avaliar(Questao("x", soma_alvo=4), ler(QUARTO, OITAVO))
    assert (
        r.texto.startswith("Quase!")
        and "Falta um oitavo."
        in avaliar(Questao("x", soma_alvo=4), ler(QUARTO, OITAVO), tentativa=2).texto
    )


def test_passou_sugere_retirar_ou_trocar():
    q = Questao("x", soma_alvo=2)
    assert "Retire um quarto." in avaliar(q, ler(QUARTO, QUARTO), tentativa=3).texto
    assert "Troque um meio por um quarto." in avaliar(q, ler(MEIO), tentativa=3).texto


# peças obrigatórias
def test_pecas_exatas_em_qualquer_ordem():
    q = Questao("x", ids_obrigatorios=(QUARTO, OITAVO))
    assert avaliar(q, ler(OITAVO, QUARTO)).tipo == "ok"


def test_valor_certo_pecas_erradas_com_dicas():
    q = Questao("x", ids_obrigatorios=(QUARTO, QUARTO))
    t1 = avaliar(q, ler(MEIO), tentativa=1).texto
    t2 = avaliar(q, ler(MEIO), tentativa=2).texto
    t3 = avaliar(q, ler(MEIO), tentativa=3).texto
    assert "valor total está certo" in t1 and "Sobra" not in t1
    assert "Sobra um meio." in t2 and "Faltam dois quartos." in t2
    assert "Troque um meio por dois quartos." in t3
    assert "Um meio vale o mesmo que dois quartos." in t3


def test_pecas_obrigatorias_valor_errado():
    q = Questao("x", ids_obrigatorios=(QUARTO, QUARTO))
    r = avaliar(q, ler(MEIO, QUARTO), tentativa=3)
    assert (
        r.tipo == "erro"
        and "Passaram dois oitavos." in r.texto
        and "Troque um meio por um quarto." in r.texto
    )



# funções auxiliares
@pytest.mark.parametrize("valor,esperado", [(1, 1), (3, 2), (7, 3), (8, 2)])
def test_ids_para_valor_usa_poucas_pecas(valor, esperado):
    ids = ids_para_valor(valor)
    assert total_oitavos(list(ids)) == valor and len(ids) == esperado


def test_sugerir_ajuste_casos():
    assert sugerir_ajuste([QUARTO], 2) == ((QUARTO,), ())
    assert sugerir_ajuste([QUARTO, OITAVO], -1) == ((), (OITAVO,))
    assert sugerir_ajuste([MEIO, MEIO, MEIO], -5) == ((OITAVO, QUARTO), (MEIO, MEIO))
    assert sugerir_ajuste([MEIO], 0) == ((), ())


def test_diagnostico_das_pecas():
    q = Questao("x", ids_obrigatorios=(MEIO, QUARTO))
    d = diagnosticar(q, [MEIO, OITAVO])
    assert d.situacao == "valor_errado"
    assert d.faltam == (QUARTO,) and d.sobram == (OITAVO,) and d.diferenca == 1
