from fracoes.deteccao import Estabilizador


def test_ignora_falha_isolada():
    e = Estabilizador(janela=5)
    for _ in range(4):
        e.atualizar([10, 20])
    assert sorted(e.atualizar([10])) == [10, 20]  # tag 20 sumiu em 1 quadro só


def test_atualiza_quando_peca_sai():
    e = Estabilizador(janela=3)
    for _ in range(3):
        e.atualizar([10, 20])
    for _ in range(3):
        r = e.atualizar([10])
    assert r == [10]


def test_conta_pecas_repetidas():
    e = Estabilizador(janela=3)
    for _ in range(3):
        r = e.atualizar([20, 20])
    assert r == [20, 20]
