"""Configurações centrais do sistema."""

from __future__ import annotations

import cv2

# Definição do dicionário ArUco
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50

# Valor da peça (em oitavos) -> ID da tag.
TAG_ID_MAP = {1: 10, 2: 20, 4: 30}  # 1/8, 1/4 (2/8) e 1/2 (4/8)
ID_VALUES_MAP = {tag_id: valor for valor, tag_id in TAG_ID_MAP.items()}

# Teclas
DEBOUNCE_TECLA = 0.6

# Parâmetros do detector
MIN_MARKER_PERIMETER_RATE = 0.015
ADAPTIVE_THRESH_WIN_MIN = 3
ADAPTIVE_THRESH_WIN_MAX = 20
ADAPTIVE_THRESH_WIN_STEP = 10
FRAMES_ESTABILIDADE = 7

# Câmera
CAMERA_INDEX = 0
CAMERA_LARGURA = 1280
CAMERA_ALTURA = 720
JANELA_TITULO = "Sistema Educativo de Frações"
FALHAS_CAMERA_MAX = 15
INTERVALO_RECONEXAO = 2.0

# Áudio (text-to-speech)
TTS_TAXA = 160
TTS_VOZ_DICAS = ("pt-br", "pt_br", "portuguese", "portugu", "brazil", "brasil")

# Cores da interface em RGB
VERDE = (90, 230, 110)
VERMELHO = (255, 95, 95)
AMARELO = (255, 220, 70)
BRANCO = (255, 255, 255)
CINZA = (190, 190, 190)

# Tamanho monitor (para dimensionar a interface)
AJUSTAR_TELA = True

# Fontes da interface
FONT_CANDIDATES = [
    "arialbd.ttf",
    "arial.ttf",    
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
TAMANHOS_FONTE = {
    "titulo": 22,
    "enunciado": 30,
    "mensagem": 26,
    "tag": 22,
    "pequeno": 18,
    "leitura": 22,
}
