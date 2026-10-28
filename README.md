# MemeCam

MemeCam is a Windows desktop webcam effects studio. Hand gestures and calibrated facial expressions trigger your images; face landmarks keep them aligned to your face or eyes. Video processing uses local MediaPipe Tasks models. OBS supplies the virtual camera.

```text
Physical webcam → MemeCam Output → OBS Window Capture
                                      ↓
                              OBS Virtual Camera → Teams / Discord / Zoom / Meet
```

## Requirements and installation

Windows 10/11 x64, Python **3.11 or 3.12** x64, a physical webcam, and OBS Studio for virtual-camera output. Python 3.13+ is excluded because the pinned MediaPipe wheel does not support it. Use a writable source checkout; configuration and assets live beside the source. Packaging is intentionally deferred.

Run PowerShell in the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe scripts\create_assets.py
.\.venv\Scripts\python.exe scripts\setup_models.py
.\.venv\Scripts\python.exe -m memecam
```

Installation and the one-time model download need internet. Subsequent launches use local files. The model downloader uses versioned official Google URLs and verifies SHA256 against `assets/models/manifest.json`. Keep that manifest with the project. No camera images are saved or uploaded by MemeCam.

The dependency deliberately pins MediaPipe **0.10.21** while using its Tasks API. During development, the 0.10.35 Windows wheel attempted Clearcut metric uploads; 0.10.21 avoids that observed behavior. Do not upgrade the pin without reviewing runtime network behavior. See the [upstream telemetry report](https://github.com/google-ai-edge/mediapipe/issues/6291) and official [Hand Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python) / [Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python) APIs. The application does not implement a virtual-camera driver, server, cloud API, or recording feature.

For the exact tested Windows/Python 3.12 dependency set, install `requirements-lock.txt` before `pip install -e ".[dev]"`. Only the contrib OpenCV distribution is used; it supplies the normal OpenCV APIs too.

This checkout has an installed `.venv` and downloaded models. Start it with:

On Windows, double-click **MemeCam** on the desktop or `MemeCam.lnk` in this folder to open the app without a console. Keep the project folder and its `.venv` in place. To recreate the desktop shortcut after moving the project, run `powershell -ExecutionPolicy Bypass -File .\scripts\create_shortcut.ps1` from the new location.

```powershell
.\launch.ps1
# If script execution policy prevents running .ps1:
.\.venv\Scripts\python.exe -m memecam
```

## Camera and controls

Open **Settings** in the right panel to select a webcam, resolution, and requested FPS, then click **Start Camera** in the header. The **Gestures** tab shows the hand gesture guide; recognition details and output options are grouped under **Settings**. The default is 1280×720 at 30 FPS. Devices can negotiate a different format; the footer displays actual frame dimensions and measured processing FPS. Stop before changing cameras or resolution. Refresh discovers newly connected cameras. Capture tries DirectShow first, then Media Foundation.

Hand detection, face tracking, mirroring, and preview debug can be changed live. Debug draws hand connections, face landmark points, candidate, confirmation progress, last confirmed gesture, and measured FPS. The Settings detection section shows the candidate and progress even when debug is off. With both detectors disabled, camera and manual library triggers still work.

| Gesture | Action |
| --- | --- |
| Peace: index/middle straight, ring/pinky folded | Toggle persistent eye-tracked glasses |
| Thumbs up, other fingers folded | Approved for 2 seconds |
| Thumbs down, other fingers folded | Rejected for 2 seconds |
| Open palm, fingers and thumb extended | BRUH reaction for 2 seconds |
| Fist, all fingers folded | Clear all active overlays |

Hold a gesture for 350 ms. A confirmed gesture latches: holding it does not repeatedly trigger. The gesture must disappear or change for at least 250 ms to rearm, and all triggers have an 800 ms global cooldown. Keep one hand fully visible, approximately facing the camera, with good lighting. Sideways thumbs and ambiguous finger configurations are deliberately rejected. Classification uses metric hand-world joint geometry; thumb direction is intentionally relative to the upright camera image. The MVP tracks one hand and one face.

Settings persist in `config/settings.json` on changes, camera start, and close. Missing settings use defaults; invalid settings produce a visible warning and fall back to defaults. `config/settings.example.json` documents all supported fields. Stop and close the app before editing advanced settings:

| Setting | Purpose |
| --- | --- |
| `confirmation`, `release`, `cooldown` | Gesture timing in seconds |
| `smoothing` | Exponential interpolation weight; lower is smoother but follows more slowly |
| `face_hold` | Hold last face pose briefly, then hide attached overlays (default 0.2 s) |
| `detection_width` | Inference input width (default 640); output retains camera resolution |

## Overlay library

Four original transparent placeholder PNGs are included in `assets/overlays/`. The asset generator only creates missing built-ins, so it never replaces your edits.

Click **+ Add effect**, select a PNG, JPG or WebP image, set a name, tracking mode (`screen`, `face`, `eyes`), and duration. New imports default to face tracking. Zero duration means persistent. The file is converted to an RGBA PNG in the library with a unique ID, shown with a thumbnail, and retained across launches. Existing transparency is preserved; opaque images remain opaque. Click its library tile to trigger or toggle it independently of gesture recognition; **Clear all** removes all overlays. Very large images should be resized before import (8192-pixel maximum per dimension).

Metadata is in `config/overlays.json`. Supported properties are `id`, `name`, `file`, `type`, `anchor`, `duration`, `scale`, `offset_x`, `offset_y`, `rotation_mode`, and `tracking_mode`. Anchors are `top`, `center`, `bottom` for screen effects. Screen scale is a fraction of frame width; eyes scale multiplies eye distance; face scale multiplies face width. Offsets are fractions of frame width/height. `rotation_mode: face` follows head tilt; `none` stays upright. Tracking centers take precedence over screen anchors for attached effects. PNG is the only current renderer; the metadata type and compositor boundary allow future animation decoders.

Hand gesture behavior lives in `config/gestures.json`; replace an overlay ID there to assign your PNG to a hand gesture, then restart. Allowed actions: `toggle_overlay`, `show_overlay`, `clear_overlays`. Unknown hand gestures, actions, IDs, duplicate overlay IDs, unsafe paths, and invalid metadata fail startup with a clear error. Fix that file and relaunch. A hand mapping editor and GIF/video/audio effects are future work.

## Facial expression setup

Start the camera, enable **Face tracking**, and click **Configure facial gestures ↗** below the right panel. The separate, resizable window shares the running camera; it does not open another capture device. The tracking tab shows a live face mesh even when preview debug is off. The result tab shows your composited output. Setup lines never enter the OBS output.

1. Import your image using **+ Add effect** in the main window. Main-window controls and library tiles remain available while setup is open.
2. Choose **+ Nuevo gesto** and enter a name, such as smile, wink, raised eyebrows, or open mouth.
3. Relax your face and click **Capturar neutral**; hold still for one second. Make your expression, click **Capturar gesto**, and hold it for one second. Each capture uses the median of at least five live samples. Face loss cancels a capture.
4. Watch the facial parameters and match meter as you repeat the expression. Lower **Umbral de activación** for greater sensitivity; raise it to require a stronger expression. The meter previews the selected unsaved template; automatic recognition uses saved values.
5. Choose **Imagen vinculada**, then adjust face/eye/screen tracking, size, X/Y position, duration, and head rotation. **Aplicar posición y probar imagen** saves that image's placement and triggers it manually; view the result in the result tab. Placement changes apply everywhere that image is used.
6. Click **Guardar gesto y vincular imagen**, then close setup to resume automatic triggers. Both hand and facial automatic effects are paused while setup is open; manual clicks remain enabled. Expressions use the same hold, release and cooldown settings as hand gestures, with independent timing. A held expression fires once; temporary effects expire and persistent effects remain until cleared or toggled manually.

Saved expressions can be selected, renamed, disabled, remapped, recalibrated or deleted in this window without restarting. Rules live in `config/facial_gestures.json`, created on the first save. Invalid rules produce a startup warning and disable facial rules until repaired or replaced through setup. Rules contain numeric blendshape samples and image IDs; no photos or video are stored. This feature tracks facial movement for effects rather than identifying people.

Expression matching uses up to six of the strongest changes from neutral among MediaPipe's [facial blendshape scores](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python). All selected features must reach the configured proportion of the captured expression. Expressions too similar to neutral are rejected. Use distinct expressions, recalibrate for your camera and lighting, and test recognition in person; automated fixtures do not establish human recognition accuracy. Manual face-attached images still require a visible tracked face to position them, although they do not require any expression to be detected.

## OBS → Virtual Camera → Teams

1. Launch MemeCam.
2. Select your physical webcam.
3. Start camera.
4. Open **Output Window**. Its stable window title is **MemeCam Output**.
5. Open OBS Studio.
6. Add a **Window Capture** source to a scene.
7. Select **MemeCam Output**, use the Windows capture method available for that window, and disable **Capture Cursor**. Enable **Client Area** if offered so the OS title bar is excluded. Do not select the control window.
8. Fit the source to your canvas. A 1280×720 canvas at 30 FPS is a useful starting point. Click **Start Virtual Camera** in OBS.
9. Open Teams.
10. Select **OBS Virtual Camera** in Teams device/video settings. Discord, Zoom, and Google Meet can select the same camera.

The output surface contains only video and black letterboxing, preserves the source aspect ratio at any window size, and has no controls or status text in its pixels. **Borderless** removes OS window decorations; **Fullscreen** fills the screen. Escape exits fullscreen/borderless. The main controls stay available separately. Leave the output open and avoid minimizing it while OBS captures it. Default output is clean even when preview debug is enabled; **Include debug in output** is a separate explicit opt-in and starts off on each launch. Stop/failed camera clears both surfaces to prevent frozen private frames being left on screen.

If OBS is black, first make the output window visible, try the alternate Window Capture method, confirm the correct window, and match OBS/MemeCam privilege levels. Restart the conferencing app after starting OBS Virtual Camera if the device is missing. Camera selection and virtual-camera menus vary with application versions.

## Architecture

```text
Capture thread                Processing QThread                  Qt GUI thread
OpenCV device ──latest slot──→ MediaPipe hand + face ──latest slot─→ 16 ms poll
  drops old frames               ↓                                  ├─ Preview + debug
                              classifier                            └─ Clean Output
                                 ↓
                         confirmation / debounce
                                 ↓
                        configured gesture action
                                 ↓
                         overlay engine / RGBA
```

Camera discovery also runs off the GUI thread. Neither captured frames nor rendered frames build an unbounded event queue. UI commands are delivered to the processing worker, which alone owns its detectors and overlay state. Eye position, scale, center, and wrapped head angle are smoothed; short face loss holds the last pose, then attached effects hide until reacquisition. Model initialization and camera failures are shown in the control window. Stop/exit requests cooperative cleanup; camera and native model resources close in their owning threads. A driver that hangs beyond shutdown timeout blocks reopening until restart instead of racing a second device handle.

Modules: `camera/` capture/pipeline, `vision/` landmarks/classification/smoothing, `gestures/` temporal state and dispatch, `overlays/` models/assets/compositing, `config/` validation/persistence, `ui/` controls/output/video painting. There are no animation or sound implementations yet.

## Development and verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=.tmp\pytest
.\.venv\Scripts\python.exe -m ruff check memecam scripts tests
.\.venv\Scripts\python.exe -m compileall -q memecam scripts
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe scripts\verify_vision.py
.\.venv\Scripts\python.exe -m memecam --demo --smoke-test
.\.venv\Scripts\python.exe -m memecam --smoke-test
# Physical camera attempt; auto-exits for diagnostics:
.\.venv\Scripts\python.exe -m memecam --start-camera --quit-after 20
# Interactive synthetic preview without camera:
.\.venv\Scripts\python.exe -m memecam --demo
```

Tests cover timing, hold/release, cooldown, synthetic joint fixtures, smoothing and angle wrapping, lifetime/toggle/clear, RGBA clipping, hidden lost-face effects, configuration validation and roundtrips, custom PNG imports, threaded processing with a fake camera, shutdown/error recovery, single-slot delivery, and clean output ownership. Real model loading/inference is a separate explicit check so unit tests need no model downloads. See `docs/MANUAL_TESTS.md` for physical/OBS acceptance checks and `docs/VALIDATION.md` for results on this machine.

## Troubleshooting

- **Camera cannot open:** close apps using the physical webcam, verify Windows Settings → Privacy & security → Camera → access for desktop apps, reconnect the device, refresh, and retry. OBS should capture MemeCam's window, rather than opening that same webcam again.
- **Camera disconnects:** the app shows an error and clears video. Reconnect, refresh, select, and start again. If the driver itself stops responding, restart MemeCam.
- **Missing models:** run `scripts/setup_models.py` once online. Model files are not committed. Keep the manifest so subsequent downloads can verify exact hashes.
- **Import/DLL errors:** use `.venv\Scripts\python.exe`, Python 3.11/3.12 x64, and a fresh environment. Install the Microsoft Visual C++ x64 runtime if Windows reports missing runtime DLLs. Do not install another OpenCV distribution alongside `opencv-contrib-python`; they share the `cv2` namespace.
- **Slow video:** choose 640×480, disable one detector, reduce inference width, and use a well-lit view. Measured FPS includes inference and composition; processing milliseconds exclude USB sensor and OBS/conferencing buffering. No 30 FPS claim is made without physical measurement.
- **Gesture missed:** inspect debug landmarks, keep all fingers visible, hold longer than the configured confirmation period, and release between actions. Face glasses need face tracking enabled and visible eyes.
- **Unexpected errors:** check rotating `logs/memecam.log`. It records transitions rather than every frame. MediaPipe can print native informational/warning messages on stderr. Logs and settings are local and video is not recorded.
