from fracoes.atividades import FASES
from fracoes.avaliacao import Leitura
from fracoes.config import TAG_ID_MAP
from fracoes.estado import Sessao

class FaladorFalso:
    """Só registra o que foi pedido, sem tocar som."""

    def __init__(self):
        self.falas = []
        self.bipes = []

    def falar(self, texto):
        self.falas.append(texto)

    def bipe(self, tipo):
        self.bipes.append(tipo)

def test_inicio_fala_boas_vindas_e_opcoes():
    s, f = _sessao()
    s.iniciar()
    assert s.estado.menu
    assert "Bem-vindo" in f.falas[-1] and "aperte espaço" in f.falas[-1].lower()


def test_espaco_no_menu_comeca_na_fase_1():
    s, f = _sessao()
    s.iniciar()
    s.verificar_ou_avancar(Leitura([]))
    assert not s.estado.menu and s.estado.fase == 1
    assert "Atividade 1 de" in f.falas[-1]


def test_numero_no_menu_escolhe_a_fase():
    s, _ = _sessao()
    s.iniciar()
    s.trocar_fase(3)
    assert not s.estado.menu and s.estado.fase == 3


def test_p_no_menu_repete_as_instrucoes_e_r_nao_faz_nada():
    s, f = _sessao()
    s.iniciar()
    s.repetir_pergunta()
    assert "Bem-vindo" in f.falas[-1]
    antes = len(f.falas)
    s.reiniciar_questao()
    assert len(f.falas) == antes and s.estado.menu


def _sessao():
    f = FaladorFalso()
    return Sessao(f), f


def _ids_corretos(q):
    if q.ids_obrigatorios:
        return list(q.ids_obrigatorios)
    ids, restante = [], q.soma_alvo
    for tag, val in ((TAG_ID_MAP[4], 4), (TAG_ID_MAP[2], 2), (TAG_ID_MAP[1], 1)):
        while restante >= val:
            ids.append(tag)
            restante -= val
    return ids

def test_resposta_certa_marca_resolvida_e_toca_bipe():
    s, f = _sessao()
    s.verificar_ou_avancar(Leitura([TAG_ID_MAP[1]]))
    assert s.estado.resolvida and f.bipes[-1] == "ok"


def test_erro_conta_tentativas_e_repete_enunciado_na_segunda():
    s, f = _sessao()
    errada = Leitura([TAG_ID_MAP[4]])  # a questão 1 pede um oitavo
    s.verificar_ou_avancar(errada)
    assert s.estado.tentativas == 1 and "Repetindo o enunciado" not in f.falas[-1]
    s.verificar_ou_avancar(errada)
    assert s.estado.tentativas == 2 and "Repetindo o enunciado" in f.falas[-1]
    assert f.bipes[-2:] == ["erro", "erro"]
    assert not s.estado.resolvida


def test_aviso_sem_pecas_nao_conta_tentativa():
    s, f = _sessao()
    s.verificar_ou_avancar(Leitura([]))
    assert s.estado.tentativas == 0 and f.bipes[-1] == "aviso"


def test_tentativas_zeram_ao_avancar_reiniciar_e_trocar_fase():
    s, _ = _sessao()
    s.verificar_ou_avancar(Leitura([TAG_ID_MAP[4]]))
    s.reiniciar_questao()
    assert s.estado.tentativas == 0
    s.verificar_ou_avancar(Leitura([TAG_ID_MAP[4]]))
    s.trocar_fase(2)
    assert s.estado.tentativas == 0


def test_percorre_todas_as_fases():
    s, _ = _sessao()
    for fase in sorted(FASES):
        s.trocar_fase(fase)
        for q in FASES[fase].questoes:
            leitura = Leitura(_ids_corretos(q))
            s.verificar_ou_avancar(leitura)
            assert s.estado.resolvida
            s.verificar_ou_avancar(leitura)  # avança
    assert s.estado.rotulo == "FASE CONCLUÍDA"


def test_reiniciar_e_repetir():
    s, f = _sessao()
    s.reiniciar_questao()
    s.repetir_pergunta()
    assert len(f.falas) == 2
