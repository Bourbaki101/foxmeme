# Validation on 2026-10-26

Environment: Windows x64, bundled CPython 3.12.14, MediaPipe Tasks 0.10.21, OpenCV contrib 4.11.0.86, NumPy 1.26.4, PySide6 6.12.0. Full installed versions are in `requirements-lock.txt` (the lock records this Windows/Python 3.12 environment; use `pyproject.toml` for other supported environments).

## Commands and observed results

Executed from `C:\Tools\FoxMeme`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest
.\.venv\Scripts\python.exe -m ruff check memecam scripts tests
.\.venv\Scripts\python.exe -m compileall -q memecam scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_vision.py
.\.venv\Scripts\python.exe -m memecam --demo --smoke-test --screenshot artifacts\memecam-ui.png
.\.venv\Scripts\python.exe -m memecam --start-camera --quit-after 25
.\.venv\Scripts\python.exe scripts\benchmark_camera.py --seconds 4
```

- Automated tests: **50 passed**, including a final layout regression check at normal and minimum window sizes. Two protobuf deprecation warnings concern unsupported future Python 3.14; this project supports 3.11/3.12.
- Ruff: passed. Python byte-compilation: passed. Dependency check: no broken requirements.
- Actual local hand and face models: loaded, blank-frame inference completed, and resources closed successfully. Native MediaPipe initialization emits feedback-tensor and normalized-ROI warnings; they do not prevent inference.
- Synthetic UI startup: control and output windows opened, rendered, and closed without error. UI screenshot inspected for preview proportions, text clipping, thumbnails, controls, and dark styling.
- Physical discovery: **USB2.0 HD UVC WebCam**, index 0.
- Physical runtime outside the execution sandbox: webcam opened at **1280×720**, both detectors initialized, **169 frames** processed, and camera/model resources released on timed exit. Logged sample: **9.5 FPS**, **31 ms processing** at frame 30. This is a short run, not a sustained or worst-case benchmark.
- Raw webcam benchmark without inference: **10.0 FPS at 1280×720** (40 frames/4.00 s), **15.0 FPS at 640×480** (60 frames/4.00 s), despite requesting 30 FPS. The camera/driver/environment limits measured throughput here. Frames were processed locally and not recorded.
- The first sandboxed camera attempt could enumerate but not open the physical device; outside-sandbox verification succeeded. Both failure handling and normal shutdown were observed.
- During dependency investigation, the initial MediaPipe 0.10.35 wheel emitted Clearcut network errors. It was replaced by pinned 0.10.21; subsequent runs did not emit those errors. This is an observed behavior check, not a packet-capture audit.

## Remaining hands-on checks

No claim is made that human gesture accuracy, face attachment under natural motion, long-session stability, or OBS Virtual Camera → Teams has been manually accepted. Those require the user performing the checklist in `MANUAL_TESTS.md`. Automated synthetic classification, smoothing/composition, real model inference, and the physical camera pipeline have been exercised separately. The application is implemented and runs, but complete meeting-workflow acceptance still needs that hands-on pass.

The MVP uses original placeholder images, supports RGBA PNG only, and tracks one face/one hand. A frozen Windows installer, animated assets, audio, mapping editor, and virtual-camera driver are outside its current scope.
