from fracoes.atividades import FASES
from fracoes.avaliacao import total_oitavos
from fracoes.config import TAG_ID_MAP
from fracoes.estado import Sessao


class FaladorFalso:
    def __init__(self):
        self.falas = []

    def falar(self, texto):
        self.falas.append(texto)


def _sessao():
    f = FaladorFalso()
    return Sessao(f), f


def test_inicio_fala_titulo_e_questao():
    s, f = _sessao()
    s.iniciar()
    assert "Questão 1 de" in f.falas[-1]


def test_erro_repete_enunciado():
    s, _ = _sessao()
    s.verificar_ou_avancar([TAG_ID_MAP[1]], 1)
    s.verificar_ou_avancar([], 0)
    assert s.estado.resolvida is False


def test_percorre_todas_as_fases():
    s, _ = _sessao()
    for fase in sorted(FASES):
        s.trocar_fase(fase)
        for q in FASES[fase].questoes:
            ids = list(q.ids_obrigatorios) if q.ids_obrigatorios else None
            if ids is None:
                ids, restante = [], q.soma_alvo
                for tag, val in ((TAG_ID_MAP[4], 4), (TAG_ID_MAP[2], 2), (TAG_ID_MAP[1], 1)):
                    while restante >= val:
                        ids.append(tag)
                        restante -= val
            s.verificar_ou_avancar(ids, total_oitavos(ids))
            assert s.estado.resolvida
            s.verificar_ou_avancar(ids, total_oitavos(ids))  # avança
    assert s.estado.rotulo == "FASE CONCLUÍDA"


def test_reiniciar_e_repetir():
    s, f = _sessao()
    s.reiniciar_questao()
    s.repetir_pergunta()
    assert len(f.falas) == 2
