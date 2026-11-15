# Sistema Educativo de Frações

Câmera + tags ArUco (DICT_4X4_50) nas peças impressas em 3D + áudio em português.
IDs: 10 = 1/8, 20 = 1/4, 30 = 1/2 (definidos em `fracoes/config.py`, em `TAG_ID_MAP`).

## Executar
    pip install -r requirements.txt
    python -m fracoes

Teclas: 1-4 fases · espaço verificar/avançar · R refazer · P repetir pergunta · Q sair.

## Estrutura
- `config.py` constantes · `atividades.py` fases e questões · `avaliacao.py` lógica pura
- `deteccao.py` ArUco + estabilização · `fala.py` áudio · `estado.py` regras da sessão
- `interface.py` desenho na tela · `app.py` laço principal

## Testes
    pytest
