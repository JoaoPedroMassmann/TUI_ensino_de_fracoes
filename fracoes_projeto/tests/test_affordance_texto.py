"""Orçamento de texto da interface: falha se alguma mensagem voltar a crescer.

Rodar: python -m unittest discover -s tests -t .   (a partir da pasta do pacote)
"""

import importlib
import unittest
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent.name


def _mod(nome):
    return importlib.import_module(f"{PKG}.{nome}")


atividades, avaliacao, mensagens = _mod("atividades"), _mod("avaliacao"), _mod("mensagens")
interface, estado = _mod("interface"), _mod("estado")
Leitura = avaliacao.Leitura
OITAVO, QUARTO, MEIO = atividades.OITAVO, atividades.QUARTO, atividades.MEIO

LIMITE_ENUNCIADO = 80
LIMITE_TITULO_FASE = 32
LIMITE_FEEDBACK = 120            # mensagens fixas de aviso, confirmação e resultado
LIMITE_AJUDA = 250               # só falada sob demanda (H)
LIMITE_FALHA_CALIBRACAO = 70
LIMITE_LINHA_AJUDA = 45          # linha do painel de comandos na tela
LIMITE_ATALHOS = 60
# Erro por tentativa: a 1ª diz o que viu e o que pede; a 2ª, quanto falta; a 3ª, só a ação.
LIMITE_ERRO = {1: 135, 2: 115, 3: 80}
LIMITE_OK = 100

EXCECOES = {"CALIBRACAO_INICIO": 150, "BOAS_VINDAS": 120}
LEITURAS_ERRADAS = (
    [OITAVO], [QUARTO], [MEIO], [OITAVO] * 2, [QUARTO] * 2, [MEIO] * 2, [OITAVO] * 3,
    [OITAVO, QUARTO], [MEIO, QUARTO, OITAVO], [OITAVO] * 9, [QUARTO] * 5,
)


class OrcamentoDeTexto(unittest.TestCase):
    def test_enunciados_e_titulos(self):
        for fase in atividades.FASES.values():
            self.assertLessEqual(len(fase.titulo), LIMITE_TITULO_FASE, fase.titulo)
            for q in fase.questoes:
                for texto in (q.enunciado, q.segundo_enunciado):
                    if texto:
                        self.assertLessEqual(len(texto), LIMITE_ENUNCIADO, texto)

    def test_mensagens_fixas(self):
        for nome in dir(mensagens):
            valor = getattr(mensagens, nome)
            if not nome.isupper() or not isinstance(valor, str) or nome.startswith("_"):
                continue
            if nome.startswith("AJUDA"):
                limite = LIMITE_AJUDA
            else:
                limite = EXCECOES.get(nome, LIMITE_FEEDBACK)
            self.assertLessEqual(len(valor), limite, f"{nome}: {len(valor)} caracteres")
        for codigo, texto in mensagens.CALIBRACAO_FALHAS.items():
            self.assertLessEqual(len(texto), LIMITE_FALHA_CALIBRACAO, codigo)

    def test_mensagens_de_avaliacao(self):
        for fase in atividades.FASES.values():
            for q in fase.questoes:
                for ids in LEITURAS_ERRADAS:
                    for tentativa in (1, 2, 3):
                        r = avaliacao.avaliar(q, Leitura(ids), tentativa)
                        if r.tipo == "erro":
                            self.assertLessEqual(
                                len(r.texto), LIMITE_ERRO[tentativa], f"t{tentativa}: {r.texto}"
                            )
                        elif r.tipo == "ok":
                            self.assertLessEqual(len(r.texto), LIMITE_OK, r.texto)

    def test_ajuda_por_modo(self):
        for modo in ("menu", "atividade", "troca", "exploracao", "calibracao"):
            self.assertLessEqual(len(mensagens.ajuda_falada(modo, 1, 6)), LIMITE_AJUDA, modo)
            linhas = mensagens.comandos_tela(modo, 1, 6)
            self.assertLessEqual(len(linhas), 12, modo)
            for linha in linhas:
                self.assertLessEqual(len(linha), LIMITE_LINHA_AJUDA, linha)

    def test_barra_de_atalhos_mostra_so_as_teclas_do_momento(self):
        modos = [
            {}, {"menu": True}, {"exploracao": True}, {"calibrando": True},
            {"troca": 1}, {"resolvida": True}, {"acao_pendente": "3"}, {"confirmando_saida": True},
            {"ajuda_visivel": True},
        ]
        for campos in modos:
            texto = interface.texto_atalhos(estado.EstadoSistema(**campos))
            self.assertLessEqual(len(texto), LIMITE_ATALHOS, f"{campos}: {texto}")
            self.assertLessEqual(texto.count("["), 3, texto)


if __name__ == "__main__":
    unittest.main()
