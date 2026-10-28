"""Generate original transparent MVP assets; never overwrite user replacements."""
from pathlib import Path
import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "assets/overlays"
    directory.mkdir(parents=True, exist_ok=True)
    glasses = np.zeros((100,400,4), np.uint8)
    for x in (10, 220):
        cv2.rectangle(glasses, (x,20), (x+165,75), (12,12,12,255), -1)
        for dx in (25,50):
            cv2.line(glasses, (x+dx,28), (x+dx-18,53), (240,240,240,255), 9)
    cv2.rectangle(glasses, (170,25), (230,40), (12,12,12,255), -1)
    cv2.rectangle(glasses, (0,15), (399,30), (12,12,12,255), -1)
    images = {"deal_glasses": glasses}
    for key, text, color in (("approved","APPROVED",(136,238,166,255)),
                             ("rejected","REJECTED",(126,120,255,255)),
                             ("reaction","BRUH.",(120,220,255,255))):
        image = np.zeros((160,700,4), np.uint8)
        cv2.rectangle(image, (8,8), (692,152), (20,24,31,230), -1)
        cv2.rectangle(image, (8,8), (692,152), color, 5)
        scale = 2.4
        (width, height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 5)
        cv2.putText(image, text, ((700-width)//2,(160+height)//2), cv2.FONT_HERSHEY_DUPLEX,
                    scale, color, 5, cv2.LINE_AA)
        images[key] = image
    for name, image in images.items():
        path = directory / (name + ".png")
        if not path.exists():
            path.write_bytes(cv2.imencode(".png", image)[1].tobytes())
            print(f"Created {path}")


if __name__ == "__main__":
    main()
