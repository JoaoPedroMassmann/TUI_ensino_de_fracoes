from fracoes.fala import Falador

def test_codigo_1_sem_corte_e_falha_de_audio():
    f = Falador(bipes=False)
    f._registrar_saida(1)
    assert not f.saude_ok

def test_fala_cortada_nao_e_falha():
    f = Falador(bipes=False)
    f._cortado = True
    f._registrar_saida(1)
    assert f.saude_ok

def test_sucesso_limpa_a_falha():
    f = Falador(bipes=False)
    f._registrar_saida(1)
    f._registrar_saida(0)
    assert f.saude_ok