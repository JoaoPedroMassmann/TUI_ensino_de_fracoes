"""Mostra os blobs escuros e suas medidas. Espaço imprime; q sai."""
import cv2

from . import config
from .app import abrir_camera
from .deteccao import candidatos_base


def main() -> int:
    cap = abrir_camera()
    if cap is None:
        print("Não foi possível abrir a câmera.")
        return 1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        menor_lado = min(frame.shape[:2])
        candidatos = candidatos_base(frame)
        for raio, circ, centro in candidatos[:4]:
            aceito = (
                config.BASE_RAIO_MIN <= raio <= config.BASE_RAIO_MAX
                and circ >= config.BASE_CIRCULARIDADE_MIN
            )
            cor = (0, 200, 0) if aceito else (0, 0, 255)
            cv2.circle(frame, centro, int(raio * menor_lado), cor, 3)
            cv2.putText(frame, f"r={raio:.2f} circ={circ:.2f}", centro,
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, cor, 2)
        cv2.imshow("Calibração da base (espaço = imprimir, q = sair)", frame)
        tecla = cv2.waitKey(1) & 0xFF
        if tecla == ord(" "):
            print([(round(r, 3), round(c, 3)) for r, c, _ in candidatos[:4]])
        elif tecla == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())