"""Measure raw delivered camera FPS without saving video or running inference."""
import argparse
import time
import cv2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera",type=int,default=0)
    parser.add_argument("--seconds",type=float,default=4)
    args = parser.parse_args()
    for width, height in ((1280,720),(640,480)):
        cap = cv2.VideoCapture(args.camera,cv2.CAP_DSHOW)
        try:
            if not cap.isOpened():
                raise RuntimeError("Camera cannot open")
            cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*"MJPG"))
            cap.set(cv2.CAP_PROP_FRAME_WIDTH,width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT,height)
            cap.set(cv2.CAP_PROP_FPS,30)
            for _ in range(5):
                cap.read()
            start, count = time.monotonic(), 0
            while time.monotonic()-start < args.seconds:
                ok, _ = cap.read()
                if not ok:
                    raise RuntimeError("Camera read failed")
                count += 1
            elapsed = time.monotonic()-start
            print(f"Requested {width}x{height}/30 FPS; delivered "
                  f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))} "
                  f"at {count/elapsed:.1f} measured FPS ({count} frames/{elapsed:.2f}s)",flush=True)
        finally:
            cap.release()


if __name__ == "__main__":
    main()
