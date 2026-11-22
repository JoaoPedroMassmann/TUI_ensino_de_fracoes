"""Testes da lógica do sistema (sem câmera nem áudio). Rodar: python -m unittest discover -s tests -t ."""

import importlib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent.name


def _mod(nome):
    return importlib.import_module(f"{PKG}.{nome}")


estado, avaliacao, deteccao = _mod("estado"), _mod("avaliacao"), _mod("deteccao")
atividades, config = _mod("atividades"), _mod("config")
Sessao, Leitura = estado.Sessao, avaliacao.Leitura
OITAVO, QUARTO, MEIO = atividades.OITAVO, atividades.QUARTO, atividades.MEIO


class FaladorFalso:
    tocou_bipe = False

    def __init__(self):
        self.falas = []

    def bipe(self, tipo):
        pass

    def calar(self):
        self.calou = True

    def falar(self, texto):
        self.falas.append(texto)


def sessao_na_fase(fase):
    s = Sessao(FaladorFalso())
    s.iniciar()
    s.trocar_fase(fase)
    return s


class Avaliacao(unittest.TestCase):
    def test_correto_por_pecas(self):
        q = atividades.FASES[1].questoes[0]
        self.assertEqual(avaliacao.avaliar(q, Leitura([OITAVO])).tipo, "ok")

    def test_valor_certo_pecas_erradas(self):
        q = atividades.FASES[4].questoes[0]  # dois oitavos
        r = avaliacao.avaliar(q, Leitura([QUARTO]))
        self.assertEqual(r.tipo, "erro")
        self.assertIn("o mesmo que", r.texto)

    def test_soma_aceita_qualquer_combinacao(self):
        q = atividades.FASES[3].questoes[1]  # metade, soma 4
        self.assertEqual(avaliacao.avaliar(q, Leitura([QUARTO, QUARTO])).tipo, "ok")
        self.assertEqual(avaliacao.avaliar(q, Leitura([MEIO])).tipo, "ok")

    def test_sem_base_e_sem_pecas(self):
        q = atividades.FASES[1].questoes[0]
        self.assertEqual(avaliacao.avaliar(q, Leitura([OITAVO], base=False)).tipo, "aviso")
        self.assertEqual(avaliacao.avaliar(q, Leitura([])).tipo, "aviso")

    def test_sugerir_ajuste(self):
        self.assertEqual(avaliacao.sugerir_ajuste([OITAVO], 1), ((OITAVO,), ()))
        faltam, sobram = avaliacao.sugerir_ajuste([MEIO, OITAVO], -1)
        self.assertEqual(sobram, (OITAVO,))
        self.assertEqual(faltam, ())

    def test_mensagem_fica_mais_detalhada(self):
        q = atividades.FASES[3].questoes[2]  # soma 8
        t1 = avaliacao.avaliar(q, Leitura([MEIO]), tentativa=1).texto
        t3 = avaliacao.avaliar(q, Leitura([MEIO]), tentativa=3).texto
        self.assertGreater(len(t3), len(t1))


class Fase6(unittest.TestCase):
    def _etapa1_certa(self):
        s = sessao_na_fase(6)
        s.verificar_ou_avancar(Leitura([OITAVO] * 4))
        self.assertEqual(s.estado.troca, estado.TROCA_RETIRAR)
        return s

    def test_troca_com_base_desligada_nao_trava(self):
        s = self._etapa1_certa()
        sem_deteccao = Leitura([], False, True, False, False)
        s.verificar_ou_avancar(sem_deteccao)
        self.assertEqual(s.estado.troca, estado.TROCA_POSICIONAR)
        s.verificar_ou_avancar(sem_deteccao)
        self.assertEqual(s.estado.etapa_atual, 2)

    def test_retirada_exige_mesa_sem_pecas(self):
        s = self._etapa1_certa()
        s.verificar_ou_avancar(Leitura([], False, False, True, True))  # peça esquecida
        self.assertEqual(s.estado.troca, estado.TROCA_RETIRAR)
        s.verificar_ou_avancar(Leitura([], False, True, False, True))  # base ainda visível
        self.assertEqual(s.estado.troca, estado.TROCA_RETIRAR)
        s.verificar_ou_avancar(Leitura([], False, False, False, True))
        self.assertEqual(s.estado.troca, estado.TROCA_POSICIONAR)

    def test_fora_da_base_sem_base_vista_pede_a_base(self):
        s = sessao_na_fase(1)
        s.verificar_ou_avancar(Leitura([], False, False, True, True))
        self.assertNotIn("fora da peça base", s.estado.mensagem)


class Teclado(unittest.TestCase):
    def test_cancelar_saida_usa_contexto_certo(self):
        s = Sessao(FaladorFalso())
        s.iniciar()
        s.iniciar_calibracao()
        s.pedir_confirmacao_saida()
        s.cancelar_confirmacao_saida()
        self.assertIn("Calibração", s.estado.mensagem)


class Calibracao(unittest.TestCase):
    def test_deteccao_comeca_desligada(self):
        self.assertFalse(deteccao.DetectorBase().ativo)

    def test_calibracao_liga_a_deteccao(self):
        import cv2
        import numpy as np

        quadro = np.full((720, 1280, 3), 230, np.uint8)
        cv2.circle(quadro, (640, 360), 180, (20, 20, 20), -1)
        d = deteccao.DetectorBase()
        for _ in range(config.CALIBRACAO_QUADROS):
            d.medir(quadro)
        self.assertEqual(d.calibrar(quadro, False), "ok")
        self.assertTrue(d.ativo)

    def test_calibracao_com_pecas_falha_e_mantem_estado(self):
        d = deteccao.DetectorBase()
        self.assertEqual(d.calibrar(None, True), "pecas")
        self.assertFalse(d.ativo)

    def test_calibrar_no_meio_da_atividade_preserva_tudo(self):
        s = sessao_na_fase(6)
        s.verificar_ou_avancar(Leitura([OITAVO] * 4))  # entra na troca de base
        antes = (s.estado.fase, s.estado.questao_atual, s.estado.troca, s.estado.mensagem)
        s.iniciar_calibracao()
        self.assertTrue(s.estado.calibrando)
        s.cancelar_calibracao(False)
        self.assertFalse(s.estado.calibrando)
        depois = (s.estado.fase, s.estado.questao_atual, s.estado.troca, s.estado.mensagem)
        self.assertEqual(antes, depois)

    def test_falha_nao_perde_a_tela_anterior(self):
        s = sessao_na_fase(2)
        original = s.estado.mensagem
        s.iniciar_calibracao()
        s.resultado_calibracao("pecas")
        self.assertTrue(s.estado.calibrando)
        s.resultado_calibracao("ok")
        self.assertEqual(s.estado.mensagem, original)

    def test_repetir_pergunta_na_calibracao_fala_calibracao(self):
        s = sessao_na_fase(1)
        s.iniciar_calibracao()
        s.estado.exploracao = True
        s.repetir_pergunta()
        self.assertIn("Calibração", s.falador.falas[-1])


class Confirmacoes(unittest.TestCase):
    def _app(self):
        return _mod("app")

    def _em_andamento(self):
        s = sessao_na_fase(1)
        s.verificar_ou_avancar(Leitura([OITAVO]))  # acerta a 1ª
        s.verificar_ou_avancar(Leitura([]))        # avança
        return s

    def test_troca_de_fase_sem_progresso_e_direta(self):
        s = sessao_na_fase(1)
        s.solicitar_fase(3)
        self.assertEqual(s.estado.fase, 3)

    def test_troca_de_fase_com_progresso_pede_confirmacao(self):
        s = sessao_na_fase(1)
        s.verificar_ou_avancar(Leitura([OITAVO]))
        s.verificar_ou_avancar(Leitura([OITAVO]))  # avançar para a 2ª atividade
        self.assertEqual(s.estado.questao_atual, 1)
        app = self._app()
        self.assertTrue(app.tratar_tecla("3", s, Leitura([])))
        self.assertEqual(s.estado.fase, 1)
        self.assertEqual(s.estado.acao_pendente, "3")
        app.tratar_tecla("3", s, Leitura([]))
        self.assertEqual(s.estado.fase, 3)
        self.assertIsNone(s.estado.acao_pendente)

    def test_outra_tecla_cancela(self):
        s = sessao_na_fase(1)
        s.estado.questao_atual = 1
        app = self._app()
        app.tratar_tecla("4", s, Leitura([]))
        app.tratar_tecla("x", s, Leitura([]))
        self.assertEqual((s.estado.fase, s.estado.questao_atual), (1, 1))
        self.assertIsNone(s.estado.acao_pendente)

    def test_menu_e_pular_pedem_confirmacao(self):
        s = sessao_na_fase(1)
        app = self._app()
        app.tratar_tecla("s", s, Leitura([]))
        self.assertEqual(s.estado.questao_atual, 0)
        app.tratar_tecla("s", s, Leitura([]))
        self.assertEqual(s.estado.questao_atual, 1)
        app.tratar_tecla("m", s, Leitura([]))
        app.tratar_tecla("m", s, Leitura([]))
        self.assertTrue(s.estado.menu)

    def test_pular_ultima_atividade_nao_conclui(self):
        s = sessao_na_fase(6)
        s.estado.questao_atual = 2
        s.solicitar_pular(); s.confirmar_acao()
        self.assertNotEqual(s.estado.rotulo, "FASE CONCLUÍDA")

    def test_escape_cala(self):
        s = sessao_na_fase(1)
        self._app().tratar_tecla("\x1b", s, Leitura([]))
        self.assertTrue(getattr(s.falador, "calou", False))

    def test_ajuda_depende_do_modo(self):
        s = Sessao(FaladorFalso()); s.iniciar()
        s.falar_ajuda(); self.assertIn("menu", s.falador.falas[-1])
        s.trocar_fase(1); s.falar_ajuda(); self.assertIn("pula a atividade", s.falador.falas[-1])
        s.iniciar_calibracao(); s.falar_ajuda(); self.assertIn("Calibração", s.falador.falas[-1])


class Oscilacao(unittest.TestCase):
    def test_oscilando_nao_gasta_tentativa(self):
        s = sessao_na_fase(1)
        errada = Leitura([QUARTO], oscilando=True)
        s.verificar_ou_avancar(errada)
        self.assertEqual(s.estado.tentativas, 0)
        self.assertIn("oscilando", s.estado.mensagem)

    def test_oscilacao_persistente_avalia_sem_contar(self):
        s = sessao_na_fase(1)
        errada = Leitura([QUARTO], oscilando=True)
        for _ in range(estado.LIMITE_RECUSAS_OSCILACAO + 2):
            s.verificar_ou_avancar(errada)
        self.assertEqual(s.estado.tentativas, 0)
        self.assertEqual(s.estado.rotulo, "TENTE DE NOVO")

    def test_erro_estavel_conta(self):
        s = sessao_na_fase(1)
        s.verificar_ou_avancar(Leitura([QUARTO]))
        self.assertEqual(s.estado.tentativas, 1)


class MarcaDesconhecida(unittest.TestCase):
    def test_avisa_o_instrutor_quando_so_ha_marca_desconhecida(self):
        s = sessao_na_fase(1)
        s.verificar_ou_avancar(Leitura([], desconhecidas=True))
        self.assertIn("marca que não pertence", s.estado.mensagem)
        s.verificar_ou_avancar(Leitura([OITAVO], desconhecidas=True))
        self.assertTrue(s.estado.resolvida)


class CalibracaoInicial(unittest.TestCase):
    def test_comeca_calibrando_e_pode_pular(self):
        s = Sessao(FaladorFalso())
        s.iniciar(calibrar=True)
        self.assertTrue(s.estado.calibrando)
        s.cancelar_calibracao(False)
        self.assertFalse(s.estado.calibrando)
        self.assertTrue(s.estado.menu)
        self.assertIn("Bem-vindo", s.falador.falas[-1])
        self.assertIn("desligada", s.falador.falas[-1])

    def test_candidata_so_na_faixa_da_calibracao(self):
        import cv2
        import numpy as np

        d = deteccao.DetectorBase()
        self.assertIsNone(d.candidata_calibracao(720))
        quadro = np.full((720, 1280, 3), 230, np.uint8)
        cv2.circle(quadro, (640, 360), 180, (20, 20, 20), -1)
        d.medir(quadro)
        centro, raio = d.candidata_calibracao(720)
        self.assertLess(abs(centro[0] - 640), 5)
        self.assertLess(abs(raio - 180), 5)
        quadro2 = np.full((720, 1280, 3), 230, np.uint8)
        cv2.circle(quadro2, (640, 360), 40, (20, 20, 20), -1)  # pequena demais
        d.medir(quadro2)
        self.assertIsNone(d.candidata_calibracao(720))


class Estabilizacao(unittest.TestCase):
    def test_falso_positivo_isolado_nao_vira_leitura(self):
        e = deteccao.Estabilizador()
        self.assertEqual(e.atualizar([OITAVO]), [])

    def test_leitura_estavel(self):
        e = deteccao.Estabilizador()
        for _ in range(7):
            ids = e.atualizar([OITAVO, OITAVO])
        self.assertEqual(sorted(ids), [OITAVO, OITAVO])


if __name__ == "__main__":
    unittest.main()
    